"""Score the day signatures: the model, a weekday-only baseline and a nearest-neighbour curve classifier.

Usage::

    uv run sgcot-explain-score                                   # baselines only
    uv run sgcot-explain-score --predictions <test_predictions.jsonl> --name <system>

Systems:

* ``weekday only``: sees what the prompt states, the weekday, and answers the train majority label of
  that weekday. It is what a model that does not read the series can do.
* ``curve kNN``: the 7 nearest train samples (copies left out) on the hourly gap e(h) =
  load(h) / reference(h) - 1 and the three shape distances, each standardized on train; majority
  vote, a tie goes to the nearest. A simple reader of the same curves, the bar the model has to clear.
* the model: the label of its last 'Answer:'; a missing or unknown label counts as wrong.

Groups: validation 2024, test 2025, holdout 2026, each split into all real days, the flagged real days
(|z| >= 3, the alerts) and the simulated irregularities. Metrics: accuracy, macro F1 over the labels
present in the group, recall per label. The confusion matrix covers the real days of 2025 and 2026.
"""

import argparse
import json
from collections import Counter

import numpy as np
import pandas as pd

from swissgrid_cot.explain.export import OUT as SAMPLES
from swissgrid_cot.explain.labels import LABELS
from swissgrid_cot.explain.samples import parse_answer
from swissgrid_cot.sources import REPO_ROOT

OUT = REPO_ROOT / "reports" / "explain_eval"
K = 7


def load(name: str) -> list[dict]:
    with open(SAMPLES / f"{name}.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def features(s: dict) -> np.ndarray:
    load_, ref = (np.asarray(x["values"], dtype=float) for x in s["series"][:2])
    dist = s["evidence"]["profile_distances"]
    return np.concatenate([load_ / ref - 1, [dist["weekday"], dist["saturday"], dist["sunday"]]])


class WeekdayOnly:
    def __init__(self, train: list[dict]):
        by_day: dict[str, Counter] = {}
        for s in train:
            by_day.setdefault(s["weekday"], Counter())[s["target"]["label"]] += 1
        self.answer = {d: c.most_common(1)[0][0] for d, c in by_day.items()}

    def __call__(self, s: dict) -> str:
        return self.answer[s["weekday"]]


class CurveKNN:
    def __init__(self, train: list[dict]):
        unique = [s for s in train if "/copy" not in s["id"]]
        x = np.vstack([features(s) for s in unique])
        self.mean, self.sd = x.mean(axis=0), x.std(axis=0) + 1e-9
        self.x = (x - self.mean) / self.sd
        self.y = [s["target"]["label"] for s in unique]

    def __call__(self, s: dict) -> str:
        d = np.sqrt((((features(s) - self.mean) / self.sd - self.x) ** 2).sum(axis=1))
        near = np.argsort(d)[:K]
        votes = Counter(self.y[i] for i in near)
        top = max(votes.values())
        return next(self.y[i] for i in near if votes[self.y[i]] == top)


def macro_f1(gold: list[str], pred: list[str | None]) -> float:
    f1s = []
    for lab in sorted(set(gold)):
        tp = sum(g == lab and p == lab for g, p in zip(gold, pred))
        fp = sum(g != lab and p == lab for g, p in zip(gold, pred))
        fn = sum(g == lab and p != lab for g, p in zip(gold, pred))
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return float(np.mean(f1s)) if f1s else float("nan")


def groups(items: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for s in items:
        year = {"validation": "validation 2024", "test": "test 2025", "holdout": "holdout 2026"}[s["split"]]
        if s["set"] == "simulated":
            out.setdefault(f"{year} / simulated", []).append(s)
            continue
        out.setdefault(f"{year} / real", []).append(s)
        if s["flagged"]:
            out.setdefault(f"{year} / flagged", []).append(s)
    return out


def score(items: list[dict], answers: dict[str, str | None], system: str) -> list[dict]:
    rows = []
    for name, group in groups(items).items():
        gold = [s["target"]["label"] for s in group]
        pred = [answers.get(s["id"]) for s in group]
        row = {"group": name, "system": system, "n": len(group),
               "parsable": round(float(np.mean([p is not None for p in pred])), 3),
               "accuracy": round(float(np.mean([g == p for g, p in zip(gold, pred)])), 3),
               "macro_f1": round(macro_f1(gold, pred), 3)}  # fmt: skip
        for lab in LABELS:
            hit = [p == lab for g, p in zip(gold, pred) if g == lab]
            row[f"recall_{lab}"] = round(float(np.mean(hit)), 3) if hit else None
        rows.append(row)
    return rows


def confusion(items: list[dict], answers: dict[str, str | None]) -> pd.DataFrame:
    real = [s for s in items if s["set"] == "real" and s["split"] in ("test", "holdout")]
    gold = pd.Series([s["target"]["label"] for s in real], name="calendar")
    pred = pd.Series([answers.get(s["id"]) or "unparsable" for s in real], name="answer")
    return pd.crosstab(gold, pred)


def report(rows: list[dict], conf: dict[str, pd.DataFrame], title: str) -> str:
    df = pd.DataFrame(rows).sort_values(["group", "system"])
    lines = [f"# {title}", "", df.to_markdown(index=False), ""]
    for system, table in conf.items():
        lines += [f"Real days of 2025 and 2026, calendar label (rows) against {system} (columns):", "",
                  table.to_markdown(), ""]  # fmt: skip
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--predictions", help="test_predictions.jsonl written by train/select_epoch.py")
    parser.add_argument("--name", default="model")
    args = parser.parse_args()
    train, validation, test = load("train"), load("validation"), load("test")
    systems = {"weekday only": WeekdayOnly(train), "curve kNN": CurveKNN(train)}
    OUT.mkdir(parents=True, exist_ok=True)

    if not args.predictions:
        rows, conf = [], {}
        for system, f in systems.items():
            answers = {s["id"]: f(s) for s in validation + test}
            rows += score(validation + test, answers, system)
            conf[system] = confusion(test, answers)
        (OUT / "baselines.json").write_text(json.dumps(rows, indent=1) + "\n")
        text = report(rows, conf, "Day signature: baselines")
        (OUT / "baselines.md").write_text(text, encoding="utf-8")
        print(text)
        return

    with open(args.predictions, encoding="utf-8") as f:
        model = {r["sample_id"]: parse_answer(r["generated"]) for r in map(json.loads, f)}
    rows, conf = [], {}
    for system, f in systems.items():
        rows += score(test, {s["id"]: f(s) for s in test}, system)
    rows += score(test, model, args.name)
    conf[args.name] = confusion(test, model)
    (OUT / f"{args.name}_test.json").write_text(json.dumps(rows, indent=1) + "\n")
    text = report(rows, conf, f"Day signature: {args.name}")
    (OUT / f"{args.name}_test.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
