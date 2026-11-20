"""Select the stage 6 epoch on the validation review score, then write its test predictions.

The validation loss is dominated by the easy template tokens and does not follow the task metrics.
This script scores every ``epoch_N.pt`` (saved with ``OPENTSLM_SAVE_EVERY_EPOCH=1``) on the
alert-review samples of the validation year (``sgcot-review-export``), keeps the best, and generates
the test predictions with it. The score is the mean of the outcome macro F1, the F1 over the hours
under review and the profile accuracy (ties left out), parsed as
``swissgrid_cot.review.samples.parse_answer`` does.

Run from an OpenTSLM checkout that has the stage 6 patch, with ``SWISSGRID_COT_DIR`` set::

    uv run python select_epoch.py --checkpoints results/Llama_3_2_1B/OpenTSLMSP/stage6_swissgrid_cot/checkpoints \
        --out results/Llama_3_2_1B/OpenTSLMSP/stage6_swissgrid_cot/results/test_predictions.jsonl
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

def generate(model, samples: list, max_new_tokens: int) -> list[str]:
    loader = DataLoader(  # batch size 1, as OpenTSLM's evaluation: no padding inside a batch
        samples, batch_size=1, shuffle=False,
        collate_fn=lambda b: extend_time_series_to_match_patch_size_and_aggregate(b, patch_size=PATCH_SIZE),
    )
    out = []
    with torch.no_grad():
        for batch in loader:
            out += model.generate(batch, max_new_tokens=max_new_tokens)
    return out


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--checkpoints", required=True, help="folder holding epoch_N.pt")
    parser.add_argument("--out", required=True, help="test predictions to write (jsonl)")
    parser.add_argument("--llm-id", default="meta-llama/Llama-3.2-1B")
    parser.add_argument("--max-new-tokens", type=int, default=600)
    args = parser.parse_args()

    root = os.environ["SWISSGRID_COT_DIR"]
    with open(os.path.join(root, "validation.jsonl"), encoding="utf-8") as f:
        targets = {r["id"]: r["target"] for r in map(json.loads, f) if r["task"] == "alert_review"}

    model = OpenTSLMSP(llm_id=args.llm_id, device="cuda")
    model.enable_lora(lora_r=16, lora_alpha=32, lora_dropout=0.0)  # as in curriculum_learning.py
    model.eval()
    eos = model.get_eos_token()
    val_ds = SwissGridCoTQADataset("validation", EOS_TOKEN=eos)
    val = [val_ds[i] for i in range(len(val_ds)) if val_ds[i]["id"] in targets]

    paths = sorted(glob.glob(os.path.join(args.checkpoints, "epoch_*.pt")),
                   key=lambda p: int(re.search(r"epoch_(\d+)", p).group(1)))  # fmt: skip
    scores = {}
    for path in paths:
        model.load_from_file(path)
        preds = generate(model, val, args.max_new_tokens)
        scores[path], detail = review_score(val, preds, targets)
        print(f"{os.path.basename(path)}: validation score {scores[path]:.3f} ({detail})", flush=True)
    best = max(paths, key=lambda p: (scores[p], -paths.index(p)))  # ties: the earlier epoch
    print(f"selected {os.path.basename(best)}", flush=True)
    with open(os.path.join(os.path.dirname(args.out), "selection.json"), "w", encoding="utf-8") as f:
        json.dump({"selected": os.path.basename(best), "validation_review_score": {
            os.path.basename(p): round(s, 4) for p, s in scores.items()}}, f, indent=1)

    model.load_from_file(best)
    test_ds = SwissGridCoTQADataset("test", EOS_TOKEN=eos)
    test = [test_ds[i] for i in range(len(test_ds))]
    preds = generate(model, test, args.max_new_tokens)
    with open(args.out, "w", encoding="utf-8") as f:
        for s, p in zip(test, preds):
            f.write(json.dumps({"sample_id": s["id"], "generated": p, "gold": s["answer"]}, ensure_ascii=False) + "\n")
    print(f"wrote {len(preds)} test predictions to {args.out}")


if __name__ == "__main__":
    main()
