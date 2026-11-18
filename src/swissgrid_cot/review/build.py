"""Review every day of 2020-2026 at hourly resolution; the flagged days are the alerts.

Usage::

    uv run sgcot-review

Reads ``ch_hourly.parquet`` (and ``ch_hourly_holdout.parquet`` when present). Writes
``data/processed/review/days.jsonl`` (one reviewed day per line: context, the 24 local hours of load,
the references, the review), ``data/processed/review/calibration.json`` and
``reports/review/summary.md``. Unflagged days are reviewed too: the training samples use them.
"""

import json
from dataclasses import replace

import numpy as np
import pandas as pd

from swissgrid_cot.annotate.anomalies import residual_scale
from swissgrid_cot.review.assess import Calibration, calibrate, residuals_for_calibration, review_day
from swissgrid_cot.review.context import context_of, load_hourly, scored_days
from swissgrid_cot.review.hourly import day_matrix, dst_adjusted, format_windows
from swissgrid_cot.review.references import ReferenceBuilder, as_list
from swissgrid_cot.sources import PROCESSED_DIR, REPO_ROOT

OUT = PROCESSED_DIR / "review"
REPORT = REPO_ROOT / "reports" / "review"


class Reviewer:
    """Everything needed to review any day, including a day whose curve is replaced (simulations)."""

    def __init__(self):
        hourly = load_hourly()
        self.days = scored_days(hourly)
        self.load = day_matrix(hourly)
        self.dst = dst_adjusted(hourly)
        self.builder = ReferenceBuilder(self.days, self.load)
        self.cal = calibrate(residuals_for_calibration(self.builder, self.days, self.load))
        self.scale = residual_scale(self.days, self.days.rel_dev)

    def dates(self) -> list[pd.Timestamp]:
        ok = self.load.reindex(self.days.index).notna().all(axis=1) & self.days.z.notna()
        return list(self.days.index[ok])

    def row(self, date: pd.Timestamp, values: np.ndarray | None = None) -> dict:
        """Review a day. ``values`` replaces its 24 hours of load; the calendar and weather stay, and the
        daily mean, deviation and z-score follow the new curve."""
        ctx = context_of(self.days.loc[date])
        if values is None:
            values = self.load.loc[date].to_numpy()
        else:
            rel = float(values.mean()) / ctx.expected_mw - 1
            z = (rel - self.scale.median) / self.scale.robust_sd
            ctx = replace(ctx, load_mw=float(values.mean()), rel_dev=rel, z=z)
        b = self.builder
        ref, normal, cands = b.context(date), b.normal(date), b.profiles(date)
        rev = review_day(ctx, values, ref, normal, cands, self.cal, float(b.level.at[date]))
        mean = float(values.mean())
        return {
            "date": date.date().isoformat(),
            "split": self.days.at[date, "split"],
            "flagged": bool(self.days.at[date, "is_anomaly"]),
            "cause": self.days.at[date, "cause"],
            "dst_adjusted": bool(self.dst.get(date, False)),
            "context": {
                "weekday": ctx.weekday, "kind": ctx.kind, "period": ctx.period,
                "holiday_name": ctx.holiday_name, "holiday_pop_share": ctx.holiday_pop_share,
                "temp_c": round(ctx.temp_c, 1), "temp_normal_c": round(ctx.temp_normal_c, 1),
                "expected_mw": round(ctx.expected_mw, 0), "load_mw": round(ctx.load_mw, 0),
                "rel_dev_pct": round(100 * ctx.rel_dev, 1), "z": round(ctx.z, 2),
                "description": ctx.describe(),
            },
            "load_mw": as_list(values),
            "context_reference_mw": as_list(ref.curve),
            "normal_reference_mw": as_list(normal.curve),
            "profiles_mw": {k: as_list(None if v is None else v * mean) for k, v in cands.items()},
            "comparable_dates": [d.date().isoformat() for d in ref.dates],
            "review": rev.to_dict(),
        }  # fmt: skip


def reviewed_days() -> tuple[list[dict], Calibration]:
    r = Reviewer()
    return [r.row(d) for d in r.dates()], r.cal


def summary(rows: list[dict], cal: Calibration) -> str:
    df = pd.DataFrame([{
        "split": r["split"], "flagged": r["flagged"], "outcome": r["review"]["outcome"],
        "kind": r["context"]["kind"], "period": r["context"]["period"], "profile": r["review"]["profile"],
        "tie": r["review"]["profile_tie"]} for r in rows])  # fmt: skip
    f = df[df.flagged]
    lines = ["# Alert review: outcomes of the flagged days", ""]
    lines.append("Flagged days (|z| >= 3) by split and outcome:\n")
    lines.append(pd.crosstab(f.split, f.outcome, margins=True).to_markdown())
    lines.append("\nFlagged days by context and outcome:\n")
    lines.append(pd.crosstab([f.kind, f.period], f.outcome).to_markdown())
    lines.append("\nProfile of the flagged days (ties apart):\n")
    lines.append(pd.crosstab(f.split, f.profile.where(~f.tie, "tie")).to_markdown())
    lines.append("\nAll reviewed days by split and outcome (training pool included):\n")
    lines.append(pd.crosstab(df.split, df.outcome, margins=True).to_markdown())
    lines.append("\nCalibration (train years 2021-2023): robust spread of the day-level residual "
                 f"{ {g: round(100 * v, 2) for g, v in cal.day_sd.items()} } %, days {cal.n_days}; "
                 "hourly localized spreads (%): "
                 + "; ".join(f"{g}: {np.round(100 * np.array(v), 2).tolist()}" for g, v in cal.hour_sd.items()))
    lines.append("\nFlagged days where a deviation remains:\n")
    for r in rows:
        if r["flagged"] and r["review"]["outcome"] == "deviation_remains":
            v = r["review"]
            lines.append(f"- {r['date']} ({r['split']}, {r['context']['description']}): day residual "
                         f"{v['day_residual_pct']}% (z {v['day_residual_z']}), hours "
                         f"{format_windows(v['review_hours'])}, recent level {v['recent_level_pct']:+.1f}%")  # fmt: skip
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    rows, cal = reviewed_days()
    with open(OUT / "days.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (OUT / "calibration.json").write_text(json.dumps(cal.__dict__, indent=1) + "\n")
    text = summary(rows, cal)
    (REPORT / "summary.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
