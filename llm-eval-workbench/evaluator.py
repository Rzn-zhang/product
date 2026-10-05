"""Deterministic offline evaluation for archived LLM responses."""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from statistics import mean
from typing import Any


QUALITY_GUARDRAILS = {"min_quality": 80.0, "min_pass_rate": 0.8}
PRODUCT_PROFILES = {
    "balanced": {"label": "均衡上线", "quality": 0.65, "speed": 0.20, "cost": 0.15},
    "quality_first": {"label": "质量优先", "quality": 0.98, "speed": 0.01, "cost": 0.01},
    "latency_first": {"label": "时延优先", "quality": 0.45, "speed": 0.45, "cost": 0.10},
}


def _keywords(value: Any) -> list[str]:
    return [item.strip().lower() for item in str(value or "").split("|") if item.strip()]


def keyword_coverage(answer: str, required: Any) -> float:
    terms = _keywords(required)
    if not terms:
        return 1.0
    lowered = answer.lower()
    return sum(term in lowered for term in terms) / len(terms)


def numeric_grounding(answer: str, reference: str) -> tuple[float, list[str]]:
    answer = re.sub(r"(?m)^\s*\d+[.)、]\s*", "", answer)
    # A word-boundary assertion fails for Chinese text because Han characters
    # and digits are both classified as ``\w``. Extract numeric claims directly.
    answer_numbers = re.findall(r"-?\d+(?:\.\d+)?%?", answer)
    reference_numbers = set(re.findall(r"-?\d+(?:\.\d+)?%?", reference))
    if not answer_numbers:
        return 1.0, []
    unsupported = [number for number in answer_numbers if number not in reference_numbers]
    return 1 - len(unsupported) / len(answer_numbers), unsupported


def format_score(answer: str, expected_format: str) -> float:
    expected = (expected_format or "text").lower()
    if expected == "json":
        try:
            json.loads(answer)
            return 1.0
        except json.JSONDecodeError:
            return 0.0
    if expected == "list":
        return 1.0 if re.search(r"(^|\n)\s*(?:[-*•]|\d+[.)])\s+", answer) else 0.35
    if expected == "short":
        return 1.0 if len(answer) <= 160 else max(0.0, 1 - (len(answer) - 160) / 400)
    return 1.0


def percentile(values: list[float], ratio: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, math.ceil(len(ordered) * ratio) - 1)
    return ordered[index]


def evaluate(rows: list[dict[str, Any]], weights: dict[str, float] | None = None) -> dict[str, Any]:
    weights = weights or {"coverage": 0.55, "grounding": 0.25, "format": 0.20}
    details = []
    for row in rows:
        answer = str(row.get("answer", ""))
        coverage = keyword_coverage(answer, row.get("required_keywords"))
        grounding, unsupported = numeric_grounding(answer, str(row.get("reference", "")))
        structure = format_score(answer, str(row.get("expected_format", "text")))
        quality = 100 * (
            weights.get("coverage", 0.55) * coverage
            + weights.get("grounding", 0.25) * grounding
            + weights.get("format", 0.20) * structure
        )
        detail = dict(row)
        detail.update({
            "coverage": round(coverage, 4),
            "grounding": round(grounding, 4),
            "format_score": round(structure, 4),
            "quality_score": round(quality, 1),
            "passed": quality >= 70 and grounding >= 0.8,
            "unsupported_numbers": unsupported,
        })
        details.append(detail)

    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for detail in details:
        grouped[str(detail.get("model", "Unknown"))].append(detail)

    raw_summaries = []
    for model, items in grouped.items():
        latencies = [float(item.get("latency_ms", 0) or 0) for item in items]
        costs = [float(item.get("cost_usd", 0) or 0) for item in items]
        raw_summaries.append({
            "model": model,
            "cases": len(items),
            "quality": round(mean(item["quality_score"] for item in items), 1),
            "pass_rate": round(sum(item["passed"] for item in items) / len(items), 4),
            "avg_latency_ms": round(mean(latencies), 0),
            "p95_latency_ms": round(percentile(latencies, 0.95), 0),
            "avg_cost_usd": round(mean(costs), 6),
            "bad_cases": sum(not item["passed"] for item in items),
        })

    max_latency = max((item["p95_latency_ms"] for item in raw_summaries), default=1) or 1
    max_cost = max((item["avg_cost_usd"] for item in raw_summaries), default=1) or 1
    for item in raw_summaries:
        quality_index = item["quality"] / 100
        speed_index = 1 - item["p95_latency_ms"] / max_latency
        cost_index = 1 - item["avg_cost_usd"] / max_cost
        reasons = []
        if item["quality"] < QUALITY_GUARDRAILS["min_quality"]:
            reasons.append(f"平均质量分低于 {QUALITY_GUARDRAILS['min_quality']:.0f}")
        if item["pass_rate"] < QUALITY_GUARDRAILS["min_pass_rate"]:
            reasons.append(f"通过率低于 {QUALITY_GUARDRAILS['min_pass_rate']:.0%}")
        item.update({
            "quality_index": round(quality_index, 4),
            "speed_index": round(speed_index, 4),
            "cost_index": round(cost_index, 4),
            "eligible": not reasons,
            "guardrail_reasons": reasons,
            "profile_scores": {},
        })
        for profile_key, profile in PRODUCT_PROFILES.items():
            score = 100 * (
                profile["quality"] * quality_index
                + profile["speed"] * speed_index
                + profile["cost"] * cost_index
            )
            item["profile_scores"][profile_key] = round(score, 1)
        item["product_score"] = item["profile_scores"]["balanced"]
    raw_summaries.sort(key=lambda item: item["product_score"], reverse=True)

    eligible = [item for item in raw_summaries if item["eligible"]]
    profile_recommendations = []
    for profile_key, profile in PRODUCT_PROFILES.items():
        best = max(eligible, key=lambda item: item["profile_scores"][profile_key], default=None)
        profile_recommendations.append({
            "key": profile_key,
            "label": profile["label"],
            "model": best["model"] if best else None,
            "score": best["profile_scores"][profile_key] if best else None,
            "weights": {
                "quality": profile["quality"],
                "speed": profile["speed"],
                "cost": profile["cost"],
            },
        })

    categories: defaultdict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for item in details:
        categories[str(item.get("category", "其他"))][str(item.get("model", "Unknown"))].append(item["quality_score"])

    return {
        "summary": raw_summaries,
        "recommended": profile_recommendations[0]["model"] if profile_recommendations else None,
        "profiles": profile_recommendations,
        "guardrails": QUALITY_GUARDRAILS,
        "details": details,
        "categories": [
            {"category": category, "scores": {model: round(mean(scores), 1) for model, scores in models.items()}}
            for category, models in categories.items()
        ],
        "method": "单用例质量分 = 关键词覆盖 55% + 数值忠实度 25% + 格式合规 20%；模型进入选型前还需满足平均质量分 >= 80、通过率 >= 80%",
    }
