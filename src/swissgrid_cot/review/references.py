"""Hourly references for a flagged day, built from earlier days only.

Every reference is a set of comparable earlier days. Each comparable day c contributes its hourly
ratio to its own daily expectation, q_c(h) = load_c(h) / expected_c, and the reference of the
flagged day D is

    R_D(h) = expected_D * b_D * median_c (q_c(h) / b_c)

``expected`` is the daily baseline (weekday type x month, weather, trend). Scaling by it carries
D's weather and season over to the comparable days. The ratio keeps what the baseline does not
model: the hourly shape and the calendar effect (a holiday's ratio is below 1 because the baseline
treats every day as a normal day of its weekday type).

``b_x`` is the recent level: the median of load / expected over the ordinary days of the 28 days
before x (1 when fewer than 7 qualify). It removes the slow drift of the baseline, whose linear trend
was fitted on 2020-2023: over the ordinary days of January 2026 the baseline runs 6 % low. The
review reports b_D, so a drifting baseline is visible instead of being read as an anomaly.

Comparable days, always strictly before D, never in the 2020 lockdown, with complete data:

* ordinary day, regular period: same weekday type, not a special day, |z| < 3, within 28 days of
  D's day of year in any earlier year or in the 42 days before D, daily mean temperature within
  3 °C of D's (6 °C if fewer than 5 days qualify). This is the "comparable weather" check: a cold
  day is compared with earlier days as cold.
* ordinary day, summer core (14 Jul - 15 Aug): same weekday type, summer core, no holiday or
  bridge day, within 14 days of D's day of year.
* ordinary day, Christmas period: earlier Christmas periods, same weekday group (Monday-Friday,
  Saturday or Sunday), holiday share below 0.2, at most 2 days apart in the period.
* full holiday (share >= 0.5, Monday-Friday): earlier full holidays on a weekday, inside the
  Christmas period if D is, outside if not.
* partial holiday (0.2 <= share < 0.5): no earlier day has the same share, so the reference blends
  the two: (1 - s) * ordinary reference + s * full-holiday reference, with s the share of the
  population on holiday. The assumption is that the load of the population on holiday behaves
  like a full holiday and the rest like a normal day. Whether the morning really moves toward the
  holiday profile is what the review then checks.
* bridge day: earlier bridge days.
* lockdown: no earlier comparable day exists.

A reference needs at least ``MIN_COMPARABLE`` days (``MIN_COMPARABLE_ORDINARY`` for ordinary days).
Below that, the review answers "insufficient evidence".

Candidate profiles: the median hourly shape (load / daily mean) of the ordinary Tuesdays to
Thursdays, Saturdays and Sundays of the 8 weeks before D. A day's profile "resembles" the
candidate with the smallest root mean square difference of shapes, whatever its weekday.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from swissgrid_cot.annotate.anomalies import Z_THRESHOLD
from swissgrid_cot.annotate.baseline import PARTIAL_HOLIDAY_SHARE

MIN_COMPARABLE = 3
MIN_COMPARABLE_ORDINARY = 5
ORDINARY_DOY_WINDOW = 28
ORDINARY_RECENT_DAYS = 42
RECENT_FILL = 7
TEMP_WINDOW_C = (3.0, 6.0)
SUMMER_DOY_WINDOW = 14
CHRISTMAS_OFFSET_DAYS = 2
PROFILE_WEEKS = 8
PROFILE_MIN_DAYS = 3
LEVEL_DAYS = 28
LEVEL_MIN_DAYS = 7
PROFILES = ("weekday", "saturday", "sunday")
_PROFILE_DOW = {"weekday": (1, 2, 3), "saturday": (5,), "sunday": (6,)}


@dataclass
class Reference:
    """A reference curve and how it was built."""

    curve: np.ndarray | None
    dates: list[pd.Timestamp] = field(default_factory=list)
    description: str = ""
    sufficient: bool = False
    needed: int = MIN_COMPARABLE

    @property
    def n(self) -> int:
        return len(self.dates)


DAYTYPE_TEXT = {"mon": "Monday", "tue-thu": "Tuesday-Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday"}


def _weekday_group(dow: int) -> str:
    return "weekday" if dow < 5 else ("saturday" if dow == 5 else "sunday")


def _circular_doy_distance(a: np.ndarray, b: int) -> np.ndarray:
    d = np.abs(a - b)
    return np.minimum(d, 365 - d)


def _christmas_offset(date: pd.Timestamp) -> int:
    """Days since 22 December of the period the date belongs to."""
    start_year = date.year if date.month == 12 else date.year - 1
    return (date - pd.Timestamp(start_year, 12, 22)).days


class ReferenceBuilder:
    def __init__(self, days: pd.DataFrame, load: pd.DataFrame):
        """
        Args:
            days: The scored days (``context.scored_days``).
            load: The 24-slot day matrix of end-user load (``hourly.day_matrix``).
        """
        self.days = days
        self.load = load.reindex(days.index)
        complete = self.load.notna().all(axis=1) & days.temp_c.notna() & days.expected_mw.notna()
        self.usable = complete & ~days.lockdown
        self.ratio = self.load.div(days.expected_mw, axis=0)
        self.shape = self.load.div(self.load.mean(axis=1), axis=0)
        self.doy = np.minimum(days.index.day_of_year.to_numpy(), 365)
        self.ordinary = ~days.special_day & (days.z.abs() < Z_THRESHOLD) & ~days.summer_holiday_core
        self.level = self._recent_level()

    def _recent_level(self) -> pd.Series:
        """b_x: median load / expected over the ordinary days of the 28 days before x."""
        r = (self.days.load_mw / self.days.expected_mw).where(self.ordinary & self.usable)
        med = r.rolling(f"{LEVEL_DAYS}D", closed="left", min_periods=LEVEL_MIN_DAYS).median()
        return med.fillna(1.0)

    # ---- comparable days ------------------------------------------------------------------------

    def _before(self, date: pd.Timestamp) -> np.ndarray:
        return (self.days.index < date) & self.usable.to_numpy()

    def ordinary_dates(self, date: pd.Timestamp) -> tuple[list[pd.Timestamp], str]:
        d = self.days.loc[date]
        period = d.period
        before = self._before(date)
        if period == "christmas":
            group = _weekday_group(int(d.dow))
            offsets = np.array([_christmas_offset(x) if c else 999 for x, c in
                                zip(self.days.index, self.days.christmas_period, strict=True)])  # fmt: skip
            groups = np.array([_weekday_group(int(x)) for x in self.days.dow])
            mask = (
                before & self.days.christmas_period.to_numpy() & (groups == group)
                & (self.days.holiday_pop_share.to_numpy() < PARTIAL_HOLIDAY_SHARE)
                & (np.abs(offsets - _christmas_offset(date)) <= CHRISTMAS_OFFSET_DAYS)
                & (self.days.index < date - pd.Timedelta(days=20))  # an earlier period, not this one
            )  # fmt: skip
            label = {"weekday": "Monday-Friday", "saturday": "Saturday", "sunday": "Sunday"}[group]
            return list(self.days.index[mask]), (
                f"{label} days of earlier Christmas periods, at most {CHRISTMAS_OFFSET_DAYS} days apart in the period")
        same_type = (self.days.daytype == d.daytype).to_numpy()
        if period == "summer":
            mask = (
                before & same_type & self.days.summer_holiday_core.to_numpy()
                & (self.days.holiday_pop_share.to_numpy() < PARTIAL_HOLIDAY_SHARE)
                & ~self.days.is_bridge_day.to_numpy()
                & (_circular_doy_distance(self.doy, self.doy[self.days.index.get_loc(date)]) <= SUMMER_DOY_WINDOW)
            )  # fmt: skip
            return list(self.days.index[mask]), (
                f"{DAYTYPE_TEXT[d.daytype]} days of earlier summer holidays, within {SUMMER_DOY_WINDOW} days of the date")
        return self.regular_dates(date)

    def regular_dates(self, date: pd.Timestamp) -> tuple[list[pd.Timestamp], str]:
        """Ordinary days of the regular period comparable with D, whatever D's own calendar."""
        d = self.days.loc[date]
        same_type = (self.days.daytype == d.daytype).to_numpy()
        near = (_circular_doy_distance(self.doy, self.doy[self.days.index.get_loc(date)]) <= ORDINARY_DOY_WINDOW) | (
            self.days.index >= date - pd.Timedelta(days=ORDINARY_RECENT_DAYS))
        base = self._before(date) & same_type & self.ordinary.to_numpy() & near
        dt = np.abs(self.days.temp_c.to_numpy() - d.temp_c)
        for window in TEMP_WINDOW_C:
            mask = base & (dt <= window)
            if mask.sum() >= MIN_COMPARABLE_ORDINARY:
                break
        return list(self.days.index[mask]), (
            f"ordinary {DAYTYPE_TEXT[d.daytype]} days within {ORDINARY_DOY_WINDOW} days of the date in earlier years or in the "
            f"previous {ORDINARY_RECENT_DAYS} days, with a daily mean temperature within {window:.0f} °C "
            f"({d.temp_c:.1f} °C)")

    def full_holiday_dates(self, date: pd.Timestamp) -> list[pd.Timestamp]:
        d = self.days.loc[date]
        mask = (
            self._before(date) & (self.days.kind == "full_holiday").to_numpy()
            & (self.days.christmas_period.to_numpy() == bool(d.christmas_period))
        )  # fmt: skip
        return list(self.days.index[mask])

    def bridge_dates(self, date: pd.Timestamp) -> list[pd.Timestamp]:
        return list(self.days.index[self._before(date) & (self.days.kind == "bridge_day").to_numpy()])

    # ---- references -----------------------------------------------------------------------------

    def _curve(self, date: pd.Timestamp, dates: list[pd.Timestamp]) -> np.ndarray | None:
        if not dates:
            return None
        detrended = self.ratio.loc[dates].div(self.level.loc[dates], axis=0)
        scale = float(self.days.at[date, "expected_mw"]) * float(self.level.at[date])
        return scale * detrended.median().to_numpy()

    def normal(self, date: pd.Timestamp) -> Reference:
        """What a normal day of D's weekday type, season and weather looks like, ignoring any holiday."""
        dates, how = self.ordinary_dates(date)
        need = MIN_COMPARABLE if self.days.at[date, "period"] != "regular" else MIN_COMPARABLE_ORDINARY
        return Reference(self._curve(date, dates), dates, how, len(dates) >= need, need)

    def blind_normal(self, date: pd.Timestamp) -> Reference:
        """What an ordinary day of D's weekday type, time of year and temperature looks like, built the same way
        for every day: a holiday, a Christmas or a summer day is compared with ordinary days of the regular
        period. Nothing in it depends on D's calendar."""
        dates, how = self.regular_dates(date)
        return Reference(self._curve(date, dates), dates, how, len(dates) >= MIN_COMPARABLE_ORDINARY,
                         MIN_COMPARABLE_ORDINARY)  # fmt: skip

    def recent_dates(self, date: pd.Timestamp) -> tuple[list[pd.Timestamp], str]:
        """Ordinary days of D's weekday type, the most recent first: those of the 42 days before D at a
        comparable temperature; when fewer than 5, the ``RECENT_FILL`` most recent of ``regular_dates``."""
        d = self.days.loc[date]
        base = (self._before(date) & (self.days.daytype == d.daytype).to_numpy() & self.ordinary.to_numpy()
                & (self.days.index >= date - pd.Timedelta(days=ORDINARY_RECENT_DAYS)))  # fmt: skip
        dt = np.abs(self.days.temp_c.to_numpy() - d.temp_c)
        for window in TEMP_WINDOW_C:
            mask = base & (dt <= window)
            if mask.sum() >= MIN_COMPARABLE_ORDINARY:
                return list(self.days.index[mask]), (
                    f"ordinary {DAYTYPE_TEXT[d.daytype]} days of the previous {ORDINARY_RECENT_DAYS} days, with a "
                    f"daily mean temperature within {window:.0f} °C")
        dates, how = self.regular_dates(date)
        return sorted(dates)[-RECENT_FILL:], f"the {RECENT_FILL} most recent {how}"

    def recent_normal(self, date: pd.Timestamp) -> Reference:
        """``blind_normal`` from the most recent comparable days, so that its shape follows the grid as it
        changes (solar output, heat pumps, population); its level follows the last 28 days in any case."""
        dates, how = self.recent_dates(date)
        return Reference(self._curve(date, dates), dates, how, len(dates) >= MIN_COMPARABLE_ORDINARY,
                         MIN_COMPARABLE_ORDINARY)  # fmt: skip

    def context(self, date: pd.Timestamp) -> Reference:
        """What D's calendar context predicts: the reference the review compares the day with."""
        d = self.days.loc[date]
        if d.kind == "lockdown":
            return Reference(None, [], "no earlier day was in a lockdown", False, MIN_COMPARABLE)
        if d.kind == "full_holiday":
            dates = self.full_holiday_dates(date)
            where = "inside" if d.christmas_period else "outside"
            return Reference(self._curve(date, dates), dates,
                             f"earlier full public holidays on a weekday, {where} the Christmas period",
                             len(dates) >= MIN_COMPARABLE)  # fmt: skip
        if d.kind == "bridge_day":
            dates = self.bridge_dates(date)
            return Reference(self._curve(date, dates), dates, "earlier bridge days", len(dates) >= MIN_COMPARABLE)
        normal = self.normal(date)
        if d.kind == "ordinary":
            return normal
        # partial holiday: blend the normal day and the full holiday by the population share
        holiday = self.full_holiday_dates(date)
        s = float(d.holiday_pop_share)
        ok = normal.sufficient and len(holiday) >= MIN_COMPARABLE
        curve = None
        if normal.curve is not None and holiday:
            curve = (1 - s) * normal.curve + s * self._curve(date, holiday)
        return Reference(curve, normal.dates + holiday,
                         f"{100 * (1 - s):.0f}% {normal.description} (n={normal.n}) + {100 * s:.0f}% earlier full "
                         f"public holidays (n={len(holiday)}), weighted by the population on holiday",
                         ok)  # fmt: skip

    def profiles(self, date: pd.Timestamp) -> dict[str, np.ndarray | None]:
        """Candidate weekday, Saturday and Sunday shapes from the ordinary days of the 8 weeks before D."""
        window = (self.days.index >= date - pd.Timedelta(weeks=PROFILE_WEEKS)) & self._before(date)
        pool = window & ~self.days.special_day.to_numpy() & (self.days.z.abs() < Z_THRESHOLD).to_numpy()
        out = {}
        for name, dows in _PROFILE_DOW.items():
            mask = pool & self.days.dow.isin(dows).to_numpy()
            out[name] = self.shape[mask].median().to_numpy() if mask.sum() >= PROFILE_MIN_DAYS else None
        return out


def as_list(curve: np.ndarray | None, digits: int = 1) -> list[float] | None:
    return None if curve is None else [round(float(v), digits) for v in curve]
