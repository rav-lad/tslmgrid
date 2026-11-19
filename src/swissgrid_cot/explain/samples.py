"""Prompt, rationale and answer of one day-signature sample.

The question has the form of OpenTSLM's activity, sleep and ECG tasks: a few series, a prompt that
does not hold the answer, a closed list of labels, a rationale, then the label. The prompt names the
weekday and nothing else about the day: no date, month, temperature, holiday or daily z-score. The
label is the day's calendar context (``labels``), which the model never sees, so only the curve can
give it.

Series (24 local hours, 00:00 to 23:00 Swiss time):

* the observed load;
* the ordinary-day reference (``ReferenceBuilder.blind_normal``): earlier ordinary days of the same
  weekday type, time of year and temperature, built the same way whatever the day's calendar;
* the typical Sunday profile of the previous 8 weeks, scaled to the day's mean load.

The rationale states what the rules measure on those curves, with e(h) = load(h) / reference(h) - 1:
the day-level gap (mean of e), the gap per part of the day, the closest typical profile, and the hours
whose gap departs from the day-level gap. Then the label's signature, then the answer::

    Answer: public_holiday
"""

import re

import numpy as np

from swissgrid_cot.explain.labels import LABELS, SIGNATURE
from swissgrid_cot.review.assess import profile_match
from swissgrid_cot.review.hourly import DAYPARTS, HOURS, daypart, format_windows, hour_windows

SERIES = (
    ("Observed load", "load_mw"),
    ("Ordinary-day reference", "reference_mw"),
    ("Typical Sunday profile", "sunday_mw"),
)
LOCAL_GAP = 0.08
"""An hour departs from the median hour when |e(h) - median e| reaches 8 % (below that, the solar output of
sunny and cloudy days already moves a few hours of an ordinary day since 2024) ..."""
LOCAL_RUN_HOURS = 3
"""... in a run of at least 3 consecutive hours on the same side."""
CONFINED_HOURS = 8
"""At most 8 such hours: the gap is confined to them. More: the gap reshapes the day."""
UNEXPLAINED_LEVEL_PCT = 5.0
UNEXPLAINED = ("No calendar signature matches the gap, so the calendar does not explain it; the weather, an event "
               "or the reference itself are left to check.")  # fmt: skip
"""The rationale of an ordinary day whose gap is large or confined, in place of its signature."""
POST_PROMPT = "Rationale:"


def pre_prompt(weekday: str) -> str:
    return (
        f"You are given the electricity consumption of Switzerland on a {weekday}: the 24 local hours of the "
        "observed load, an ordinary-day reference (earlier ordinary days of the same weekday type, time of year "
        "and temperature), and the typical Sunday profile of the previous weeks scaled to the day's mean load. "
        "Your task is to tell why the day deviates from an ordinary day, from the series alone.\n\n"
        "Instructions:\n"
        "- Compare the observed load with the reference: the level over the day and in each part of the day.\n"
        "- Compare its shape with the reference and with the Sunday profile.\n"
        "- Say whether the gap spans the day or stays in a few hours.\n"
        "- Write your rationale as a single paragraph, then end with 'Answer: <label>'.\n\n"
        f"Possible labels: {', '.join(LABELS)}."
    )


def evidence(load: np.ndarray, reference: np.ndarray, profiles: dict[str, np.ndarray | None]) -> dict:
    """What the rules measure on the curves; the rationale states it."""
    e = load / reference - 1
    level = float(e.mean())
    by_part = {p: float(np.mean([e[h] for h in range(HOURS) if daypart(h) == p])) for p in DAYPARTS}
    profile, tie, dist = profile_match(load, profiles)
    loc = e - float(np.median(e))
    local = {}
    for name, side in (("above", 1), ("below", -1)):
        hit = [h for h in range(HOURS) if side * loc[h] >= LOCAL_GAP]
        hours = [h for a, b in hour_windows(hit) if b - a + 1 >= LOCAL_RUN_HOURS for h in range(a, b + 1)]
        local[name] = {"hours": hours, "pct": round(100 * float(loc[hours].mean()), 1) if hours else None}
    n_local = len(local["above"]["hours"]) + len(local["below"]["hours"])
    return {
        "level_pct": round(100 * level, 1),
        "daypart_pct": {p: round(100 * v, 1) for p, v in by_part.items()},
        "profile": profile,
        "profile_tie": tie,
        "profile_distances": {k: (None if v is None else round(v, 3)) for k, v in dist.items()},
        "local": local,
        "confined": 0 < n_local <= CONFINED_HOURS,
    }


def rationale(weekday: str, ev: dict, label: str) -> str:
    p = ev["daypart_pct"]
    parts = [
        f"Against an ordinary {weekday} of the same time of year and temperature, the load runs "
        f"{ev['level_pct']:+.1f}% over the day: {p['night']:+.1f}% at night, {p['morning']:+.1f}% in the morning, "
        f"{p['afternoon']:+.1f}% in the afternoon and {p['evening']:+.1f}% in the evening."
    ]
    dist = ev["profile_distances"]
    others = ", ".join(f"{dist[k]:.3f} for {k}" for k in ("weekday", "saturday", "sunday") if k != ev["profile"])
    lead = "nearly tied, but closest" if ev["profile_tie"] else "closest"
    parts.append(f"Its shape is {lead} to a typical {ev['profile']} (shape distance {dist[ev['profile']]:.3f}, "
                 f"against {others}).")  # fmt: skip
    sides = [f"{s['pct']:+.1f}% over {format_windows(s['hours'])}" for s in ev["local"].values() if s["hours"]]
    if not sides:
        parts.append(f"No run of {LOCAL_RUN_HOURS} or more hours departs from the median hour by "
                     f"{100 * LOCAL_GAP:.0f}% or more: the gap spans the day.")  # fmt: skip
    elif ev["confined"]:
        parts.append(f"Against its median hour, the load is {' and '.join(sides)}; the rest of the day follows it.")
    else:
        parts.append(f"The gap reshapes the day: against its median hour, the load is {' and '.join(sides)}.")
    if label == "ordinary" and (abs(ev["level_pct"]) >= UNEXPLAINED_LEVEL_PCT or ev["confined"]):
        parts.append(UNEXPLAINED)
    else:
        parts.append(SIGNATURE[label])
    parts.append(f"Answer: {label}")
    return " ".join(parts)


ANSWER = re.compile(r"Answer:\s*([a-z_]+)")


def parse_answer(text: str) -> str | None:
    """The label of the last 'Answer:', or None if there is none or it is not a label."""
    found = ANSWER.findall(text)
    return found[-1] if found and found[-1] in LABELS else None
