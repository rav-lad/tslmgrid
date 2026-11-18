"""Score alert reviews: the model, a context-only baseline, and the hourly rules.

Usage::

    uv run sgcot-review-score                                   # baselines only
    uv run sgcot-review-score --predictions <test_predictions.jsonl> --name <system>

Systems:

* ``hourly rules``: the deterministic hourly comparison (``review.assess``). The reference answers
  are its output, so it scores 1.000 by construction. It is the product baseline: where it suffices,
  the model adds the reading and the wording, not the decision.
* ``context only``: sees what the prompt states (calendar kind, period, weekday, daily z-score,
  whether a context reference exists) and never the curve. For each field it answers the majority of
  the train samples with the same context cell (kind, period, weekday group, z bin), backing off to
  coarser cells; it never names hours.
* the model: parsed from the last 'Answer:' line of its generation; an unparsable or missing answer
  counts as wrong.

Metrics per group (split x set, alerts split into flagged |z| >= 3 and near-alerts 2 <= |z| < 3):
outcome accuracy and macro F1, precision and recall of "deviation remains", profile accuracy (ties left out), concentration accuracy, F1 over the
hours that warrant review (pooled over the samples), the absolute error of the reported day-level
residual (percentage points), and the parsable rate. For the curve swap, ``follows_curve`` is the
share of samples whose outcome changed between the original and the swapped curve and where the
answer gives the swapped curve's outcome.
"""

import argparse
import json
from collections import Counter

import numpy as np
import pandas as pd

from swissgrid_cot.review.assess import OUTCOMES
from swissgrid_cot.review.samples import parse_answer
from swissgrid_cot.sources import PROCESSED_DIR, REPO_ROOT

SAMPLES = PROCESSED_DIR / "opentslm_review"
OUT = REPO_ROOT / "reports" / "review_eval"
FIELDS = ("profile", "concentrated", "outcome")


