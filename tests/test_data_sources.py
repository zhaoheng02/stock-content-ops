import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from content_ops.data_sources import (
    CredentialFile,
    DataSourceConfig,
    DataSourceRun,
    DataSourceService,
    JsonDataSourceRepository,
    SupabaseDataSourceRepository,
    load_sources_file,
    parse_account_targets,
)


class FakeTransport:
    def __init__(self):
        self.tokens = []

    def get_json(self, url, bearer_token):
        self.tokens.append(bearer_token)
        if "/users/by/username/" in url:
            username = url.split("/users/by/username/")[1].split("?")[0]
            return {"data": {"id": f"id-{username}", "username": username}}
        return {
            "data": [
                {
                    "id": "tweet-1",
                    "text": "AI pricing teardown with exact funnel metrics.",
                    "public_metrics": {"like_count": 30, "retweet_count": 4, "reply_count": 2},
                }
            ]
        }


class FakeSupabaseTransport:
    def __init__(self):
        self.requests = []
        self.sources = []
        self.runs = []
        self.accounts = []

    def request_json(self, method, path, payload=None, query=None):
        self.requests.append((method, path, payload, query))
        if path == "data_sources" and method == "GET":
            rows = list(self.sources)
            if query and query.startswith("id=eq."):
                source_id = query.split("id=eq.", 1)[1].split("&", 1)[0]
                rows = [row for row in rows if row["id"] == source_id]
            return rows
        if path == "data_sources" and method == "POST":
            self.sources = [row for row in self.sources if row["id"] != payload["id"]]
            self.sources.append(dict(payload))
            return [payload]
        if path == "data_source_runs" and method == "GET":
            rows = list(self.runs)
            if query and query.startswith("source_id=eq."):
                source_id = query.split("source_id=eq.", 1)[1].split("&", 1)[0]
                rows = [row for row in rows if row["source_id"] == source_id]
            return rows
        if path == "data_source_runs" and method == "POST":
            self.runs.append(dict(payload))
            return [payload]
        if path == "monitored_accounts" and method == "GET":
            rows = list(self.accounts)
            if query and query.startswith("source_id=eq."):
                source_id = query.split("source_id=eq.", 1)[1].split("&", 1)[0]
                rows = [row for row in rows if row["source_id"] == source_id]
            return rows
        if path == "monitored_accounts" and method == "POST":
            payload_rows = payload if isinstance(payload, list) else [payload]
            for row in payload_rows:
                self.accounts = [
                    existing for existing in self.accounts
                    if (existing["source_id"], existing["handle"]) != (row["source_id"], row["handle"])
                ]
                self.accounts.append(dict(row))
            return payload_rows
        if path == "monitored_accounts" and method == "PATCH":
            source_id = query.split("source_id=eq.", 1)[1].split("&", 1)[0]
            handle = query.split("handle=eq.", 1)[1].split("&", 1)[0]
            for row in self.accounts:
                if row["source_id"] == source_id and row["handle"] == handle:
                    row.update(payload)
            return []
        if path == "monitored_accounts" and method == "DELETE":
            source_id = query.split("source_id=eq.", 1)[1].split("&", 1)[0]
            handle = query.split("handle=eq.", 1)[1].split("&", 1)[0]
            self.accounts = [
                row for row in self.accounts
                if not (row["source_id"] == source_id and row["handle"] == handle)
            ]
            return []
        raise AssertionError((method, path, payload, query))


