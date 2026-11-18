"""Review one flagged day: profile, where the deviation sits, and whether a deviation remains.

For a flagged day D with context reference R (``references``), the hourly residual is

    e(h) = load(h) / R(h) - 1

It splits into a day-level part and a localized part:

    day residual   e_day   = mean_h e(h)
    localized      e_loc(h) = e(h) - e_day

Each is scaled by its spread on the train years (2021-2023, the years with enough history),
measured on the same references (``calibrate``), per context group: ordinary days of the regular
period, ordinary days of a holiday period (Christmas, summer), and holidays and bridge days, whose
references rest on fewer and less similar days.

Outcome:

* insufficient evidence: the context reference has too few comparable earlier days.
* deviation remains: |e_day| >= 3 spreads, or a run of at least 3 consecutive hours with
  |e_loc(h)| >= 3 hourly spreads, of the same sign.
* consistent with available context: otherwise.

Hours under review: the hours of those localized runs, and, when the day-level part triggers, the
hours whose e(h) lies beyond 3 day-level spreads on the same side.

Where the deviation is concentrated: the alert itself is measured against the normal-day reference N
(D's weekday type, season and weather, ignoring the calendar). The daypart (night 00-06, morning
06-12, afternoon 12-18, evening 18-24) holding the largest share of sum_h |load(h) - N(h)| is the
answer.

Profile: the candidate (weekday, Saturday, Sunday) closest in shape. A tie is declared when the
second candidate is within ``PROFILE_TIE_MARGIN`` of the first; ties are left out of the profile
accuracy and counted apart.
"""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from swissgrid_cot.review.context import Context
from swissgrid_cot.review.hourly import DAYPARTS, HOURS, daypart, format_windows, hour_windows, shape
from swissgrid_cot.review.references import PROFILES, Reference

THRESHOLD = 3.0
MIN_RUN_HOURS = 3
PROFILE_TIE_MARGIN = 0.10
OUTCOMES = ("consistent", "deviation_remains", "insufficient_evidence")
OUTCOME_TEXT = {
    "consistent": "consistent with available context",
    "deviation_remains": "deviation remains",
    "insufficient_evidence": "insufficient evidence",
}


@dataclass(frozen=True)
class Calibration:
    """Robust spreads of the residuals on the train years, per context group."""

    day_sd: dict[str, float]
    hour_sd: dict[str, list[float]]
    n_days: dict[str, int]

    @staticmethod
    def group(ctx: Context) -> str:
        if ctx.kind == "ordinary":
            return "ordinary" if ctx.period == "regular" else "period"
        return "holiday"


