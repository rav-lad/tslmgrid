"""Generate the test predictions of one stage 6 checkpoint, without epoch selection.

Run from an OpenTSLM checkout that has the stage 6 patch, with ``SWISSGRID_COT_DIR`` set::

    uv run python predict.py <epoch_N.pt> <out.jsonl> [--device cpu] [--skip <earlier predictions.jsonl> ...]

Writes one ``{sample_id, generated, gold}`` line per test sample, flushed as it goes. A 1B model on
16 CPU cores takes about 15 s per review sample.
"""

import argparse
import json
import os
import time

import torch
from torch.utils.data import DataLoader

from opentslm.model.llm.OpenTSLMSP import OpenTSLMSP
from opentslm.model_config import PATCH_SIZE
from opentslm.time_series_datasets.swissgrid.SwissGridCoTQADataset import SwissGridCoTQADataset
from opentslm.time_series_datasets.util import extend_time_series_to_match_patch_size_and_aggregate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("checkpoint")
    parser.add_argument("out")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--llm-id", default="meta-llama/Llama-3.2-1B")
    parser.add_argument("--max-new-tokens", type=int, default=400)
    parser.add_argument("--skip", nargs="*", default=[], help="prediction files whose sample ids are left out")
    args = parser.parse_args()
    done = set()
    for path in args.skip:
        with open(path, encoding="utf-8") as f:
            done |= {json.loads(line)["sample_id"] for line in f if line.strip()}

    if args.device == "cpu":
        torch.set_num_threads(os.cpu_count())
    model = OpenTSLMSP(llm_id=args.llm_id, device=args.device)
    model.enable_lora(lora_r=16, lora_alpha=32, lora_dropout=0.0)  # as in curriculum_learning.py
    model.eval()
    model.load_from_file(args.checkpoint)
    ds = SwissGridCoTQADataset("test", EOS_TOKEN=model.get_eos_token())
    samples = [s for s in (ds[i] for i in range(len(ds))) if s["id"] not in done]
    loader = DataLoader(samples, batch_size=1, shuffle=False,
                        collate_fn=lambda b: extend_time_series_to_match_patch_size_and_aggregate(b, patch_size=PATCH_SIZE))  # fmt: skip
    t0 = time.time()
    with open(args.out, "w", encoding="utf-8") as f, torch.no_grad():
        for i, (s, batch) in enumerate(zip(samples, loader, strict=True)):
            p = model.generate(batch, max_new_tokens=args.max_new_tokens)[0]
            f.write(json.dumps({"sample_id": s["id"], "generated": p, "gold": s["answer"]}, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{i + 1}/{len(samples)} {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
