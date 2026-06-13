import json
import tempfile
import unittest
from pathlib import Path

from content_ops.data_sources import DataSourceConfig, DataSourceService, JsonDataSourceRepository
from content_ops.server import create_app


class ServerApiTest(unittest.TestCase):
    def test_sources_api_lists_and_creates_sources_without_secrets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = JsonDataSourceRepository(Path(tmpdir) / "sources.json", Path(tmpdir) / "runs.json")
            service = DataSourceService(repo)
            service.save_source(
                DataSourceConfig(
                    id="x-growth-ai",
                    name="X Growth AI Sources",
                    platform="x",
                    targets=("levelsio", "lennysan"),
                )
            )
            client = create_app(service)

            status, headers, body = client.handle("GET", "/api/sources")
            payload = json.loads(body)

            self.assertEqual(status, 200)
            self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
            self.assertEqual(payload["sources"][0]["account_count"], 2)
            self.assertNotIn("credential", json.dumps(payload))

            status, _, body = client.handle(
                "POST",
                "/api/sources",
                json.dumps(
                    {
                        "id": "x-pricing",
                        "name": "X Pricing Sources",
                        "platform": "x",
                        "targets": "@Patticus,@marc_louvion",
                    }
                ).encode("utf-8"),
            )

            self.assertEqual(status, 201)
            self.assertEqual(json.loads(body)["source"]["account_count"], 2)
            self.assertEqual(repo.get_source("x-pricing").targets, ("Patticus", "marc_louvion"))

    def test_source_runs_api_returns_recent_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = JsonDataSourceRepository(Path(tmpdir) / "sources.json", Path(tmpdir) / "runs.json")
            service = DataSourceService(repo)
            client = create_app(service)

            status, _, body = client.handle("GET", "/api/source-runs?source_id=x-growth-ai")

            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body), {"runs": []})

    def test_run_source_api_returns_structured_errors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = JsonDataSourceRepository(root / "sources.json", root / "runs.json")
            service = DataSourceService(repo)
            service.save_source(
                DataSourceConfig(
                    id="x",
                    name="X",
                    platform="x",
                    targets=("levelsio",),
                    credential_file=str(root / "missing.config"),
                )
            )
            client = create_app(service)

            status, _, body = client.handle(
                "POST",
                "/api/source-runs",
                json.dumps({"source_id": "x", "out": str(root / "inbox")}).encode("utf-8"),
            )
            payload = json.loads(body)

            self.assertEqual(status, 400)
            self.assertIn("credential file not found", payload["error"])
            self.assertEqual(repo.list_runs("x")[0].status, "failed")


if __name__ == "__main__":
    unittest.main()
