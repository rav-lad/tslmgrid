"""Build the alert-review demo: demo/template.html + review outputs -> demo/index.html.

Usage::

    uv run python demo/build_demo.py [--predictions <test predictions> <all-days predictions>] [--name <system>]

A week grid of 2020-2026: a week is an anomaly if one of its flagged days keeps a deviation after the
hourly review, not sure if one has too few comparable days, normal otherwise. Every week opens its 7
days of load against the comparable days; every day opens its review and the model's written review
of that day (2025-2026: the test predictions plus ``sgcot-review-export --all-days`` run through
``train/predict.py``). It opens on 1 July 2026 (an anomaly); 25 May 2026 is a flagged holiday that the
review explains. The scores stay in the README and ``reports/``.
"""

import argparse
import datetime as dt
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROCESSED = REPO / "data" / "processed"
TEMPLATE = REPO / "demo" / "template.html"
OUT = REPO / "demo" / "index.html"
ARTIFACT = REPO / "scratch" / "review_artifact.html"
STATUS = {"deviation_remains": "anomaly", "consistent": "normal", "insufficient_evidence": "not_sure"}
"""A flagged day takes the review's verdict; a day the detector did not flag is normal."""
START = "2026-07-01"
"""The alert shown when the page opens; 2026-05-25 (Pentecost Monday) is the consistent counterpart."""
SKELETON = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>:root{{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}}body{{margin:0}}[hidden]{{display:none!important}}</style>
</head>
<body>
{page}
</body>
</html>
"""


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, nargs="*", default=[],
                        help="OpenTSLM prediction files (sample_id, generated); later files add days")  # fmt: skip
    parser.add_argument("--name", default=None, help="system name shown with the model's answers")
    args = parser.parse_args()

    days = {r["date"]: r for r in read_jsonl(PROCESSED / "review" / "days.jsonl")}
    prompts = {}
    for path in (PROCESSED / "opentslm_review_days" / "test.jsonl", PROCESSED / "opentslm_review" / "test.jsonl"):
        if path.exists():
            prompts |= {s["id"]: s["pre_prompt"] for s in read_jsonl(path) if s["set"] == "real"}
    preds = {}
    for path in args.predictions:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            try:  # a file still being written may end with a partial line
                p = json.loads(line)
            except json.JSONDecodeError:
                continue
            preds[p["sample_id"]] = p["generated"]

    out = []
    for date, r in days.items():
        c, v = r["context"], r["review"]
        d = dt.date.fromisoformat(date)
        iso = d.isocalendar()
        status = STATUS[v["outcome"]] if r["flagged"] else "normal"
        subtitle = (f"{c['holiday_name']}, holiday for {100 * c['holiday_pop_share']:.0f}% of the population"
                    if c["holiday_name"] and c["holiday_pop_share"] > 0 else "No holiday")  # fmt: skip
        special = [p for p in (
            f"{c['holiday_name']} ({100 * c['holiday_pop_share']:.0f}% of the population)"
            if c["holiday_name"] and c["holiday_pop_share"] > 0 and d.weekday() < 5 else None,
            "bridge day" if c["kind"] == "bridge_day" else None,
            {"christmas": "Christmas holidays", "summer": "summer holidays"}.get(c["period"]),
            "COVID-19 lockdown" if c["kind"] == "lockdown" else None,
        ) if p]  # fmt: skip
        ref = r["context_reference_mw"] if v["outcome"] != "insufficient_evidence" else None
        out.append({
            "date": date, "year": iso.year, "week": iso.week, "status": status, "flagged": r["flagged"],
            "title": f"{d.strftime('%A')} {d.day} {d.strftime('%B %Y')}", "subtitle": subtitle, "special": ", ".join(special)[:1].upper() + ", ".join(special)[1:],
            "load": [round(x) for x in r["load_mw"]], "ref": None if ref is None else [round(x) for x in ref],
            "hours": v["review_hours"], "residual": v["day_residual_pct"], "n_comparable": v["n_comparable"],
            "rel_dev_pct": c["rel_dev_pct"], "temp_c": c["temp_c"], "temp_normal_c": c["temp_normal_c"],
            "model_text": preds.get(f"{date}/real"),
            "prompt": prompts.get(f"{date}/real") if f"{date}/real" in preds else None,
        })  # fmt: skip
    last_week = dt.date.fromisoformat(max(days)).isocalendar()

    data = {"days": out, "model_name": args.name, "start": START,
            "last_week": [last_week.year, last_week.week], "first_year": 2020,
            "weeks_in_year": {y: dt.date(y, 12, 28).isocalendar().week for y in range(2020, last_week.year + 1)}}  # fmt: skip
    page = TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", json.dumps(data, ensure_ascii=False))
    OUT.write_text(SKELETON.format(page=page), encoding="utf-8")
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} and {ARTIFACT}")


if __name__ == "__main__":
    main()
