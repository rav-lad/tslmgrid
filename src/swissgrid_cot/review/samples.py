"""Prompt, reference rationale and answer format of one alert-review sample.

The question asks for three things that only the curve answers, plus the decision:

1. the typical profile the day's load resembles (weekday, Saturday, Sunday);
2. the part of the day where the deviation from a normal day is concentrated;
3. the outcome after comparison with the context reference, and the hours that still warrant review.

The prompt gives the calendar, the weather, the daily deviation and how the references were built;
it never gives the answers. The final line is machine-readable::

    Answer: profile=sunday; concentrated=morning; outcome=deviation_remains; hours=07-10,18-18
"""

import re

from swissgrid_cot.review.hourly import hour_windows

SERIES = (
    ("Observed load", "load_mw"),
    ("Context reference", "context_reference_mw"),
    ("Normal-day reference", "normal_reference_mw"),
    ("Typical weekday profile", "weekday"),
    ("Typical Saturday profile", "saturday"),
    ("Typical Sunday profile", "sunday"),
)
DAYPART_HOURS = {"night": "00:00-05:59", "morning": "06:00-11:59", "afternoon": "12:00-17:59", "evening": "18:00-23:59"}
POST_PROMPT = (
    "Reason from the series, then end with 'Answer: profile=<weekday|saturday|sunday>; "
    "concentrated=<night|morning|afternoon|evening>; outcome=<consistent|deviation_remains|insufficient_evidence>; "
    "hours=<HH-HH,...|none>'."
)


def hours_code(hours: list[int]) -> str:
    """'07-10,18-18' (first and last hour of each run, both included), or 'none'."""
    return ",".join(f"{a:02d}-{b:02d}" for a, b in hour_windows(hours)) if hours else "none"


def parse_hours(code: str) -> set[int]:
    out: set[int] = set()
    for a, b in re.findall(r"(\d{1,2})\s*-\s*(\d{1,2})", code):
        a_, b_ = int(a), int(b)
        if 0 <= a_ <= b_ <= 23:
            out.update(range(a_, b_ + 1))
    return out


ANSWER = re.compile(
    r"profile\s*=\s*(?P<profile>[a-z_]+)\s*;\s*concentrated\s*=\s*(?P<concentrated>[a-z_]+)\s*;\s*"
    r"outcome\s*=\s*(?P<outcome>[a-z_]+)\s*;\s*hours\s*=\s*(?P<hours>[0-9,\- ]+|none)"
)
DAY_RESIDUAL = re.compile(r"day-level residual is ([+-]?\d+(?:\.\d+)?)%")


def parse_answer(text: str) -> dict | None:
    """The fields of the last 'Answer:' line, or None if it does not parse."""
    cut = text.rfind("Answer:")
    if cut < 0:
        return None
    m = ANSWER.search(text[cut:])
    if not m:
        return None
    out = m.groupdict()
    out["hours"] = sorted(parse_hours(out["hours"])) if out["hours"].strip() != "none" else []
    d = DAY_RESIDUAL.findall(text[:cut])
    out["day_residual_pct"] = float(d[-1]) if d else None
    return out


def _pct(x: float) -> str:
    return f"{x:+.1f}%"


def pre_prompt(row: dict) -> str:
    c, v = row["context"], row["review"]
    lines = [
        f"Demand alert review for Switzerland, {c['description']}.",
        f"The daily detector flagged the day: mean end-user load {c['load_mw']:.0f} MW, {_pct(c['rel_dev_pct'])} "
        f"against the daily baseline (weekday type, month, weather, trend), z = {c['z']:+.2f}. Daily mean "
        f"temperature {c['temp_c']:.1f} °C, normal for the date {c['temp_normal_c']:.1f} °C. The ordinary days of "
        f"the previous 4 weeks ran {_pct(v['recent_level_pct'])} against the baseline.",
    ]
    if row["context_reference_mw"] is not None and v["outcome"] != "insufficient_evidence":
        lines.append(f"Context reference: {v['comparison']}; {v['n_comparable']} comparable earlier days.")
    else:
        lines.append(f"Context reference: {v['comparison']}; only {v['n_comparable']} comparable earlier days, "
                     f"{v['needed']} needed, so no context reference is given.")  # fmt: skip
    lines.append(
        "The series are the 24 local hours (00:00 to 23:00 Swiss time) of the observed load, the context reference, "
        "a normal day of the same weekday type, season and weather, and the typical weekday, Saturday and Sunday "
        "profiles of the previous 8 weeks scaled to the day's mean load.")
    lines.append(
        "Which typical profile does the observed load resemble most? In which part of the day is its deviation "
        "from the normal day concentrated? Is the alert consistent with the available context, does a deviation "
        "remain (and in which hours), or is the evidence insufficient?")
    return " ".join(lines)


