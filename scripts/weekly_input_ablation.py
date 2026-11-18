"""Which input does the weekly anomaly_days model read: the holiday list in the prompt, or the curve?

Usage::

    uv run python scripts/weekly_input_ablation.py variants --out scratch/ablation      # build the variants
    # then, from an OpenTSLM checkout with the stage 6 patch, for v in orig noholiday swap:
    #   SWISSGRID_COT_DIR=scratch/ablation/v python train/predict.py <epoch_N.pt> scratch/ablation/preds/v.jsonl
    uv run python scripts/weekly_input_ablation.py score --out scratch/ablation

Variants of the 52 test anomaly_days samples (2025), same checkpoint:

* ``orig``: unchanged.
* ``noholiday``: the curve unchanged, the holiday sentence replaced by "Public holidays this week: none."
* ``swap``: the prompt unchanged, the series of the window 4 weeks later (cyclic).

For the swap, the predicted days are mapped to their position in the week and scored against the
prompt's week (does the answer follow the text?) and against the donor week (does it follow the curve?).
"""

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "data" / "processed" / "opentslm"
HOL = re.compile(r"Public holidays this week: .*?(?= (?:Which|Did) )")
SHIFT = 4
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def test_days() -> list[dict]:
    rows = [json.loads(line) for line in (SRC / "test.jsonl").read_text(encoding="utf-8").splitlines()]
    return sorted((r for r in rows if r["task"] == "anomaly_days"), key=lambda r: r["window_id"])


def variants(out: Path) -> None:
    days = test_days()
    built = {"orig": [dict(r) for r in days], "swap": [], "noholiday": []}
    for i, r in enumerate(days):
        built["swap"].append({**r, "series": days[(i + SHIFT) % len(days)]["series"]})
        text, n = HOL.subn("Public holidays this week: none.", r["pre_prompt"])
        assert n == 1, r["id"]
        built["noholiday"].append({**r, "pre_prompt": text})
    for name, rows in built.items():
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        for split in ("train", "validation"):
            link = d / f"{split}.jsonl"
            if not link.exists():
                os.symlink(SRC / f"{split}.jsonl", link)
        (d / "test.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        print(name, len(rows))


def answer_days(text: str) -> set[str]:
    cut = text.rfind("Answer:")
    return set(DATE.findall(text[cut:])) if cut >= 0 else set()


def f1(pairs) -> tuple[float, int, int, int]:
    tp = sum(len(g & p) for g, p in pairs)
    fp = sum(len(p - g) for g, p in pairs)
    fn = sum(len(g - p) for g, p in pairs)
    return (2 * tp / (2 * tp + fp + fn) if tp else 0.0), tp, fp, fn


def score(out: Path) -> dict:
    days = test_days()
    order = [r["window_id"] for r in days]
    by_id = {r["id"]: r for r in days}
    gold_w = {r["window_id"]: set(r["target"]) for r in days}
    start = {r["window_id"]: dt.date.fromisoformat(r["facts"]["start_local"][:10]) for r in days}

    def pos(dates, w):
        return {(dt.date.fromisoformat(d) - start[w]).days for d in dates}

    result = {}
    for v in ("orig", "noholiday", "swap"):
        rows = [json.loads(line) for line in (out / "preds" / f"{v}.jsonl").read_text(encoding="utf-8").splitlines()]
        preds = {r["sample_id"]: answer_days(r["generated"]) for r in rows}
        res = {"n": len(preds), "day_f1_true_labels": f1([(set(by_id[i]["target"]), p) for i, p in preds.items()])}
        if v == "swap":
            text, curve = [], []
            for i, p in preds.items():
                w = by_id[i]["window_id"]
                donor = order[(order.index(w) + SHIFT) % len(order)]
                text.append((pos(gold_w[w], w), pos(p, w)))
                curve.append((pos(gold_w[donor], donor), pos(p, w)))
            res["follows_text_f1"], res["follows_curve_f1"] = f1(text), f1(curve)
        result[v] = res
        print(v, res)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=("variants", "score"))
    parser.add_argument("--out", type=Path, default=REPO / "scratch" / "ablation")
    args = parser.parse_args()
    variants(args.out) if args.step == "variants" else score(args.out)


if __name__ == "__main__":
    main()
