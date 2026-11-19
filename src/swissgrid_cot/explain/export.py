"""Export the day-signature samples for OpenTSLM.

Usage::

    uv run sgcot-explain-export

Writes ``data/processed/opentslm_explain/{train,validation,test}.jsonl`` in the format the stage 6
dataset reads (``pre_prompt, series, post_prompt, answer``), plus ``target``, ``set`` and the
measured ``evidence``.

Every day of 2020-2026 with an ordinary-day reference (at least 5 comparable earlier days) and the
three typical profiles is a sample; most of early 2020 has neither. Sets (the ``set`` field):

* ``real``: the day as it is, labelled by its calendar (``labels``).
* ``simulated``: an ordinary day with 3 to 6 consecutive hours multiplied by (1 + delta),
  |delta| 12-25 % (an outage, an event or a metering gap; since 2024 a gap of 6-15 % over a few
  hours is common on ordinary days, as solar output varies), labelled ``irregularity``. Always marked
  simulated.

Splits: train 2020-2023, validation 2024, test 2025 and 2026 (holdout, ``split`` = holdout). Train
keeps 30 % of the ordinary days and repeats the days of the small labels up to about 100 samples (at
most 4 copies each); it adds 200 simulated days. Validation (epoch selection) keeps every calendar
day, 30 % of the ordinary days and 25 simulated days. The test file holds every day of 2025 and 2026
and 25 simulated days of each year.
"""

import json
import random
from collections import Counter

import numpy as np
import pandas as pd

from swissgrid_cot.explain import samples
from swissgrid_cot.explain.labels import label_of
from swissgrid_cot.review.context import load_hourly, scored_days
from swissgrid_cot.review.hourly import day_matrix
from swissgrid_cot.review.references import ReferenceBuilder, as_list
from swissgrid_cot.sources import PROCESSED_DIR

OUT = PROCESSED_DIR / "opentslm_explain"
SEED = 20261120
ORDINARY_KEEP = {"train": 0.3, "validation": 0.3, "test": 1.0, "holdout": 1.0}
TRAIN_TARGET = 100
MAX_COPIES = 4
SIMULATED = {"train": 200, "validation": 25, "test": 25, "holdout": 25}
SPLIT_FILE = {"train": "train", "validation": "validation", "test": "test", "holdout": "test"}


def inject_window(values: np.ndarray, rng: random.Random) -> np.ndarray:
    out = values.copy()
    length = rng.randint(3, 6)
    start = rng.randint(0, 24 - length)
    out[start : start + length] *= 1 + rng.choice((-1, 1)) * rng.uniform(0.12, 0.25)
    return out


class DayRows:
    """The curves of every day and the samples built from them."""

    def __init__(self):
        hourly = load_hourly()
        self.days = scored_days(hourly)
        self.load = day_matrix(hourly).reindex(self.days.index)
        self.builder = ReferenceBuilder(self.days, self.load)

    def row(self, date: pd.Timestamp, values: np.ndarray | None = None, label: str | None = None) -> dict | None:
        """The sample of a day, or None when it has no reference or profile. ``values`` replaces its load."""
        d = self.days.loc[date]
        if not np.isfinite(d.z):  # no weather or expectation for the day
            return None
        if values is None:
            if self.load.loc[date].isna().any():
                return None
            values = self.load.loc[date].to_numpy()
        ref = self.builder.blind_normal(date)
        profiles = self.builder.profiles(date)
        if not ref.sufficient or any(v is None for v in profiles.values()):
            return None
        weekday = date.day_name()
        label = label or label_of(d.kind, d.period)
        ev = samples.evidence(values, ref.curve, profiles)
        curves = {"load_mw": as_list(values), "reference_mw": as_list(ref.curve),
                  "sunday_mw": as_list(profiles["sunday"] * float(values.mean()))}  # fmt: skip
        return {
            "task": "day_signature",
            "split": d.split,
            "date": date.date().isoformat(),
            "weekday": weekday,
            "flagged": bool(d.is_anomaly),
            "cause": d.cause,
            "z": round(float(d.z), 2),
            "pre_prompt": samples.pre_prompt(weekday),
            "series": [{"name": name, "unit": "MW", "values": curves[key]} for name, key in samples.SERIES],
            "post_prompt": samples.POST_PROMPT,
            "answer": samples.rationale(weekday, ev, label),
            "target": {"label": label},
            "evidence": ev,
            "n_comparable": ref.n,
        }


def main() -> None:
    rng = random.Random(SEED)
    dr = DayRows()
    real: dict[str, list[dict]] = {}
    for date in dr.days.index:
        row = dr.row(date)
        if row is not None:
            real.setdefault(row["split"], []).append({"id": f"{row['date']}/real", "set": "real", **row})

    out: dict[str, list[dict]] = {"train": [], "validation": [], "test": []}
    for split, rows in real.items():
        counts = Counter(r["target"]["label"] for r in rows)
        for r in rows:
            label = r["target"]["label"]
            if label == "ordinary":
                if rng.random() < ORDINARY_KEEP[split]:
                    out[SPLIT_FILE[split]].append(r)
                continue
            copies = min(MAX_COPIES, max(1, round(TRAIN_TARGET / counts[label]))) if split == "train" else 1
            out[SPLIT_FILE[split]] += [r] + [{**r, "id": f"{r['id']}/copy{i}"} for i in range(2, copies + 1)]
        ordinary = [r for r in rows if r["target"]["label"] == "ordinary"]
        for r in rng.sample(ordinary, SIMULATED[split]):
            date = pd.Timestamp(r["date"])
            values = inject_window(np.asarray(r["series"][0]["values"], dtype=float), rng)
            sim = dr.row(date, values, "irregularity")
            out[SPLIT_FILE[split]].append({"id": f"{r['date']}/simulated", "set": "simulated", **sim,
                                           "simulated": True})  # fmt: skip

    OUT.mkdir(parents=True, exist_ok=True)
    stats = {}
    for name, items in out.items():
        with open(OUT / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for s in items:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
        table = pd.crosstab(pd.Series([s["target"]["label"] for s in items], name="label"),
                            pd.Series([s["split"] for s in items], name="split"))  # fmt: skip
        stats[name] = table.to_dict()
        print(f"{name}: {len(items)} samples\n{table.to_string()}\n")
    (OUT / "stats.json").write_text(json.dumps(stats, indent=1) + "\n")


if __name__ == "__main__":
    main()
