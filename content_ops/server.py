import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .data_sources import DataSourceConfig, DataSourceService, parse_account_targets
from .generator import generate_assets
from .models import SourcePost
from .settings import DEFAULT_PERSONA
from .studio import StudioService


# Maps backend asset keys to a stable platform slug used by drafts rows.
PLATFORM_KEYS = ("xiaohongshu", "wechat_article", "video_account", "douyin_script")


class DataSourceApi:
    def __init__(self, service: DataSourceService, studio: Optional[StudioService] = None):
        self.service = service
        self._studio = studio

    @property
    def studio(self) -> StudioService:
        if self._studio is None:
            self._studio = StudioService()
        return self._studio

    def handle(self, method: str, path: str, body: bytes = b"") -> Tuple[int, dict, str]:
        parsed = urlparse(path)
        query = parse_qs(parsed.query)
        try:
            if method == "GET" and parsed.path == "/api/sources":
                return _json_response(200, {"sources": [_public_source(source) for source in self.service.list_sources()]})
            if method == "POST" and parsed.path == "/api/sources":
                payload = json.loads(body.decode("utf-8") or "{}")
                source = self.service.save_source(_source_from_request(payload))
                return _json_response(201, {"source": _public_source(source)})
            if method == "GET" and parsed.path == "/api/source-runs":
                source_id = _first(query.get("source_id"))
                limit = int(_first(query.get("limit")) or "10")
                runs = [run.__dict__ for run in self.service.list_runs(source_id=source_id, limit=limit)]
                return _json_response(200, {"runs": runs})
            if method == "GET" and parsed.path == "/api/source-posts":
                source_id = _first(query.get("source_id"))
                run_id = _first(query.get("run_id"))
                limit_raw = _first(query.get("limit"))
                limit = int(limit_raw) if limit_raw else None
                posts = self.service.list_posts(source_id=source_id, run_id=run_id, limit=limit)
                return _json_response(200, {"posts": posts})
            if method == "POST" and parsed.path == "/api/source-runs":
                payload = json.loads(body.decode("utf-8") or "{}")
                run = self.service.run_source(
                    str(payload.get("source_id", "")),
                    output_dir=str(payload.get("out", "/tmp/inbox")),
                )
                return _json_response(201, {"run": run.__dict__})
            if method == "POST" and parsed.path == "/api/generate":
                payload = json.loads(body.decode("utf-8") or "{}")
                return _json_response(200, {"drafts": self._generate_drafts(payload)})
            if (method in ("GET", "POST")) and parsed.path == "/api/cron":
                results = self.service.run_due_sources(output_dir="/tmp/inbox")
                return _json_response(200, {"ran": results, "count": len(results)})

            studio_response = self._handle_studio(method, parsed.path, query, body)
            if studio_response is not None:
                return studio_response

            return _json_response(404, {"error": "not found"})
        except Exception as error:
            return _json_response(400, {"error": str(error)})

    def _handle_studio(self, method, path, query, body):
        payload = json.loads(body.decode("utf-8") or "{}") if body else {}

        # Drafts: list / create / update-status / delete
        if path == "/api/drafts" and method == "GET":
            return _json_response(200, {"drafts": self.studio.list_drafts(
                status=_first(query.get("status")),
                platform=_first(query.get("platform")),
                limit=int(_first(query.get("limit"))) if _first(query.get("limit")) else None,
            )})
        if path == "/api/drafts" and method == "POST":
            return _json_response(201, {"draft": self.studio.save_draft(payload)})
        if path == "/api/drafts" and method in ("PATCH", "PUT"):
            draft_id = str(payload.get("id", ""))
            status = str(payload.get("status", ""))
            extra = {k: v for k, v in payload.items() if k not in ("id", "status")}
            return _json_response(200, {"draft": self.studio.update_draft_status(draft_id, status, extra)})
        if path == "/api/drafts" and method == "DELETE":
            self.studio.delete_draft(str(_first(query.get("id")) or payload.get("id", "")))
            return _json_response(200, {"ok": True})

        # Accounts
        if path == "/api/accounts" and method == "GET":
            return _json_response(200, {"accounts": self.studio.list_accounts()})
        if path == "/api/accounts" and method == "POST":
            return _json_response(201, {"account": self.studio.save_account(payload)})
        if path == "/api/accounts" and method == "DELETE":
            self.studio.delete_account(str(_first(query.get("id")) or payload.get("id", "")))
            return _json_response(200, {"ok": True})

        # Assets
        if path == "/api/assets" and method == "GET":
            return _json_response(200, {"assets": self.studio.list_assets(group=_first(query.get("group")))})
        if path == "/api/assets" and method == "POST":
            return _json_response(201, {"asset": self.studio.save_asset(payload)})
        if path == "/api/assets" and method == "DELETE":
            self.studio.delete_asset(str(_first(query.get("id")) or payload.get("id", "")))
            return _json_response(200, {"ok": True})

        # Team
        if path == "/api/team" and method == "GET":
            return _json_response(200, {"members": self.studio.list_team()})
        if path == "/api/team" and method == "POST":
            return _json_response(201, {"member": self.studio.save_member(payload)})
        if path == "/api/team" and method == "DELETE":
            self.studio.delete_member(str(_first(query.get("id")) or payload.get("id", "")))
            return _json_response(200, {"ok": True})

        # Proxies
        if path == "/api/proxies" and method == "GET":
            return _json_response(200, {"proxies": self.studio.list_proxies()})
        if path == "/api/proxies" and method == "POST":
            return _json_response(201, {"proxy": self.studio.save_proxy(payload)})
        if path == "/api/proxies" and method == "DELETE":
            self.studio.delete_proxy(str(_first(query.get("id")) or payload.get("id", "")))
            return _json_response(200, {"ok": True})

        # Analytics
        if path == "/api/analytics" and method == "GET":
            return _json_response(200, self.studio.analytics_summary())

        return None

    def _generate_drafts(self, payload: dict) -> list:
        persona = str(payload.get("persona") or DEFAULT_PERSONA)
        post_id = payload.get("post_id")
        persist = bool(payload.get("persist", True))
        posts = self.service.list_posts(
            source_id=payload.get("source_id"),
            run_id=payload.get("run_id"),
            limit=int(payload.get("limit", 3)) if not post_id else None,
        )
        if post_id:
            posts = [p for p in posts if p.get("post_id") == post_id or p.get("content_hash") == post_id]
        drafts = []
        for record in posts:
            post = SourcePost(
                id=record.get("post_id") or record.get("content_hash", ""),
                account=record.get("author_handle", ""),
                text=record.get("text", ""),
                url=record.get("url") or "",
                metrics=record.get("metrics") or {},
            )
            assets = generate_assets(post, persona)
            entry = {
                "post_id": post.id,
                "account": post.account,
                "source_url": post.url,
                "assets": {
                    key: {"platform": a.platform, "title": a.title, "body": a.body}
                    for key, a in assets.items()
                },
            }
            if persist:
                saved = {}
                for key, asset in assets.items():
                    row = self.studio.save_draft({
                        "id": f"draft-{post.id}-{key}",
                        "post_id": post.id,
                        "source_id": payload.get("source_id"),
                        "platform": key,
                        "title": asset.title,
                        "body": asset.body,
                        "tags": ["AI", "出海", "产品观察"],
                        "status": "needs_review",
                        "source_url": post.url,
                        "ai_analysis": f"基于 @{post.account} 的海外信号，重构为可迁移的中文观点型内容。",
                    })
                    saved[key] = row.get("id")
                entry["draft_ids"] = saved
            drafts.append(entry)
        return drafts


