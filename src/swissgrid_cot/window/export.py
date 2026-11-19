"""Export the window-review samples for OpenTSLM, and the real days the rules find worth investigating.

Usage::

    uv run sgcot-window-export

Writes ``data/processed/opentslm_window/{train,validation,test}.jsonl`` in the format the stage 6
dataset reads (``pre_prompt, series, post_prompt, answer``; the series carry ``scale_like``), plus
``target`` {investigate, by}, ``set``, ``perturbation`` and the measured ``evidence``. Writes
``reports/window_eval/candidates.md``: the real days labelled yes by the rules, to be checked by hand.

A day is a sample when it has a sufficient recent reference (``ReferenceBuilder.recent_normal``),
complete load, the three typical profiles and a complete day 52 weeks earlier (so not 2020).

Sets (the ``set`` field):

* ``real``: the day as it is, labelled by the rules (``samples.label``).
* ``injected``: a real day with a perturbation (``inject``): a drop or a spike over 2 to 8 hours, or a
  level shift from one hour to the end of the day; |delta| 15-35 % over a window, 10-30 % for a shift,
  above what the weather and the solar output already do to an ordinary day (``samples.LEVEL_PCT``). The reference is the one of the
  original measurements. Labelled yes by construction; type, bounds and delta in ``perturbation``,
  never in the input. Special days (holidays, bridge days, Christmas, summer, lockdown) are drawn twice
  as often, so that a holiday in the text does not mean no.

Splits by date, before any perturbation: train 2021-2023, validation 2024, test 2025 and 2026 (holdout,
``split`` = holdout). A day and its perturbation stay in the same split. Train keeps 35 % of the
ordinary days of the regular period labelled no (validation 40 %), every other real day, and 450
perturbations; validation 80; test 80 per year.
"""

import json
import random
from collections import Counter

import numpy as np
import pandas as pd

from swissgrid_cot.explain.samples import evidence
from swissgrid_cot.review.context import context_of, load_hourly, scored_days
from swissgrid_cot.review.hourly import day_matrix, format_windows
from swissgrid_cot.review.references import ReferenceBuilder, as_list
from swissgrid_cot.sources import PROCESSED_DIR, REPO_ROOT
from swissgrid_cot.window import samples

OUT = PROCESSED_DIR / "opentslm_window"
REPORT = REPO_ROOT / "reports" / "window_eval"
SEED = 20261121
ORDINARY_KEEP = {"train": 0.35, "validation": 0.4, "test": 1.0, "holdout": 1.0}
INJECTED = {"train": 450, "validation": 80, "test": 80, "holdout": 80}
SPLIT_FILE = {"train": "train", "validation": "validation", "test": "test", "holdout": "test"}
LAST_YEAR = pd.Timedelta(weeks=52)


def inject(values: np.ndarray, rng: random.Random) -> tuple[np.ndarray, dict]:
    out = values.copy()
    sign = rng.choice((-1, 1))
    if rng.random() < 0.25:
        kind, start = "level_shift", rng.randint(4, 20)
        end, delta = 23, sign * rng.uniform(0.10, 0.30)
    else:
        delta = sign * rng.uniform(0.15, 0.35)
        length = rng.randint(2, 8)
        start = rng.randint(0, 24 - length)
        end = start + length - 1
        kind = "spike" if delta > 0 else "drop"
    out[start : end + 1] *= 1 + delta
    return out, {"type": kind, "start": start, "end": end, "delta_pct": round(100 * delta, 1)}


def is_special(d) -> bool:
    return d.kind in samples.SPECIAL_KINDS or d.period != "regular"


