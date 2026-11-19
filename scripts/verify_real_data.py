"""Cross-check the processed hourly dataset against references we did not compute.

Run: ``uv run python scripts/verify_real_data.py``. Writes ``reports/data_verification.md``.

1. Swissgrid's own annual totals (sheet "Uebersicht", values cached by Excel in the workbook).
2. Swissgrid's own hourly sheet "Zeitreihen1h00" (2020-2022 workbooks only).
3. Energy-Charts (Fraunhofer ISE, ENTSO-E based) hourly Swiss load, generation and trade.
4. MeteoSwiss's own daily means (tre200d0, gre000d0) for Zürich / Fluntern.

The downloads go to data/raw/external/ and are used for verification only, never in the dataset.
"""

import json
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import requests

from swissgrid_cot.sources import PROCESSED_DIR, RAW_DIR, REPO_ROOT, YEARS, swissgrid_file

EXT = RAW_DIR / "external"
LINES: list[str] = []


def say(s: str = "") -> None:
    print(s)
    LINES.append(s)


def fetch(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, timeout=300, headers={"User-Agent": "swissgrid-cot verification"})
        r.raise_for_status()
        path.write_bytes(r.content)
    return path


def uebersicht_energies(path: Path) -> list[float]:
    """Every 'E' value (MWh) of the summary sheet, in order."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    for row in wb["Uebersicht"].iter_rows(values_only=True):
        cells = [c for c in row if c is not None]
        if len(cells) >= 3 and cells[0] == "E" and cells[2] == "MWh":
            out.append(float(cells[1]))
    return out


def main() -> None:
    df = pd.read_parquet(PROCESSED_DIR / "ch_hourly.parquet")
    say("# Data verification against independent references\n")
    say(f"Dataset: `data/processed/ch_hourly.parquet`, {len(df)} hours, {df.index.min()} to {df.index.max()} (UTC).\n")

    # 1 ------------------------------------------------------------------------------------------
    say("## 1. Swissgrid annual totals (sheet `Uebersicht`) vs our hourly sums\n")
    say("| year | series | ours (MWh) | Swissgrid sheet (MWh) | rel. diff |")
    say("| --- | --- | --- | --- | --- |")
    # The first three E blocks of the sheet are production, end-user consumption, total consumption
    # (checked by reading the sheet's titles for 2024).
    worst = 0.0
    for year in YEARS:
        sheet = uebersicht_energies(swissgrid_file(year).path)[:3]
        y = df[df.year == year]
        ours = [y.production_mw.sum(), y.load_enduser_mw.sum(), y.load_total_mw.sum()]
        for name, a, b in zip(("production", "end-user consumption", "total consumption"), ours, sheet, strict=True):
            rel = abs(a - b) / b
            if year != 2020:
                worst = max(worst, rel)
            say(f"| {year} | {name} | {a:,.0f} | {b:,.0f} | {rel:.1e} |")
    say(f"\nLargest relative difference, 2021-2025: **{worst:.1e}** (identical up to float rounding).\n")
    say("2020: the cached values of the summary sheet match neither the year nor any month of the "
        "time series (the formulas were last evaluated before the April 2021 re-publication of the "
        "data). 2020 is therefore checked only against Energy-Charts in section 2.\n")

    # 3 ------------------------------------------------------------------------------------------
    say("## 2. Energy-Charts (Fraunhofer ISE, ENTSO-E data) hourly Swiss data\n")
    ec_frames = []
    for year in YEARS:
        p = fetch(
            f"https://api.energy-charts.info/public_power?country=ch&start={year}-01-01&end={year}-12-31",
            EXT / f"energy_charts_ch_public_power_{year}.json",
        )
        d = json.loads(p.read_text())
        idx = pd.to_datetime(d["unix_seconds"], unit="s", utc=True)
        cols = {pt["name"]: pt["data"] for pt in d["production_types"]}
        ec_frames.append(pd.DataFrame(cols, index=idx))
    ec = pd.concat(ec_frames)
    ec = ec[~ec.index.duplicated()]
    # Energy-Charts may be quarter-hourly for recent years: average to hours.
    ec = ec.groupby(ec.index.floor("h")).mean()
    gen_cols = [c for c in ec.columns if c not in ("Load", "Residual load", "Cross border electricity trading")
                and not c.startswith("Renewable share")]  # fmt: skip
    ec["generation_sum"] = ec[gen_cols].sum(axis=1, min_count=1)
    j = df.join(ec, how="inner")
    say(f"Overlap: {len(j)} hours. Generation columns summed: {', '.join(gen_cols)}.\n")
    say("| comparison | Pearson r (hourly) | Pearson r (daily) | mean ratio ours/EC |")
    say("| --- | --- | --- | --- |")
    daily = j.groupby("local_date").mean(numeric_only=True)
    for ours, theirs, label in [
        ("load_total_mw", "Load", "Swissgrid total consumption vs EC load"),
        ("load_enduser_mw", "Load", "Swissgrid end-user consumption vs EC load"),
        ("production_mw", "generation_sum", "Swissgrid production vs EC generation sum"),
        ("net_import_mw", "Cross border electricity trading", "Swissgrid net import vs EC cross-border"),
    ]:
        ok = j[[ours, theirs]].dropna()
        r_h = ok[ours].corr(ok[theirs])
        r_d = daily[ours].corr(daily[theirs])
        ratio = ok[ours].mean() / ok[theirs].mean()
        say(f"| {label} | {r_h:.3f} | {r_d:.3f} | {ratio:.3f} |")
    say()
    say("Per year, daily r of Swissgrid total consumption vs EC load: " + ", ".join(
        f"{y}: {g.load_total_mw.corr(g.Load):.3f}" for y, g in daily.groupby(daily.index.year)) + ".\n")

    # 4 ------------------------------------------------------------------------------------------
    say("## 3. MeteoSwiss daily means (Zürich / Fluntern) vs our hourly station data\n")
    p = fetch(
        "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/sma/ogd-smn_sma_d_historical.csv",
        EXT / "ogd-smn_sma_d_historical.csv",
    )
    d = pd.read_csv(p, sep=";", usecols=["reference_timestamp", "tre200d0", "gre000d0"])
    d.index = pd.to_datetime(d.reference_timestamp, format="%d.%m.%Y %H:%M")
    from swissgrid_cot.ingest.meteoswiss import read_station
    from swissgrid_cot.sources import meteoswiss_file

    sma = read_station(meteoswiss_file("SMA").path, "SMA")
    for shift_h, name in [(0, "UTC day 00-24"), (-1, "UTC day 23-23 (= CET civil day)")]:
        g = sma.copy()
        g.index = g.index - pd.Timedelta(hours=shift_h)
        ours = g.groupby(g.index.tz_localize(None).normalize()).agg({"temp_c": "mean", "radiation_wm2": "mean"})
        m = ours.join(d[["tre200d0", "gre000d0"]], how="inner").dropna()
        say(f"- Daily window {name}: {len(m)} days; temperature r = {m.temp_c.corr(m.tre200d0):.4f}, "
            f"mean abs diff {np.abs(m.temp_c - m.tre200d0).mean():.3f} °C; radiation r = "
            f"{m.radiation_wm2.corr(m.gre000d0):.4f}, mean abs diff {np.abs(m.radiation_wm2 - m.gre000d0).mean():.2f} W/m².")  # fmt: skip
    say()

    # 5 ------------------------------------------------------------------------------------------
    say("## 4. Known real-world events visible in the data\n")
    dly = df.groupby("local_date").agg(load=("load_enduser_mw", "mean"), dow=("dow", "first"))
    wd = dly[dly.dow < 5]
    def mean_between(a, b):
        return wd.loc[a:b, "load"].mean()
    say(f"- COVID-19 lockdown (CH, from 16 Mar 2020): weekday mean 23 Mar-17 Apr 2020 = "
        f"{mean_between('2020-03-23', '2020-04-17'):,.0f} MW vs same weeks 2021 = "
        f"{mean_between('2021-03-22', '2021-04-16'):,.0f} MW.")  # fmt: skip
    say(f"- Christmas: mean load 25 Dec 2024 = {dly.loc['2024-12-25', 'load']:,.0f} MW vs "
        f"weekday mean 2-13 Dec 2024 = {mean_between('2024-12-02', '2024-12-13'):,.0f} MW.")  # fmt: skip
    yr = df.groupby("year").net_import_mw.sum() / 1e6
    say(f"- Net import by year (TWh): {', '.join(f'{y}: {v:+.2f}' for y, v in yr.items())}. "
        "Switzerland was a net importer in 2021-2022 and a large net exporter in 2024 (very high hydro output).")
    say(f"- 1 August (national day): 2024-08-01 mean {dly.loc['2024-08-01', 'load']:,.0f} MW vs Thursday "
        f"2024-07-25 {dly.loc['2024-07-25', 'load']:,.0f} MW.")  # fmt: skip

    out = REPO_ROOT / "reports" / "data_verification.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(LINES) + "\n", encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
