"""Select the stage 6 epoch on the validation day F1, then write its test predictions.

The validation loss is dominated by the easy template tokens and does not follow the task metrics:
the epoch it selects ranged from day F1 0.18 to 0.74 on the test year across runs. This script scores
every ``epoch_N.pt`` (saved with ``OPENTSLM_SAVE_EVERY_EPOCH=1``) on the anomaly_days samples of the
validation year, keeps the best, and generates the test predictions with it.

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

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def days(text: str) -> set[str]:
    """The dates after the last 'Answer:', as scored by swissgrid-cot (none or unparsable: no day)."""
    cut = text.rfind("Answer:")
    return set(DATE.findall(text[cut:])) if cut >= 0 else set()


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


def day_f1(samples: list, preds: list[str], targets: dict[str, list[str]]) -> tuple[float, int, int, int]:
    tp = fp = fn = 0
    for s, p in zip(samples, preds):
        gold, pred = set(targets[s["id"]]), days(p)
        tp, fp, fn = tp + len(gold & pred), fp + len(pred - gold), fn + len(gold - pred)
    f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    return f1, tp, fp, fn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--checkpoints", required=True, help="folder holding epoch_N.pt")
    parser.add_argument("--out", required=True, help="test predictions to write (jsonl)")
    parser.add_argument("--llm-id", default="meta-llama/Llama-3.2-1B")
    parser.add_argument("--max-new-tokens", type=int, default=600)
    args = parser.parse_args()

    root = os.environ["SWISSGRID_COT_DIR"]
    with open(os.path.join(root, "validation.jsonl"), encoding="utf-8") as f:
        targets = {r["id"]: r["target"] for r in map(json.loads, f) if r["task"] == "anomaly_days"}

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
        f1, tp, fp, fn = day_f1(val, generate(model, val, args.max_new_tokens), targets)
        scores[path] = f1
        print(f"{os.path.basename(path)}: validation day F1 {f1:.3f} (tp={tp} fp={fp} fn={fn})", flush=True)
    best = max(paths, key=lambda p: (scores[p], -paths.index(p)))  # ties: the earlier epoch
    print(f"selected {os.path.basename(best)}", flush=True)
    with open(os.path.join(os.path.dirname(args.out), "selection.json"), "w", encoding="utf-8") as f:
        json.dump({"selected": os.path.basename(best), "validation_day_f1": {
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
