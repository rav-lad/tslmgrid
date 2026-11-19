"""Prompt, series, label and answer of one window-review sample.

The analyst's question: does the load of this day show a gap worth investigating? The model sees what
the analyst knows on the day:

* the text: the date and its calendar (``review.context.Context.describe``), the daily mean
  temperature and its normal, the reference's comparable days, and what the day 52 weeks earlier was;
* four series of 24 local hours:
  1. the reference (``ReferenceBuilder.recent_normal``): recent ordinary days of the same weekday
     type at a comparable temperature, in MW, its mean and std in the text;
  2. the observed load, on the scale of the reference: normalized with the reference's mean and std,
     so the level gap is in the values and not in the text;
  3. the same weekday 52 weeks earlier, on the scale of the reference;
  4. the hourly temperature, in °C.

It never sees the z-score, the daily gap or the label.

The label (yes = investigate), by rules, with its provenance:

* ``construction``: a perturbation was added to the day (``inject``): yes, whatever the day.
* ``rule``, on a real day: the day shows a gap when its level against the reference reaches 7 %
  (``LEVEL_PCT``) or a run of at least 3 hours departs from its median hour by 15 % (``RUN_PCT``).
  Below that, the solar output of sunny and cloudy days and the weather already move ordinary days:
  over 2021-2026, 83 ordinary days of the regular period reach 5 % and 191 have 3 hours at 8 %, but 22
  reach 7 % and 4 have 3 hours at 15 %. A gap is explained, and the answer is no, when
  - the calendar explains a lower day: a public holiday (at least 20 % of the population), a bridge
    day, the Christmas or summer holidays or the lockdown, and the level is below the reference; or
  - the temperature explains it: a day at least 5 °C colder than normal with a higher load, or 5 °C
    warmer with a lower load (``TEMP_ANOMALY_C``).
  Any other gap is unexplained: yes. No gap: no.

A real day labelled no is not an annotated incident-free day: a real problem is not excluded.
"""

import re

import numpy as np

from swissgrid_cot.explain.samples import LOCAL_GAP, LOCAL_RUN_HOURS
from swissgrid_cot.review.hourly import format_windows, hour_windows

LEVEL_PCT = 7.0
RUN_PCT = 15.0
TEMP_ANOMALY_C = 5.0
SPECIAL_KINDS = ("full_holiday", "partial_holiday", "bridge_day", "lockdown")
SERIES = (
    ("Reference", "reference_mw", "MW", None),
    ("Observed load", "load_mw", "MW", "Reference"),
    ("Same weekday 52 weeks earlier", "last_year_mw", "MW", "Reference"),
    ("Temperature", "temp_c", "°C", None),
)
POST_PROMPT = "Analysis:"


def pre_prompt(context_text: str, temp_c: float, temp_normal_c: float, n_ref: int, last_year_text: str) -> str:
    return (
        "You are given the electricity consumption of Switzerland over the 24 local hours of one day, as an "
        "analyst sees it on that day.\n\n"
        f"Day: {context_text}. Daily mean temperature {temp_c:.1f} °C (normal {temp_normal_c:.1f} °C).\n"
        f"Reference: the median of {n_ref} recent ordinary days of the same weekday type at a comparable "
        f"temperature. The same weekday 52 weeks earlier was {last_year_text}.\n\n"
        "Your task is to tell whether the load shows a gap worth investigating.\n\n"
        "Instructions:\n"
        "- Compare the observed load with the reference: over the day, and hour by hour.\n"
        "- Say which hours depart from the rest of the day, if any.\n"
        "- Say whether the calendar or the temperature explains the gap.\n"
        "- End with 'Answer: yes' (investigate) or 'Answer: no'."
    )


def calendar_reason(kind: str, period: str) -> str | None:
    """What in the calendar explains a lower day, or None."""
    if kind == "lockdown":
        return "the lockdown"
    if kind in ("full_holiday", "partial_holiday"):
        return "the public holiday"
    if kind == "bridge_day":
        return "the bridge day"
    if period == "christmas":
        return "the Christmas holidays"
    if period == "summer":
        return "the summer holidays"
    return None


