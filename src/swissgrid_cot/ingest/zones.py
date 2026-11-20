"""Hourly consumption of the 18 canton zones that Swissgrid publishes, for the map of the demo.

Usage::

    uv run sgcot-ingest-zones

Writes ``data/processed/ch_zones_hourly.parquet``: one row per UTC hour of 2024-2026 (as far as the
holdout year is published), one column per zone in MW, with ``local_date`` and ``local_hour``.

* The same workbooks as the national load, columns ``Consumption Canton XX``. Some cantons are
  published together (``GE+VD``, ``SH+ZH``, ``BE+JU`` ...). The zones include the pumping of storage
  plants (Limmern in GL, Nant de Drance in VS), which the national end-user load leaves out.
* ``ingest.swissgrid.read_year`` reads them with its own checks: only its column list is swapped (the
  TimeNet connector carries an exact copy of the module), and for 2026 its label check, as in
  ``ingest.holdout``.
"""

from unittest import mock

import pandas as pd

from swissgrid_cot.download import sha256
from swissgrid_cot.ingest import swissgrid
from swissgrid_cot.ingest.holdout import partial_labels_to_utc_start
from swissgrid_cot.ingest.timefields import floor_hour
from swissgrid_cot.sources import HOLDOUT_YEAR, INTERIM_DIR, PROCESSED_DIR, swissgrid_file

OUT = PROCESSED_DIR / "ch_zones_hourly.parquet"
YEARS = (2024, 2025, HOLDOUT_YEAR)
ZONES = {
    "Consumption Canton AG": "AG",
    "Consumption Canton FR": "FR",
    "Consumption Canton GL": "GL",
    "Consumption Canton GR": "GR",
    "Consumption Canton LU": "LU",
    "Consumption Canton NE": "NE",
    "Consumption Canton SO": "SO",
    "Consumption Canton SG": "SG",
    "Consumption Canton TI": "TI",
    "Consumption Canton TG": "TG",
    "Consumption Canton VS": "VS",
    "Consumption Cantons AI, AR": "AI+AR",
    "Consumption Cantons BL, BS": "BL+BS",
    "Consumption Cantons BE, JU": "BE+JU",
    "Consumption Cantons SZ, ZG": "SZ+ZG",
    "Consumption Cantons OW, NW, UR": "OW+NW+UR",
    "Consumption Cantons GE, VD": "GE+VD",
    "Consumption Cantons SH, ZH": "SH+ZH",
}
"""English header -> zone. Every canton belongs to exactly one zone."""


def read_zones(year: int) -> pd.DataFrame:
    """One year of zone consumption, kWh per quarter hour, cached per file digest."""
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    src = swissgrid_file(year)
    cache = INTERIM_DIR / f"zones_{year}_{sha256(src.path)[:12]}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    print(f"parsing the zones of {src.path.name} ...", flush=True)
    with mock.patch.object(swissgrid, "COLUMNS", ZONES):
        if year == HOLDOUT_YEAR:
            with mock.patch.object(swissgrid, "labels_to_utc_start", partial_labels_to_utc_start):
                frame = swissgrid.read_year(src.path, year)
        else:
            frame = swissgrid.read_year(src.path, year)
    frame.to_parquet(cache)
    return frame


def main() -> None:
    quarters = pd.concat([read_zones(y) for y in YEARS])
    hourly = quarters.groupby(floor_hour(quarters.index)).sum() / 1000.0  # kWh per quarter -> MW per hour
    hourly.index.name = "utc_start"
    local = hourly.index.tz_convert(swissgrid.TZ)
    hourly["local_date"] = pd.DatetimeIndex(local.date)
    hourly["local_hour"] = local.hour
    hourly.to_parquet(OUT)
    print(f"wrote {OUT} ({len(hourly)} hours, {len(ZONES)} zones)")


if __name__ == "__main__":
    main()
