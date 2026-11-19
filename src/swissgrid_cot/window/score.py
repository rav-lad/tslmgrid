"""Score the window review: the model against a threshold and the rules, on the same test samples.

Usage::

    uv run sgcot-window-score                                   # baselines only
    uv run sgcot-window-score --predictions <test_predictions.jsonl> --name <system>

Systems:

* ``threshold``: yes when the day shows a gap (level >= 7 % against the reference, or 3+ hours at 15 %
  from the median hour), whatever the calendar and the temperature.
* ``rules``: the threshold, then the calendar and the temperature (``samples.label`` without knowing of
  any perturbation). On the real days it is the label itself; on the perturbations it is what the rules
  see of them.
* the model: its last 'Answer: yes|no'; none counts as wrong.

Groups: test 2025 and holdout 2026, each split into the perturbations (yes by construction), the
special real days (holidays, bridge days, Christmas, summer, lockdown: expected gaps), the ordinary
real days labelled no and the real days labelled yes (the candidates, ``candidates.md``). Metrics: the
share answered yes, and the accuracy against the label. Perturbations: recall by type and by |delta|.
"""

import argparse
import json
import re

import numpy as np
import pandas as pd

from swissgrid_cot.window import samples
from swissgrid_cot.window.export import OUT as SAMPLES
from swissgrid_cot.window.export import REPORT as OUT

TEMP = re.compile(r"Daily mean temperature (-?\d+\.\d) °C \(normal (-?\d+\.\d) °C\)")
BINS = ((10, 15), (15, 20), (20, 25), (25, 36))


def load(name: str) -> list[dict]:
    with open(SAMPLES / f"{name}.jsonl", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def threshold(s: dict) -> bool:
    return samples.has_gap(s["evidence"], s["evidence"]["strong_runs"])


def rules(s: dict) -> bool:
    t, normal = map(float, TEMP.search(s["pre_prompt"]).groups())
    return samples.label(s["evidence"], s["evidence"]["strong_runs"], s["kind"], s["period"], t, normal, None)["investigate"]


def group_of(s: dict) -> str:
    year = {"test": "test 2025", "holdout": "holdout 2026"}.get(s["split"], s["split"])
    if s["set"] == "injected":
        return f"{year} / perturbations"
    if s["target"]["investigate"]:
        return f"{year} / real, labelled yes"
    if s["kind"] in samples.SPECIAL_KINDS or s["period"] != "regular":
        return f"{year} / real special days, labelled no"
    return f"{year} / real ordinary days, labelled no"


def score(items: list[dict], answers: dict[str, bool | None], system: str) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for s in items:
        groups.setdefault(group_of(s), []).append(s)
    rows = []
    for name, group in sorted(groups.items()):
        pred = [answers.get(s["id"]) for s in group]
        gold = [s["target"]["investigate"] for s in group]
        row = {"group": name, "system": system, "n": len(group),
               "answered_yes": round(float(np.mean([p is True for p in pred])), 3),
               "accuracy": round(float(np.mean([p == g for p, g in zip(pred, gold)])), 3)}  # fmt: skip
        if name.endswith("perturbations"):
            for kind in ("drop", "spike", "level_shift"):
                hit = [p is True for s, p in zip(group, pred) if s["perturbation"]["type"] == kind]
                row[f"recall_{kind}"] = round(float(np.mean(hit)), 3) if hit else None
            for lo, hi in BINS:
                hit = [p is True for s, p in zip(group, pred) if lo <= abs(s["perturbation"]["delta_pct"]) < hi]
                row[f"recall_{lo}-{hi}%"] = round(float(np.mean(hit)), 3) if hit else None
        rows.append(row)
    return rows


def days_table(items: list[dict], systems: dict[str, dict[str, bool | None]]) -> pd.DataFrame:
    """The real days labelled yes and the flagged real days, with every system's answer."""
    rows = []
    for s in items:
        if s["set"] != "real" or not (s["target"]["investigate"] or s["flagged"]):
            continue
        row = {"date": s["date"], "weekday": s["weekday"][:3], "kind": s["kind"], "period": s["period"],
               "level_pct": s["evidence"]["level_pct"], "z": s["z"], "label": "yes" if s["target"]["investigate"] else "no"}  # fmt: skip
        for name, answers in systems.items():
            a = answers.get(s["id"])
            row[name] = "-" if a is None else ("yes" if a else "no")
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--predictions", help="test_predictions.jsonl written by train/select_epoch.py")
    parser.add_argument("--name", default="model")
    args = parser.parse_args()
    test = load("test")
    systems = {"threshold": {s["id"]: threshold(s) for s in test}, "rules": {s["id"]: rules(s) for s in test}}
    if args.predictions:
        with open(args.predictions, encoding="utf-8") as f:
            systems[args.name] = {r["sample_id"]: samples.parse_answer(r["generated"]) for r in map(json.loads, f)}
    rows = [row for name, answers in systems.items() for row in score(test, answers, name)]
    df = pd.DataFrame(rows).sort_values(["group", "system"])
    title = args.name if args.predictions else "baselines"
    text = "\n".join([f"# Window review: {title}", "", df.to_markdown(index=False), "",
                      "Real days labelled yes and flagged real days (|z| >= 3), 2025 and 2026:", "",
                      days_table(test, systems).to_markdown(index=False), ""])  # fmt: skip
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"{args.name}_test" if args.predictions else "baselines"
    (OUT / f"{stem}.json").write_text(json.dumps(rows, indent=1) + "\n")
    (OUT / f"{stem}.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
