import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from content_ops.cli import main


class CliTest(unittest.TestCase):
    def test_run_command_processes_json_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "posts.json"
            source.write_text(
                json.dumps(
                    [
                        {
                            "id": "cli-1",
                            "account": "ai_ops",
                            "text": "An AI founder published exact onboarding metrics after changing trial pricing.",
                            "url": "https://x.example/cli-1",
                            "metrics": {"likes": 500, "reposts": 80, "replies": 12},
                        }
                    ]
                ),
                encoding="utf-8",
            )

            with redirect_stdout(StringIO()):
                code = main(
                    [
                        "run",
                        "--source",
                        str(source),
                        "--out",
                        str(root / "out"),
                        "--min-score",
                        "60",
                    ]
                )

            self.assertEqual(code, 0)
            manifest = root / "out" / "daily-manifest.json"
            self.assertTrue(manifest.exists())
            self.assertEqual(json.loads(manifest.read_text(encoding="utf-8"))["accepted_count"], 1)

    def test_sources_command_saves_and_lists_data_source(self):
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                with redirect_stdout(StringIO()) as stdout:
                    code = main(
                        [
                            "sources",
                            "save",
                            "--id",
                            "x",
                            "--name",
                            "X / Twitter",
                            "--targets",
                            "@openai,@levelsio",
                        ]
                    )

                self.assertEqual(code, 0)
                self.assertIn("accounts=2", stdout.getvalue())

                with redirect_stdout(StringIO()) as stdout:
                    code = main(["sources", "list"])

                self.assertEqual(code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertEqual(payload["sources"][0]["id"], "x")
                self.assertEqual(payload["sources"][0]["account_count"], 2)
                self.assertNotIn("credential", json.dumps(payload))
            finally:
                os.chdir(original_cwd)

    def test_sources_import_loads_seed_file(self):
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            seed = root / "seed.json"
            seed.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "id": "x-growth-ai",
                                "name": "X Growth AI Sources",
                                "platform": "x",
                                "targets": ["levelsio", "lennysan", "Patticus"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            os.chdir(root)
            try:
                with redirect_stdout(StringIO()) as stdout:
                    code = main(["sources", "import", "--file", str(seed)])

                self.assertEqual(code, 0)
                self.assertIn("imported=1", stdout.getvalue())

                with redirect_stdout(StringIO()) as stdout:
                    main(["sources", "list"])

                payload = json.loads(stdout.getvalue())
                self.assertEqual(payload["sources"][0]["account_count"], 3)
            finally:
                os.chdir(original_cwd)

    def test_sources_run_reports_credential_error_without_traceback(self):
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            credential = root / "personal.config"
            credential.write_text("", encoding="utf-8")
            os.chdir(root)
            try:
                main(
                    [
                        "sources",
                        "save",
                        "--id",
                        "x",
                        "--name",
                        "X",
                        "--targets",
                        "@levelsio",
                        "--credential-file",
                        str(credential),
                    ]
                )
                with redirect_stdout(StringIO()) as stdout:
                    code = main(["sources", "run", "x", "--out", str(root / "inbox")])

                self.assertEqual(code, 1)
                self.assertIn("error=", stdout.getvalue())
                self.assertIn("X_BEARER_TOKEN", stdout.getvalue())
            finally:
                os.chdir(original_cwd)

    def test_sources_run_ingests_airtap_result_file(self):
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            credential = root / "personal.config"
            credential.write_text("", encoding="utf-8")
            airtap_file = root / "airtap.json"
            airtap_file.write_text(
                json.dumps(
                    {
                        "collected_at": "2026-06-13T11:20:00+08:00",
                        "posts": [
                            {"id": "1", "author_handle": "levelsio", "text": "post one", "published_at": "下午10:52 · 2026年6月12日"},
                            {"id": "2", "author_handle": "lennysan", "text": "post two", "published_at": "下午9:05 · 2026年6月12日"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            os.chdir(root)
            try:
                main(
                    [
                        "sources",
                        "save",
                        "--id",
                        "x",
                        "--name",
                        "X",
                        "--targets",
                        "@levelsio,@lennysan",
                        "--credential-file",
                        str(credential),
                    ]
                )
                with redirect_stdout(StringIO()) as stdout:
                    code = main(["sources", "run", "x", "--out", str(root / "inbox"), "--from-airtap", str(airtap_file)])

                self.assertEqual(code, 0)
                self.assertIn("items=2", stdout.getvalue())
            finally:
                os.chdir(original_cwd)

    def test_sources_doctor_reports_missing_supabase_and_x_credentials(self):
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            credential = root / "personal.config"
            credential.write_text("", encoding="utf-8")
            os.chdir(root)
            try:
                with redirect_stdout(StringIO()) as stdout:
                    code = main(["sources", "doctor", "--credential-file", str(credential)])

                self.assertEqual(code, 1)
                output = stdout.getvalue()
                self.assertIn("X_BEARER_TOKEN=missing", output)
                self.assertIn("SUPABASE_URL=missing", output)
                self.assertIn("SUPABASE_SERVICE_ROLE_KEY=missing", output)
            finally:
                os.chdir(original_cwd)

    def test_sources_doctor_accepts_supabase_keys_from_credential_file(self):
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            credential = root / "personal.config"
            credential.write_text(
                "X_BEARER_TOKEN x-token\n"
                "SUPABASE_URL https://example.supabase.co\n"
                "SUPABASE_SERVICE_ROLE_KEY service-key\n",
                encoding="utf-8",
            )
            os.chdir(root)
            try:
                with redirect_stdout(StringIO()) as stdout:
                    code = main(["sources", "doctor", "--credential-file", str(credential)])

                self.assertEqual(code, 0)
                output = stdout.getvalue()
                self.assertIn("X_BEARER_TOKEN=present", output)
                self.assertIn("SUPABASE_URL=present", output)
                self.assertIn("SUPABASE_SERVICE_ROLE_KEY=present", output)
            finally:
                os.chdir(original_cwd)

    def test_sources_supabase_repo_reports_missing_env_without_traceback(self):
        with redirect_stdout(StringIO()) as stdout:
            code = main(["sources", "--repo", "supabase", "list"])

        self.assertEqual(code, 1)
        self.assertIn("SUPABASE_URL is required", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