def series(row: dict) -> list[dict]:
    out = []
    for name, key in SERIES:
        values = row["profiles_mw"].get(key) if key in row["profiles_mw"] else row.get(key)
        if key == "context_reference_mw" and row["review"]["outcome"] == "insufficient_evidence":
            values = None
        if values is not None:
            out.append({"name": name, "unit": "MW", "values": values})
    return out


def rationale(row: dict) -> str:
    c, v = row["context"], row["review"]
    parts = []
    dist = v["profile_distances"]
    if v["profile"] is None:
        parts.append("Too few ordinary days in the previous 8 weeks give a typical profile.")
    else:
        others = ", ".join(f"{dist[k]:.3f} for {k}" for k in ("weekday", "saturday", "sunday") if k != v["profile"])
        lead = "nearly tied, but closest" if v["profile_tie"] else "closest"
        parts.append(f"The observed load is {lead} in shape to the typical {v['profile']} profile "
                     f"(shape distance {dist[v['profile']]:.3f}, against {others}).")  # fmt: skip
    if v["concentrated"] is not None:
        parts.append(f"Its deviation from a normal {c['weekday']} at this temperature is concentrated in the "
                     f"{v['concentrated']} ({DAYPART_HOURS[v['concentrated']]}, "
                     f"{100 * v['concentrated_share']:.0f}% of the absolute gap).")  # fmt: skip
    if v["outcome"] == "insufficient_evidence":
        parts.append(f"Only {v['n_comparable']} comparable earlier days exist ({v['comparison']}), "
                     f"{v['needed']} are needed: the evidence is insufficient.")  # fmt: skip
    else:
        parts.append(f"Against the context reference ({v['n_comparable']} comparable earlier days), the day-level "
                     f"residual is {v['day_residual_pct']:+.1f}% (z = {v['day_residual_z']:+.2f}).")  # fmt: skip
        if v["outcome"] == "consistent":
            parts.append("No run of 3 or more hours leaves the hourly tolerance. The alert is consistent with "
                         "the available context.")  # fmt: skip
        else:
            hours = v["review_hours"]
            win = ", ".join(f"{a:02d}:00-{b:02d}:59" for a, b in hour_windows(hours))
            side = "above" if v["review_mwh"] > 0 else "below"
            parts.append(f"The load stays {side} the reference over {win} ({len(hours)} hours, "
                         f"{v['review_mwh']:+,.0f} MWh); the largest hourly gap is "
                         f"{v['peak_residual_pct']:+.1f}% at {v['peak_hour']:02d}:00. A deviation remains.")  # fmt: skip
    prof = v["profile"] or "none"
    conc = v["concentrated"] or "none"
    parts.append(f"Answer: profile={prof}; concentrated={conc}; outcome={v['outcome']}; "
                 f"hours={hours_code(v['review_hours'])}")  # fmt: skip
    return " ".join(parts)


def target(row: dict) -> dict:
    v = row["review"]
    return {
        "profile": v["profile"],
        "profile_tie": v["profile_tie"],
        "concentrated": v["concentrated"],
        "outcome": v["outcome"],
        "hours": v["review_hours"],
        "day_residual_pct": v["day_residual_pct"],
    }
