"""Build the demo page: demo/template.html + the project's outputs -> demo/index.html (self-contained).

Usage::

    uv run python demo/build_demo.py [--predictions <OpenTSLM test predictions .jsonl>]

The page embeds every ISO week: hourly series, the daily expectation and normal temperature, the
rule-based facts, prompts and reference rationales. With ``--predictions`` (the OpenTSLM file whose
rows carry ``sample_id`` and ``generated``), it also embeds the model's answers for those samples.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
PROCESSED = REPO / "data" / "processed"
TEMPLATE = REPO / "demo" / "template.html"
OUT = REPO / "demo" / "index.html"
ARTIFACT = REPO / "scratch" / "demo_artifact.html"
TASKS = ("anomaly_cause", "anomaly_days", "exchange")
SKELETON = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}[hidden]{display:none!important}</style>
</head>
<body>
{page}
</body>
</html>
"""


def rounded(values, digits: int) -> list:
    return [round(float(v), digits) for v in values]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, help="OpenTSLM predictions with sample_id and generated")
    args = parser.parse_args()

    hourly = pd.read_parquet(PROCESSED / "ch_hourly.parquet")
    days = pd.read_parquet(PROCESSED / "annotations" / "days.parquet")
    windows = [json.loads(line) for line in (PROCESSED / "annotations" / "windows.jsonl").read_text(encoding="utf-8").splitlines()]
    predictions: dict[str, str] = {}
    if args.predictions:
        for line in args.predictions.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if "sample_id" in row:
                predictions[row["sample_id"]] = row["generated"]

    weeks = []
    for w in windows:
        f = w["facts"]
        span = pd.date_range(f["start_local"], f["end_local"], freq="D")
        h = hourly[hourly.local_date.isin(span)]
        d = days.loc[span]
        weeks.append({
            "id": w["window_id"],
            "split": w["split"],
            "label": w["label"],
            "start": f["start_local"],
            "anomalous": w["anomalous_dates"],
            "exchange": w["exchange_answer"],
            # Hour index -> local day index (0-6) and local hour, for the axes.
            "dayIdx": [int((t - span[0]).days) for t in h.local_date],
            "hour": [int(x) for x in h.local_hour],
            "load": rounded(h.load_enduser_mw, 0),
            "temp": rounded(h.temp_c, 1),
            "rad": rounded(h.radiation_wm2, 0),
            "imp": {b: rounded(h[f"net_import_{b}_mw"], 0) for b in ("at", "de", "fr", "it")},
            "net": rounded(h.net_import_mw, 0),
            "expected": rounded(d.expected_mw, 0),
            "tempNormal": rounded(d.temp_normal_c, 1),
            "days": f["days"],
            "weather": f["weather"],
            "x": f["exchange"],
            "prompts": w["prompts"],
            "reference": w["rationales"],
            "model": {t: predictions[f"{w['window_id']}/{t}"] for t in TASKS if f"{w['window_id']}/{t}" in predictions},
        })  # fmt: skip

    summary = json.loads((PROCESSED / "annotations" / "summary.json").read_text())
    baselines_path = REPO / "reports" / "eval" / "baselines.json"
    payload = {
        "weeks": weeks,
        "hasModel": bool(predictions),
        "baseline": summary["baseline_accuracy"],
        "evalBaselines": json.loads(baselines_path.read_text())["test"] if baselines_path.exists() else None,
    }
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8")
    marker = "/*__DATA__*/null"
    if html.count(marker) != 1:
        raise SystemExit(f"{TEMPLATE.name} must hold the marker {marker} exactly once")
    page = html.replace(marker, data)
    # The template is a body fragment: the artifact host adds the document skeleton, a static host needs it here.
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(page, encoding="utf-8")
    OUT.write_text(SKELETON.replace("{page}", page), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB, {len(weeks)} weeks, {len(predictions)} model answers)")


if __name__ == "__main__":
    main()
