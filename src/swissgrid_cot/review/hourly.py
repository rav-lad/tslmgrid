"""One row of 24 local-hour slots per local day.

Analysts read Swiss local time, so every day becomes 24 slots, 00:00 to 23:00 local. The hourly
table stays in UTC; the slots are its local hours. On the spring-forward day the 02:00 slot does not
exist and takes the mean of 01:00 and 03:00. On the fall-back day 02:00 occurs twice and takes the
mean of both hours. Both are marked in ``dst_adjusted``.
"""

import numpy as np
import pandas as pd

HOURS = 24


def day_matrix(hourly: pd.DataFrame, column: str = "load_enduser_mw") -> pd.DataFrame:
    """Pivot an hourly column into one row per local date and one column per local hour (0-23).

    Returns:
        A frame indexed by local date with columns 0..23, plus nothing else.
    """
    g = hourly.groupby(["local_date", "local_hour"])[column].mean().unstack("local_hour")
    g = g.reindex(columns=range(HOURS))
    missing_two = g[2].isna() & g[1].notna() & g[3].notna()
    g.loc[missing_two, 2] = (g.loc[missing_two, 1] + g.loc[missing_two, 3]) / 2
    g.index = pd.DatetimeIndex(g.index, name="date")
    g.columns.name = "hour"
    return g


def dst_adjusted(hourly: pd.DataFrame) -> pd.Series:
    n = hourly.groupby("local_date").size()
    n.index = pd.DatetimeIndex(n.index, name="date")
    return n != HOURS


def shape(row: np.ndarray) -> np.ndarray:
    """The hourly profile divided by its daily mean: 1.0 is an average hour of that day."""
    return row / np.nanmean(row)


def daypart(hour: int) -> str:
    return ("night", "morning", "afternoon", "evening")[hour // 6]


DAYPARTS = ("night", "morning", "afternoon", "evening")
"""00:00-05:59, 06:00-11:59, 12:00-17:59, 18:00-23:59 local time."""


def hour_windows(hours: list[int]) -> list[tuple[int, int]]:
    """Group hours into runs of consecutive hours, as (first, last) pairs."""
    runs: list[tuple[int, int]] = []
    for h in sorted(hours):
        if runs and h == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], h)
        else:
            runs.append((h, h))
    return runs


def format_windows(hours: list[int]) -> str:
    """'07:00-10:59, 18:00-18:59', or 'none'."""
    if not hours:
        return "none"
    return ", ".join(f"{a:02d}:00-{b:02d}:59" for a, b in hour_windows(hours))
