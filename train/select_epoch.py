"""Select the stage 6 epoch on the validation day F1, then write its test predictions.

The validation loss is dominated by the easy template tokens and does not follow the task metrics:
the epoch it selects ranged from day F1 0.18 to 0.74 on the test year across runs. This script scores
every ``epoch_N.pt`` (saved with ``OPENTSLM_SAVE_EVERY_EPOCH=1``) on the anomaly_days samples of the
validation year, keeps the best, and generates the test predictions with it.

Run from an OpenTSLM checkout that has the stage 6 patch, with ``SWISSGRID_COT_DIR`` set::

    uv run python select_epoch.py --checkpoints results/Llama_3_2_1B/OpenTSLMSP/stage6_swissgrid_cot/checkpoints \
        --out results/Llama_3_2_1B/OpenTSLMSP/stage6_swissgrid_cot/results/test_predictions.jsonl

``--task alert_review`` selects on the alert-review samples (``sgcot-review-export``) instead: the
mean of the validation outcome macro F1, the F1 over the hours under review and the profile accuracy
(ties left out), parsed as ``swissgrid_cot.review.samples.parse_answer`` does.

``--task day_signature`` selects on the day-signature samples (``sgcot-explain-export``): the validation
macro F1 of the label after the last 'Answer:', parsed as ``swissgrid_cot.explain.samples.parse_answer`` does.
``--task window_review`` (``sgcot-window-export``) selects on the validation macro F1 of yes / no.
"""

import argparse
import glob
import json
import os
import re

import torch
from torch.utils.data import DataLoader

from opentslm.model.llm.OpenTSLMSP import OpenTSLMSP
from opentslm.model_config import PATCH_SIZE
from opentslm.time_series_datasets.swissgrid.SwissGridCoTQADataset import SwissGridCoTQADataset
from opentslm.time_series_datasets.util import extend_time_series_to_match_patch_size_and_aggregate

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def days(text: str) -> set[str]:
    """The dates after the last 'Answer:', as scored by swissgrid-cot (none or unparsable: no day)."""
    cut = text.rfind("Answer:")
    return set(DATE.findall(text[cut:])) if cut >= 0 else set()


def generate(model, samples: list, max_new_tokens: int, done=None) -> list[str]:
    """The generated text of each sample; ``done(sample, text)`` is called after each one."""
    loader = DataLoader(  # batch size 1, as OpenTSLM's evaluation: no padding inside a batch
        samples, batch_size=1, shuffle=False,
        collate_fn=lambda b: extend_time_series_to_match_patch_size_and_aggregate(b, patch_size=PATCH_SIZE),
    )
    out = []
    with torch.no_grad():
        for sample, batch in zip(samples, loader):
            out += model.generate(batch, max_new_tokens=max_new_tokens)
            if done:
                done(sample, out[-1])
    return out


def day_f1(samples: list, preds: list[str], targets: dict[str, list[str]]) -> tuple[float, int, int, int]:
    tp = fp = fn = 0
    for s, p in zip(samples, preds):
        gold, pred = set(targets[s["id"]]), days(p)
        tp, fp, fn = tp + len(gold & pred), fp + len(pred - gold), fn + len(gold - pred)
    f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    return f1, tp, fp, fn


REVIEW = re.compile(
    r"profile\s*=\s*(?P<profile>[a-z_]+)\s*;\s*concentrated\s*=\s*(?P<concentrated>[a-z_]+)\s*;\s*"
    r"outcome\s*=\s*(?P<outcome>[a-z_]+)\s*;\s*hours\s*=\s*(?P<hours>[0-9,\- ]+|none)"
)


def review_fields(text: str) -> dict:
    cut = text.rfind("Answer:")
    m = REVIEW.search(text[cut:]) if cut >= 0 else None
    if not m:
        return {"profile": None, "outcome": None, "hours": set()}
    hours = set()
    for a, b in re.findall(r"(\d{1,2})\s*-\s*(\d{1,2})", m["hours"]):
        hours.update(range(int(a), int(b) + 1))
    return {"profile": m["profile"], "outcome": m["outcome"], "hours": hours}


def review_score(samples: list, preds: list[str], targets: dict[str, dict]) -> tuple[float, str]:
    got = [(targets[s["id"]], review_fields(p)) for s, p in zip(samples, preds)]
    f1s = []
    for o in ("consistent", "deviation_remains", "insufficient_evidence"):
        tp = sum(t["outcome"] == o and p["outcome"] == o for t, p in got)
        fp = sum(t["outcome"] != o and p["outcome"] == o for t, p in got)
        fn = sum(t["outcome"] == o and p["outcome"] != o for t, p in got)
        if tp + fp + fn:
            f1s.append(2 * tp / (2 * tp + fp + fn))
    outcome_f1 = sum(f1s) / len(f1s)
    tp = sum(len(set(t["hours"]) & p["hours"]) for t, p in got)
    fp = sum(len(p["hours"] - set(t["hours"])) for t, p in got)
    fn = sum(len(set(t["hours"]) - p["hours"]) for t, p in got)
    hours_f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    prof = [(t["profile"], p["profile"]) for t, p in got if t["profile"] and not t["profile_tie"]]
    profile_acc = sum(a == b for a, b in prof) / len(prof) if prof else 0.0
    score = (outcome_f1 + hours_f1 + profile_acc) / 3
    return score, f"outcome macro F1 {outcome_f1:.3f}, hours F1 {hours_f1:.3f}, profile {profile_acc:.3f}"


SIGNATURE = re.compile(r"Answer:\s*([a-z_]+)")


