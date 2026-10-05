"""Evaluate the rule baseline on a small, transparent demo set.

This is a smoke test for explainability and regression detection. It is not a
claim about production accuracy because the examples are synthetic and small.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from voc.pipeline import sentiment_score  # noqa: E402


def evaluate(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    labels = ["正向", "中性", "负向"]
    confusion = {expected: Counter() for expected in labels}
    errors = []
    for row in rows:
        predicted, score, confidence = sentiment_score(row["text"], row.get("rating"))
        expected = row["expected"]
        confusion[expected][predicted] += 1
        if predicted != expected:
            errors.append({
                "text": row["text"],
                "expected": expected,
                "predicted": predicted,
                "score": score,
                "confidence": confidence,
            })

    per_label = {}
    for label in labels:
        true_positive = confusion[label][label]
        false_positive = sum(confusion[other][label] for other in labels if other != label)
        false_negative = sum(confusion[label][other] for other in labels if other != label)
        precision = true_positive / max(1, true_positive + false_positive)
        recall = true_positive / max(1, true_positive + false_negative)
        f1 = 2 * precision * recall / max(1e-9, precision + recall)
        per_label[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    correct = sum(confusion[label][label] for label in labels)
    return {
        "data_scope": "18 条人工编写的演示样例，仅用于冒烟验证与回归测试",
        "samples": len(rows),
        "accuracy": round(correct / max(1, len(rows)), 4),
        "macro_f1": round(sum(item["f1"] for item in per_label.values()) / len(labels), 4),
        "per_label": per_label,
        "confusion_matrix": {label: dict(confusion[label]) for label in labels},
        "errors": errors,
    }


if __name__ == "__main__":
    result = evaluate(ROOT / "data" / "demo_sentiment_labeled.csv")
    print(json.dumps(result, ensure_ascii=False, indent=2))
