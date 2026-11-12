"""Diagnostic plots for the Phase 2 checkpoint: ``uv run python -m swissgrid_cot.ingest.plots``."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from swissgrid_cot.sources import PROCESSED_DIR, REPO_ROOT

OUT = REPO_ROOT / "reports" / "phase2"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.6,
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "legend.frameon": False,
})  # fmt: skip


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=130)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(PROCESSED_DIR / "ch_hourly.parquet")
    daily = df.groupby("local_date").agg(
        load=("load_enduser_mw", "mean"),
        temp=("temp_c", "mean"),
        rad=("radiation_wm2", "mean"),
        dow=("dow", "first"),
        hol=("is_holiday", "first"),
    )

    # 1. Daily load and temperature, stacked panels on one time axis.
    fig, (a, b) = plt.subplots(2, 1, figsize=(11, 5.2), sharex=True, height_ratios=[3, 2])
    a.plot(daily.index, daily.load, color=SERIES[0], linewidth=0.9)
    a.set_title("Daily mean end-user consumption, Switzerland (MW)")
    b.plot(daily.index, daily.temp, color=SERIES[1], linewidth=0.9)
    b.axhline(0, color=INK2, linewidth=0.6)
    b.set_title("Daily mean population-weighted temperature (°C)")
    _save(fig, "01_daily_load_temp.png")

    # 2. Mean weekday intraday profile per year, local time: label alignment check.
    fig, ax = plt.subplots(figsize=(8, 4.2))
    wk = df[(df.dow < 5) & ~df.is_holiday]
    for i, (year, g) in enumerate(wk.groupby("year")):
        p = g.groupby("local_hour").load_enduser_mw.mean()
        ax.plot(p.index, p.values, color=SERIES[i], label=str(year))
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("local hour (start)")
    ax.set_title("Mean working-day profile by year (MW): ramps align across label conventions")
    ax.legend(ncol=6, loc="upper left")
    _save(fig, "02_intraday_profile_by_year.png")

    # 3. Load vs temperature, daily, working days vs weekends/holidays.
    fig, ax = plt.subplots(figsize=(7, 4.6))
    work = (daily.dow < 5) & ~daily.hol
    ax.scatter(daily.temp[work], daily.load[work], s=9, color=SERIES[0], alpha=0.6, label="working day", linewidths=0)
    ax.scatter(
        daily.temp[~work], daily.load[~work], s=9, color=SERIES[1], alpha=0.6, label="weekend / holiday", linewidths=0
    )
    ax.set_xlabel("daily mean temperature (°C)")
    ax.set_ylabel("daily mean end-user load (MW)")
    ax.set_title("Consumption falls with temperature; the cooling uptick is weak")
    ax.legend()
    _save(fig, "03_load_vs_temp.png")

    # 4. DST transition days: 23 and 25 local hours, no gap or spike.
    days = [d for d in pd.to_datetime(["2024-03-31", "2024-10-27", "2025-03-30", "2025-10-26"])]
    fig, axes = plt.subplots(1, 4, figsize=(12, 3), sharey=True)
    for ax, d in zip(axes, days, strict=True):
        win = df[(df.local_date >= d - pd.Timedelta("1D")) & (df.local_date <= d + pd.Timedelta("1D"))]
        ax.plot(win.index, win.load_enduser_mw, color=SERIES[0], linewidth=1.2, marker="o", markersize=2.2)
        day = df[df.local_date == d]
        ax.axvspan(day.index.min(), day.index.max() + pd.Timedelta("1h"), color=GRID, alpha=0.6, linewidth=0)
        ax.set_title(f"{d.date()} ({len(day)} h)")
        ax.tick_params(axis="x", labelrotation=45, labelsize=7)
    axes[0].set_ylabel("MW (UTC axis)")
    _save(fig, "04_dst_days.png")

    # 5. Monthly net import per border (positive = import into CH), small multiples.
    m = df.groupby(df.local_date.dt.to_period("M"))[[f"net_import_{b}_mw" for b in ("at", "de", "fr", "it")]].mean()
    m.index = m.index.to_timestamp()
    fig, axes = plt.subplots(5, 1, figsize=(11, 8), sharex=True)
    total = m.sum(axis=1)
    axes[0].bar(total.index, total, width=25, color=[SERIES[0] if v >= 0 else SERIES[1] for v in total])
    axes[0].set_title("Net import, all borders (MW, monthly mean; + import, − export)")
    for ax, b in zip(axes[1:], ("AT", "DE", "FR", "IT"), strict=True):
        s = m[f"net_import_{b.lower()}_mw"]
        ax.bar(s.index, s, width=25, color=[SERIES[0] if v >= 0 else SERIES[1] for v in s])
        ax.set_title(f"{b}", fontsize=9)
    for ax in axes:
        ax.axhline(0, color=INK2, linewidth=0.6)
    _save(fig, "05_net_import_by_border.png")

    print("wrote", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