class DayRows:
    """The curves of every day and the samples built from them."""

    def __init__(self):
        hourly = load_hourly()
        self.days = scored_days(hourly)
        self.load = day_matrix(hourly).reindex(self.days.index)
        self.temp = day_matrix(hourly, "temp_c").reindex(self.days.index)
        self.builder = ReferenceBuilder(self.days, self.load)

    def row(self, date: pd.Timestamp, values: np.ndarray | None = None, injected: dict | None = None) -> dict | None:
        """The sample of a day, or None when it lacks a reference, a profile or its day 52 weeks earlier."""
        d = self.days.loc[date]
        last = date - LAST_YEAR
        if not np.isfinite(d.z) or last not in self.load.index or self.load.loc[last].isna().any():
            return None
        if values is None:
            if self.load.loc[date].isna().any():
                return None
            values = self.load.loc[date].to_numpy()
        temp = self.temp.loc[date].interpolate(limit_direction="both").to_numpy()
        ref = self.builder.recent_normal(date)
        profiles = self.builder.profiles(date)
        if not ref.sufficient or np.isnan(temp).any() or any(v is None for v in profiles.values()):
            return None
        ev = evidence(values, ref.curve, profiles)
        runs = samples.strong_runs(values, ref.curve)
        target = samples.label(ev, runs, d.kind, d.period, float(d.temp_c), float(d.temp_normal_c), injected)
        curves = {"reference_mw": as_list(ref.curve), "load_mw": as_list(values),
                  "last_year_mw": as_list(self.load.loc[last].to_numpy()), "temp_c": as_list(temp)}  # fmt: skip
        return {
            "task": "window_review",
            "split": d.split,
            "date": date.date().isoformat(),
            "weekday": date.day_name(),
            "kind": d.kind,
            "period": d.period,
            "flagged": bool(d.is_anomaly),
            "z": round(float(d.z), 2),
            "pre_prompt": samples.pre_prompt(context_of(d).describe(), float(d.temp_c), float(d.temp_normal_c),
                                             ref.n, context_of(self.days.loc[last]).describe()),  # fmt: skip
            "series": [{"name": name, "unit": unit, "values": curves[key], **({"scale_like": like} if like else {})}
                       for name, key, unit, like in samples.SERIES],  # fmt: skip
            "post_prompt": samples.POST_PROMPT,
            "answer": samples.answer(ev, target, injected, values, ref.curve),
            "target": target,
            "perturbation": injected,
            "evidence": {**ev, "strong_runs": runs},
            "n_reference": ref.n,
        }


def candidates(real: list[dict]) -> str:
    rows = [{"date": r["date"], "weekday": r["weekday"][:3], "split": r["split"], "kind": r["kind"],
             "period": r["period"], "level_pct": r["evidence"]["level_pct"],
             "strong_runs": format_windows(r["evidence"]["strong_runs"]), "z": r["z"]}
            for r in real if r["target"]["investigate"]]  # fmt: skip
    table = pd.DataFrame(rows).to_markdown(index=False) if rows else "none"
    return ("# Real days the rules find worth investigating\n\nA gap (level >= 7 % against the recent reference, or "
            "a run of 3+ hours at 15 % from the median hour) that neither the calendar nor the temperature "
            "explains. To be checked by hand: label each day yes or no.\n\n" + table + "\n")  # fmt: skip


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
        for r in rows:
            d = dr.days.loc[pd.Timestamp(r["date"])]
            if not is_special(d) and not r["target"]["investigate"] and rng.random() >= ORDINARY_KEEP[split]:
                continue
            out[SPLIT_FILE[split]].append(r)
        weights = [2.0 if is_special(dr.days.loc[pd.Timestamp(r["date"])]) else 1.0 for r in rows]
        chosen = set()
        while len(chosen) < min(INJECTED[split], len(rows)):
            chosen.add(rng.choices(range(len(rows)), weights)[0])
        for i in sorted(chosen):
            r = rows[i]
            values, meta = inject(np.asarray(r["series"][1]["values"], dtype=float), rng)
            sim = dr.row(pd.Timestamp(r["date"]), values, meta)
            out[SPLIT_FILE[split]].append({"id": f"{r['date']}/{meta['type']}", "set": "injected", **sim})

    OUT.mkdir(parents=True, exist_ok=True)
    stats = {}
    for name, items in out.items():
        with open(OUT / f"{name}.jsonl", "w", encoding="utf-8") as f:
            f.writelines(json.dumps(s, ensure_ascii=False) + "\n" for s in items)
        counts = Counter((s["split"], s["set"], "yes" if s["target"]["investigate"] else "no") for s in items)
        stats[name] = {" / ".join(k): v for k, v in sorted(counts.items())}
        print(f"{name}: {len(items)} samples")
        for k, v in sorted(counts.items()):
            print(f"  {' / '.join(k)}: {v}")
    (OUT / "stats.json").write_text(json.dumps(stats, indent=1) + "\n")
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / "candidates.md").write_text(candidates([r for rows in real.values() for r in rows]), encoding="utf-8")


if __name__ == "__main__":
    main()
