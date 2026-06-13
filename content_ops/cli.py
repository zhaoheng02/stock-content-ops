import argparse
import json
import os
from pathlib import Path
from typing import List, Optional

from .ai_review import OpenAIResponsesReviewer
from .accounts import load_accounts
from .data_sources import (
    CredentialFile,
    DEFAULT_CREDENTIAL_FILE,
    DEFAULT_X_CREDENTIAL_KEY,
    DataSourceConfig,
    DataSourceService,
    SupabaseDataSourceRepository,
    credential_value,
    default_data_source_repository,
    load_sources_file,
    parse_account_targets,
)
from .exporter import export_review_queue
from .pipeline import run_pipeline
from .providers import JsonFilePostProvider
from .server import serve
from .settings import PipelineSettings
from .x_api import XApiPostProvider, write_posts_json


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return _run(args)
    if args.command == "collect-x":
        return _collect_x(args)
    if args.command == "sources":
        return _sources(args)
    if args.command == "serve":
        return _serve(args)

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="content-ops",
        description="Monitor X sources, keep high-value cases, and generate Chinese platform drafts.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run one source-to-review batch")
    run_parser.add_argument("--source", required=True, help="JSON file containing X post records")
    run_parser.add_argument("--out", default="dist", help="Output directory for review queue")
    run_parser.add_argument("--min-score", type=int, default=70, help="Minimum score for accepted cases")
    run_parser.add_argument("--limit", type=int, default=20, help="Maximum accepted cases per batch")
    run_parser.add_argument("--batch-name", default="daily", help="Manifest and draft batch name")
    run_parser.add_argument("--use-gpt", action="store_true", help="Use OpenAI Responses API for filtering")

    collect_parser = subparsers.add_parser("collect-x", help="Collect latest X posts into JSON inbox")
    collect_parser.add_argument("--accounts", required=True, help="CSV file with handle/category/priority")
    collect_parser.add_argument("--out", default="data/inbox/x_posts.json", help="Output JSON inbox path")
    collect_parser.add_argument(
        "--max-results-per-account",
        type=int,
        default=5,
        help="Recent posts to fetch per account, clamped to X API allowed range",
    )

    serve_parser = subparsers.add_parser("serve", help="Start the local content ops API server")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8787)
    serve_parser.add_argument(
        "--repo",
        choices=["json", "supabase"],
        default="json",
        help="Persistence backend for source configuration and runs",
    )

    sources_parser = subparsers.add_parser("sources", help="Manage data source configurations")
    sources_parser.add_argument(
        "--repo",
        choices=["json", "supabase"],
        default="json",
        help="Persistence backend for source configuration and runs",
    )
    sources_subparsers = sources_parser.add_subparsers(dest="sources_command")

    sources_subparsers.add_parser("list", help="List configured data sources")

    doctor_parser = sources_subparsers.add_parser("doctor", help="Check local data source prerequisites")
    doctor_parser.add_argument("--credential-file", default=DEFAULT_CREDENTIAL_FILE)

    import_parser = sources_subparsers.add_parser("import", help="Import data sources from a JSON seed file")
    import_parser.add_argument("--file", required=True, help="Seed file with a sources array")

    save_parser = sources_subparsers.add_parser("save", help="Create or update a data source")
    save_parser.add_argument("--id", required=True, help="Stable source id, for example x")
    save_parser.add_argument("--name", required=True, help="Display name")
    save_parser.add_argument("--platform", default="x", help="Source platform")
    save_parser.add_argument("--cadence-minutes", type=int, default=30, help="Collection cadence")
    save_parser.add_argument("--targets", required=True, help="Comma or newline separated handles")
    save_parser.add_argument("--min-score", type=int, default=70, help="Minimum score after collection")
    save_parser.add_argument(
        "--material-strategy",
        default="download_media",
        help="Material handling strategy: download_media, links_only, or text_only",
    )
    save_parser.add_argument("--credential-key", default=DEFAULT_X_CREDENTIAL_KEY)
    save_parser.add_argument("--credential-file", default=DEFAULT_CREDENTIAL_FILE)

    run_source_parser = sources_subparsers.add_parser("run", help="Run one configured data source")
    run_source_parser.add_argument("id", help="Data source id")
    run_source_parser.add_argument("--out", default="data/inbox", help="Output directory for collected posts")
    run_source_parser.add_argument(
        "--from-airtap",
        help="Ingest posts from an Airtap result JSON file instead of the X API",
    )

    runs_parser = sources_subparsers.add_parser("runs", help="List recent data source runs")
    runs_parser.add_argument("--source-id", help="Filter by source id")
    runs_parser.add_argument("--limit", type=int, default=10)

    return parser


