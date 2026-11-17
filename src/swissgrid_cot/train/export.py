"""Export the training and evaluation samples for OpenTSLM.

Usage::

    uv run sgcot-export                          # from data/processed/annotations (no TimeNet needed)
    uv run --with-editable ext/TimeNet/packages/timenet sgcot-export --registry <TimeNet local registry>

By default the ISO-week windows come from ``windows.jsonl``, which the connector's pipeline also
produces. With ``--registry`` they are read back from the built TimeNet dataset instead, so training
consumes exactly what TimeNet publishes (``scripts/check_timenet_build.py`` shows both agree).
The train split is augmented with the 7-day windows starting on
every train day (``windows_rolling_train.jsonl``, same rules, never reaching into 2024-2025); the
Monday-start ones are dropped, as TimeNet already holds them. ``--normal-stride N`` keeps the anomaly
tasks of only one in N rolling windows without an anomalous day, as most weeks have none; every
window keeps its exchange task.

Writes ``data/processed/opentslm/{train,validation,test}.jsonl``, one sample per task:
``id, window_id, task, split, pre_prompt, series[{name, unit, values}], post_prompt, answer, target, facts``.
"""

import argparse
import json
from collections import Counter

import pandas as pd

from swissgrid_cot.annotate.causes import CAUSES
from swissgrid_cot.sources import PROCESSED_DIR

DATASET = "scooby-team/swiss-grid-anomaly-cot"
OUT = PROCESSED_DIR / "opentslm"

SERIES = {
    "anomaly_cause": [("End-user consumption", "MW"), ("Temperature", "°C"), ("Global radiation", "W/m²")],
    "anomaly_days": [("End-user consumption", "MW"), ("Temperature", "°C"), ("Global radiation", "W/m²")],
    "exchange": [
        ("Net import (all borders)", "MW"),
        ("Net import from Austria", "MW"),
        ("Net import from Germany", "MW"),
        ("Net import from France", "MW"),
        ("Net import from Italy", "MW"),
        ("Production", "MW"),
        ("Total consumption", "MW"),
    ],
}
COLUMNS = {
    "End-user consumption": "load_enduser_mw", "Total consumption": "load_total_mw", "Production": "production_mw",
    "Net import from Austria": "net_import_at_mw", "Net import from Germany": "net_import_de_mw",
    "Net import from France": "net_import_fr_mw", "Net import from Italy": "net_import_it_mw",
    "Temperature": "temp_c", "Global radiation": "radiation_wm2",
}  # fmt: skip
POST_PROMPTS = {
    "anomaly_cause": "Possible causes: " + ", ".join(CAUSES) + ". Reason step by step from the series, "
    "then end with 'Answer: <cause>'.",
    "anomaly_days": "Reason from the series, then end with 'Answer: ' followed by the anomalous dates as "
    "YYYY-MM-DD separated by commas, or 'Answer: none'.",
    "exchange": "Reason from the series, then end with 'Answer: net importer' or 'Answer: net exporter'.",
}


BORDER_SERIES = [f"Net import from {c}" for c in ("Austria", "Germany", "France", "Italy")]


def with_total_import(values: dict[str, list[float]]) -> dict[str, list[float]]:
    """Add the net import over all borders, the hourly sum of the four borders (as in ingest)."""
    total = [round(sum(v), 3) for v in zip(*(values[n] for n in BORDER_SERIES), strict=True)]
    return {**values, "Net import (all borders)": total}


def sample(window: dict, task: str, values: dict[str, list[float]], augmented: bool) -> dict:
    values = with_total_import(values)
    targets = {
        "anomaly_cause": window["label"],
        "anomaly_days": window["anomalous_dates"],
        "exchange": window["exchange_answer"],
    }
    return {
        "id": f"{window['window_id']}/{task}",
        "window_id": window["window_id"],
        "task": task,
        "split": window["split"],
        "augmented": augmented,
        "pre_prompt": window["prompts"][task],
        "series": [{"name": n, "unit": u, "values": values[n]} for n, u in SERIES[task]],
        "post_prompt": POST_PROMPTS[task],
        "answer": window["rationales"][task],
        "target": targets[task],
        "facts": window["facts"],
    }


