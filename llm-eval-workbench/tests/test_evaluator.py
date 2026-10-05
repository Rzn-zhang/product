import unittest

from evaluator import evaluate, format_score, keyword_coverage, numeric_grounding


class EvaluatorTests(unittest.TestCase):
    def test_keyword_coverage(self):
        self.assertEqual(keyword_coverage("7天内支持退款", "7天|退款"), 1.0)

    def test_numeric_grounding_flags_unsupported_claims(self):
        score, unsupported = numeric_grounding("可保留90天", "30天内删除")
        self.assertEqual(score, 0.0)
        self.assertEqual(unsupported, ["90"])

    def test_json_format(self):
        self.assertEqual(format_score('{"ok": true}', "json"), 1.0)
        self.assertEqual(format_score("ok=true", "json"), 0.0)

    def test_list_numbers_are_not_hallucination_claims(self):
        score, unsupported = numeric_grounding("1. 重启客户端\n2. 检查网络", "重启客户端并检查网络")
        self.assertEqual(score, 1.0)
        self.assertEqual(unsupported, [])

    def test_evaluate_ranks_models(self):
        rows = [
            {"model": "A", "answer": "7天退款", "reference": "7天退款", "required_keywords": "7天|退款", "expected_format": "short", "latency_ms": 800, "cost_usd": .002},
            {"model": "B", "answer": "90天退款", "reference": "7天退款", "required_keywords": "7天|退款", "expected_format": "short", "latency_ms": 300, "cost_usd": .001},
        ]
        result = evaluate(rows)
        self.assertEqual(result["recommended"], "A")
        self.assertEqual(len(result["summary"]), 2)

    def test_quality_guardrail_blocks_fast_but_unreliable_model(self):
        rows = [
            {"model": "Reliable", "answer": "7天退款", "reference": "7天退款", "required_keywords": "7天|退款", "expected_format": "short", "latency_ms": 900, "cost_usd": .003},
            {"model": "Fast", "answer": "90天", "reference": "7天退款", "required_keywords": "7天|退款", "expected_format": "short", "latency_ms": 50, "cost_usd": .0001},
        ]
        result = evaluate(rows)
        fast = next(item for item in result["summary"] if item["model"] == "Fast")
        self.assertFalse(fast["eligible"])
        self.assertEqual(result["recommended"], "Reliable")

    def test_evaluate_returns_three_product_profiles(self):
        rows = [
            {"model": "A", "answer": "7天退款", "reference": "7天退款", "required_keywords": "7天|退款", "expected_format": "short", "latency_ms": 900, "cost_usd": .003},
        ]
        result = evaluate(rows)
        self.assertEqual([item["key"] for item in result["profiles"]], ["balanced", "quality_first", "latency_first"])
        self.assertEqual(result["profiles"][0]["model"], "A")


if __name__ == "__main__":
    unittest.main()
