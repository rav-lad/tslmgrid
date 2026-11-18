"""The scored days of 2020-2026 and the calendar context of each day.

The daily detector is the one of ``swissgrid_cot.annotate``: the same baseline, fitted on the same
train days, the same robust z-score and threshold. Adding the holdout year changes no score of
2020-2025 (``tests/test_review.py`` checks it against ``days.parquet``).
"""

from dataclasses import dataclass
from unittest import mock

import pandas as pd

from swissgrid_cot.annotate import baseline as baseline_module
from swissgrid_cot.annotate.anomalies import score_days
from swissgrid_cot.annotate.baseline import PARTIAL_HOLIDAY_SHARE, daily_frame, fit_baseline, split_of_year
from swissgrid_cot.annotate.causes import attribute, weather_effect
from swissgrid_cot.ingest.calendar_ch import HOLIDAY_SHARE as FULL_HOLIDAY_SHARE
from swissgrid_cot.sources import HOLDOUT_YEAR, PROCESSED_DIR

KINDS = ("ordinary", "partial_holiday", "full_holiday", "bridge_day", "lockdown")
PERIODS = ("regular", "christmas", "summer")


def load_hourly() -> pd.DataFrame:
    """2020-2025 and the holdout year, one row per UTC hour."""
    main = pd.read_parquet(PROCESSED_DIR / "ch_hourly.parquet")
    path = PROCESSED_DIR / "ch_hourly_holdout.parquet"
    if not path.exists():
        return main
    holdout = pd.read_parquet(path)
    return pd.concat([main, holdout[~holdout.index.isin(main.index)]]).sort_index()


def split_with_holdout(year: int) -> str:
    return "holdout" if year == HOLDOUT_YEAR else split_of_year(year)


def scored_days(hourly: pd.DataFrame) -> pd.DataFrame:
    # annotate.baseline knows the 2020-2025 splits only, and stays as it is: the TimeNet connector
    # carries an exact copy of it. The holdout year gets its split here.
    with mock.patch.object(baseline_module, "split_of_year", split_with_holdout):
        days = daily_frame(hourly)
    baseline = fit_baseline(days)
    scored, _ = score_days(days, baseline)
    scored = attribute(scored)
    scored["weather_effect_mw"] = weather_effect(scored, baseline)
    scored["kind"] = [kind_of(r) for r in scored.itertuples()]
    scored["period"] = [period_of(r) for r in scored.itertuples()]
    return scored


def kind_of(day) -> str:
    """The calendar kind of a day. A holiday on a weekend day changes nothing: the day is a weekend day."""
    if day.lockdown:
        return "lockdown"
    if day.dow >= 5:
        return "ordinary"
    if day.holiday_pop_share >= FULL_HOLIDAY_SHARE:
        return "full_holiday"
    if day.holiday_pop_share >= PARTIAL_HOLIDAY_SHARE:
        return "partial_holiday"
    if day.is_bridge_day:
        return "bridge_day"
    return "ordinary"


def period_of(day) -> str:
    if day.christmas_period:
        return "christmas"
    if day.summer_holiday_core:
        return "summer"
    return "regular"


@dataclass(frozen=True)
class Context:
    """What the analyst knows about a flagged day without looking at its curve."""

    date: pd.Timestamp
    weekday: str
    kind: str
    period: str
    holiday_name: str | None
    holiday_pop_share: float
    temp_c: float
    temp_normal_c: float
    expected_mw: float
    load_mw: float
    rel_dev: float
    z: float

    def describe(self) -> str:
        parts = [f"{self.weekday} {self.date.day} {self.date.strftime('%B %Y')}"]
        if self.holiday_name and self.holiday_pop_share > 0:
            parts.append(f"{self.holiday_name}, a public holiday for {100 * self.holiday_pop_share:.1f}% of the population")
        else:
            parts.append("no public holiday")
        if self.kind == "bridge_day":
            parts.append("a bridge day between a public holiday and the weekend")
        if self.period == "christmas":
            parts.append("inside the Christmas school holidays (22 December - 6 January)")
        if self.period == "summer":
            parts.append("inside the core summer holidays (14 July - 15 August)")
        if self.kind == "lockdown":
            parts.append("during the COVID-19 lockdown")
        return "; ".join(parts)


def context_of(day: pd.Series) -> Context:
    date = pd.Timestamp(day.name)
    return Context(
        date=date,
        weekday=date.day_name(),
        kind=day.kind,
        period=day.period,
        holiday_name=day.holiday_name if isinstance(day.holiday_name, str) else None,
        holiday_pop_share=float(day.holiday_pop_share),
        temp_c=float(day.temp_c),
        temp_normal_c=float(day.temp_normal_c),
        expected_mw=float(day.expected_mw),
        load_mw=float(day.load_mw),
        rel_dev=float(day.rel_dev),
        z=float(day.z),
    )
