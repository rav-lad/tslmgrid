"""Check the figures of the model's rationales against what the rules measure on the same curves.

Usage::

    uv run sgcot-explain-fidelity --predictions <test_predictions.jsonl> --name <system>

The label is the weak part of the day signature (``score``); this checks the reading. Each rationale
states the day-level gap, the gap per part of the day, the closest typical profile, whether the gap
spans the day, stays in a few hours or reshapes the day, and those hours. The rules measure the same
on the curves (``samples.evidence``).

OpenTSLM writes the mean of each series in the text, so the day-level gap is close to
mean(load) / mean(reference) - 1 without reading the shape: the ``stated means`` row does that. What the
means do not give is the shape: the gap of each part of the day against the day-level gap, the profile,
the structure and the hours. ``weekday only`` answers the train average (or majority) of the weekday.

Metrics: mean absolute error in points (level, part of the day relative to the level), share within 3
points, sign agreement on days whose gap is at least 3 %, profile accuracy (ties left out), structure
accuracy, and the overlap (Jaccard) of the hours the model names with the measured ones on the days
that have some.
"""

import argparse
import json
import re
from collections import Counter

import numpy as np
import pandas as pd

from swissgrid_cot.explain.score import OUT, groups, load
from swissgrid_cot.review.hourly import DAYPARTS

NUM = r"([+-]?\d+\.\d)%"
LEVEL = re.compile(rf"runs {NUM} over the day: {NUM} at night, {NUM} in the morning, {NUM} in the afternoon "
                   rf"and {NUM} in the evening")  # fmt: skip
PROFILE = re.compile(r"closest to a typical (weekday|saturday|sunday)")
SIDE = re.compile(rf"{NUM} over ((?:\d\d:00-\d\d:59(?:, )?)+)")
WINDOW = re.compile(r"(\d\d):00-(\d\d):59")


def structure_of(ev: dict) -> str:
    if not ev["local"]["above"]["hours"] and not ev["local"]["below"]["hours"]:
        return "spans"
    return "confined" if ev["confined"] else "reshapes"


def measured(s: dict) -> dict:
    ev = s["evidence"]
    return {"level": ev["level_pct"], "parts": ev["daypart_pct"], "profile": None if ev["profile_tie"] else ev["profile"],
            "structure": structure_of(ev),
            "hours": set(ev["local"]["above"]["hours"] + ev["local"]["below"]["hours"])}  # fmt: skip


def read(text: str) -> dict | None:
    """The figures of a rationale, or None when its first sentence does not parse."""
    m = LEVEL.search(text)
    if not m:
        return None
    p = PROFILE.search(text)
    if "spans the day" in text:
        structure = "spans"
    elif "the rest of the day follows it" in text:
        structure = "confined"
    elif "reshapes the day" in text:
        structure = "reshapes"
    else:
        structure = None
    hours = set()
    for _, windows in SIDE.findall(text):
        for a, b in WINDOW.findall(windows):
            hours |= set(range(int(a), int(b) + 1))
    return {"level": float(m.group(1)), "parts": dict(zip(DAYPARTS, map(float, m.groups()[1:]))),
            "profile": p.group(1) if p else None, "structure": structure, "hours": hours}  # fmt: skip


class WeekdayOnly:
    def __init__(self, train: list[dict]):
        by_day: dict[str, list[dict]] = {}
        for s in train:
            if "/copy" not in s["id"]:
                by_day.setdefault(s["weekday"], []).append(measured(s))
        self.answer = {}
        for day, ms in by_day.items():
            self.answer[day] = {
                "level": float(np.mean([m["level"] for m in ms])),
                "parts": {p: float(np.mean([m["parts"][p] for m in ms])) for p in DAYPARTS},
                "profile": Counter(m["profile"] for m in ms if m["profile"]).most_common(1)[0][0],
                "structure": Counter(m["structure"] for m in ms).most_common(1)[0][0],
                "hours": set(),
            }

    def __call__(self, s: dict) -> dict:
        return self.answer[s["weekday"]]


