"""Build the demo: a 3D map of Switzerland, one day at a time, with the review of each flagged day.

Usage::

    uv run sgcot-ingest-zones
    uv run python demo/build_demo.py --predictions <test predictions> <all-days predictions>

Writes ``demo/index.html`` (not committed: it embeds Swissgrid data, whose license is unknown) and
``scratch/map_artifact.html``, the same page without the document skeleton.

* **Columns** are H3 cells (resolution 7, about 5 km²) placed where people live (Kontur population
  2023). Each cell belongs to the Swissgrid canton zone that holds most of its population.
* **Height and colour** show, hour by hour, how far the zone's consumption sits from normal:
  the national load against the review's ordinary-day reference (same weekday type, comparable
  temperature, earlier days only), times the zone's share of the total against its usual share (the
  median of the same hour over the 4 previous same weekdays that were ordinary). A national holiday
  lowers the whole country; a cantonal one lowers its zones further. GL and VS follow the national
  term only: their published consumption includes the pumping of storage plants.
* **Panel**: whether the detector flagged the day, the review's verdict, and for a flagged day the
  model's written review (2025-2026: the test predictions plus ``sgcot-review-export --all-days``
  run through ``train/predict.py``).
"""

import argparse
import base64
import datetime as dt
import gzip
import hashlib
import json
import shutil
import sqlite3
import struct
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.path import Path as Polygon

from swissgrid_cot.ingest.zones import OUT as ZONES_FILE
from swissgrid_cot.ingest.zones import ZONES
from swissgrid_cot.review.hourly import day_matrix

REPO = Path(__file__).resolve().parents[1]
PROCESSED = REPO / "data" / "processed"
GEO = REPO / "data" / "raw" / "geo"
TEMPLATE = REPO / "demo" / "template.html"
OUT = REPO / "demo" / "index.html"
ARTIFACT = REPO / "scratch" / "map_artifact.html"
FIRST_DAY = "2025-01-01"
START = "2026-01-10"
"""The day shown when the page opens: a flagged Saturday 11 % above normal that the review keeps."""
SOURCES = {
    "ch-combined-2021.json": ("https://unpkg.com/swiss-maps@4.5.0/2021/ch-combined.json",
                              "ce95c7364e18dbed304d51094bf43e83cefbfc4492dd7d788a9a6f5c466cbfd9"),
    "kontur_population_CH_20231101.gpkg.gz": (
        "https://geodata-eu-central-1-kontur-public.s3.amazonaws.com/kontur_datasets/kontur_population_CH_20231101.gpkg.gz",
        "848dd2d07eb905cdf020c84242a6530d4e4679944adf1c428e9b349d13aefc69"),
}  # fmt: skip
CANTONS = ("ZH", "BE", "LU", "UR", "SZ", "OW", "NW", "GL", "ZG", "FR", "SO", "BS", "BL",
           "SH", "AR", "AI", "SG", "GR", "AG", "TG", "TI", "VD", "VS", "NE", "GE", "JU")  # fmt: skip