def load(split: str) -> list[dict]:
    with open(SAMPLES / f"{split}.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def _zbin(z: float) -> str:
    a = abs(z)
    return ("lt2" if a < 2 else "2to3" if a < 3 else "ge3") + ("+" if z >= 0 else "-")


def _wgroup(weekday: str) -> str:
    return {"Saturday": "sat", "Sunday": "sun"}.get(weekday, "wd")


def _cells(s: dict) -> list[tuple]:
    c = s["context"]
    no_ref = "no context reference is given" in s["pre_prompt"]
    full = (no_ref, c["kind"], c["period"], _wgroup(c["weekday"]), _zbin(c["z"]))
    return [full, full[:4], full[:3], full[:1], ()]


class ContextOnly:
    def __init__(self, train: list[dict]):
        self.counts: dict[str, dict[tuple, Counter]] = {f: {} for f in FIELDS}
        for s in train:
            for f in FIELDS:
                for cell in _cells(s):
                    self.counts[f].setdefault(cell, Counter())[s["target"][f]] += 1

    def answer(self, s: dict) -> str:
        out = {}
        for f in FIELDS:
            for cell in _cells(s):
                if cell in self.counts[f]:
                    out[f] = self.counts[f][cell].most_common(1)[0][0] or "none"
                    break
        return (f"Answer: profile={out['profile']}; concentrated={out['concentrated']}; "
                f"outcome={out['outcome']}; hours=none")  # fmt: skip


def oracle_answer(s: dict) -> str:
    return s["answer"]


def group_of(s: dict) -> str:
    if s["set"] == "real":
        return f"{s['split']}/real/{'flagged' if s['flagged'] else 'near-alert'}"
    return f"{s['split']}/{s['set']}"


def metrics(samples: list[dict], answers: dict[str, str]) -> dict:
    n = len(samples)
    parsed = {s["id"]: parse_answer(answers.get(s["id"], "")) for s in samples}
    ok = [p is not None for p in parsed.values()]
    out: dict = {"n": n, "parsable": round(float(np.mean(ok)), 3) if n else None}
    gold_o = [s["target"]["outcome"] for s in samples]
    pred_o = [(parsed[s["id"]] or {}).get("outcome") for s in samples]
    out["outcome_counts"] = dict(Counter(gold_o))
    out["outcome_acc"] = round(float(np.mean([g == p for g, p in zip(gold_o, pred_o)])), 3) if n else None
    f1s = []
    for o in OUTCOMES:
        tp = sum(g == o and p == o for g, p in zip(gold_o, pred_o))
        fp = sum(g != o and p == o for g, p in zip(gold_o, pred_o))
        fn = sum(g == o and p != o for g, p in zip(gold_o, pred_o))
        if tp + fp + fn:
            f1s.append(2 * tp / (2 * tp + fp + fn))
    out["outcome_macro_f1"] = round(float(np.mean(f1s)), 3) if f1s else None
    dev = "deviation_remains"
    tp = sum(g == dev and p == dev for g, p in zip(gold_o, pred_o))
    said, real = sum(p == dev for p in pred_o), sum(g == dev for g in gold_o)
    out["deviation_precision"] = round(tp / said, 3) if said else None
    out["deviation_recall"] = round(tp / real, 3) if real else None
    prof = [(s["target"]["profile"], (parsed[s["id"]] or {}).get("profile")) for s in samples
            if s["target"]["profile"] is not None and not s["target"]["profile_tie"]]  # fmt: skip
    out["profile_n"] = len(prof)
    out["profile_acc"] = round(float(np.mean([g == p for g, p in prof])), 3) if prof else None
    conc = [(s["target"]["concentrated"], (parsed[s["id"]] or {}).get("concentrated")) for s in samples
            if s["target"]["concentrated"] is not None]  # fmt: skip
    out["concentrated_acc"] = round(float(np.mean([g == p for g, p in conc])), 3) if conc else None
    tp = fp = fn = 0
    for s in samples:
        g = set(s["target"]["hours"])
        p = set((parsed[s["id"]] or {}).get("hours") or [])
        tp, fp, fn = tp + len(g & p), fp + len(p - g), fn + len(g - p)
    out["hours_f1"] = round(2 * tp / (2 * tp + fp + fn), 3) if (tp + fp + fn) else None
    out["hours_support"] = tp + fn
    errs = [abs(parsed[s["id"]]["day_residual_pct"] - s["target"]["day_residual_pct"]) for s in samples
            if parsed[s["id"]] and parsed[s["id"]]["day_residual_pct"] is not None
            and s["target"]["day_residual_pct"] is not None]  # fmt: skip
    with_number = [s for s in samples if s["target"]["day_residual_pct"] is not None]
    out["day_residual_reported"] = round(len(errs) / len(with_number), 3) if with_number else None
    out["day_residual_mae_pp"] = round(float(np.mean(errs)), 2) if errs else None
    out["day_residual_within_1pp"] = round(float(np.mean([e <= 1.0 for e in errs])), 3) if errs else None
    swaps = [s for s in samples if s["set"] == "curve_swap" and s["target"]["outcome"] != s["original_target"]["outcome"]]
    if swaps:
        out["swap_changed_n"] = len(swaps)
        out["follows_curve"] = round(float(np.mean(
            [(parsed[s["id"]] or {}).get("outcome") == s["target"]["outcome"] for s in swaps])), 3)  # fmt: skip
        out["follows_text"] = round(float(np.mean(
            [(parsed[s["id"]] or {}).get("outcome") == s["original_target"]["outcome"] for s in swaps])), 3)  # fmt: skip
    return out


def score_all(samples: list[dict], answers: dict[str, str]) -> dict[str, dict]:
    groups: dict[str, list[dict]] = {}
    for s in samples:
        groups.setdefault(group_of(s), []).append(s)
    return {g: metrics(items, answers) for g, items in sorted(groups.items())}


TABLE = ("n", "parsable", "outcome_acc", "outcome_macro_f1", "deviation_precision", "deviation_recall",
         "profile_acc", "concentrated_acc", "hours_f1", "day_residual_mae_pp", "follows_curve", "follows_text")  # fmt: skip


def table(results: dict[str, dict[str, dict]]) -> str:
    rows = []
    for system, by_group in results.items():
        for g, m in by_group.items():
            rows.append({"group": g, "system": system, **{k: m.get(k) for k in TABLE}})
    df = pd.DataFrame(rows).sort_values(["group", "system"])
    return df.to_markdown(index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--predictions", help="OpenTSLM test predictions (sample_id, generated)")
    parser.add_argument("--name", default="model")
    parser.add_argument("--split", default="test", choices=("validation", "test"))
    args = parser.parse_args()

    train, samples = load("train"), load(args.split)
    ctx = ContextOnly(train)
    results = {
        "hourly rules": score_all(samples, {s["id"]: oracle_answer(s) for s in samples}),
        "context only": score_all(samples, {s["id"]: ctx.answer(s) for s in samples}),
    }
    if args.predictions:
        with open(args.predictions, encoding="utf-8") as f:
            preds = [json.loads(line) for line in f]
        ids = {s["id"] for s in samples}
        unknown = [p["sample_id"] for p in preds if p["sample_id"] not in ids]
        if unknown:
            raise SystemExit(f"{len(unknown)} predictions have unknown sample ids, first {unknown[0]}")
        results[args.name] = score_all(samples, {p["sample_id"]: p["generated"] for p in preds})
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"{args.name if args.predictions else 'baselines'}_{args.split}"
    (OUT / f"{stem}.json").write_text(json.dumps(results, indent=1) + "\n")
    text = table(results)
    (OUT / f"{stem}.md").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
