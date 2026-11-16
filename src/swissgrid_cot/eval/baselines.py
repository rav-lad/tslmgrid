"""Non-learned baselines, scored with the same metrics as the fine-tuned model.

Usage::

    uv run sgcot-baselines            # scores every baseline on validation and test

* ``oracle``: the gold rationale itself. It must score 1.0 everywhere; it checks the parser.
* ``majority``: the most frequent train answer of each task ("none", no day, the majority role).
* ``calendar``: rules that see the calendar only, never the consumption series. A weekday is
  anomalous if it is a public holiday for at least half the population, a bridge day, a weekday of
  24 Dec - 2 Jan, or a weekday of the 2020 lockdown; its cause follows from that rule. The exchange
  answer is the train majority role of the window's month.

Writes ``reports/eval/baselines.json`` and the Markdown table ``reports/eval/baselines.md``.
"""

import json
from collections import Counter

import pandas as pd

from swissgrid_cot.eval.metrics import score
from swissgrid_cot.sources import PROCESSED_DIR, REPO_ROOT

SAMPLES = PROCESSED_DIR / "opentslm"
OUT = REPO_ROOT / "reports" / "eval"
TABLE_METRICS = (
    "cause_accuracy", "cause_macro_f1", "window_anomaly_f1", "day_precision", "day_recall", "day_f1",
    "exchange_accuracy", "parsable_rate", "hallucinated_number_rate", "ungrounded_number_rate_tol",
)  # fmt: skip


def load(split: str) -> list[dict]:
    return [json.loads(line) for line in (SAMPLES / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()]


def oracle(samples: list[dict]) -> dict[str, str]:
    return {s["id"]: s["answer"] for s in samples}


def majority(samples: list[dict], train: list[dict]) -> dict[str, str]:
    role = Counter(s["target"] for s in train if s["task"] == "exchange").most_common(1)[0][0]
    answers = {"anomaly_cause": "Answer: none", "anomaly_days": "Answer: none", "exchange": f"Answer: {role}"}
    return {s["id"]: answers[s["task"]] for s in samples}


def _calendar_cause(day: pd.Series) -> str | None:
    if day.dow >= 5:
        return None
    if day.lockdown:
        return "covid_lockdown"
    if (day.name.month == 12 and day.name.day >= 24) or (day.name.month == 1 and day.name.day <= 2):
        return "christmas_newyear"
    if day.holiday_pop_share >= 0.5:
        return "public_holiday"
    if day.is_bridge_day:
        return "bridge_day"
    return None


def calendar(samples: list[dict], train: list[dict]) -> dict[str, str]:
    days = pd.read_parquet(PROCESSED_DIR / "annotations" / "days.parquet")
    month_role = {}
    for s in train:
        if s["task"] == "exchange":
            month_role.setdefault(pd.Timestamp(s["facts"]["start_local"]).month, Counter())[s["target"]] += 1
    month_role = {m: c.most_common(1)[0][0] for m, c in month_role.items()}
    priority = ["covid_lockdown", "christmas_newyear", "public_holiday", "bridge_day"]
    out = {}
    for s in samples:
        week = pd.date_range(s["facts"]["start_local"], s["facts"]["end_local"], freq="D")
        flagged = {str(d.date()): c for d, c in ((d, _calendar_cause(days.loc[d])) for d in week) if c}
        if s["task"] == "anomaly_cause":
            label = min(flagged.values(), key=priority.index) if flagged else "none"
            out[s["id"]] = f"Answer: {label}"
        elif s["task"] == "anomaly_days":
            out[s["id"]] = "Answer: " + (", ".join(sorted(flagged)) if flagged else "none")
        else:
            out[s["id"]] = f"Answer: {month_role[pd.Timestamp(s['facts']['start_local']).month]}"
    return out


def table(results: dict[str, dict[str, dict]]) -> str:
    lines = ["| split | system | " + " | ".join(TABLE_METRICS) + " |", "|" + " --- |" * (len(TABLE_METRICS) + 2)]
    for split, systems in results.items():
        for name, m in systems.items():
            lines.append(f"| {split} | {name} | " + " | ".join(f"{m.get(k, float('nan')):.3f}" for k in TABLE_METRICS) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    train = load("train")
    results: dict[str, dict[str, dict]] = {}
    for split in ("validation", "test"):
        samples = load(split)
        results[split] = {
            "oracle (gold rationale)": score(samples, oracle(samples)),
            "majority": score(samples, majority(samples, train)),
            "calendar rules (no load data)": score(samples, calendar(samples, train)),
        }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "baselines.json").write_text(json.dumps(results, indent=2) + "\n")
    (OUT / "baselines.md").write_text(table(results), encoding="utf-8")
    print(table(results))
    print("calendar baseline, test cause confusion:", results["test"]["calendar rules (no load data)"]["cause_confusion"])


if __name__ == "__main__":
    main()