def from_timenet(registry: str) -> list[dict]:
    """Rebuild each window's prompts, rationales and targets from the TimeNet dataset."""
    import timenet
    from timenet.types import AnswerTask, ClassificationTask, TemporalLocalizationTask
    from timenet.types.text import read_value

    kinds = {ClassificationTask: "anomaly_cause", TemporalLocalizationTask: "anomaly_days", AnswerTask: "exchange"}
    samples = []
    with timenet.TimeNet(sources=[registry]).open(DATASET) as reader:
        ds = reader.read()
        windows: dict[int, dict] = {}
        for record in ds.records:
            facts = json.loads(read_value(next(a.value for a in record.annotations if a.key == "facts")))
            windows[record.id] = {
                "window_id": record.metadata["window_id"],
                "facts": facts,
                "label": facts["label"],
                "anomalous_dates": [d["date"] for d in facts["anomalous_days"]],
                "exchange_answer": f"net {facts['exchange']['role']}",
                "prompts": {},
                "rationales": {},
                "values": {s.name: s.to_numpy().astype(float).round(3).tolist() for s in record.signals},
            }
        for cls, name in kinds.items():
            for task in ds.tasks_of(cls):
                w = windows[task.inputs[0].id]
                w["split"] = task.split.value
                w["prompts"][name] = read_value(task.prompt)
                w["rationales"][name] = read_value(task.rationale)
        for w in windows.values():
            samples += [sample(w, t, w["values"], augmented=False) for t in SERIES]
    return samples


def _read_windows(name: str) -> list[dict]:
    path = PROCESSED_DIR / "annotations" / name
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _window_values(hourly: pd.DataFrame, w: dict) -> dict[str, list[float]]:
    week = pd.date_range(w["facts"]["start_local"], w["facts"]["end_local"], freq="D")
    rows = hourly[hourly.local_date.isin(week)]
    return {n: rows[c].astype(float).round(3).tolist() for n, c in COLUMNS.items()}


def from_windows() -> list[dict]:
    """The ISO-week samples, built from the annotation files without TimeNet."""
    hourly = pd.read_parquet(PROCESSED_DIR / "ch_hourly.parquet")
    samples = []
    for w in _read_windows("windows.jsonl"):
        values = _window_values(hourly, w)
        samples += [sample(w, t, values, augmented=False) for t in SERIES]
    return samples


def keep_rolling(windows: list[dict], normal_stride: int) -> list[tuple[dict, list[str]]]:
    """Each rolling window with the tasks it keeps.

    The Monday starts are dropped. Of the windows without an anomalous day, one in ``normal_stride``
    keeps its anomaly tasks; the others keep only ``exchange``, which does not depend on anomalies.
    """
    kept, n_normal = [], 0
    for w in windows:
        if "-W" in w["window_id"]:  # a Monday start: the ISO week is already in the base samples
            continue
        tasks = list(SERIES)
        if not w["anomalous_dates"]:
            n_normal += 1
            if (n_normal - 1) % normal_stride:
                tasks = ["exchange"]
        kept.append((w, tasks))
    return kept


def rolling_train(normal_stride: int = 1) -> list[dict]:
    hourly = pd.read_parquet(PROCESSED_DIR / "ch_hourly.parquet")
    samples = []
    for w, tasks in keep_rolling(_read_windows("windows_rolling_train.jsonl"), normal_stride):
        values = _window_values(hourly, w)
        samples += [sample(w, t, values, augmented=True) for t in tasks]
    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--registry", help="read the ISO weeks from this TimeNet local registry (needs timenet)")
    parser.add_argument("--no-augment", action="store_true")
    parser.add_argument(
        "--normal-stride", type=int, default=1,
        help="keep the anomaly tasks of one in N rolling train windows without an anomalous day",
    )  # fmt: skip
    args = parser.parse_args()
    samples = from_timenet(args.registry) if args.registry else from_windows()
    if not args.no_augment:
        samples += rolling_train(args.normal_stride)
    OUT.mkdir(parents=True, exist_ok=True)
    for split in ("train", "validation", "test"):
        rows = [s for s in samples if s["split"] == split]
        with open(OUT / f"{split}.jsonl", "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        counts = Counter((r["task"], str(r["target"]) if r["task"] != "anomaly_days" else bool(r["target"])) for r in rows)
        print(f"{split}: {len(rows)} samples ({sum(r['augmented'] for r in rows)} augmented)")
        for key, n in sorted(counts.items()):
            print(f"    {key}: {n}")


if __name__ == "__main__":
    main()
