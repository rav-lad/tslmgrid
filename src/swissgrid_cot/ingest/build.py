"""Build the aligned hourly national dataset, 2020-2025.

Usage::

    uv run sgcot-download && uv run sgcot-ingest

Writes ``data/processed/ch_hourly.parquet`` and ``data/processed/ingest_report.json``.
"""

import json

import numpy as np
import pandas as pd

from swissgrid_cot.download import sha256
from swissgrid_cot.ingest import meteoswiss, swissgrid
from swissgrid_cot.ingest.assemble import hourly_dataset
from swissgrid_cot.sources import (
    INTERIM_DIR,
    PROCESSED_DIR,
    STATION_CANTONS,
    YEARS,
    meteoswiss_file,
    swissgrid_file,
)

TZ = swissgrid.TZ


def load_swissgrid_quarters() -> pd.DataFrame:
    """Parse every year, cached per file digest because reading the workbooks takes minutes."""
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for year in YEARS:
        src = swissgrid_file(year)
        cache = INTERIM_DIR / f"swissgrid_{year}_{sha256(src.path)[:12]}.parquet"
        if cache.exists():
            frame = pd.read_parquet(cache)
        else:
            print(f"parsing {src.path.name} ...", flush=True)
            frame = swissgrid.read_year(src.path, year)
            frame.to_parquet(cache)
        frames.append(frame)
    quarters = pd.concat(frames)
    if quarters.index.has_duplicates:
        raise swissgrid.SwissgridFormatError("the yearly files overlap")
    return quarters


def profile_lag_quarters(quarters: pd.DataFrame, year: int, ref_year: int = 2024) -> int:
    """Lag, in quarter hours, that best aligns a year's mean local weekday profile with the reference.

    Zero means both years put the morning ramp in the same quarter hour, which checks the label
    conventions independently of the parser's own logic.
    """

    def profile(y: int) -> np.ndarray:
        q = quarters.loc[str(y), "load_enduser"]
        local = q.index.tz_convert(TZ)
        weekday = local.day_of_week < 5
        slot = local.hour[weekday] * 4 + local.minute[weekday] // 15
        p = q[weekday].groupby(slot).mean().to_numpy()
        return (p - p.mean()) / p.std()

    a, b = profile(ref_year), profile(year)
    # The lag maximising correlation, on the ramp-dominated derivative.
    da, db = np.diff(a), np.diff(b)
    lags = range(-4, 5)
    return max(lags, key=lambda k: float(np.dot(da, np.roll(db, k))))


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    report: dict = {}

    quarters = load_swissgrid_quarters()
    report["profile_lag_vs_2024_quarters"] = {y: profile_lag_quarters(quarters, y) for y in YEARS}
    stations = {s: meteoswiss.read_station(meteoswiss_file(s).path, s) for s in STATION_CANTONS}
    df = hourly_dataset(quarters, stations)
    report["station_weights"] = meteoswiss.station_weights(meteoswiss.canton_population()).round(4).to_dict()
    report["station_nulls"] = {
        s: {c: int(sf[c].reindex(df.index).isna().sum()) for c in meteoswiss.PARAMETERS.values()}
        for s, sf in stations.items()
    }
    cal = df.groupby("local_date")[["is_holiday", "is_bridge_day"]].first()

    out = PROCESSED_DIR / "ch_hourly.parquet"
    df.to_parquet(out)

    # ---- sanity checks -------------------------------------------------------------------------
    hours_per_day = df.groupby("local_date").size()
    report["n_hours"] = len(df)
    report["utc_range"] = [str(df.index.min()), str(df.index.max())]
    report["regular_hourly"] = bool((df.index.to_series().diff().dropna() == pd.Timedelta("1h")).all())
    report["local_days_with_23h"] = [str(d.date()) for d in hours_per_day[hours_per_day == 23].index]
    report["local_days_with_25h"] = [str(d.date()) for d in hours_per_day[hours_per_day == 25].index]
    report["other_day_lengths"] = int((~hours_per_day.isin([23, 24, 25])).sum())
    report["nulls"] = {c: int(v) for c, v in df.isna().sum().items() if v and c != "holiday_name"}
    by_year = df.groupby("year")
    report["annual_twh"] = {
        c: by_year[f"{c}_mw"].sum().div(1e6).round(2).to_dict() for c in ("load_enduser", "load_total", "production")
    }
    report["annual_net_import_twh"] = by_year.net_import_mw.sum().div(1e6).round(2).to_dict()
    report["import_minus_export_vs_net_import_max_abs_mw"] = float(
        (df.import_mw - df.export_mw - df.net_import_mw).abs().max()
    )
    daily = df.groupby("local_date").agg(load=("load_enduser_mw", "mean"), temp=("temp_c", "mean"))
    report["corr_daily_load_temp"] = round(float(daily.load.corr(daily.temp)), 3)
    report["mean_temp_by_year"] = by_year.temp_c.mean().round(2).to_dict()
    report["holidays_ge_50pct"] = int(cal.is_holiday.sum())
    report["bridge_days"] = [str(d.date()) for d in cal.index[cal.is_bridge_day]]

    (PROCESSED_DIR / "ingest_report.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps(report, indent=2, default=str))
    print(f"wrote {out} ({len(df)} rows, {df.shape[1]} columns)")


if __name__ == "__main__":
    main()
