import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from http.server import BaseHTTPRequestHandler

try:
    from content_ops.vercel_handler import build_handler  # noqa: F401
    IMPORT_OK = True
    IMPORT_ERR = ""
except Exception as e:  # capture, don't crash the function
    IMPORT_OK = False
    IMPORT_ERR = repr(e)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        import json
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "ok": True,
            "service": "content-ops",
            "content_ops_import": IMPORT_OK,
            "import_error": IMPORT_ERR,
        }).encode("utf-8"))
