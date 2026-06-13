import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import urllib.parse
import urllib.request
from typing import Callable, List, Optional, Protocol, Tuple

from .models import SourcePost
from .x_api import JsonTransport, XApiPostProvider, write_posts_json


DEFAULT_CREDENTIAL_FILE = "/Users/bytedance/personal.config"
DEFAULT_X_CREDENTIAL_KEY = "X_BEARER_TOKEN"
SUPPORTED_PLATFORMS = {"x"}


@dataclass(frozen=True)
class DataSourceConfig:
    id: str
    name: str
    platform: str
    cadence_minutes: int = 30
    targets: Tuple[str, ...] = ()
    min_score: int = 70
    material_strategy: str = "download_media"
    credential_key: str = DEFAULT_X_CREDENTIAL_KEY
    credential_file: str = DEFAULT_CREDENTIAL_FILE
    enabled: bool = True

    @property
    def account_count(self) -> int:
        return len(self.targets)


@dataclass(frozen=True)
class DataSourceRun:
    id: str
    source_id: str
    started_at: str
    finished_at: str
    status: str
    items_collected: int
    output_path: str
    message: str = ""
    airtap_task_id: str = ""


class CredentialFile:
    def __init__(self, path: str):
        self.path = Path(path)

    def get(self, key: str) -> str:
        if not self.path.exists():
            raise RuntimeError(f"credential file not found: {self.path}")

        for line in self.path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_assignment(line)
            if parsed and parsed[0] == key:
                return parsed[1]

        raise RuntimeError(f"{key} is required in credential file")