def stated_means(s: dict) -> dict:
    load_, ref = (float(np.mean(x["values"])) for x in s["series"][:2])
    level = 100 * (load_ / ref - 1)
    return {"level": level, "parts": dict.fromkeys(DAYPARTS, level), "profile": None, "structure": None,
            "hours": set()}  # fmt: skip


def rate(values: list[bool]) -> float | None:
    return round(float(np.mean(values)), 3) if values else None


def score(items: list[dict], reads: dict[str, dict | None], system: str) -> list[dict]:
    rows = []
    for name, group in groups(items).items():
        pairs = [(measured(s), reads.get(s["id"])) for s in group]
        ok = [(g, r) for g, r in pairs if r is not None]
        level_err = [abs(r["level"] - g["level"]) for g, r in ok]
        part_err = [abs((r["parts"][p] - r["level"]) - (g["parts"][p] - g["level"])) for g, r in ok for p in DAYPARTS]
        with_hours = [(g, r) for g, r in ok if g["hours"]]
        rows.append({
            "group": name, "system": system, "n": len(group), "parsed": rate([r is not None for _, r in pairs]),
            "level_mae": round(float(np.mean(level_err)), 2) if ok else None,
            "level_within_3": rate([e <= 3 for e in level_err]),
            "level_sign": rate([np.sign(r["level"]) == np.sign(g["level"]) for g, r in ok if abs(g["level"]) >= 3]),
            "daypart_rel_mae": round(float(np.mean(part_err)), 2) if ok else None,
            "profile_acc": rate([r["profile"] == g["profile"] for g, r in ok if g["profile"] and r["profile"]]),
            "structure_acc": rate([r["structure"] == g["structure"] for g, r in ok if r["structure"]]),
            "hours_jaccard": round(float(np.mean([len(g["hours"] & r["hours"]) / len(g["hours"] | r["hours"])
                                                  for g, r in with_hours])), 3) if with_hours and any(
                r["hours"] for _, r in ok) else None,
        })  # fmt: skip
    return rows


def flagged_table(items: list[dict], reads: dict[str, dict | None]) -> pd.DataFrame:
    rows = []
    for s in items:
        if s["set"] != "real" or not s["flagged"]:
            continue
        g, r = measured(s), reads.get(s["id"])
        rows.append({"date": s["date"], "weekday": s["weekday"][:3], "calendar": s["target"]["label"],
                     "level": g["level"], "model_level": r and r["level"],
                     "profile": s["evidence"]["profile"], "model_profile": r and r["profile"],
                     "structure": g["structure"], "model_structure": r and r["structure"]})  # fmt: skip
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--predictions", required=True, help="test_predictions.jsonl written by train/select_epoch.py")
    parser.add_argument("--name", default="model")
    args = parser.parse_args()
    train, test = load("train"), load("test")
    with open(args.predictions, encoding="utf-8") as f:
        model = {r["sample_id"]: read(r["generated"]) for r in map(json.loads, f)}
    weekday = WeekdayOnly(train)
    rows = (score(test, {s["id"]: weekday(s) for s in test}, "weekday only")
            + score(test, {s["id"]: stated_means(s) for s in test}, "stated means")
            + score(test, model, args.name))  # fmt: skip
    df = pd.DataFrame(rows).sort_values(["group", "system"])
    table = flagged_table(test, model)
    text = "\n".join([f"# Rationale figures: {args.name}", "", df.to_markdown(index=False), "",
                      "Flagged real days (|z| >= 3) of 2025 and 2026, measured against read:", "",
                      table.to_markdown(index=False), ""])  # fmt: skip
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{args.name}_fidelity.json").write_text(json.dumps(rows, indent=1) + "\n")
    (OUT / f"{args.name}_fidelity.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
