"""Score the predictions of a fine-tuned model on a split and compare them with the baselines.

Usage::

    uv run sgcot-score --predictions <results/.../stage6_swissgrid_cot/results/test_predictions.jsonl>
    uv run sgcot-score --predictions preds.jsonl --split validation --name opentslm-sp-llama1b

Each prediction row holds ``sample_id`` (``<window_id>/<task>``, as exported by ``sgcot-export``) and
``generated`` (the model's text). OpenTSLM writes ``sample_id`` once the stage 6 patch is applied
(``train/opentslm-stage6-swissgrid-cot.patch``). The text is scored with ``eval.metrics``, exactly as
the baselines are, and the run is written to ``reports/eval/<name>_<split>.json`` and ``.md``.

A sample without a prediction counts as unparsable and wrong, so a partial run cannot look better
than it is; the coverage is printed. Unknown or duplicated sample ids are errors, since they mean the
predictions come from another export or split.
"""

import argparse
import json
import sys
from pathlib import Path

from swissgrid_cot.eval.baselines import OUT, SAMPLES, TABLE_METRICS, load, table
from swissgrid_cot.eval.metrics import score

SPLITS = ("validation", "test")


class PredictionError(ValueError):
    """The predictions file does not match the samples."""


def read_predictions(path: Path) -> dict[str, str]:
    """Read ``sample_id`` -> generated text from a JSONL file.

    Raises:
        PredictionError: If a row lacks ``sample_id`` or ``generated``, or an id repeats.
    """
    predictions: dict[str, str] = {}
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if "sample_id" not in row:
            raise PredictionError(
                f"{path.name} line {n} has no sample_id: apply train/opentslm-stage6-swissgrid-cot.patch "
                "and rerun the evaluation, or add the id to each row"
            )
        if not isinstance(row.get("generated"), str):
            raise PredictionError(f"{path.name} line {n} ({row['sample_id']}) has no generated text")
        if row["sample_id"] in predictions:
            raise PredictionError(f"{path.name} line {n}: sample_id {row['sample_id']} appears twice")
        predictions[row["sample_id"]] = row["generated"]
    return predictions


def check_ids(samples: list[dict], predictions: dict[str, str], split: str) -> None:
    """Raise if a prediction belongs to no sample of the split."""
    known = {s["id"] for s in samples}
    unknown = sorted(set(predictions) - known)
    if unknown:
        raise PredictionError(
            f"{len(unknown)} predictions are not samples of the {split} split (first: {unknown[:3]}). "
            "Wrong --split, or predictions from another export?"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--predictions", type=Path, required=True, help="JSONL with sample_id and generated")
    parser.add_argument("--split", choices=SPLITS, default="test")
    parser.add_argument("--name", default="model", help="label of the system in the table and the file names")
    args = parser.parse_args()

    if not (SAMPLES / f"{args.split}.jsonl").exists():
        sys.exit(f"{SAMPLES / (args.split + '.jsonl')} is missing: run `uv run sgcot-export` first")
    samples = load(args.split)
    try:
        predictions = read_predictions(args.predictions)
        check_ids(samples, predictions, args.split)
    except PredictionError as e:
        sys.exit(f"error: {e}")

    result = score(samples, predictions)
    missing = len(samples) - len(predictions)
    if missing:
        print(f"warning: {missing} of {len(samples)} samples have no prediction and count as wrong", file=sys.stderr)

    systems: dict[str, dict] = {}
    baselines = OUT / "baselines.json"
    if baselines.exists():
        systems.update(json.loads(baselines.read_text())[args.split])
    systems[args.name] = result
    text = table({args.split: systems})

    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"{args.name}_{args.split}"
    (OUT / f"{stem}.json").write_text(json.dumps(result, indent=2) + "\n")
    (OUT / f"{stem}.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"coverage: {len(predictions)}/{len(samples)} samples")
    print("cause confusion:", result.get("cause_confusion"))
    print("per-metric file:", OUT / f"{stem}.json", "| metrics:", ", ".join(TABLE_METRICS))


if __name__ == "__main__":
    main()
