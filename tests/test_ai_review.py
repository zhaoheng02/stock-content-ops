import unittest

from content_ops.ai_review import AIReviewDecision, parse_review_json
from content_ops.pipeline import run_pipeline
from content_ops.providers import StaticPostProvider
from content_ops.settings import PipelineSettings


class StubReviewer:
    def review(self, post):
        if post.id == "ai-keep":
            return AIReviewDecision(score=92, reasons=["gpt_high_signal"], summary="AI tool case")
        return AIReviewDecision(score=30, reasons=["gpt_low_signal"], summary="not useful")


class AIReviewTest(unittest.TestCase):
    def test_parse_review_json_accepts_plain_json_response(self):
        decision = parse_review_json(
            '{"score": 88, "reasons": ["evidence", "china_relevance"], "summary": "useful"}'
        )

        self.assertEqual(decision.score, 88)
        self.assertEqual(decision.reasons, ["evidence", "china_relevance"])
        self.assertEqual(decision.summary, "useful")

    def test_pipeline_can_use_gpt_reviewer_score(self):
        provider = StaticPostProvider(
            [
                {
                    "id": "ai-keep",
                    "account": "builder",
                    "text": "short but strategically valuable",
                    "url": "https://x.example/ai-keep",
                    "metrics": {},
                },
                {
                    "id": "ai-drop",
                    "account": "builder",
                    "text": "AI startup exact metrics and pricing onboarding case",
                    "url": "https://x.example/ai-drop",
                    "metrics": {"likes": 1000},
                },
            ]
        )

        result = run_pipeline(
            provider,
            PipelineSettings(min_score=70, daily_limit=10),
            reviewer=StubReviewer(),
        )

        self.assertEqual([case.source_id for case in result.cases], ["ai-keep"])
        self.assertEqual(result.cases[0].score_reasons, ["gpt_high_signal"])


if __name__ == "__main__":
    unittest.main()