def signature_score(samples: list, preds: list[str], targets: dict[str, dict]) -> tuple[float, str]:
    gold = [targets[s["id"]]["label"] for s in samples]
    pred = [(SIGNATURE.findall(p) or [None])[-1] for p in preds]
    return label_f1(gold, pred)


WINDOW = re.compile(r"Answer:\s*(yes|no)\b")


def window_score(samples: list, preds: list[str], targets: dict[str, dict]) -> tuple[float, str]:
    gold = ["yes" if targets[s["id"]]["investigate"] else "no" for s in samples]
    pred = [(WINDOW.findall(p) or [None])[-1] for p in preds]
    return label_f1(gold, pred)


def label_f1(gold: list[str], pred: list[str | None]) -> tuple[float, str]:
    """Macro F1 over the gold labels, and the accuracy."""
    f1s = []
    for lab in sorted(set(gold)):
        tp = sum(g == lab and q == lab for g, q in zip(gold, pred))
        fp = sum(g != lab and q == lab for g, q in zip(gold, pred))
        fn = sum(g == lab and q != lab for g, q in zip(gold, pred))
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    acc = sum(g == q for g, q in zip(gold, pred)) / len(gold)
    return sum(f1s) / len(f1s), f"accuracy {acc:.3f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--checkpoints", required=True, help="folder holding epoch_N.pt")
    parser.add_argument("--out", required=True, help="test predictions to write (jsonl)")
    parser.add_argument("--llm-id", default="meta-llama/Llama-3.2-1B")
    parser.add_argument("--max-new-tokens", type=int, default=600)
    parser.add_argument("--task", default="anomaly_days", choices=("anomaly_days", "alert_review", "day_signature", "window_review"))
    args = parser.parse_args()

    root = os.environ["SWISSGRID_COT_DIR"]
    with open(os.path.join(root, "validation.jsonl"), encoding="utf-8") as f:
        targets = {r["id"]: r["target"] for r in map(json.loads, f) if r["task"] == args.task}

    model = OpenTSLMSP(llm_id=args.llm_id, device="cuda")
    model.enable_lora(lora_r=16, lora_alpha=32, lora_dropout=0.0)  # as in curriculum_learning.py
    model.eval()
    eos = model.get_eos_token()
    val_ds = SwissGridCoTQADataset("validation", EOS_TOKEN=eos)
    val = [val_ds[i] for i in range(len(val_ds)) if val_ds[i]["id"] in targets]

    paths = sorted(glob.glob(os.path.join(args.checkpoints, "epoch_*.pt")),
                   key=lambda p: int(re.search(r"epoch_(\d+)", p).group(1)))  # fmt: skip
    # a spot VM can stop at any time: the scores and the test predictions are kept as they come, and a
    # rerun starts where the last one stopped
    cache = os.path.join(os.path.dirname(args.out), "validation_scores.json")
    done = {}
    if os.path.exists(cache):
        with open(cache, encoding="utf-8") as f:
            done = json.load(f)
    scores = {}
    for path in paths:
        if os.path.basename(path) in done:
            scores[path] = done[os.path.basename(path)]
            print(f"{os.path.basename(path)}: validation score {scores[path]:.3f} (kept)", flush=True)
            continue
        model.load_from_file(path)
        preds = generate(model, val, args.max_new_tokens)
        if args.task in ("alert_review", "day_signature", "window_review"):
            fn = {"alert_review": review_score, "day_signature": signature_score, "window_review": window_score}[args.task]
            scores[path], detail = fn(val, preds, targets)
            print(f"{os.path.basename(path)}: validation score {scores[path]:.3f} ({detail})", flush=True)
        else:
            f1, tp, fp, fn = day_f1(val, preds, targets)
            scores[path] = f1
            print(f"{os.path.basename(path)}: validation day F1 {f1:.3f} (tp={tp} fp={fp} fn={fn})", flush=True)
        done[os.path.basename(path)] = scores[path]
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(done, f)
    best = max(paths, key=lambda p: (scores[p], -paths.index(p)))  # ties: the earlier epoch
    print(f"selected {os.path.basename(best)}", flush=True)
    with open(os.path.join(os.path.dirname(args.out), "selection.json"), "w", encoding="utf-8") as f:
        key = {"alert_review": "validation_review_score", "day_signature": "validation_macro_f1",
               "window_review": "validation_macro_f1"}.get(
            args.task, "validation_day_f1")
        json.dump({"selected": os.path.basename(best), key: {
            os.path.basename(p): round(s, 4) for p, s in scores.items()}}, f, indent=1)

    model.load_from_file(best)
    test_ds = SwissGridCoTQADataset("test", EOS_TOKEN=eos)
    test = [test_ds[i] for i in range(len(test_ds))]
    partial = args.out + ".partial"
    kept = {}
    if os.path.exists(partial):
        with open(partial, encoding="utf-8") as f:
            for line in f:
                try:
                    kept[json.loads(line)["sample_id"]] = line
                except json.JSONDecodeError:  # the last line of a stopped run
                    pass
    with open(partial, "w", encoding="utf-8") as f:
        f.writelines(kept.values())
    print(f"{len(kept)} test predictions kept, {len(test) - len(kept)} to generate", flush=True)
    with open(partial, "a", encoding="utf-8") as f:

        def write(s, p):
            f.write(json.dumps({"sample_id": s["id"], "generated": p, "gold": s["answer"]}, ensure_ascii=False) + "\n")
            f.flush()

        generate(model, [s for s in test if s["id"] not in kept], args.max_new_tokens, write)
    os.replace(partial, args.out)
    print(f"wrote {len(test)} test predictions to {args.out}")


if __name__ == "__main__":
    main()