def _run(args) -> int:
    provider = JsonFilePostProvider(args.source)
    settings = PipelineSettings(min_score=args.min_score, daily_limit=args.limit)
    reviewer = OpenAIResponsesReviewer.from_env() if args.use_gpt else None
    result = run_pipeline(provider, settings, reviewer=reviewer)
    manifest_path = export_review_queue(result, args.out, batch_name=args.batch_name)
    print(
        f"scanned={result.scanned_count} accepted={result.accepted_count} manifest={manifest_path}"
    )
    return 0


def _collect_x(args) -> int:
    accounts = load_accounts(args.accounts)
    provider = XApiPostProvider.from_env(
        [account.handle for account in accounts],
        max_results_per_account=args.max_results_per_account,
    )
    posts = list(provider.fetch_posts())
    out_path = write_posts_json(posts, args.out)
    print(f"accounts={len(accounts)} posts={len(posts)} out={out_path}")
    return 0


def _sources(args) -> int:
    try:
        service = DataSourceService(_build_source_repository(args.repo))
    except RuntimeError as error:
        print(f"error={error}")
        return 1

    if args.sources_command == "list":
        payload = [
            {
                "id": source.id,
                "name": source.name,
                "platform": source.platform,
                "cadence_minutes": source.cadence_minutes,
                "account_count": source.account_count,
                "min_score": source.min_score,
                "material_strategy": source.material_strategy,
                "enabled": source.enabled,
            }
            for source in service.list_sources()
        ]
        print(json.dumps({"sources": payload}, ensure_ascii=False, indent=2))
        return 0

    if args.sources_command == "doctor":
        return _sources_doctor(args)

    if args.sources_command == "save":
        source = service.save_source(
            DataSourceConfig(
                id=args.id,
                name=args.name,
                platform=args.platform,
                cadence_minutes=args.cadence_minutes,
                targets=parse_account_targets(args.targets),
                min_score=args.min_score,
                material_strategy=args.material_strategy,
                credential_key=args.credential_key,
                credential_file=args.credential_file,
            )
        )
        print(f"saved source={source.id} accounts={source.account_count}")
        return 0

    if args.sources_command == "import":
        sources = load_sources_file(args.file)
        for source in sources:
            service.save_source(source)
        print(f"imported={len(sources)}")
        return 0

    if args.sources_command == "run":
        records_collector = None
        if getattr(args, "from_airtap", None):
            records_collector = _airtap_records_collector(args.from_airtap)
        try:
            run = service.run_source(args.id, output_dir=args.out, records_collector=records_collector)
        except RuntimeError as error:
            print(f"source={args.id} status=failed error={error}")
            return 1
        else:
            print(
                f"source={run.source_id} status={run.status} items={run.items_collected} out={run.output_path}"
            )
            return 0

    if args.sources_command == "runs":
        payload = [run.__dict__ for run in service.list_runs(source_id=args.source_id, limit=args.limit)]
        print(json.dumps({"runs": payload}, ensure_ascii=False, indent=2))
        return 0

    return 1


def _build_source_repository(repo_name: str):
    if repo_name == "supabase":
        return SupabaseDataSourceRepository.from_config()
    return default_data_source_repository()


def _airtap_records_collector(path: str):
    from .x_ingest import normalize_airtap_payload

    payload = json.loads(Path(path).read_text(encoding="utf-8"))

    def collector(source):
        return normalize_airtap_payload(payload, source_id=source.id)

    return collector


def _serve(args) -> int:
    service = DataSourceService(_build_source_repository(args.repo))
    print(f"serving http://{args.host}:{args.port}")
    serve(service, host=args.host, port=args.port)
    return 0


def _sources_doctor(args) -> int:
    checks = {
        DEFAULT_X_CREDENTIAL_KEY: _credential_present(args.credential_file, DEFAULT_X_CREDENTIAL_KEY),
        "SUPABASE_URL": bool(os.environ.get("SUPABASE_URL") or credential_value(args.credential_file, "SUPABASE_URL")),
        "SUPABASE_SERVICE_ROLE_KEY": bool(
            os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
            or credential_value(args.credential_file, "SUPABASE_SERVICE_ROLE_KEY")
        ),
    }
    for key, ok in checks.items():
        print(f"{key}={'present' if ok else 'missing'}")
    return 0 if all(checks.values()) else 1


def _credential_present(path: str, key: str) -> bool:
    try:
        CredentialFile(path).get(key)
    except RuntimeError:
        return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
