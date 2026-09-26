import http.server
import socketserver
import json
import base64
import os
import sys
import tempfile
from datetime import datetime

# Ensure root dir is in python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.parser import parse_docx
from src.ai_generator import AIGenerator
from src.payload_builder import build_payload, payload_to_dict
from src.renderer import render_report
from run import load_config, _get_fallback_content, sanitize_filename

PORT = int(os.environ.get("PORT", 8080))
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")


def handle_api_request(method, body_str):
    if method == "GET":
        samples = []
        for file in os.listdir(ROOT_DIR):
            if file.endswith(".docx") and not file.startswith("~$") and "template" not in file.lower():
                samples.append(file)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"status": "online", "service": "MarketIQ API", "samples": samples}),
        }

    if method != "POST":
        return {"statusCode": 405, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": "Method not allowed"})}

    temp_files = []
    try:
        body_data = json.loads(body_str) if body_str else {}
        file_data = body_data.get("file_data")
        sample_name = body_data.get("sample_name")
        use_api = body_data.get("use_api", True)
        custom_api_key = body_data.get("api_key")

        config = load_config(os.path.join(ROOT_DIR, "config.json"))
        if custom_api_key:
            config["openrouter_api_key"] = custom_api_key

        if file_data:
            file_bytes = base64.b64decode(file_data)
            tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
            tmp_input.write(file_bytes)
            tmp_input.close()
            input_docx_path = tmp_input.name
            temp_files.append(input_docx_path)
        elif sample_name:
            input_docx_path = os.path.join(ROOT_DIR, sample_name)
        else:
            return {"statusCode": 400, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": "No input file provided"})}

        market_input = parse_docx(input_docx_path)
        if not market_input:
            return {"statusCode": 422, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": "Failed to parse DOCX"})}

        ai_content = None
        api_key = config.get("openrouter_api_key", os.environ.get("OPENROUTER_API_KEY", ""))
        if use_api and api_key:
            model_name = config.get("model") or os.environ.get("MODEL") or "openrouter/free"
            generator = AIGenerator(api_key=api_key, model=model_name)
            ai_content = generator.generate(market_input.market_name, market_input.market_name_title, market_input.custom_sections)

        if not ai_content:
            ai_content = _get_fallback_content(market_input)

        payload = build_payload(ai_content, market_input)
        placeholder_dict = payload_to_dict(payload)

        template_path = os.path.join(ROOT_DIR, config.get("template_file", "full_market_report_template_updated.docx"))
        tmp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp_output_path = tmp_output.name
        tmp_output.close()
        temp_files.append(tmp_output_path)

        render_report(template_path, placeholder_dict, tmp_output_path, adjust_cover_title=market_input.cover_title_truncated)

        with open(tmp_output_path, "rb") as f:
            output_bytes = f.read()

        docx_b64 = base64.b64encode(output_bytes).decode("utf-8")
        download_filename = f"report_{sanitize_filename(market_input.market_name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "success": True,
                "market_name": market_input.market_name,
                "filename": download_filename,
                "docx_base64": docx_b64,
                "audit_json": {
                    "market_name": market_input.market_name,
                    "generated_at": datetime.now().isoformat(),
                    "ai_content": ai_content,
                    "payload": placeholder_dict,
                }
            }),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"statusCode": 500, "headers": {"Content-Type": "application/json"}, "body": json.dumps({"error": str(e)})}

    finally:
        for p in temp_files:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


class LocalDevHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_OPTIONS(self):
        if self.path.startswith("/api/") or "generate" in self.path:
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()
        else:
            super().do_OPTIONS()

    def do_GET(self):
        if "generate" in self.path:
            res = handle_api_request("GET", "")
            self._send_res(res)
        else:
            super().do_GET()

    def do_POST(self):
        if "generate" in self.path:
            content_length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(content_length)
            res = handle_api_request("POST", body_bytes.decode("utf-8"))
            self._send_res(res)
        else:
            self.send_error(404, "Endpoint not found")

    def _send_res(self, res):
        self.send_response(res.get("statusCode", 200))
        for k, v in res.get("headers", {}).items():
            self.send_header(k, v)
        self.end_headers()
        body = res.get("body", "")
        self.wfile.write(body.encode("utf-8") if isinstance(body, str) else body)


def main():
    print("=" * 60)
    print(f"MARKETIQ LOCAL DEV SERVER: http://localhost:{PORT}")
    print("=" * 60)
    with socketserver.TCPServer(("", PORT), LocalDevHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