class JsonDataSourceRepository:
    def __init__(self, sources_path: str, runs_path: str, posts_path: Optional[str] = None):
        self.sources_path = Path(sources_path)
        self.runs_path = Path(runs_path)
        self.posts_path = Path(posts_path) if posts_path else self.runs_path.parent / "posts.json"

    def list_sources(self) -> List[DataSourceConfig]:
        payload = self._read_json(self.sources_path, {"sources": []})
        return [_source_from_dict(item) for item in payload.get("sources", [])]

    def save_source(self, source: DataSourceConfig) -> DataSourceConfig:
        sources = [item for item in self.list_sources() if item.id != source.id]
        sources.append(source)
        sources.sort(key=lambda item: item.id)
        self._write_json(self.sources_path, {"sources": [_source_to_dict(item) for item in sources]})
        return source

    def get_source(self, source_id: str) -> DataSourceConfig:
        for source in self.list_sources():
            if source.id == source_id:
                return source
        raise KeyError(f"data source not found: {source_id}")

    def list_runs(self, source_id: Optional[str] = None, limit: Optional[int] = None) -> List[DataSourceRun]:
        payload = self._read_json(self.runs_path, {"runs": []})
        runs = [_run_from_dict(item) for item in payload.get("runs", [])]
        if source_id is not None:
            runs = [run for run in runs if run.source_id == source_id]
        runs.sort(key=lambda run: run.started_at, reverse=True)
        return runs[:limit] if limit is not None else runs

    def append_run(self, run: DataSourceRun) -> DataSourceRun:
        runs = self.list_runs()
        runs.append(run)
        runs.sort(key=lambda item: item.started_at, reverse=True)
        self._write_json(self.runs_path, {"runs": [_run_to_dict(item) for item in runs]})
        return run

    def patch_run(self, run_id: str, changes: dict) -> None:
        payload = self._read_json(self.runs_path, {"runs": []})
        for row in payload.get("runs", []):
            if row.get("id") == run_id:
                row.update(changes)
        self._write_json(self.runs_path, payload)

    def list_runs_by_status(self, status: str) -> List[DataSourceRun]:
        return [run for run in self.list_runs() if run.status == status]

    def list_posts(
        self,
        source_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[dict]:
        payload = self._read_json(self.posts_path, {"posts": []})
        posts = list(payload.get("posts", []))
        if source_id is not None:
            posts = [p for p in posts if p.get("source_id") == source_id]
        if run_id is not None:
            posts = [p for p in posts if p.get("run_id") == run_id]
        posts.sort(key=lambda p: (p.get("published_at") or p.get("collected_at") or ""), reverse=True)
        return posts[:limit] if limit is not None else posts

    def upsert_posts(self, records: List[dict]) -> int:
        existing = {p.get("content_hash"): p for p in self._read_json(self.posts_path, {"posts": []}).get("posts", [])}
        new_count = 0
        for record in records:
            chash = record.get("content_hash")
            if not chash:
                continue
            if chash not in existing:
                new_count += 1
                existing[chash] = record
            else:
                # keep first_seen_at, refresh the rest
                first_seen = existing[chash].get("first_seen_at") or record.get("first_seen_at")
                existing[chash] = {**record, "first_seen_at": first_seen}
        self._write_json(self.posts_path, {"posts": list(existing.values())})
        return new_count

    def _read_json(self, path: Path, default: dict) -> dict:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class SupabaseTransport(Protocol):
    def request_json(
        self,
        method: str,
        path: str,
        payload: Optional[dict] = None,
        query: Optional[str] = None,
    ) -> list:
        ...


class UrlLibSupabaseTransport:
    def __init__(self, project_url: str, service_key: str):
        self.project_url = project_url.rstrip("/")
        self.service_key = service_key

    def request_json(
        self,
        method: str,
        path: str,
        payload: Optional[dict] = None,
        query: Optional[str] = None,
    ) -> list:
        url = f"{self.project_url}/rest/v1/{path.strip('/')}"
        if query:
            url = f"{url}?{query}"
        body = None
        headers = {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if method == "POST":
            headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        elif method in ("PATCH", "DELETE"):
            headers["Prefer"] = "return=representation"
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else []


class SupabaseDataSourceRepository:
    def __init__(self, transport: SupabaseTransport):
        self.transport = transport

    @classmethod
    def from_env(cls) -> "SupabaseDataSourceRepository":
        project_url = os.environ.get("SUPABASE_URL")
        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not project_url:
            raise RuntimeError("SUPABASE_URL is required")
        if not service_key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required")
        return cls(UrlLibSupabaseTransport(project_url=project_url, service_key=service_key))

    @classmethod
    def from_config(cls, credential_file: str = DEFAULT_CREDENTIAL_FILE) -> "SupabaseDataSourceRepository":
        project_url = os.environ.get("SUPABASE_URL") or credential_value(
            credential_file, "SUPABASE_URL"
        )
        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or credential_value(
            credential_file, "SUPABASE_SERVICE_ROLE_KEY"
        )
        if not project_url:
            raise RuntimeError("SUPABASE_URL is required")
        if not service_key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required")
        return cls(UrlLibSupabaseTransport(project_url=project_url, service_key=service_key))

    def list_sources(self) -> List[DataSourceConfig]:
        rows = self.transport.request_json(
            "GET",
            "data_sources",
            query="select=*&order=id.asc",
        )
        return [_source_from_supabase(row) for row in rows]

    def save_source(self, source: DataSourceConfig) -> DataSourceConfig:
        payload = _source_to_supabase(_normalize_source(source))
        rows = self.transport.request_json(
            "POST",
            "data_sources",
            payload=payload,
            query="on_conflict=id",
        )
        return _source_from_supabase(rows[0]) if rows else source

    def get_source(self, source_id: str) -> DataSourceConfig:
        rows = self.transport.request_json(
            "GET",
            "data_sources",
            query=f"id=eq.{_quote_value(source_id)}&select=*&limit=1",
        )
        if not rows:
            raise KeyError(f"data source not found: {source_id}")
        return _source_from_supabase(rows[0])

    def list_runs(self, source_id: Optional[str] = None, limit: Optional[int] = None) -> List[DataSourceRun]:
        query_parts = []
        if source_id is not None:
            query_parts.append(f"source_id=eq.{_quote_value(source_id)}")
        query_parts.append("select=*")
        query_parts.append("order=started_at.desc")
        if limit is not None:
            query_parts.append(f"limit={limit}")
        rows = self.transport.request_json("GET", "data_source_runs", query="&".join(query_parts))
        return [_run_from_supabase(row) for row in rows]

    def append_run(self, run: DataSourceRun) -> DataSourceRun:
        rows = self.transport.request_json(
            "POST",
            "data_source_runs",
            payload=_run_to_supabase(run),
        )
        return _run_from_supabase(rows[0]) if rows else run

    def patch_run(self, run_id: str, changes: dict) -> None:
        self.transport.request_json(
            "PATCH",
            "data_source_runs",
            payload=changes,
            query=f"id=eq.{_quote_value(run_id)}",
        )

    def list_runs_by_status(self, status: str) -> List[DataSourceRun]:
        rows = self.transport.request_json(
            "GET",
            "data_source_runs",
            query=f"status=eq.{_quote_value(status)}&select=*&order=started_at.desc",
        )
        return [_run_from_supabase(row) for row in rows]

    def list_posts(
        self,
        source_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[dict]:
        query_parts = []
        if source_id is not None:
            query_parts.append(f"source_id=eq.{_quote_value(source_id)}")
        if run_id is not None:
            query_parts.append(f"run_id=eq.{_quote_value(run_id)}")
        query_parts.append("select=*")
        query_parts.append("order=published_at.desc.nullslast")
        if limit is not None:
            query_parts.append(f"limit={limit}")
        return self.transport.request_json("GET", "source_posts", query="&".join(query_parts))

    def upsert_posts(self, records: List[dict]) -> int:
        if not records:
            return 0
        payload = [_post_to_supabase(record) for record in records]
        self.transport.request_json(
            "POST",
            "source_posts",
            payload=payload,
            query="on_conflict=content_hash",
        )
        return len(payload)


class DataSourceService:
    def __init__(
        self,
        repository: JsonDataSourceRepository,
        now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self.repository = repository
        self.now = now

    def list_sources(self) -> List[DataSourceConfig]:
        return self.repository.list_sources()

    def list_runs(self, source_id: Optional[str] = None, limit: Optional[int] = None) -> List[DataSourceRun]:
        return self.repository.list_runs(source_id=source_id, limit=limit)

    def list_posts(
        self,
        source_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[dict]:
        if hasattr(self.repository, "list_posts"):
            return self.repository.list_posts(source_id=source_id, run_id=run_id, limit=limit)
        return []

    def save_source(self, source: DataSourceConfig) -> DataSourceConfig:
        normalized = _normalize_source(source)
        return self.repository.save_source(normalized)

    def run_source(
        self,
        source_id: str,
        output_dir: str,
        transport: Optional[JsonTransport] = None,
        collector: Optional[Callable[["DataSourceConfig"], List[SourcePost]]] = None,
        records_collector: Optional[Callable[["DataSourceConfig"], List[dict]]] = None,
    ) -> DataSourceRun:
        """Synchronous collection. Used by tests and the CLI (with an injected
        collector / records_collector). The production Airtap path is async via
        start_run + reconcile_run, but if neither collector is given this still
        collects synchronously via Airtap (blocking), kept for CLI use."""
        source = self.repository.get_source(source_id)
        started_at = self.now()
        run_id = f"{source_id}-{_compact_timestamp(started_at)}"
        status = "success"
        message = ""
        output_path = ""
        items_collected = 0
        new_items = 0
        records: List[dict] = []

        try:
            if source.platform != "x":
                raise RuntimeError(f"unsupported data source platform: {source.platform}")
            if records_collector is not None:
                records = list(records_collector(source))
                posts = _posts_from_records(records)
            elif collector is not None:
                posts = list(collector(source))
            else:
                from .airtap_client import build_x_collection_prompt, collect_via_airtap
                from .x_ingest import normalize_airtap_payload

                prompt = build_x_collection_prompt(source.targets, posts_per_account=3)
                payload = collect_via_airtap(prompt)
                records = normalize_airtap_payload(payload, source_id=source_id, run_id=run_id)
                posts = _posts_from_records(records)
            items_collected = len(posts)
            try:
                output_path = write_posts_json(
                    posts,
                    str(Path(output_dir) / f"{source.id}-{_compact_timestamp(started_at)}.json"),
                )
            except OSError:
                output_path = ""
            if records and hasattr(self.repository, "upsert_posts"):
                for record in records:
                    record["source_id"] = source_id
                    record["run_id"] = run_id
                new_items = self.repository.upsert_posts(records)
        except Exception as error:
            status = "failed"
            message = str(error)

        finished_at = self.now()
        run = DataSourceRun(
            id=run_id,
            source_id=source_id,
            started_at=_format_datetime(started_at),
            finished_at=_format_datetime(finished_at),
            status=status,
            items_collected=items_collected,
            output_path=output_path,
            message=message if status == "failed" else (f"new={new_items}" if records else ""),
        )
        self.repository.append_run(run)

        if status == "failed":
            raise RuntimeError(message)

        return run

    def start_run(self, source_id: str) -> DataSourceRun:
        """Kick off an async Airtap collection: create the task, record a pending
        run with the task id, and return immediately. reconcile_run finishes it."""
        from .airtap_client import build_x_collection_prompt, create_task

        source = self.repository.get_source(source_id)
        if source.platform != "x":
            raise RuntimeError(f"unsupported data source platform: {source.platform}")
        started_at = self.now()
        run_id = f"{source_id}-{_compact_timestamp(started_at)}"
        prompt = build_x_collection_prompt(source.targets, posts_per_account=3)
        try:
            task_id = create_task(prompt)
        except Exception as error:
            run = DataSourceRun(
                id=run_id, source_id=source_id,
                started_at=_format_datetime(started_at), finished_at=_format_datetime(self.now()),
                status="failed", items_collected=0, output_path="", message=str(error),
            )
            self.repository.append_run(run)
            raise
        run = DataSourceRun(
            id=run_id, source_id=source_id,
            started_at=_format_datetime(started_at), finished_at=_format_datetime(started_at),
            status="pending", items_collected=0, output_path="",
            message="采集中…", airtap_task_id=task_id,
        )
        self.repository.append_run(run)
        return run

    def reconcile_run(self, run: DataSourceRun) -> DataSourceRun:
        """Check one pending run's Airtap task; if done, ingest and update it."""
        from .airtap_client import poll_until_done, latest_agent_text, AirtapError
        from .x_ingest import extract_airtap_json, normalize_airtap_payload

        if not run.airtap_task_id:
            return run
        # Single non-blocking-ish poll: short max_wait so cron/refresh stays fast.
        details = poll_until_done(run.airtap_task_id, interval_secs=4.0, max_wait_secs=20.0)
        state = details.get("_finalState")
        if state in (None, "TIMEOUT") or state not in ("COMPLETED", "FAILED", "CANCELLED"):
            return run  # still running; leave pending
        changes = {"finished_at": _format_datetime(self.now())}
        if state == "COMPLETED":
            text = latest_agent_text(details)
            payload = extract_airtap_json(text)
            if payload is None:
                changes.update(status="failed", message="采集完成但未返回可解析结果")
            else:
                records = normalize_airtap_payload(payload, source_id=run.source_id, run_id=run.id)
                new_items = 0
                if records and hasattr(self.repository, "upsert_posts"):
                    new_items = self.repository.upsert_posts(records)
                changes.update(
                    status="success",
                    items_collected=len(records),
                    message=f"new={new_items}",
                )
        else:
            changes.update(status="failed", message=f"Airtap 任务{state}")
        self.repository.patch_run(run.id, changes)
        return run

    def reconcile_pending(self, limit: int = 5) -> List[dict]:
        results = []
        if not hasattr(self.repository, "list_runs_by_status"):
            return results
        pending = self.repository.list_runs_by_status("pending")[:limit]
        for run in pending:
            try:
                self.reconcile_run(run)
                results.append({"run_id": run.id, "reconciled": True})
            except Exception as error:
                results.append({"run_id": run.id, "error": str(error)})
        return results

    def list_due_sources(self, output_dir: str = "data/inbox") -> List[DataSourceConfig]:
        """Return enabled sources whose cadence has elapsed since the last run."""
        now = self.now()
        due = []
        for source in self.repository.list_sources():
            if not source.enabled or source.platform != "x":
                continue
            runs = self.repository.list_runs(source_id=source.id, limit=1)
            if not runs:
                due.append(source)
                continue
            last = runs[0]
            try:
                last_at = datetime.fromisoformat(last.started_at)
            except ValueError:
                due.append(source)
                continue
            if last_at.tzinfo is None:
                last_at = last_at.replace(tzinfo=timezone.utc)
            elapsed_minutes = (now - last_at).total_seconds() / 60.0
            if elapsed_minutes >= source.cadence_minutes:
                due.append(source)
        return due

    def run_due_sources(self, output_dir: str = "data/inbox") -> List[dict]:
        results = []
        for source in self.list_due_sources(output_dir=output_dir):
            try:
                run = self.start_run(source.id)
                results.append({"source_id": source.id, "status": run.status, "run_id": run.id})
            except Exception as error:
                results.append({"source_id": source.id, "status": "failed", "error": str(error)})
        return results


def _posts_from_records(records: List[dict]) -> List[SourcePost]:
    return [
        SourcePost(
            id=record.get("post_id") or record["content_hash"],
            account=record.get("author_handle", ""),
            text=record.get("text", ""),
            url=record.get("url") or "",
            metrics=record.get("metrics") or {},
        )
        for record in records
    ]


def parse_account_targets(text: str) -> Tuple[str, ...]:
    targets: List[str] = []
    seen = set()
    for raw in re.split(r"[\s,]+", text):
        normalized = _normalize_target(raw)
        if not normalized or normalized.startswith("#"):
            continue
        lowered = normalized.lower()
        if lowered not in seen:
            seen.add(lowered)
            targets.append(normalized)
    return tuple(targets)


def load_sources_file(path: str) -> List[DataSourceConfig]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("sources", payload if isinstance(payload, list) else [])
    return [_normalize_source(_source_from_dict(row)) for row in rows]


def credential_value(path: str, key: str) -> str:
    try:
        return CredentialFile(path).get(key)
    except RuntimeError:
        return ""


def default_data_source_repository(root: str = "data") -> JsonDataSourceRepository:
    base = Path(root)
    return JsonDataSourceRepository(
        sources_path=base / "sources" / "sources.json",
        runs_path=base / "sources" / "runs.json",
        posts_path=base / "sources" / "posts.json",
    )


def _normalize_source(source: DataSourceConfig) -> DataSourceConfig:
    source_id = source.id.strip().lower()
    name = source.name.strip()
    platform = source.platform.strip().lower()
    targets = tuple(_normalize_target(target) for target in source.targets)
    targets = tuple(target for target in targets if target)

    if not source_id:
        raise ValueError("data source id is required")
    if not name:
        raise ValueError("data source name is required")
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"unsupported data source platform: {platform}")
    if source.cadence_minutes < 30 or source.cadence_minutes > 1440:
        raise ValueError("cadence_minutes must be between 30 and 1440 (24h)")
    if source.min_score < 0 or source.min_score > 100:
        raise ValueError("min_score must be 0-100")
    if not targets:
        raise ValueError("at least one target is required")
    if not source.credential_key.strip():
        raise ValueError("credential_key is required")
    if not source.credential_file.strip():
        raise ValueError("credential_file is required")

    return DataSourceConfig(
        id=source_id,
        name=name,
        platform=platform,
        cadence_minutes=source.cadence_minutes,
        targets=targets,
        min_score=source.min_score,
        material_strategy=source.material_strategy.strip() or "download_media",
        credential_key=source.credential_key.strip(),
        credential_file=source.credential_file.strip(),
        enabled=source.enabled,
    )


def _normalize_target(raw: str) -> str:
    target = raw.strip().strip(",")
    if not target:
        return ""
    if target.startswith("https://x.com/"):
        target = target[len("https://x.com/") :]
    elif target.startswith("https://twitter.com/"):
        target = target[len("https://twitter.com/") :]
    target = target.split("/")[0]
    return target.lstrip("@").strip()


def _parse_env_assignment(line: str) -> Optional[Tuple[str, str]]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].strip()
    if "=" in stripped:
        key, value = stripped.split("=", 1)
    else:
        parts = stripped.split(None, 1)
        if len(parts) != 2 or not _looks_like_env_key(parts[0]):
            return None
        key, value = parts
    key = key.strip()
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def _looks_like_env_key(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Z0-9_]*", value.strip()))


def _source_to_dict(source: DataSourceConfig) -> dict:
    payload = asdict(source)
    payload["targets"] = list(source.targets)
    payload["account_count"] = source.account_count
    return payload


def _source_from_dict(payload: dict) -> DataSourceConfig:
    return DataSourceConfig(
        id=str(payload["id"]),
        name=str(payload["name"]),
        platform=str(payload["platform"]),
        cadence_minutes=int(payload.get("cadence_minutes", 30)),
        targets=tuple(str(item) for item in payload.get("targets", [])),
        min_score=int(payload.get("min_score", 70)),
        material_strategy=str(payload.get("material_strategy", "download_media")),
        credential_key=str(payload.get("credential_key", DEFAULT_X_CREDENTIAL_KEY)),
        credential_file=str(payload.get("credential_file", DEFAULT_CREDENTIAL_FILE)),
        enabled=bool(payload.get("enabled", True)),
    )


def _run_to_dict(run: DataSourceRun) -> dict:
    return asdict(run)


def _run_from_dict(payload: dict) -> DataSourceRun:
    return DataSourceRun(
        id=str(payload["id"]),
        source_id=str(payload["source_id"]),
        started_at=str(payload["started_at"]),
        finished_at=str(payload["finished_at"]),
        status=str(payload["status"]),
        items_collected=int(payload.get("items_collected", 0)),
        output_path=str(payload.get("output_path", "")),
        message=str(payload.get("message", "")),
        airtap_task_id=str(payload.get("airtap_task_id", "")),
    )


def _source_to_supabase(source: DataSourceConfig) -> dict:
    return {
        "id": source.id,
        "name": source.name,
        "platform": source.platform,
        "cadence_minutes": source.cadence_minutes,
        "targets": list(source.targets),
        "min_score": source.min_score,
        "material_strategy": source.material_strategy,
        "credential_key": source.credential_key,
        "credential_file": source.credential_file,
        "enabled": source.enabled,
    }


def _source_from_supabase(payload: dict) -> DataSourceConfig:
    return DataSourceConfig(
        id=str(payload["id"]),
        name=str(payload["name"]),
        platform=str(payload["platform"]),
        cadence_minutes=int(payload.get("cadence_minutes", 30)),
        targets=tuple(str(item) for item in payload.get("targets", [])),
        min_score=int(payload.get("min_score", 70)),
        material_strategy=str(payload.get("material_strategy", "download_media")),
        credential_key=str(payload.get("credential_key", DEFAULT_X_CREDENTIAL_KEY)),
        credential_file=str(payload.get("credential_file", DEFAULT_CREDENTIAL_FILE)),
        enabled=bool(payload.get("enabled", True)),
    )


def _run_to_supabase(run: DataSourceRun) -> dict:
    return _run_to_dict(run)


def _run_from_supabase(payload: dict) -> DataSourceRun:
    return _run_from_dict(payload)


def _post_to_supabase(record: dict) -> dict:
    allowed = {
        "content_hash",
        "source_id",
        "run_id",
        "platform",
        "post_id",
        "author_handle",
        "author_name",
        "author_avatar_url",
        "author_bio",
        "text",
        "url",
        "published_at",
        "published_at_raw",
        "image_urls",
        "video_urls",
        "link_cards",
        "quote",
        "metrics",
        "media_error",
        "collected_at",
        "raw",
    }
    return {key: value for key, value in record.items() if key in allowed and value is not None}


def _quote_value(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _compact_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.strftime("%Y%m%dT%H%M%S%fZ")
