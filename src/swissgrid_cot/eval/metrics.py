"""Score generated explanations against the rule-based ground truth.

A prediction is the text a system generated for one sample. Its answer is what follows the last
"Answer:". Metrics, per task:

* anomaly_cause: accuracy, macro-F1 over the classes present in the gold labels, and the window-level
  F1 of "some anomaly" versus "none".
* anomaly_days: day-level precision, recall and F1 over every day of the evaluated windows, and the
  share of windows whose set of days is exactly right.
* exchange: accuracy of "net importer" / "net exporter".
* all tasks: the share of outputs with a parsable answer, and the share that state a number found
  neither in the window's facts nor in the prompt (a hallucinated number).
"""

import json
import re
from collections import defaultdict

from swissgrid_cot.annotate.causes import CAUSES
from swissgrid_cot.annotate.rationales import check_numbers

_ANSWER = re.compile(r"Answer:\s*(.+?)\s*$", re.DOTALL)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def answer_of(text: str) -> str | None:
    """The text after the last "Answer:", or None."""
    if "Answer:" not in text:
        return None
    m = _ANSWER.search(text[text.rindex("Answer:") :])
    return m.group(1).strip().rstrip(".").strip() if m else None


def parse(task: str, text: str):
    """Parse a generated text into the task's answer type, or None if it has no valid answer."""
    a = answer_of(text)
    if a is None:
        return None
    a_low = a.lower()
    if task == "anomaly_cause":
        token = a_low.split()[0].strip(",.;") if a_low.split() else ""
        return token if token in CAUSES else None
    if task == "anomaly_days":
        if a_low.startswith("none"):
            return set()
        dates = set(_DATE.findall(a))
        return dates or None
    if task == "exchange":
        if "importer" in a_low:
            return "net importer"
        if "exporter" in a_low:
            return "net exporter"
        return None
    raise ValueError(task)


def _f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def score(samples: list[dict], predictions: dict[str, str]) -> dict:
    """Score predictions (sample id -> generated text) on the given samples.

    Returns:
        A flat dict of metrics, with ``n`` per task and the coverage of predictions.
    """
    by_task: dict[str, list[tuple[dict, str | None]]] = defaultdict(list)
    for s in samples:
        by_task[s["task"]].append((s, predictions.get(s["id"])))
    out: dict = {"n_samples": len(samples), "n_predicted": sum(p is not None for p in predictions.values())}

    halluc, parsable, total = 0, 0, 0
    for task, rows in by_task.items():
        for s, text in rows:
            total += 1
            if text is None:
                continue
            parsable += parse(task, text) is not None
            facts_text = json.dumps(s["facts"], ensure_ascii=False) + " " + s["pre_prompt"]
            halluc += bool(check_numbers(text, facts_text))
    out["parsable_rate"] = round(parsable / total, 4) if total else None
    out["hallucinated_number_rate"] = round(halluc / total, 4) if total else None

    rows = by_task.get("anomaly_cause", [])
    if rows:
        gold = [s["target"] for s, _ in rows]
        pred = [parse("anomaly_cause", t) if t else None for _, t in rows]
        out["cause_n"] = len(rows)
        out["cause_accuracy"] = round(sum(g == p for g, p in zip(gold, pred)) / len(rows), 4)
        f1s = []
        for c in sorted(set(gold)):
            tp = sum(g == c and p == c for g, p in zip(gold, pred))
            fp = sum(g != c and p == c for g, p in zip(gold, pred))
            fn = sum(g == c and p != c for g, p in zip(gold, pred))
            f1s.append(_f1(tp, fp, fn)[2])
        out["cause_macro_f1"] = round(sum(f1s) / len(f1s), 4)
        tp = sum(g != "none" and p not in (None, "none") for g, p in zip(gold, pred))
        fp = sum(g == "none" and p not in (None, "none") for g, p in zip(gold, pred))
        fn = sum(g != "none" and p in (None, "none") for g, p in zip(gold, pred))
        out["window_anomaly_f1"] = round(_f1(tp, fp, fn)[2], 4)
        out["cause_confusion"] = confusion(gold, pred)

    rows = by_task.get("anomaly_days", [])
    if rows:
        tp = fp = fn = exact = 0
        for s, t in rows:
            gold_days = set(s["target"])
            pred_days = parse("anomaly_days", t) if t else None
            pred_days = pred_days if pred_days is not None else set()
            tp += len(gold_days & pred_days)
            fp += len(pred_days - gold_days)
            fn += len(gold_days - pred_days)
            exact += gold_days == pred_days
        p, r, f = _f1(tp, fp, fn)
        out.update({
            "days_n_windows": len(rows), "days_n_gold": tp + fn, "day_precision": round(p, 4),
            "day_recall": round(r, 4), "day_f1": round(f, 4), "days_exact_window_rate": round(exact / len(rows), 4),
        })  # fmt: skip

    rows = by_task.get("exchange", [])
    if rows:
        ok = sum(parse("exchange", t) == s["target"] for s, t in rows if t)
        out["exchange_n"] = len(rows)
        out["exchange_accuracy"] = round(ok / len(rows), 4)
    return out


def confusion(gold: list[str], pred: list[str | None]) -> dict[str, dict[str, int]]:
    """Gold label -> predicted label (or "invalid") -> count."""
    table: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for g, p in zip(gold, pred):
        table[g][p or "invalid"] += 1
    return {g: dict(row) for g, row in table.items()}