class DataSourceServiceTest(unittest.TestCase):
    def test_save_source_persists_configuration_without_secret_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = JsonDataSourceRepository(Path(tmpdir) / "sources.json", Path(tmpdir) / "runs.json")
            source = DataSourceConfig(
                id="x",
                name="X / Twitter",
                platform="x",
                cadence_minutes=30,
                targets=("@openai", "@levelsio"),
                min_score=70,
                material_strategy="links_only",
                credential_key="X_BEARER_TOKEN",
                credential_file="/Users/bytedance/personal.config",
            )

            saved = DataSourceService(repo).save_source(source)
            payload = json.loads((Path(tmpdir) / "sources.json").read_text(encoding="utf-8"))

            self.assertEqual(saved.account_count, 2)
            self.assertEqual(payload["sources"][0]["credential_key"], "X_BEARER_TOKEN")
            self.assertEqual(payload["sources"][0]["credential_file"], "/Users/bytedance/personal.config")
            self.assertNotIn("secret-token", json.dumps(payload))

    def test_run_x_source_via_records_collector_records_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = JsonDataSourceRepository(root / "sources.json", root / "runs.json")
            service = DataSourceService(
                repo,
                now=lambda: datetime(2026, 6, 13, 10, 0, tzinfo=timezone.utc),
            )
            service.save_source(
                DataSourceConfig(
                    id="x",
                    name="X / Twitter",
                    platform="x",
                    cadence_minutes=30,
                    targets=("@builder_a",),
                )
            )

            def collector(source):
                return [{
                    "content_hash": "hash-1",
                    "post_id": "tweet-1",
                    "author_handle": "builder_a",
                    "text": "AI pricing teardown with exact funnel metrics.",
                    "url": "https://x.com/builder_a/status/tweet-1",
                    "metrics": {"likes": 30},
                }]

            run = service.run_source("x", output_dir=root / "inbox", records_collector=collector)

            self.assertEqual(run.status, "success")
            self.assertEqual(run.items_collected, 1)
            runs_payload = json.loads((root / "runs.json").read_text(encoding="utf-8"))
            self.assertEqual(runs_payload["runs"][0]["source_id"], "x")

    def test_run_ids_include_microseconds_to_avoid_same_second_collisions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            credential_path = root / "personal.config"
            credential_path.write_text("", encoding="utf-8")
            repo = JsonDataSourceRepository(root / "sources.json", root / "runs.json")
            service = DataSourceService(
                repo,
                now=lambda: datetime(2026, 6, 13, 10, 0, 0, 123456, tzinfo=timezone.utc),
            )
            service.save_source(
                DataSourceConfig(
                    id="x",
                    name="X / Twitter",
                    platform="x",
                    targets=("levelsio",),
                    credential_file=str(credential_path),
                )
            )

            with self.assertRaises(RuntimeError):
                service.run_source("x", output_dir=root / "inbox")

            self.assertIn("20260613T100000123456Z", repo.list_runs("x")[0].id)

    def test_run_source_uses_injected_collector(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            credential_path = root / "personal.config"
            credential_path.write_text("", encoding="utf-8")
            repo = JsonDataSourceRepository(root / "sources.json", root / "runs.json")
            service = DataSourceService(repo)
            service.save_source(
                DataSourceConfig(
                    id="x",
                    name="X / Twitter",
                    platform="x",
                    targets=("levelsio", "lennysan"),
                    credential_file=str(credential_path),
                )
            )

            from content_ops.models import SourcePost

            def collector(source):
                return [
                    SourcePost(id=f"id-{handle}", account=handle, text="t", url=f"https://x.com/{handle}")
                    for handle in source.targets
                ]

            run = service.run_source("x", output_dir=root / "inbox", collector=collector)

            self.assertEqual(run.status, "success")
            self.assertEqual(run.items_collected, 2)
            payload = json.loads(Path(run.output_path).read_text(encoding="utf-8"))
            self.assertEqual([item["account"] for item in payload], ["levelsio", "lennysan"])

    def test_save_source_seeds_only_new_monitored_accounts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = JsonDataSourceRepository(root / "sources.json", root / "runs.json")
            service = DataSourceService(repo)
            service.start_onboarding = lambda source_id, handles: None

            service.save_source(DataSourceConfig(id="x", name="X", platform="x", targets=("HanKing66", "levelsio")))
            service.save_source(DataSourceConfig(id="x", name="X", platform="x", targets=("hanking66", "openai")))

            accounts = repo.list_monitored_accounts("x")
            self.assertEqual([row["handle"] for row in accounts], ["hanking66", "openai"])

    def test_save_source_onboards_only_missing_avatar_accounts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = JsonDataSourceRepository(root / "sources.json", root / "runs.json")
            service = DataSourceService(repo)
            onboarded = []
            service.start_onboarding = lambda source_id, handles: onboarded.extend(handles)
            service.save_source(DataSourceConfig(id="x", name="X", platform="x", targets=("old",)))
            onboarded.clear()
            repo.upsert_monitored_accounts([
                {"source_id": "x", "handle": "with_avatar", "avatar_url": "https://pbs.twimg.com/profile_images/a.jpg"},
            ])

            service.save_source(DataSourceConfig(id="x", name="X", platform="x", targets=("old", "with_avatar", "new_one")))

            self.assertEqual(onboarded, ["old", "new_one"])

    def test_save_source_skips_missing_avatar_onboarding_when_profile_pending(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            repo = JsonDataSourceRepository(root / "sources.json", root / "runs.json")
            service = DataSourceService(repo)
            onboarded = []
            service.start_onboarding = lambda source_id, handles: onboarded.extend(handles)
            service.save_source(DataSourceConfig(id="x", name="X", platform="x", targets=("old",)))
            repo.append_run(DataSourceRun(
                id="profile-1",
                source_id="x",
                started_at="2026-06-13T10:00:00+00:00",
                finished_at="2026-06-13T10:00:00+00:00",
                status="pending",
                items_collected=0,
                output_path="",
                kind="profile",
            ))

            service.save_source(DataSourceConfig(id="x", name="X", platform="x", targets=("old", "new_one")))

            self.assertEqual(onboarded, ["old"])

    def test_parse_account_targets_accepts_comma_and_line_separated_handles(self):
        targets = parse_account_targets("@openai, @levelsio\nhttps://x.com/builder_a #ignored")

        self.assertEqual(targets, ("openai", "levelsio", "builder_a"))

    def test_credential_file_parses_export_and_quoted_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "personal.config"
            path.write_text("export X_BEARER_TOKEN='secret-token'\n", encoding="utf-8")

            self.assertEqual(CredentialFile(path).get("X_BEARER_TOKEN"), "secret-token")

    def test_credential_file_parses_space_separated_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "personal.config"
            path.write_text(
                "supabase sexybodysuits@example.com password\n"
                "SUPABASE_URL https://example.supabase.co\n"
                "SUPABASE_SERVICE_ROLE_KEY service-key\n",
                encoding="utf-8",
            )

            self.assertEqual(CredentialFile(path).get("SUPABASE_URL"), "https://example.supabase.co")
            self.assertEqual(CredentialFile(path).get("SUPABASE_SERVICE_ROLE_KEY"), "service-key")

    def test_supabase_repository_upserts_sources_and_runs(self):
        transport = FakeSupabaseTransport()
        repo = SupabaseDataSourceRepository(transport)
        source = DataSourceConfig(
            id="x",
            name="X / Twitter",
            platform="x",
            targets=("openai", "levelsio"),
            credential_file="/Users/bytedance/personal.config",
        )

        repo.save_source(source)
        loaded = repo.get_source("x")
        run = repo.append_run(
            DataSourceRun(
                id="run-1",
                source_id="x",
                started_at="2026-06-13T10:00:00+00:00",
                finished_at="2026-06-13T10:00:03+00:00",
                status="success",
                items_collected=2,
                output_path="data/inbox/x.json",
            )
        )

        self.assertEqual(loaded.targets, ("openai", "levelsio"))
        self.assertEqual(run.items_collected, 2)
        self.assertEqual(repo.list_runs("x")[0].id, "run-1")
        self.assertEqual(transport.requests[0][0], "POST")
        self.assertEqual(transport.requests[0][3], "on_conflict=id")

    def test_supabase_repository_normalizes_monitored_account_handles(self):
        transport = FakeSupabaseTransport()
        repo = SupabaseDataSourceRepository(transport)

        repo.upsert_monitored_accounts([{"source_id": "x", "handle": "@HanKing66"}])
        repo.patch_monitored_account("x", "HanKing66", {"last_post_at": "2026-06-12T22:52:00+08:00"})

        self.assertEqual(transport.accounts[0]["handle"], "hanking66")
        self.assertEqual(transport.accounts[0]["last_post_at"], "2026-06-12T22:52:00+08:00")

    def test_supabase_repository_sends_uniform_monitored_account_payload_keys(self):
        transport = FakeSupabaseTransport()
        repo = SupabaseDataSourceRepository(transport)

        repo.upsert_monitored_accounts([
            {"source_id": "x", "handle": "with_avatar", "avatar_url": "https://pbs.twimg.com/profile_images/a.jpg"},
            {"source_id": "x", "handle": "new_one"},
        ])

        payload = transport.requests[-1][2]
        self.assertEqual(set(payload[0].keys()), set(payload[1].keys()))
        self.assertIn("avatar_url", payload[1])
        self.assertIsNone(payload[1]["avatar_url"])

    def test_supabase_repository_can_read_connection_from_credential_file(self):
        original_url = os.environ.pop("SUPABASE_URL", None)
        original_key = os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / "personal.config"
                path.write_text(
                    "SUPABASE_URL https://example.supabase.co\n"
                    "SUPABASE_SERVICE_ROLE_KEY service-key\n",
                    encoding="utf-8",
                )

                repo = SupabaseDataSourceRepository.from_config(str(path))

                self.assertEqual(repo.transport.project_url, "https://example.supabase.co")
                self.assertEqual(repo.transport.service_key, "service-key")
        finally:
            if original_url is not None:
                os.environ["SUPABASE_URL"] = original_url
            if original_key is not None:
                os.environ["SUPABASE_SERVICE_ROLE_KEY"] = original_key

    def test_load_sources_file_reads_seed_configuration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sources.json"
            path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "id": "x-growth-ai",
                                "name": "X Growth AI Sources",
                                "platform": "x",
                                "targets": ["levelsio", "lennysan"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            sources = load_sources_file(path)

            self.assertEqual(sources[0].id, "x-growth-ai")
            self.assertEqual(sources[0].targets, ("levelsio", "lennysan"))


if __name__ == "__main__":
    unittest.main()
