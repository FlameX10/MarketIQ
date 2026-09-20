import http.server
import socketserver
import json
import base64
import os
import sys

# Ensure root dir is in python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from netlify.functions.generate import handler as netlify_generate_handler

PORT = int(os.environ.get("PORT", 8080))
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")


class LocalDevHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_OPTIONS(self):
        if self.path.startswith("/api/"):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()
        else:
            super().do_OPTIONS()

    def do_GET(self):
        if self.path.startswith("/api/generate"):
            event = {
                "httpMethod": "GET",
                "path": self.path,
                "headers": dict(self.headers),
            }
            res = netlify_generate_handler(event, None)
            self._send_netlify_response(res)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/generate"):
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            body_str = body_bytes.decode("utf-8")

            event = {
                "httpMethod": "POST",
                "path": self.path,
                "headers": dict(self.headers),
                "body": body_str,
                "isBase64Encoded": False,
            }
            res = netlify_generate_handler(event, None)
            self._send_netlify_response(res)
        else:
            self.send_error(404, "Endpoint not found")

    def _send_netlify_response(self, res):
        status_code = res.get("statusCode", 200)
        headers = res.get("headers", {})
        body = res.get("body", "")

        self.send_response(status_code)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()

        if isinstance(body, str):
            self.wfile.write(body.encode("utf-8"))
        elif isinstance(body, bytes):
            self.wfile.write(body)


def main():
    print("=" * 60)
    print(f"MARKET REPORT GENERATOR - LOCAL DEV SERVER")
    print(f"Serving UI from: {PUBLIC_DIR}")
    print(f"API Endpoint: http://localhost:{PORT}/api/generate")
    print("=" * 60)

    with socketserver.TCPServer(("", PORT), LocalDevHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
