"""Load the built TimeNet dataset with the client and compare it with the project's own outputs.

Run from the TimeNet environment (it needs ``timenet``)::

    cd ext/TimeNet && uv run --no-sync python ../../scripts/check_timenet_build.py <registry dir>

Checks that every task's prompt, target and rationale, and every record's series, equal what the
project pipeline wrote to data/processed/ (windows.jsonl and ch_hourly.parquet).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import timenet
from timenet.types import AnswerTask, ClassificationTask, TemporalLocalizationTask
from timenet.types.text import read_value

REPO = Path(__file__).resolve().parents[1]
DATASET = "scooby-team/swiss-grid-anomaly-cot"
COLUMNS = {
    "End-user consumption": "load_enduser_mw", "Total consumption": "load_total_mw", "Production": "production_mw",
    "Net import from Austria": "net_import_at_mw", "Net import from Germany": "net_import_de_mw",
    "Net import from France": "net_import_fr_mw", "Net import from Italy": "net_import_it_mw",
    "Temperature": "temp_c", "Global radiation": "radiation_wm2",
}  # fmt: skip


def main() -> None:
    registry = sys.argv[1]
    windows = {
        w["window_id"]: w
        for w in map(json.loads, (REPO / "data/processed/annotations/windows.jsonl").read_text(encoding="utf-8").splitlines())
    }
    hourly = pd.read_parquet(REPO / "data/processed/ch_hourly.parquet")
    tn = timenet.TimeNet(sources=[registry])
    print(tn.get_manifest(DATASET).dataset_version if hasattr(tn.get_manifest(DATASET), "dataset_version") else "")
    with tn.open(DATASET) as reader:
        ds = reader.read()
        print(ds.describe())
        by_record = {}
        for record in ds.records:
            by_record[record.id] = record.metadata["window_id"]
        mismatches = 0
        kinds = {ClassificationTask: "anomaly_cause", TemporalLocalizationTask: "anomaly_days", AnswerTask: "exchange"}
        for cls, name in kinds.items():
            tasks = ds.tasks_of(cls)
            assert len(tasks) == len(windows), (cls, len(tasks))
            for task in tasks:
                w = windows[by_record[task.inputs[0].id]]
                if read_value(task.prompt) != w["prompts"][name] or read_value(task.rationale) != w["rationales"][name]:
                    mismatches += 1
                if task.split.value != w["split"]:
                    mismatches += 1
                if cls is ClassificationTask and read_value(task.targets[0]) != w["label"]:
                    mismatches += 1
                if cls is AnswerTask and read_value(task.targets[0]) != w["exchange_answer"]:
                    mismatches += 1
                if cls is TemporalLocalizationTask and len(task.targets) != len(w["anomalous_dates"]):
                    mismatches += 1
        # Series: compare every record's end-user load and temperature with the hourly table.
        max_diff = 0.0
        for record in ds.records:
            w = windows[record.metadata["window_id"]]
            week = pd.date_range(w["facts"]["start_local"], w["facts"]["end_local"], freq="D")
            rows = hourly[hourly.local_date.isin(week)]
            by_name = {signal.name: signal for signal in record.signals}
            for name, column in COLUMNS.items():
                values = by_name[name].to_numpy()
                max_diff = max(max_diff, float(np.max(np.abs(values - rows[column].to_numpy()))))
            start = pd.Timestamp(record.start_time.timestamp, unit="us", tz="UTC")
            assert start == rows.index[0], (start, rows.index[0])
    print(f"records: {len(ds.records)}, tasks: {len(ds.tasks)}")
    print(f"task mismatches against windows.jsonl: {mismatches}")
    print(f"max abs difference of series against ch_hourly.parquet: {max_diff}")
    sys.exit(1 if mismatches or max_diff > 0 else 0)


if __name__ == "__main__":
    main()
