"""Annotate the hourly dataset: baseline, anomalies, causes, weekly Q/A.

Usage::

    uv run sgcot-annotate

Reads ``data/processed/ch_hourly.parquet`` and writes to ``data/processed/annotations/``:
``days.parquet`` (one scored row per day), ``windows.jsonl`` (one row per week with its facts, prompts
and rationales), ``summary.json``, and the reports in ``reports/phase3/``.
"""

import json
import random

import pandas as pd

from swissgrid_cot.annotate.anomalies import events, threshold_table
from swissgrid_cot.annotate.qa import build_window, rolling_weeks, window_facts
from swissgrid_cot.annotate.run import annotate
from swissgrid_cot.sources import PROCESSED_DIR, REPO_ROOT

OUT = PROCESSED_DIR / "annotations"
REPORT = REPO_ROOT / "reports" / "phase3"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    hourly = pd.read_parquet(PROCESSED_DIR / "ch_hourly.parquet")
    result = annotate(hourly)
    scored, baseline, scale, windows = result.days, result.baseline, result.scale, result.windows
    scored.to_parquet(OUT / "days.parquet")
    with open(OUT / "windows.jsonl", "w", encoding="utf-8") as f:
        for w in windows:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")
    # Train-only augmentation: a 7-day window starting on every train day (not part of TimeNet).
    rolling = [build_window(window_facts(w, scored, hourly)) for w in rolling_weeks(scored, "train")]
    with open(OUT / "windows_rolling_train.jsonl", "w", encoding="utf-8") as f:
        for w in rolling:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")

    fit = scored[scored.split == "train"]
    accuracy = {
        split: {
            "mape_ordinary_days_pct": round(float(100 * g[~g.special_day].rel_dev.abs().mean()), 2),
            "bias_ordinary_days_pct": round(float(100 * g[~g.special_day].rel_dev.mean()), 2),
        }
        for split, g in scored.groupby("split")
    }
    wdf = pd.DataFrame([{"split": w["split"], "label": w["label"], "n_anom": len(w["anomalous_dates"]),
                         "exchange": w["exchange_answer"]} for w in windows])  # fmt: skip
    summary = {
        "baseline_fit_days": baseline.n_fit_days,
        "baseline_coefficients_non_profile": {
            k: v for k, v in baseline.named_coefficients().items() if "_" not in k or k in (
                "hdd_lag1", "radiation_wm2", "trend_years")},  # fmt: skip
        "residual_scale": {"median": round(scale.median, 5), "robust_sd": round(scale.robust_sd, 5)},
        "baseline_accuracy": accuracy,
        "anomalous_days_by_cause_and_split": pd.crosstab(
            scored[scored.is_anomaly].cause, scored[scored.is_anomaly].split).to_dict(),  # fmt: skip
        "n_events": len(events(scored)),
        "n_windows": len(windows),
        "n_rolling_train_windows": len(rolling),
        "rolling_train_label_counts": pd.Series([w["label"] for w in rolling]).value_counts().to_dict(),
        "windows_by_split": wdf.split.value_counts().to_dict(),
        "window_label_by_split": pd.crosstab(wdf.label, wdf.split).to_dict(),
        "windows_with_anomaly_by_split": wdf[wdf.n_anom > 0].split.value_counts().to_dict(),
        "exchange_answer_by_split": pd.crosstab(wdf.exchange, wdf.split).to_dict(),
        "n_fit_days_note": f"train ordinary days, {fit.index.min().date()} to {fit.index.max().date()}",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    threshold_table(scored).to_markdown(REPORT / "threshold_table.md", index=False)

    rng = random.Random(20261112)
    sample = rng.sample(windows, 20)
    with open(REPORT / "samples_20.md", "w", encoding="utf-8") as f:
        for w in sorted(sample, key=lambda w: w["window_id"]):
            f.write(f"## {w['window_id']} ({w['split']}) label `{w['label']}`, "
                    f"anomalous days {w['anomalous_dates'] or 'none'}\n\n")  # fmt: skip
            for task in ("anomaly_cause", "anomaly_days", "exchange"):
                f.write(f"**{task}**\n\n> Q: {w['prompts'][task]}\n\n> A: {w['rationales'][task]}\n\n")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
