"""Shared Vercel serverless handler for the content-ops API.

Vercel Python functions expose a `handler` class subclassing
BaseHTTPRequestHandler. Each api/*.py route reuses this via build_handler().
Storage is Supabase in production (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY);
falls back to local JSON only when those are absent (local dev).
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Make the repo root importable so `content_ops` resolves on Vercel.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from content_ops.data_sources import (  # noqa: E402
    DataSourceService,
    SupabaseDataSourceRepository,
    default_data_source_repository,
)
from content_ops.server import create_app  # noqa: E402


def _build_service() -> DataSourceService:
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return DataSourceService(SupabaseDataSourceRepository.from_env())
    return DataSourceService(default_data_source_repository())


def build_handler():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._handle()

        def do_POST(self):
            self._handle()

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.end_headers()

        def _handle(self):
            try:
                length = int(self.headers.get("Content-Length") or "0")
                body = self.rfile.read(length) if length else b""
                app = create_app(_build_service())
                status, headers, response_body = app.handle(self.command, self.path, body)
            except Exception as error:  # surface config errors as JSON, not 500 HTML
                status, headers, response_body = 500, {"Content-Type": "application/json"}, json.dumps({"error": str(error)})
            encoded = response_body.encode("utf-8")
            self.send_response(status)
            self._cors()
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def log_message(self, *args):
            return

    return Handler
