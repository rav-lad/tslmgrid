import random
import re

import numpy as np

from swissgrid_cot.explain.samples import evidence
from swissgrid_cot.window import samples
from swissgrid_cot.window.export import inject

WEEKDAY = 1 + 0.25 * np.sin(np.linspace(0, 2 * np.pi, 24))
SUNDAY = 1 + 0.08 * np.sin(np.linspace(0, 2 * np.pi, 24) - 1)
PROFILES = {"weekday": WEEKDAY, "saturday": (WEEKDAY + SUNDAY) / 2, "sunday": SUNDAY}
REF = 7000 * WEEKDAY


def case(load, kind="ordinary", period="regular", temp=10.0, normal=10.0, injected=None):
    ev = evidence(load, REF, PROFILES)
    runs = samples.strong_runs(load, REF)
    return ev, runs, samples.label(ev, runs, kind, period, temp, normal, injected)


def test_a_holiday_is_expected_with_its_calendar():
    holiday = 5600 * SUNDAY
    _, _, target = case(holiday, kind="full_holiday")
    assert target == {"investigate": False, "by": "rule", "why": "The public holiday explains a lower day."}
    _, _, target = case(holiday)
    assert target["investigate"] and target["by"] == "rule"


def test_a_perturbation_is_yes_by_construction_even_on_a_holiday():
    _, _, target = case(5600 * SUNDAY, kind="full_holiday", injected={"type": "drop", "start": 9, "end": 12})
    assert target == {"investigate": True, "by": "construction", "why": None}


def test_small_gaps_and_the_temperature_are_no():
    load = REF * 1.04
    load[13:16] *= 0.9
    _, runs, target = case(load)
    assert runs == [] and not target["investigate"]
    _, _, target = case(REF * 1.10, temp=-3.0, normal=4.0)
    assert not target["investigate"] and "colder" in target["why"]
    _, _, target = case(REF * 1.10)
    assert target["investigate"]


def test_a_strong_run_of_three_hours_is_yes():
    load = REF.copy()
    load[14:17] *= 1.2
    _, runs, target = case(load)
    assert runs == [14, 15, 16] and target["investigate"]


def test_injection_bounds_and_amplitude():
    rng = random.Random(1)
    for _ in range(200):
        out, meta = inject(REF, rng)
        changed = np.flatnonzero(~np.isclose(out, REF))
        assert changed.min() == meta["start"] and changed.max() == meta["end"]
        low = 10 if meta["type"] == "level_shift" else 15
        assert low <= abs(meta["delta_pct"]) <= 35


def test_the_answer_ends_with_the_verdict_and_parses():
    load = REF.copy()
    load[9:13] *= 0.8
    meta = {"type": "drop", "start": 9, "end": 12, "delta_pct": -20.0}
    ev, _, target = case(load, injected=meta)
    text = samples.answer(ev, target, meta, load, REF)
    assert "09:00-12:59" in text and text.endswith("Answer: yes")
    assert samples.parse_answer(text) is True
    assert samples.parse_answer("Answer: no") is False
    assert samples.parse_answer("Answer: maybe") is None


def test_the_prompt_never_states_the_gap():
    text = samples.pre_prompt("Thursday 29 May 2025; Ascension, a public holiday for 100.0% of the population",
                              14.2, 15.0, 8, "Thursday 30 May 2024; Ascension, a public holiday")  # fmt: skip
    assert "z =" not in text and "z-score" not in text
    assert re.findall(r"[-+]?\d+(?:\.\d+)?%", text) == ["100.0%"]  # the holiday share only, no gap
