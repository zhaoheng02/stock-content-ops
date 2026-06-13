"""Vercel serverless handler for the content-ops API.

Each api/*.py route imports ContentOpsHandler from here as `handler`. Storage is
Supabase in production (SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY); falls back to
local JSON only when those are absent (local dev).
"""

import json
import os
from http.server import BaseHTTPRequestHandler

from .data_sources import (
    DataSourceService,
    SupabaseDataSourceRepository,
    default_data_source_repository,
)
from .server import create_app


def build_service() -> DataSourceService:
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return DataSourceService(SupabaseDataSourceRepository.from_env())
    return DataSourceService(default_data_source_repository())


class ContentOpsHandler(BaseHTTPRequestHandler):
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
        self._cors()
        self.end_headers()

    def _handle(self):
        try:
            length = int(self.headers.get("Content-Length") or "0")
            body = self.rfile.read(length) if length else b""
            app = create_app(build_service())
            status, headers, response_body = app.handle(self.command, self.path, body)
        except Exception as error:
            status, headers, response_body = (
                500,
                {"Content-Type": "application/json"},
                json.dumps({"error": str(error)}),
            )
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
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, *args):
        return


def build_handler():
    return ContentOpsHandler
