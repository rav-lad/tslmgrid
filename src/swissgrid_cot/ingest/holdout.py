"""Build the hourly table of the holdout year 2026, as published so far, for the alert review.

Usage::

    uv run sgcot-download --holdout && uv run sgcot-ingest-holdout

Writes ``data/processed/ch_hourly_holdout.parquet`` and ``data/processed/ingest_holdout_report.json``.
``ch_hourly.parquet`` (2020-2025) and everything built from it stay unchanged.

* Swissgrid publishes the current year up to the end of a month (31 October 2026 here). The rows
  are checked like a complete year, up to their last whole local day. ``ingest.swissgrid`` is left
  as it is (the TimeNet connector carries an exact copy of it); only its label check is swapped for
  the partial-year one while the holdout workbook is read.
* MeteoSwiss puts the current year in a separate ``recent`` file. It overlaps the historical file
  by one hour at the turn of the year; the historical value wins. Recent values have passed fewer
  quality checks than historical ones.
"""

import json
from unittest import mock

import numpy as np
import pandas as pd

from swissgrid_cot.download import sha256
from swissgrid_cot.ingest import meteoswiss, swissgrid
from swissgrid_cot.ingest.assemble import hourly_dataset
from swissgrid_cot.ingest.build import load_swissgrid_quarters, profile_lag_quarters
from swissgrid_cot.sources import (
    HOLDOUT_YEAR,
    INTERIM_DIR,
    PROCESSED_DIR,
    STATION_CANTONS,
    meteoswiss_file,
    meteoswiss_recent_file,
    swissgrid_file,
)

OUT = PROCESSED_DIR / "ch_hourly_holdout.parquet"


def partial_labels_to_utc_start(labels: pd.Series, year: int) -> pd.DatetimeIndex:
    """``swissgrid.labels_to_utc_start`` for a year published up to the end of some local day.

    Returns:
        The UTC start of each quarter hour, in row order.

    Raises:
        SwissgridFormatError: If the rows stop inside a local day, or any label does not match the
            quarter hour at its position.
    """
    convention = swissgrid.detect_convention(labels.iloc[0], year)
    full = pd.date_range(
        pd.Timestamp(year, 1, 1).tz_localize(swissgrid.TZ).tz_convert("UTC"),
        pd.Timestamp(year + 1, 1, 1).tz_localize(swissgrid.TZ).tz_convert("UTC"),
        freq=swissgrid.QUARTER,
        inclusive="left",
    )
    if len(labels) > len(full):
        raise swissgrid.SwissgridFormatError(f"{year}: {len(labels)} rows, more than a year")
    expected = full[: len(labels)]
    end_local = (expected[-1] + swissgrid.QUARTER).tz_convert(swissgrid.TZ)
    if (end_local.hour, end_local.minute) != (0, 0):
        raise swissgrid.SwissgridFormatError(f"{year}: the rows stop at {end_local}, inside a local day")
    period_end = convention is swissgrid.LabelConvention.PERIOD_END
    labelled = expected + swissgrid.QUARTER if period_end else expected
    lab = pd.DatetimeIndex(labels).as_unit("us")
    ok = (lab == swissgrid._wall_clock(labelled, left=False)) | (lab == swissgrid._wall_clock(labelled, left=True))
    if not ok.all():
        i = int(np.argmin(ok))
        raise swissgrid.SwissgridFormatError(f"{year}: row {i} is labelled {lab[i]}, expected {labelled[i]}")
    return expected.rename("utc_start")


def load_holdout_quarters() -> pd.DataFrame:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    src = swissgrid_file(HOLDOUT_YEAR)
    cache = INTERIM_DIR / f"swissgrid_{HOLDOUT_YEAR}_{sha256(src.path)[:12]}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    print(f"parsing {src.path.name} ...", flush=True)
    with mock.patch.object(swissgrid, "labels_to_utc_start", partial_labels_to_utc_start):
        frame = swissgrid.read_year(src.path, HOLDOUT_YEAR)
    frame.to_parquet(cache)
    return frame


def read_station_with_recent(station: str) -> pd.DataFrame:
    historical = meteoswiss.read_station(meteoswiss_file(station).path, station)
    recent = meteoswiss.read_station(meteoswiss_recent_file(station).path, station)
    both = pd.concat([historical, recent])
    return both[~both.index.duplicated(keep="first")].sort_index()


def main() -> None:
    quarters = load_holdout_quarters()
    stations = {s: read_station_with_recent(s) for s in STATION_CANTONS}
    df = hourly_dataset(quarters, stations)
    df.to_parquet(OUT)

    reference = pd.concat([load_swissgrid_quarters().loc["2024"], quarters])
    hours_per_day = df.groupby("local_date").size()
    report = {
        "utc_range": [str(df.index.min()), str(df.index.max())],
        "local_days": [str(df.local_date.min().date()), str(df.local_date.max().date())],
        "n_hours": len(df),
        "regular_hourly": bool((df.index.to_series().diff().dropna() == pd.Timedelta("1h")).all()),
        "local_days_with_23h": [str(d.date()) for d in hours_per_day[hours_per_day == 23].index],
        "local_days_with_25h": [str(d.date()) for d in hours_per_day[hours_per_day == 25].index],
        "other_day_lengths": int((~hours_per_day.isin([23, 24, 25])).sum()),
        "nulls": {c: int(v) for c, v in df.isna().sum().items() if v and c != "holiday_name"},
        "load_enduser_twh_to_date": round(float(df.load_enduser_mw.sum() / 1e6), 3),
        "profile_lag_vs_2024_quarters": profile_lag_quarters(reference, HOLDOUT_YEAR),
        "mean_temp_c": round(float(df.temp_c.mean()), 2),
    }
    (PROCESSED_DIR / "ingest_holdout_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"wrote {OUT} ({len(df)} rows)")


if __name__ == "__main__":
    main()
