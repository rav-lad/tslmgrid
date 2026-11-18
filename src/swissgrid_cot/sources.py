"""Every external source file, by URL. Their sha256 digests live in ``sources.lock.json``."""

from dataclasses import dataclass
from pathlib import Path

from swissgrid_cot.ingest.stations import STATION_CANTONS

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
INTERIM_DIR = REPO_ROOT / "data" / "interim"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
LOCK_PATH = REPO_ROOT / "sources.lock.json"

YEARS = range(2020, 2026)
HOLDOUT_YEAR = 2026
"""The current year, published so far (Swissgrid to 31 October 2026). Only the alert review reads it,
as an evaluation year nobody inspected while the review was designed. TimeNet and the weekly tasks
stay on 2020-2025."""


@dataclass(frozen=True)
class SourceFile:
    key: str
    url: str
    path: Path


_SWISSGRID_JCR = {
    2020: "a6deeecb-74e8-4d67-a8ad-8c53c9dfbdd3",
    2021: "26fa6b22-5e81-44eb-abbd-4280c59c3697",
    2022: "e3af783a-6c00-40d9-bb3e-a630fb492dfb",
    2023: "32576046-3686-4a62-bc32-9b55a89a2142",
    2024: "4d4ca899-395d-4d3d-9958-5ace16ecbfbf",
    2025: "bbbbadc6-3656-4dfe-b81e-bbb9ad01be79",
    2026: "805e525c-44fe-4701-a227-6144193257ac",
}


def swissgrid_file(year: int) -> SourceFile:
    name = f"EnergieUebersichtCH-{year}.xlsx"
    return SourceFile(
        key=f"swissgrid/{year}",
        url=f"https://www.swissgrid.ch/dam/jcr:{_SWISSGRID_JCR[year]}/{name}",
        path=RAW_DIR / "swissgrid" / name,
    )


_SMN = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn"


def meteoswiss_file(station: str) -> SourceFile:
    name = f"ogd-smn_{station.lower()}_h_historical_2020-2029.csv"
    return SourceFile(
        key=f"meteoswiss/{station}",
        url=f"{_SMN}/{station.lower()}/{name}",
        path=RAW_DIR / "meteoswiss" / name,
    )


def meteoswiss_recent_file(station: str) -> SourceFile:
    """1 January of the current year to yesterday. MeteoSwiss moves it into the historical file yearly."""
    name = f"ogd-smn_{station.lower()}_h_recent.csv"
    return SourceFile(
        key=f"meteoswiss-recent/{station}",
        url=f"{_SMN}/{station.lower()}/{name}",
        path=RAW_DIR / "meteoswiss" / name,
    )


# BFS STATPOP, permanent resident population per canton, 2023 (table px-x-0102010000_101).
# It is fetched with a POST query, so the downloader handles it apart.
BFS_POPULATION = SourceFile(
    key="bfs/population_2023",
    url="https://www.pxweb.bfs.admin.ch/api/v1/de/px-x-0102010000_101/px-x-0102010000_101.px",
    path=RAW_DIR / "bfs" / "population_2023_by_canton.csv",
)
BFS_CANTONS = tuple(c for cantons in STATION_CANTONS.values() for c in cantons)
BFS_QUERY = {
    "query": [
        {"code": "Jahr", "selection": {"filter": "item", "values": ["2023"]}},
        {
            "code": "Kanton (-) / Bezirk (>>) / Gemeinde (......)",
            "selection": {"filter": "item", "values": sorted(BFS_CANTONS)},
        },
        {"code": "Bevölkerungstyp", "selection": {"filter": "item", "values": ["1"]}},
        {"code": "Staatsangehörigkeit (Kategorie)", "selection": {"filter": "item", "values": ["-99999"]}},
        {"code": "Geschlecht", "selection": {"filter": "item", "values": ["-99999"]}},
        {"code": "Alter", "selection": {"filter": "item", "values": ["-99999"]}},
    ],
    "response": {"format": "csv"},
}


def all_sources() -> list[SourceFile]:
    return [
        *(swissgrid_file(y) for y in YEARS),
        *(meteoswiss_file(s) for s in STATION_CANTONS),
        BFS_POPULATION,
    ]


def holdout_sources() -> list[SourceFile]:
    return [swissgrid_file(HOLDOUT_YEAR), *(meteoswiss_recent_file(s) for s in STATION_CANTONS)]
