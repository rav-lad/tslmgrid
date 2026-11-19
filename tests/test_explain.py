import re

import numpy as np

from swissgrid_cot.explain.labels import LABELS, SIGNATURE, label_of
from swissgrid_cot.explain.samples import evidence, parse_answer, pre_prompt, rationale

WEEKDAY = 1 + 0.25 * np.sin(np.linspace(0, 2 * np.pi, 24))
SUNDAY = 1 + 0.08 * np.sin(np.linspace(0, 2 * np.pi, 24) - 1)
PROFILES = {"weekday": WEEKDAY, "saturday": (WEEKDAY + SUNDAY) / 2, "sunday": SUNDAY}
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def test_labels_follow_the_cause_order():
    assert label_of("lockdown", "regular") == "lockdown"
    assert label_of("full_holiday", "christmas") == "christmas_period"
    assert label_of("ordinary", "christmas") == "christmas_period"
    assert label_of("partial_holiday", "regular") == "public_holiday"
    assert label_of("full_holiday", "summer") == "public_holiday"
    assert label_of("bridge_day", "regular") == "bridge_day"
    assert label_of("ordinary", "summer") == "summer_holidays"
    assert label_of("ordinary", "regular") == "ordinary"
    assert set(SIGNATURE) == set(LABELS)


def test_the_prompt_holds_no_calendar_fact():
    for day in ("Monday", "Thursday", "Saturday", "Sunday"):
        text = pre_prompt(day)
        assert not re.search(r"\d", text.replace("24 local hours", ""))
        assert not re.search(MONTHS, text)
        assert not re.search(r"holiday|christmas|lockdown|bridge", text.split("Possible labels:")[0], re.IGNORECASE)


def test_a_holiday_shaped_weekday_reads_as_sunday_and_low():
    ref = 7000 * WEEKDAY
    ev = evidence(5600 * SUNDAY, ref, PROFILES)
    assert ev["profile"] == "sunday"
    assert ev["level_pct"] < -10


def test_a_few_hours_step_is_local_and_the_rest_follows():
    ref = 7000 * WEEKDAY
    load = ref.copy()
    load[9:13] *= 1.12
    ev = evidence(load, ref, PROFILES)
    assert ev["local"]["above"]["hours"] == [9, 10, 11, 12] and ev["local"]["below"]["hours"] == []
    assert ev["local"]["above"]["pct"] > 4 and ev["confined"]
    assert ev["profile"] == "weekday"
    assert "the rest of the day follows it" in rationale("Monday", ev, "irregularity")
    assert "No calendar signature" in rationale("Monday", ev, "ordinary")
    flat = evidence(ref.copy(), ref, PROFILES)
    assert flat["local"]["above"]["hours"] == [] and not flat["confined"]
    assert "no calendar effect" in rationale("Monday", flat, "ordinary")


def test_rationale_round_trips_through_the_parser():
    ref = 7000 * WEEKDAY
    ev = evidence(5600 * SUNDAY, ref, PROFILES)
    text = rationale("Thursday", ev, "public_holiday")
    assert text.endswith("Answer: public_holiday")
    assert parse_answer(text) == "public_holiday"
    assert parse_answer("Answer: ordinary. Answer: bridge_day") == "bridge_day"
    assert parse_answer("Answer: weekend") is None
    assert parse_answer("no answer") is None
