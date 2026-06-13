import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .data_sources import DataSourceConfig, DataSourceService, parse_account_targets


class DataSourceApi:
    def __init__(self, service: DataSourceService):
        self.service = service

    def handle(self, method: str, path: str, body: bytes = b"") -> Tuple[int, dict, str]:
        parsed = urlparse(path)
        try:
            if method == "GET" and parsed.path == "/api/sources":
                return _json_response(200, {"sources": [_public_source(source) for source in self.service.list_sources()]})
            if method == "POST" and parsed.path == "/api/sources":
                payload = json.loads(body.decode("utf-8") or "{}")
                source = self.service.save_source(_source_from_request(payload))
                return _json_response(201, {"source": _public_source(source)})
            if method == "GET" and parsed.path == "/api/source-runs":
                query = parse_qs(parsed.query)
                source_id = _first(query.get("source_id"))
                limit = int(_first(query.get("limit")) or "10")
                runs = [run.__dict__ for run in self.service.list_runs(source_id=source_id, limit=limit)]
                return _json_response(200, {"runs": runs})
            if method == "GET" and parsed.path == "/api/source-posts":
                query = parse_qs(parsed.query)
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
                    output_dir=str(payload.get("out", "data/inbox")),
                )
                return _json_response(201, {"run": run.__dict__})
            return _json_response(404, {"error": "not found"})
        except Exception as error:
            return _json_response(400, {"error": str(error)})


def create_app(service: DataSourceService) -> DataSourceApi:
    return DataSourceApi(service)


def serve(service: DataSourceService, host: str = "127.0.0.1", port: int = 8787) -> None:
    app = create_app(service)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._handle()

        def do_POST(self):
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
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
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
