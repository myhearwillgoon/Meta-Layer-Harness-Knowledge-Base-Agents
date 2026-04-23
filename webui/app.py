import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timezone


class HITLHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, intervener=None, **kwargs):
        self.intervener = intervener
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/audit-queue":
            self._send_json(self.intervener.get_audit_queue() if self.intervener else [])
        elif parsed.path == "/api/health":
            self._send_json({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()})
        elif parsed.path == "/api/loop-break":
            self._send_json(self.intervener.get_loop_break_report() if self.intervener else {})
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/audit/"):
            request_id = parsed.path.split("/")[-1]
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length)) if content_length else {}
            action = body.get("action", "approve")
            reviewer = body.get("reviewer", "admin")

            if action == "approve":
                result = self.intervener.approve_audit_item(request_id, reviewer)
            else:
                result = self.intervener.reject_audit_item(request_id, reviewer)

            self._send_json({"success": result, "request_id": request_id, "action": action})
        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())


def run_server(port: int = 8080, intervener=None):
    def handler(*args, **kwargs):
        return HITLHandler(*args, intervener=intervener, **kwargs)
    server = HTTPServer(("0.0.0.0", port), handler)
    print(f"HITL Web UI running on http://0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
