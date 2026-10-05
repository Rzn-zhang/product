import unittest

from voc.pipeline import analyze_feedback, sentiment_score, tokenize


class PipelineTests(unittest.TestCase):
    def test_sentiment_handles_positive_and_negative(self):
        self.assertEqual(sentiment_score("界面很好用，响应也很快", 5)[0], "正向")
        self.assertEqual(sentiment_score("经常崩溃而且回答不准确", 1)[0], "负向")

    def test_sentiment_handles_chinese_negation(self):
        self.assertEqual(sentiment_score("响应并不慢", None)[0], "正向")
        self.assertEqual(sentiment_score("界面不是很好用", None)[0], "负向")

    def test_tokenizer_supports_chinese_and_english(self):
        tokens = tokenize("知识库 upload is very slow")
        self.assertIn("知识", tokens)
        self.assertIn("upload", tokens)
        self.assertIn("slow", tokens)

    def test_pipeline_deduplicates_and_assigns_topics(self):
        records = [
            {"text": "知识库上传文件特别慢", "rating": 1, "date": "2026-01-01", "channel": "工单"},
            {"text": "知识库上传文件特别慢", "rating": 1, "date": "2026-01-01", "channel": "工单"},
            {"text": "权限设置复杂，新成员无法访问", "rating": 2, "date": "2026-02-01", "channel": "访谈"},
            {"text": "界面清晰，检索速度很快", "rating": 5, "date": "2026-02-01", "channel": "访谈"},
        ]
        result = analyze_feedback(records, {"cluster_count": 3})
        self.assertEqual(result["summary"]["total"], 3)
        self.assertEqual(result["summary"]["duplicates_removed"], 1)
        self.assertTrue(result["topics"])
        self.assertTrue(all(row.get("topic") for row in result["records"]))

    def test_priority_score_is_bounded(self):
        records = [
            {"text": f"回答错误并且响应很慢 问题{i}", "rating": 1, "date": "2026-01-01", "channel": "工单"}
            for i in range(8)
        ]
        result = analyze_feedback(records, {"cluster_count": 3})
        self.assertTrue(all(0 <= topic["opportunity_score"] <= 100 for topic in result["topics"]))

    def test_empty_and_short_feedback_is_filtered(self):
        records = [{"text": ""}, {"text": "好"}, {"text": "回答准确而且引用清晰", "rating": 5}]
        result = analyze_feedback(records, {"cluster_count": 3})
        self.assertEqual(result["summary"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
