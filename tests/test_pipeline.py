import unittest

from content_ops.pipeline import run_pipeline
from content_ops.providers import StaticPostProvider
from content_ops.settings import PipelineSettings


class PipelineContractTest(unittest.TestCase):
    def test_filters_keep_only_high_value_cases(self):
        provider = StaticPostProvider(
            [
                {
                    "id": "keep-1",
                    "account": "ai_founder",
                    "text": (
                        "We reduced AI agent onboarding churn by 38% after replacing "
                        "the demo flow with a usage-based trial and published the exact funnel."
                    ),
                    "url": "https://x.example/keep-1",
                    "metrics": {"likes": 420, "reposts": 88, "replies": 31},
                },
                {
                    "id": "drop-1",
                    "account": "random_fun",
                    "text": "Just had coffee and watched a movie.",
                    "url": "https://x.example/drop-1",
                    "metrics": {"likes": 3, "reposts": 0, "replies": 0},
                },
            ]
        )

        result = run_pipeline(
            provider,
            PipelineSettings(min_score=70, daily_limit=10),
        )

        self.assertEqual([case.source_id for case in result.cases], ["keep-1"])
        self.assertGreaterEqual(result.cases[0].score, 70)

    def test_generated_assets_use_unified_persona_without_copying_creator_voice(self):
        provider = StaticPostProvider(
            [
                {
                    "id": "case-1",
                    "account": "saas_operator",
                    "text": (
                        "A B2B SaaS founder shared a pricing teardown: annual plans grew "
                        "when onboarding switched from feature tours to ROI benchmarks."
                    ),
                    "url": "https://x.example/case-1",
                    "metrics": {"likes": 260, "reposts": 54, "replies": 20},
                }
            ]
        )

        result = run_pipeline(provider, PipelineSettings(min_score=60, daily_limit=5))

        assets = result.cases[0].assets
        self.assertEqual(set(assets), {"xiaohongshu", "video_account", "wechat_article", "douyin_script"})
        for asset in assets.values():
            self.assertIn("统一人设", asset.persona_policy)
            self.assertNotIn("模仿", asset.persona_policy)
            self.assertIn("商业启发", asset.body)


if __name__ == "__main__":
    unittest.main()
