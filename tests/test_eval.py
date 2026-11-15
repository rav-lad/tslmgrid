"""Scoring of model predictions: parsing, number grounding, coverage and id checks."""

import json

import pytest

from swissgrid_cot.eval.metrics import score, ungrounded_numbers
from swissgrid_cot.eval.score import PredictionError, check_ids, read_predictions


def _sample(task: str, target, **facts) -> dict:
    return {"id": f"2025-W16/{task}", "task": task, "target": target, "facts": facts, "pre_prompt": ""}


SAMPLES = [
    _sample("anomaly_cause", "public_holiday", load="5,243"),
    _sample("anomaly_days", ["2025-04-18"], date="2025-04-18"),
    _sample("exchange", "net exporter", net="818"),
]
GOLD = {
    "2025-W16/anomaly_cause": "Load was 5,243 MW. Answer: public_holiday",
    "2025-W16/anomaly_days": "Friday was low. Answer: 2025-04-18",
    "2025-W16/exchange": "Net exports of 818 MW. Answer: net exporter",
}


def test_perfect_predictions_score_one():
    m = score(SAMPLES, GOLD)
    assert m["cause_accuracy"] == m["day_f1"] == m["exchange_accuracy"] == m["parsable_rate"] == 1.0
    assert m["hallucinated_number_rate"] == m["ungrounded_number_rate_tol"] == 0.0


def test_missing_prediction_counts_as_wrong():
    m = score(SAMPLES, {k: v for k, v in GOLD.items() if not k.endswith("exchange")})
    assert m["exchange_accuracy"] == 0.0
    assert m["parsable_rate"] == pytest.approx(2 / 3, abs=1e-4)


def test_lenient_number_check_accepts_close_values_only():
    facts = "load 5,243 and z -7.0"
    assert ungrounded_numbers("5,243 MW, z = -7.0", facts) == set()
    assert ungrounded_numbers("5,300 MW", facts) == set()  # within 2 %
    assert ungrounded_numbers("9,999 MW", facts) == {"9999"}
    preds = {**GOLD, "2025-W16/anomaly_cause": "Load was 5,300 MW. Answer: public_holiday"}
    m = score(SAMPLES, preds)
    assert m["hallucinated_number_rate"] > 0 and m["ungrounded_number_rate_tol"] == 0.0


def test_read_predictions_needs_sample_id(tmp_path):
    f = tmp_path / "p.jsonl"
    f.write_text(json.dumps({"generated": "x"}) + "\n")
    with pytest.raises(PredictionError, match="sample_id"):
        read_predictions(f)


def test_read_predictions_rejects_duplicates(tmp_path):
    f = tmp_path / "p.jsonl"
    row = json.dumps({"sample_id": "a/exchange", "generated": "x"})
    f.write_text(row + "\n" + row + "\n")
    with pytest.raises(PredictionError, match="twice"):
        read_predictions(f)


def test_unknown_ids_are_rejected():
    with pytest.raises(PredictionError, match="another export"):
        check_ids(SAMPLES, {"2024-W01/exchange": "x"}, "test")
