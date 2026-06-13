"""Backend for the phase-2 entities (drafts, accounts, assets, team, proxies,
metrics) that power the Publish / Review / Accounts / Analytics / Team / Assets
pages.

Same pattern as data_sources: a Supabase PostgREST repository for production and
a local JSON repository for dev, behind a single StudioService. Stdlib only.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .data_sources import UrlLibSupabaseTransport, credential_value, DEFAULT_CREDENTIAL_FILE


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# Tables exposed through the generic repository. Each maps to a Supabase table
# and a key in the local JSON store. order_by controls default sort.
TABLES = {
    "drafts": {"order": "updated_at.desc", "conflict": "id"},
    "publish_accounts": {"order": "updated_at.desc", "conflict": "id"},
    "assets": {"order": "created_at.desc", "conflict": "id"},
    "team_members": {"order": "joined_at.desc", "conflict": "id"},
    "proxies": {"order": "created_at.desc", "conflict": "id"},
    "publish_metrics": {"order": "recorded_at.desc", "conflict": "id"},
}


class SupabaseStudioRepository:
    def __init__(self, transport: UrlLibSupabaseTransport):
        self.transport = transport

    @classmethod
    def from_env(cls) -> "SupabaseStudioRepository":
        project_url = os.environ.get("SUPABASE_URL")
        service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not project_url or not service_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
        return cls(UrlLibSupabaseTransport(project_url=project_url, service_key=service_key))

    def list(self, table: str, filters: Optional[dict] = None, limit: Optional[int] = None) -> List[dict]:
        meta = TABLES[table]
        parts = ["select=*", f"order={meta['order']}"]
        for key, value in (filters or {}).items():
            parts.append(f"{key}=eq.{_quote(value)}")
        if limit is not None:
            parts.append(f"limit={limit}")
        return self.transport.request_json("GET", table, query="&".join(parts))

    def upsert(self, table: str, record: dict) -> dict:
        meta = TABLES[table]
        rows = self.transport.request_json(
            "POST", table, payload=record, query=f"on_conflict={meta['conflict']}"
        )
        return rows[0] if rows else record

    def patch(self, table: str, row_id: str, changes: dict) -> dict:
        rows = self.transport.request_json(
            "PATCH", table, payload=changes, query=f"id=eq.{_quote(row_id)}"
        )
        return rows[0] if rows else {**changes, "id": row_id}

    def delete(self, table: str, row_id: str) -> None:
        self.transport.request_json("DELETE", table, query=f"id=eq.{_quote(row_id)}")


class JsonStudioRepository:
    def __init__(self, root: str = "data/studio"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, table: str) -> Path:
        return self.root / f"{table}.json"

    def _read(self, table: str) -> List[dict]:
        path = self._path(table)
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8") or "[]")

    def _write(self, table: str, rows: List[dict]) -> None:
        self._path(table).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def list(self, table: str, filters: Optional[dict] = None, limit: Optional[int] = None) -> List[dict]:
        rows = self._read(table)
        for key, value in (filters or {}).items():
            rows = [r for r in rows if str(r.get(key)) == str(value)]
        order = TABLES[table]["order"].split(".")
        field, direction = order[0], (order[1] if len(order) > 1 else "asc")
        rows.sort(key=lambda r: (r.get(field) or ""), reverse=direction == "desc")
        return rows[:limit] if limit is not None else rows

    def upsert(self, table: str, record: dict) -> dict:
        rows = self._read(table)
        rows = [r for r in rows if r.get("id") != record.get("id")]
        rows.append(record)
        self._write(table, rows)
        return record

    def patch(self, table: str, row_id: str, changes: dict) -> dict:
        rows = self._read(table)
        updated = None
        for row in rows:
            if row.get("id") == row_id:
                row.update(changes)
                updated = row
        self._write(table, rows)
        return updated or {**changes, "id": row_id}

    def delete(self, table: str, row_id: str) -> None:
        rows = [r for r in self._read(table) if r.get("id") != row_id]
        self._write(table, rows)


def default_studio_repository():
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return SupabaseStudioRepository.from_env()
    return JsonStudioRepository()


class StudioService:
    def __init__(self, repository=None):
        self.repo = repository or default_studio_repository()

    # ----- drafts -----
    def list_drafts(self, status: Optional[str] = None, platform: Optional[str] = None,
                    limit: Optional[int] = None) -> List[dict]:
        filters = {}
        if status:
            filters["status"] = status
        if platform:
            filters["platform"] = platform
        return self.repo.list("drafts", filters=filters or None, limit=limit)

    def save_draft(self, payload: dict) -> dict:
        record = {
            "id": payload.get("id") or _new_id("draft"),
            "post_id": payload.get("post_id"),
            "source_id": payload.get("source_id"),
            "platform": payload.get("platform", ""),
            "title": payload.get("title", ""),
            "body": payload.get("body", ""),
            "tags": payload.get("tags", []),
            "status": payload.get("status", "needs_review"),
            "owner": payload.get("owner", "内容组"),
            "account_id": payload.get("account_id"),
            "ai_analysis": payload.get("ai_analysis", ""),
            "source_url": payload.get("source_url", ""),
            "scheduled_at": payload.get("scheduled_at"),
            "published_at": payload.get("published_at"),
            "publish_error": payload.get("publish_error", ""),
            "updated_at": _now_iso(),
        }
        if not payload.get("id"):
            record["created_at"] = _now_iso()
        return self.repo.upsert("drafts", record)

    def update_draft_status(self, draft_id: str, status: str, extra: Optional[dict] = None) -> dict:
        changes = {"status": status, "updated_at": _now_iso()}
        if status == "published":
            changes["published_at"] = _now_iso()
        if extra:
            changes.update(extra)
        return self.repo.patch("drafts", draft_id, changes)

    def delete_draft(self, draft_id: str) -> None:
        self.repo.delete("drafts", draft_id)

    # ----- accounts -----
    def list_accounts(self) -> List[dict]:
        return self.repo.list("publish_accounts")

    def save_account(self, payload: dict) -> dict:
        record = {
            "id": payload.get("id") or _new_id("acct"),
            "platform": payload.get("platform", ""),
            "slug": payload.get("slug", ""),
            "name": payload.get("name", ""),
            "status": payload.get("status", "未授权"),
            "mode": payload.get("mode", "浏览器发布"),
            "proxy": payload.get("proxy", "默认"),
            "updated_at": _now_iso(),
        }
        if not payload.get("id"):
            record["created_at"] = _now_iso()
        return self.repo.upsert("publish_accounts", record)

    def delete_account(self, account_id: str) -> None:
        self.repo.delete("publish_accounts", account_id)

    # ----- assets -----
    def list_assets(self, group: Optional[str] = None) -> List[dict]:
        filters = {"group_name": group} if group and group != "全部分组" else None
        return self.repo.list("assets", filters=filters)

    def save_asset(self, payload: dict) -> dict:
        record = {
            "id": payload.get("id") or _new_id("asset"),
            "name": payload.get("name", ""),
            "type": payload.get("type", "图片"),
            "size_bytes": int(payload.get("size_bytes", 0)),
            "group_name": payload.get("group_name", "未分组"),
            "used": payload.get("used", ""),
            "url": payload.get("url", ""),
            "created_at": payload.get("created_at") or _now_iso(),
        }
        return self.repo.upsert("assets", record)

    def delete_asset(self, asset_id: str) -> None:
        self.repo.delete("assets", asset_id)

    # ----- team -----
    def list_team(self) -> List[dict]:
        return self.repo.list("team_members")

    def save_member(self, payload: dict) -> dict:
        record = {
            "id": payload.get("id") or _new_id("member"),
            "name": payload.get("name", ""),
            "role": payload.get("role", "编辑"),
            "account_count": int(payload.get("account_count", 0)),
            "status": payload.get("status", "在线"),
            "joined_at": payload.get("joined_at") or datetime.now(timezone.utc).date().isoformat(),
            "created_at": payload.get("created_at") or _now_iso(),
        }
        return self.repo.upsert("team_members", record)

    def delete_member(self, member_id: str) -> None:
        self.repo.delete("team_members", member_id)

    # ----- proxies -----
    def list_proxies(self) -> List[dict]:
        return self.repo.list("proxies")

    def save_proxy(self, payload: dict) -> dict:
        record = {
            "id": payload.get("id") or _new_id("proxy"),
            "name": payload.get("name", ""),
            "type": payload.get("type", "HTTP"),
            "host": payload.get("host", ""),
            "port": int(payload.get("port", 0) or 0),
            "username": payload.get("username", ""),
            "password": payload.get("password", ""),
            "status": payload.get("status", "正常"),
            "created_at": payload.get("created_at") or _now_iso(),
        }
        return self.repo.upsert("proxies", record)

    def delete_proxy(self, proxy_id: str) -> None:
        self.repo.delete("proxies", proxy_id)

    # ----- analytics -----
    def list_metrics(self, limit: Optional[int] = None) -> List[dict]:
        return self.repo.list("publish_metrics", limit=limit)

    def analytics_summary(self) -> dict:
        drafts = self.repo.list("drafts")
        metrics = self.repo.list("publish_metrics")
        published = [d for d in drafts if d.get("status") == "published"]
        totals = {"views": 0, "likes": 0, "comments": 0, "shares": 0, "leads": 0}
        for m in metrics:
            for key in totals:
                totals[key] += int(m.get(key, 0) or 0)
        by_platform = {}
        for d in drafts:
            by_platform[d.get("platform", "")] = by_platform.get(d.get("platform", ""), 0) + 1
        return {
            "published_count": len(published),
            "draft_count": len(drafts),
            "interactions": totals["likes"] + totals["comments"] + totals["shares"],
            "totals": totals,
            "by_platform": by_platform,
        }


def _quote(value) -> str:
    text = str(value)
    if any(ch in text for ch in [",", ".", "(", ")", " "]):
        return '"' + text.replace('"', '\\"') + '"'
    return text