def robust_sd(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    return float(1.4826 * np.median(np.abs(x - np.median(x))))


def calibrate(residuals: dict[str, list[np.ndarray]]) -> Calibration:
    """Spreads of e_day and e_loc(h) from the hourly residuals of train days, per group."""
    day_sd, hour_sd, n = {}, {}, {}
    for g, rows in residuals.items():
        e = np.vstack(rows)
        e_day = e.mean(axis=1)
        loc = e - e_day[:, None]
        day_sd[g] = robust_sd(e_day)
        hour_sd[g] = [robust_sd(loc[:, h]) for h in range(HOURS)]
        n[g] = len(rows)
    return Calibration(day_sd, hour_sd, n)


@dataclass(frozen=True)
class Review:
    outcome: str
    profile: str | None
    profile_tie: bool
    profile_distances: dict[str, float | None]
    concentrated: str | None
    concentrated_share: float | None
    review_hours: list[int]
    day_residual_pct: float | None
    day_residual_z: float | None
    residual_pct_by_hour: list[float] | None
    review_mwh: float | None
    peak_hour: int | None
    peak_residual_pct: float | None
    comparison: str
    n_comparable: int
    needed: int
    recent_level_pct: float
    next_check: str

    def to_dict(self) -> dict:
        return asdict(self)


def _runs(flags: np.ndarray, sign: np.ndarray) -> list[int]:
    hours: list[int] = []
    for s in (1, -1):
        hit = [h for h in range(HOURS) if flags[h] and sign[h] == s]
        for a, b in hour_windows(hit):
            if b - a + 1 >= MIN_RUN_HOURS:
                hours.extend(range(a, b + 1))
    return sorted(hours)


def profile_match(load: np.ndarray, candidates: dict[str, np.ndarray | None]) -> tuple[str | None, bool, dict]:
    s = shape(load)
    dist = {k: (None if v is None else float(np.sqrt(np.mean((s - v) ** 2)))) for k, v in candidates.items()}
    known = sorted((v, k) for k, v in dist.items() if v is not None)
    if len(known) < len(PROFILES):
        return None, False, dist
    (d1, best), (d2, _) = known[0], known[1]
    return best, (d2 - d1) <= PROFILE_TIE_MARGIN * d1, dist


def concentration(load: np.ndarray, normal: Reference) -> tuple[str | None, float | None]:
    if normal.curve is None:
        return None, None
    dev = np.abs(load - normal.curve)
    by_part = {p: float(sum(dev[h] for h in range(HOURS) if daypart(h) == p)) for p in DAYPARTS}
    total = sum(by_part.values())
    best = max(DAYPARTS, key=lambda p: by_part[p])
    return best, (by_part[best] / total if total else None)


LEVEL_NOTE_PCT = 3.0


def next_check(outcome: str, ctx: Context, hours: list[int], sign: int, ref: Reference, level_pct: float) -> str:
    date = ctx.date.date().isoformat()
    if outcome == "insufficient_evidence":
        return (f"Compare {date} by hand with the closest earlier days: only {ref.n} comparable earlier days "
                f"({ref.description}), at least {ref.needed} needed.")  # fmt: skip
    if outcome == "consistent":
        text = f"Close the alert: the hourly load matches {ref.description} within tolerance."
        if abs(level_pct) >= LEVEL_NOTE_PCT:
            side = "above" if level_pct > 0 else "below"
            text += (f" The ordinary days of the previous 4 weeks ran {abs(level_pct):.1f}% {side} the daily "
                     "baseline: part of the alert is baseline drift; refit the baseline.")  # fmt: skip
        return text
    window = format_windows(hours) if hours else "the whole day"
    if hours and len(hours) <= 6:
        if sign < 0:
            return (f"Check metering completeness and incident logs for {date} {window}: load stays below "
                    f"comparable days for {len(hours)} hours.")  # fmt: skip
        return f"Check for a data revision or an unlisted demand event on {date} {window}."
    if sign < 0:
        return (f"Check for a closure, local holiday or event missing from the calendar on {date}: load stays "
                f"below comparable days over {window}.")  # fmt: skip
    return (f"Check the weather inputs (station coverage, local cold or heat) and metering for {date} "
            f"{window}: load stays above comparable days.")  # fmt: skip


def review_day(ctx: Context, load: np.ndarray, ref: Reference, normal: Reference,
               candidates: dict[str, np.ndarray | None], cal: Calibration, level: float = 1.0) -> Review:  # fmt: skip
    profile, tie, dist = profile_match(load, candidates)
    conc, share = concentration(load, normal)
    level_pct = round(100 * (level - 1), 1)
    if not ref.sufficient or ref.curve is None:
        return Review("insufficient_evidence", profile, tie, dist, conc, share, [], None, None, None, None, None,
                      None, ref.description, ref.n, ref.needed, level_pct,
                      next_check("insufficient_evidence", ctx, [], 0, ref, level_pct))  # fmt: skip
    g = Calibration.group(ctx)
    e = load / ref.curve - 1
    e_day = float(e.mean())
    z_day = e_day / cal.day_sd[g]
    loc_z = (e - e_day) / np.asarray(cal.hour_sd[g])
    hours = set(_runs(np.abs(loc_z) >= THRESHOLD, np.sign(loc_z)))
    if abs(z_day) >= THRESHOLD:
        side = np.sign(e_day)
        hours |= {h for h in range(HOURS) if np.sign(e[h]) == side and abs(e[h]) >= THRESHOLD * cal.day_sd[g]}
    hours_l = sorted(hours)
    outcome = "deviation_remains" if (abs(z_day) >= THRESHOLD or hours_l) else "consistent"
    resid_mw = load - ref.curve
    peak = int(np.argmax(np.abs(e)))
    sign = int(np.sign(resid_mw[hours_l].sum())) if hours_l else int(np.sign(e_day))
    return Review(
        outcome=outcome,
        profile=profile,
        profile_tie=tie,
        profile_distances={k: (None if v is None else round(v, 4)) for k, v in dist.items()},
        concentrated=conc,
        concentrated_share=None if share is None else round(share, 3),
        review_hours=hours_l if outcome == "deviation_remains" else [],
        day_residual_pct=round(100 * e_day, 1),
        day_residual_z=round(z_day, 2),
        residual_pct_by_hour=[round(100 * float(v), 1) for v in e],
        review_mwh=round(float(resid_mw[hours_l].sum()), 0) if hours_l else 0.0,
        peak_hour=peak,
        peak_residual_pct=round(100 * float(e[peak]), 1),
        comparison=ref.description,
        n_comparable=ref.n,
        needed=ref.needed,
        recent_level_pct=level_pct,
        next_check=next_check(outcome, ctx, hours_l, sign, ref, level_pct),
    )


def residuals_for_calibration(builder, days: pd.DataFrame, load: pd.DataFrame, years=(2021, 2022, 2023)):
    """Hourly residuals e(h) of every train day of ``years`` with a sufficient context reference, by group."""
    from swissgrid_cot.review.context import context_of

    out: dict[str, list[np.ndarray]] = {"ordinary": [], "period": [], "holiday": []}
    for date in days.index[days.index.year.isin(years)]:
        ref = builder.context(date)
        if not ref.sufficient or ref.curve is None:
            continue
        out[Calibration.group(context_of(days.loc[date]))].append(load.loc[date].to_numpy() / ref.curve - 1)
    return out