def create_app(service: DataSourceService) -> DataSourceApi:
    return DataSourceApi(service)


def serve(service: DataSourceService, host: str = "127.0.0.1", port: int = 8787) -> None:
    app = create_app(service)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._handle()

        def do_POST(self):
            self._handle()

        def do_PUT(self):
            self._handle()

        def do_PATCH(self):
            self._handle()

        def do_DELETE(self):
            self._handle()

        def do_OPTIONS(self):
            self.send_response(204)
            self._send_cors_headers()
            self.end_headers()

        def _handle(self):
            length = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(length) if length else b""
            status, headers, response_body = app.handle(self.command, self.path, body)
            encoded = response_body.encode("utf-8")
            self.send_response(status)
            self._send_cors_headers()
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _send_cors_headers(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def log_message(self, format, *args):
            return

    ThreadingHTTPServer((host, port), Handler).serve_forever()


def _source_from_request(payload: dict) -> DataSourceConfig:
    targets = payload.get("targets", ())
    if isinstance(targets, str):
        targets = parse_account_targets(targets)
    return DataSourceConfig(
        id=str(payload.get("id", "")),
        name=str(payload.get("name", "")),
        platform=str(payload.get("platform", "x")),
        cadence_minutes=int(payload.get("cadence_minutes", 30)),
        targets=tuple(str(target) for target in targets),
        min_score=int(payload.get("min_score", 70)),
        material_strategy=str(payload.get("material_strategy", "download_media")),
        credential_key=str(payload.get("credential_key", "X_BEARER_TOKEN")),
        credential_file=str(payload.get("credential_file", "/Users/bytedance/personal.config")),
        enabled=bool(payload.get("enabled", True)),
    )


def _public_source(source: DataSourceConfig) -> dict:
    return {
        "id": source.id,
        "name": source.name,
        "platform": source.platform,
        "cadence_minutes": source.cadence_minutes,
        "targets": list(source.targets),
        "account_count": source.account_count,
        "min_score": source.min_score,
        "material_strategy": source.material_strategy,
        "enabled": source.enabled,
    }


def _json_response(status: int, payload: dict) -> Tuple[int, dict, str]:
    return status, {"Content-Type": "application/json; charset=utf-8"}, json.dumps(payload, ensure_ascii=False)


def _first(values: Optional[list]) -> Optional[str]:
    return values[0] if values else None
