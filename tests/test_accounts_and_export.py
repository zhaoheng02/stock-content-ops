import json
import tempfile
import unittest
from pathlib import Path

from content_ops.accounts import load_accounts
from content_ops.exporter import export_review_queue
from content_ops.pipeline import run_pipeline
from content_ops.providers import StaticPostProvider
from content_ops.settings import PipelineSettings


class AccountsAndExportTest(unittest.TestCase):
    def test_load_accounts_rejects_duplicate_handles(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "accounts.csv"
            path.write_text(
                "handle,category,priority\n"
                "founder_a,ai_tools,1\n"
                "founder_a,ai_tools,2\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_accounts(path)

    def test_export_review_queue_writes_manifest_and_platform_drafts(self):
        provider = StaticPostProvider(
            [
                {
                    "id": "case-42",
                    "account": "ai_builder",
                    "text": "An AI startup published exact ROI metrics after changing pricing onboarding.",
                    "url": "https://x.example/case-42",
                    "metrics": {"likes": 380, "reposts": 60, "replies": 18},
                }
            ]
        )
        result = run_pipeline(provider, PipelineSettings(min_score=60, daily_limit=5))

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = export_review_queue(result, tmpdir, batch_name="daily")
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

            self.assertEqual(manifest["accepted_count"], 1)
            self.assertEqual(len(manifest["items"][0]["drafts"]), 4)
            for draft in manifest["items"][0]["drafts"].values():
                draft_path = Path(tmpdir) / draft
                self.assertTrue(draft_path.exists())
                self.assertIn("商业启发", draft_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
