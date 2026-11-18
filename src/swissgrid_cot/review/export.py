"""Export the alert-review samples for OpenTSLM.

Usage::

    uv run sgcot-review-export
    uv run sgcot-review-export --all-days 2025 2026   # every day, for the demo

Writes ``data/processed/opentslm_review/{train,validation,test}.jsonl`` in the format the stage 6
dataset reads (``pre_prompt, series, post_prompt, answer``), plus ``target`` and ``set``.

Sets (the ``set`` field):

* ``real``: real days, reviewed as they are. In validation and test, only alerts are kept: the
  flagged days (|z| >= 3) and the near-alerts (2 <= |z| < 3), told apart by ``flagged``.
* ``simulated``: a real day that the review finds consistent, with a deviation added to its curve:
  hours a..b multiplied by (1 + delta), 3 to 8 hours, |delta| 6-15 %, or the whole day by 8-14 %.
  The labels come from reviewing the modified curve with the same rules. Always labelled simulated.
* ``curve_swap`` (2025 and 2026 only), the controlled curve test: pairs of real alerts in the same calendar
  context (same kind and period). Each day keeps its text and references and receives the other
  day's curve, rescaled to its own daily mean; the labels come from reviewing that curve. If the
  answer follows the curve, it changes with it; if it follows the text, it does not.

Splits: train 2020-2023 (consistent ordinary days of the regular period that are not near-alerts
subsampled to 40 %, insufficient-evidence days to 35 %),
validation 2024, test 2025 (exploratory: its alerts were inspected while the review was designed)
and 2026 (holdout, ``split`` = holdout: nobody looked at it). The test file holds both test and
holdout rows; ``split`` tells them apart.
"""

import argparse
import json
import random

import numpy as np
import pandas as pd

from swissgrid_cot.review import samples
from swissgrid_cot.review.build import Reviewer
from swissgrid_cot.sources import PROCESSED_DIR

OUT = PROCESSED_DIR / "opentslm_review"
SEED = 20261118
TRAIN_ORDINARY_KEEP = 0.4
TRAIN_INSUFFICIENT_KEEP = 0.35
"""Insufficient evidence is stated by the prompt itself (too few comparable days); a third of those
days is enough to learn the answer."""
SIM_PER_CONSISTENT = {"train": 0.6, "validation": 0.25, "test": 0.25, "holdout": 0.25}
NEAR_ALERT_Z = 2.0


def inject(values: np.ndarray, rng: random.Random) -> np.ndarray:
    out = values.copy()
    if rng.random() < 0.25:
        out *= 1 + rng.choice((-1, 1)) * rng.uniform(0.08, 0.14)
        return out
    length = rng.randint(3, 8)
    start = rng.randint(0, 24 - length)
    out[start : start + length] *= 1 + rng.choice((-1, 1)) * rng.uniform(0.06, 0.15)
    return out


def to_sample(row: dict, sample_id: str, set_name: str, extra: dict | None = None) -> dict:
    return {
        "id": sample_id,
        "task": "alert_review",
        "split": row["split"],
        "set": set_name,
        "date": row["date"],
        "flagged": row["flagged"],
        "pre_prompt": samples.pre_prompt(row),
        "series": samples.series(row),
        "post_prompt": samples.POST_PROMPT,
        "answer": samples.rationale(row),
        "target": samples.target(row),
        "context": row["context"],
        **(extra or {}),
    }


def swap_pairs(rows: dict[str, dict], dates: list[str]) -> list[tuple[str, str]]:
    """Pair alerts of the same kind and period whose reviews differ in outcome or profile."""
    pairs = []
    by_ctx: dict[tuple, list[str]] = {}
    for d in dates:
        c = rows[d]["context"]
        by_ctx.setdefault((c["kind"], c["period"]), []).append(d)
    for group in by_ctx.values():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                ra, rb = rows[a]["review"], rows[b]["review"]
                if ra["outcome"] == "insufficient_evidence" or rb["outcome"] == "insufficient_evidence":
                    continue
                if (ra["outcome"], ra["profile"]) != (rb["outcome"], rb["profile"]):
                    pairs.append((a, b))
    return pairs


def export_days(years: list[int], out_dir) -> None:
    """Every real day of ``years`` as a test sample (for the demo, which shows the model on each day)."""
    rv = Reviewer()
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [rv.row(d) for d in rv.dates() if d.year in years]
    with open(out_dir / "test.jsonl", "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(to_sample(row, f"{row['date']}/real", "real"), ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} days of {years} to {out_dir / 'test.jsonl'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all-days", type=int, nargs="+", metavar="YEAR",
                        help="instead: every day of these years, to data/processed/opentslm_review_days/")  # fmt: skip
    args = parser.parse_args()
    if args.all_days:
        export_days(args.all_days, PROCESSED_DIR / "opentslm_review_days")
        return
    rng = random.Random(SEED)
    rv = Reviewer()
    rows = {d.date().isoformat(): rv.row(d) for d in rv.dates()}
    split_file = {"train": "train", "validation": "validation", "test": "test", "holdout": "test"}
    out: dict[str, list[dict]] = {"train": [], "validation": [], "test": []}

    for date, row in rows.items():
        split, v, c = row["split"], row["review"], row["context"]
        alert = abs(c["z"]) >= NEAR_ALERT_Z
        if split == "train":
            plain = v["outcome"] == "consistent" and c["kind"] == "ordinary" and c["period"] == "regular"
            keep = TRAIN_INSUFFICIENT_KEEP if v["outcome"] == "insufficient_evidence" else (
                TRAIN_ORDINARY_KEEP if plain and not alert else 1.0)
            if rng.random() < keep:
                out["train"].append(to_sample(row, f"{date}/real", "real"))
        elif alert:
            out[split_file[split]].append(to_sample(row, f"{date}/real", "real"))
        if v["outcome"] == "consistent" and rng.random() < SIM_PER_CONSISTENT[split]:
            ts = pd.Timestamp(date)
            sim = rv.row(ts, inject(np.asarray(row["load_mw"], dtype=float), rng))
            out[split_file[split]].append(to_sample(sim, f"{date}/simulated", "simulated", {"simulated": True}))

    eval_alerts = [d for d, r in rows.items() if r["split"] in ("test", "holdout") and r["flagged"]]
    for a, b in swap_pairs(rows, eval_alerts):
        for keep, donor in ((a, b), (b, a)):
            values = np.asarray(rows[donor]["load_mw"], dtype=float)
            values = values * (rows[keep]["context"]["load_mw"] / values.mean())
            swapped = rv.row(pd.Timestamp(keep), values)
            out["test"].append(to_sample(swapped, f"{keep}/curve_from/{donor}", "curve_swap",
                                         {"curve_from": donor, "original_target": samples.target(rows[keep])}))  # fmt: skip

    OUT.mkdir(parents=True, exist_ok=True)
    stats = {}
    for name, items in out.items():
        with open(OUT / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for s in items:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        df = pd.DataFrame([{"split": s["split"], "set": s["set"], "outcome": s["target"]["outcome"]} for s in items])
        stats[name] = pd.crosstab([df.split, df.set], df.outcome).to_dict(orient="index")
        print(f"{name}: {len(items)} samples")
        print(pd.crosstab([df.split, df.set], df.outcome).to_string())
    (OUT / "stats.json").write_text(json.dumps({k: {str(i): v for i, v in s.items()} for k, s in stats.items()},
                                               indent=1) + "\n")  # fmt: skip


if __name__ == "__main__":
    main()