"""Canton abbreviations by BFS number (1-26), the ids of the swiss-maps cantons."""
PUMPED = ("GL", "VS")
DEV_STEP = 0.005
"""Deviations are stored as int8 in steps of 0.5 %, clipped to +-60 %."""
SKELETON = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>:root{{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0}}[hidden]{{display:none!important}}</style>
</head>
<body>
{page}
</body>
</html>
"""


def fetch(name: str) -> Path:
    path = GEO / name
    url, digest = SOURCES[name]
    if not path.exists():
        GEO.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url) as r, open(path, "wb") as f:
            shutil.copyfileobj(r, f)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError(f"{path} does not match its sha256; delete it to download it again")
    return path


def topo_layers(path: Path) -> dict[str, list[tuple[int, list[list[np.ndarray]]]]]:
    """Decode a quantized TopoJSON into (id, polygons as rings of lon/lat points) per layer."""
    topo = json.loads(path.read_text(encoding="utf-8"))
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = [np.cumsum(np.array(a, dtype=float), axis=0) * (sx, sy) + (tx, ty) for a in topo["arcs"]]

    def ring(ids: list[int]) -> np.ndarray:
        parts = [arcs[i] if i >= 0 else arcs[~i][::-1] for i in ids]
        return np.concatenate([parts[0], *(p[1:] for p in parts[1:])])

    out = {}
    for name, obj in topo["objects"].items():
        out[name] = []
        for g in obj["geometries"]:
            polys = [g["arcs"]] if g["type"] == "Polygon" else g["arcs"]
            out[name].append((g.get("id"), [[ring(r) for r in p] for p in polys]))
    return out


def gpkg_centres(path: Path) -> tuple[list[str], np.ndarray, np.ndarray]:
    """H3 cell ids, populations and lon/lat centres (from each geometry's envelope) of the Kontur cells."""
    db = path.with_suffix("")
    if not db.exists():
        with gzip.open(path) as src, open(db, "wb") as dst:
            shutil.copyfileobj(src, dst)
    rows = sqlite3.connect(db).execute("select h3, population, geom from population").fetchall()
    ids, pop, xy = [], [], []
    for h3, p, blob in rows:
        flags = blob[3]
        if (flags >> 1) & 7 != 1:
            raise ValueError("expected a GeoPackage envelope [minx, maxx, miny, maxy]")
        minx, maxx, miny, maxy = struct.unpack("<4d" if flags & 1 else ">4d", blob[8:40])
        ids.append(h3)
        pop.append(p)
        xy.append(((minx + maxx) / 2, (miny + maxy) / 2))
    xy = np.array(xy)
    r = 6378137.0  # EPSG:3857 -> lon/lat
    lonlat = np.column_stack([np.degrees(xy[:, 0] / r), np.degrees(2 * np.arctan(np.exp(xy[:, 1] / r)) - np.pi / 2)])
    return ids, np.array(pop), lonlat


def parent7(h3: str) -> str:
    """The resolution-7 parent of a resolution-8 H3 cell: resolution field to 7, digit 8 unused (7)."""
    i = int(h3, 16)
    i = (i & ~(0xF << 52)) | (7 << 52) | (7 << (3 * (15 - 8)))
    return f"{i:x}"


def cells(geo: dict, ids: list[str], pop: np.ndarray, lonlat: np.ndarray) -> list[list]:
    """[H3 id, population, zone index] per resolution-7 cell with people."""
    zone_of = {c: z for z, name in enumerate(ZONES.values()) for c in name.split("+")}
    canton = np.full(len(ids), -1)
    for cid, polys in geo["cantons"]:
        for outer, *holes in polys:
            inside = Polygon(outer).contains_points(lonlat)
            for h in holes:
                inside &= ~Polygon(h).contains_points(lonlat)
            canton[inside & (canton < 0)] = cid - 1
    df = pd.DataFrame({"cell": [parent7(h) for h in ids], "pop": pop, "canton": canton})
    df = df[df.canton >= 0]
    df["zone"] = [zone_of[CANTONS[c]] for c in df.canton]
    by_zone = df.groupby(["cell", "zone"])["pop"].sum().reset_index().sort_values("pop", ascending=False)
    zone = by_zone.drop_duplicates("cell").set_index("cell")["zone"]
    total = df.groupby("cell")["pop"].sum()
    return [[c, round(float(p)), int(zone[c])] for c, p in total.items() if p >= 1]


def outlines(geo: dict) -> dict:
    def rings(layer: str) -> list:
        return [[np.round(r, 4).tolist() for r in p] for _, polys in geo[layer] for p in polys]

    return {"country": rings("country"), "cantons": rings("cantons"), "lakes": rings("lakes")}


def zone_deviation(days: dict[str, dict], dates: list[str]) -> np.ndarray:
    """Deviation from normal, days x hours x zones (see the module docstring)."""
    hourly = pd.read_parquet(ZONES_FILE)
    names = list(ZONES.values())
    hourly["total"] = hourly[names].sum(axis=1)
    total = day_matrix(hourly, "total")
    usual = {d for d, r in days.items() if not r["flagged"] and r["context"]["kind"] == "ordinary"
             and r["context"]["period"] == "regular"}  # fmt: skip
    out = np.zeros((len(dates), 24, len(names)))
    for k, name in enumerate(names):
        share = day_matrix(hourly, name) / total
        for i, date in enumerate(dates):
            r = days[date]
            national = np.array(r["load_mw"]) / np.array(r["normal_reference_mw"])
            if name in PUMPED:
                out[i, :, k] = national - 1
                continue
            d = pd.Timestamp(date)
            prev = [d - pd.Timedelta(weeks=w) for w in range(1, 13)]
            prev = [p for p in prev if p in share.index and p.date().isoformat() in usual][:4]
            ratio = share.loc[d].to_numpy() / share.loc[prev].median().to_numpy() if prev else 1.0
            out[i, :, k] = national * ratio - 1
    return np.nan_to_num(out)


def read_predictions(paths: list[Path]) -> dict[str, str]:
    preds = {}
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:  # a file still being written may end with a partial line
                p = json.loads(line)
            except json.JSONDecodeError:
                continue
            preds[p["sample_id"]] = p["generated"]
    return preds


def day_record(r: dict, model_text: str | None) -> dict:
    c, v = r["context"], r["review"]
    d = dt.date.fromisoformat(r["date"])
    special = [p for p in (
        f"{c['holiday_name']} ({100 * c['holiday_pop_share']:.0f}% of the population)"
        if c["holiday_name"] and c["holiday_pop_share"] > 0 else None,
        "bridge day" if c["kind"] == "bridge_day" else None,
        {"christmas": "Christmas holidays", "summer": "summer holidays"}.get(c["period"]),
    ) if p]  # fmt: skip
    return {
        "date": r["date"], "title": f"{d.strftime('%A')} {d.day} {d.strftime('%B %Y')}",
        "context": ", ".join(special), "flagged": r["flagged"], "z": c["z"], "rel_dev_pct": c["rel_dev_pct"],
        "temp_c": c["temp_c"], "temp_normal_c": c["temp_normal_c"],
        "outcome": v["outcome"] if r["flagged"] else None, "hours": v["review_hours"] if r["flagged"] else [],
        "load": [round(x) for x in r["load_mw"]], "normal": [round(x) for x in r["normal_reference_mw"]],
        "model_text": model_text if r["flagged"] else None,
    }  # fmt: skip


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--predictions", type=Path, nargs="*", default=[],
                        help="OpenTSLM prediction files (sample_id, generated); later files add days")  # fmt: skip
    args = parser.parse_args()

    geo = topo_layers(fetch("ch-combined-2021.json"))
    ids, pop, lonlat = gpkg_centres(fetch("kontur_population_CH_20231101.gpkg.gz"))
    days = {}
    with open(PROCESSED / "review" / "days.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            days[r["date"]] = r
    zones_end = pd.read_parquet(ZONES_FILE, columns=["local_date"]).local_date.max().date().isoformat()
    dates = [d for d in sorted(days) if FIRST_DAY <= d <= zones_end and days[d]["normal_reference_mw"]]
    dev = np.clip(np.round(zone_deviation(days, dates) / DEV_STEP), -120, 120).astype(np.int8)
    preds = read_predictions(args.predictions)

    data = {
        "zones": list(ZONES.values()), "pumped": list(PUMPED), "dev_step": DEV_STEP,
        "cells": cells(geo, ids, pop, lonlat), "outlines": outlines(geo),
        "days": [day_record(days[d], preds.get(f"{d}/real")) for d in dates],
        "dev": base64.b64encode(dev.tobytes()).decode(), "start": START,
    }  # fmt: skip
    page = TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
    OUT.write_text(SKELETON.format(page=page), encoding="utf-8")
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(page, encoding="utf-8")
    flagged = sum(r["flagged"] for r in data["days"])
    with_text = sum(r["model_text"] is not None for r in data["days"])
    print(f"{len(data['cells'])} cells, {len(dates)} days ({flagged} flagged, {with_text} with the model's review)")
    print(f"wrote {OUT} and {ARTIFACT} ({len(page) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