def strong_runs(load: np.ndarray, reference: np.ndarray) -> list[int]:
    """The hours of the runs of at least 3 hours that depart from the median hour by ``RUN_PCT`` on one side."""
    e = load / reference - 1
    loc = e - float(np.median(e))
    out = []
    for side in (1, -1):
        hit = [h for h in range(len(e)) if side * loc[h] >= RUN_PCT / 100]
        out += [h for a, b in hour_windows(hit) if b - a + 1 >= LOCAL_RUN_HOURS for h in range(a, b + 1)]
    return sorted(out)


def has_gap(ev: dict, runs: list[int]) -> bool:
    return abs(ev["level_pct"]) >= LEVEL_PCT or bool(runs)


def explanation(ev: dict, kind: str, period: str, temp_c: float, temp_normal_c: float) -> str | None:
    """Why a real day's gap is expected, or None when nothing explains it."""
    reason = calendar_reason(kind, period)
    if reason and ev["level_pct"] < 0:
        return f"{reason[0].upper()}{reason[1:]} explains a lower day."
    anomaly = temp_c - temp_normal_c
    if anomaly <= -TEMP_ANOMALY_C and ev["level_pct"] > 0:
        return f"A day {-anomaly:.1f} °C colder than normal explains a higher load."
    if anomaly >= TEMP_ANOMALY_C and ev["level_pct"] < 0:
        return f"A day {anomaly:.1f} °C warmer than normal explains a lower load."
    return None


def label(ev: dict, runs: list[int], kind: str, period: str, temp_c: float, temp_normal_c: float,
          injected: dict | None) -> dict:
    """{"investigate": bool, "by": "construction" | "rule", "why": text}."""
    if injected:
        return {"investigate": True, "by": "construction", "why": None}
    if not has_gap(ev, runs):
        return {"investigate": False, "by": "rule",
                "why": f"The gap stays within {LEVEL_PCT:.0f}% over the day and {RUN_PCT:.0f}% over any {LOCAL_RUN_HOURS} "
                       "hours: the load follows the reference."}  # fmt: skip
    why = explanation(ev, kind, period, temp_c, temp_normal_c)
    return {"investigate": why is None, "by": "rule", "why": why}


def answer(ev: dict, target: dict, injected: dict | None, load: np.ndarray, reference: np.ndarray) -> str:
    parts = [f"Against the reference, the load runs {ev['level_pct']:+.1f}% over the day."]
    sides = [f"{s['pct']:+.1f}% over {format_windows(s['hours'])}" for s in ev["local"].values() if s["hours"]]
    if sides:
        parts.append(f"Against its median hour, the load is {' and '.join(sides)}.")
    else:
        parts.append(f"No run of {LOCAL_RUN_HOURS} or more hours departs from its median hour by "
                     f"{100 * LOCAL_GAP:.0f}% or more.")  # fmt: skip
    if injected:
        hours = list(range(injected["start"], injected["end"] + 1))
        e = load / reference - 1
        rest = [h for h in range(len(e)) if h not in hours]
        gap = 100 * (float(np.mean(e[hours])) - float(np.median(e[rest])))
        parts.append(f"Over {format_windows(hours)} the load departs by {gap:+.1f}% from the rest of the day; "
                     "neither the calendar nor the temperature explains a change confined to those hours.")  # fmt: skip
    elif target["investigate"]:
        parts.append("Neither the calendar nor the temperature explains this gap.")
    else:
        parts.append(target["why"])
    parts.append(f"Answer: {'yes' if target['investigate'] else 'no'}")
    return " ".join(parts)


ANSWER = re.compile(r"Answer:\s*(yes|no)\b")


def parse_answer(text: str) -> bool | None:
    """True for yes, False for no (the last 'Answer:'), None when there is none."""
    found = ANSWER.findall(text)
    return None if not found else found[-1] == "yes"
