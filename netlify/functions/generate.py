import json
import base64
import os
import sys
import tempfile
import traceback
from datetime import datetime

# Dynamic multi-path resolution for Netlify deployment environment
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
GRANDPARENT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
CWD_DIR = os.getcwd()

for p in [CURRENT_DIR, PARENT_DIR, GRANDPARENT_DIR, CWD_DIR]:
    if p and p not in sys.path and os.path.exists(p):
        sys.path.insert(0, p)

ROOT_DIR = GRANDPARENT_DIR
if not os.path.exists(os.path.join(ROOT_DIR, "src")) and os.path.exists(os.path.join(CWD_DIR, "src")):
    ROOT_DIR = CWD_DIR

from src.parser import parse_docx
from src.ai_generator import AIGenerator
from src.payload_builder import build_payload, payload_to_dict
from src.renderer import render_report
from run import load_config, _get_fallback_content, sanitize_filename


def get_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Content-Type": "application/json",
    }


def handler(event, context):
    http_method = event.get("httpMethod", "GET")

    # Handle CORS preflight request
    if http_method == "OPTIONS":
        return {"statusCode": 200, "headers": get_headers(), "body": ""}

    if http_method == "GET":
        # Return list of sample files available in root
        samples = []
        for file in os.listdir(ROOT_DIR):
            if file.endswith(".docx") and not file.startswith("~$") and "template" not in file.lower():
                samples.append(file)
        
        return {
            "statusCode": 200,
            "headers": get_headers(),
            "body": json.dumps({
                "status": "online",
                "service": "Market Report Generator API",
                "samples": samples
            })
        }

    if http_method != "POST":
        return {
            "statusCode": 405,
            "headers": get_headers(),
            "body": json.dumps({"error": "Method not allowed"})
        }

    temp_files_to_clean = []

    try:
        raw_body = event.get("body", "")
        if event.get("isBase64Encoded", False):
            raw_body = base64.b64decode(raw_body).decode("utf-8")

        body_data = json.loads(raw_body) if raw_body else {}

        file_data = body_data.get("file_data")
        sample_name = body_data.get("sample_name")
        use_api = body_data.get("use_api", True)
        custom_api_key = body_data.get("api_key")

        config_path = os.path.join(ROOT_DIR, "config.json")
        config = load_config(config_path)

        if custom_api_key:
            config["openrouter_api_key"] = custom_api_key

        input_docx_path = None

        if file_data:
            # Decode base64 file upload
            file_bytes = base64.b64decode(file_data)
            tmp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
            tmp_input.write(file_bytes)
            tmp_input.close()
            input_docx_path = tmp_input.name
            temp_files_to_clean.append(input_docx_path)
        elif sample_name:
            # Use predefined sample file from workspace
            sample_path = os.path.join(ROOT_DIR, sample_name)
            if not os.path.exists(sample_path):
                return {
                    "statusCode": 404,
                    "headers": get_headers(),
                    "body": json.dumps({"error": f"Sample file '{sample_name}' not found"})
                }
            input_docx_path = sample_path
        else:
            return {
                "statusCode": 400,
                "headers": get_headers(),
                "body": json.dumps({"error": "No file_data or sample_name provided"})
            }

        # Step 1: Parse input DOCX
        market_input = parse_docx(input_docx_path)
        if not market_input:
            return {
                "statusCode": 422,
                "headers": get_headers(),
                "body": json.dumps({"error": "Failed to parse input DOCX file"})
            }

        # Step 2: Generate content via AI or Fallback
        ai_content = None
        api_key = config.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY", "")

        if use_api and api_key:
            # Call OpenRouter API if valid key present
            generator = AIGenerator(
                api_key=api_key,
                model=config.get("model", "nvidia/nemotron-3-nano-30b-a3b:free"),
                max_retries=config.get("max_retries", 3),
                retry_delay=config.get("retry_delay", 2),
            )
            ai_content = generator.generate(
                market_input.market_name,
                market_input.market_name_title,
                market_input.custom_sections,
            )

        if not ai_content:
            ai_content = _get_fallback_content(market_input)

        # Step 3: Build payload and render template DOCX
        payload = build_payload(ai_content, market_input)
        placeholder_dict = payload_to_dict(payload)

        # Template path resolution
        template_rel = config.get("template_file", "full_market_report_template_updated.docx")
        template_path = os.path.join(ROOT_DIR, template_rel)
        if not os.path.exists(template_path):
            template_path = os.path.join(ROOT_DIR, "templates", "master_template_v1.docx")

        tmp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
        tmp_output_path = tmp_output.name
        tmp_output.close()
        temp_files_to_clean.append(tmp_output_path)

        adjust_cover = market_input.cover_title_truncated
        success = render_report(
            template_path, placeholder_dict, tmp_output_path, adjust_cover_title=adjust_cover
        )

        if not success:
            return {
                "statusCode": 500,
                "headers": get_headers(),
                "body": json.dumps({"error": "Failed to render target DOCX document"})
            }

        # Read rendered output into memory
        with open(tmp_output_path, "rb") as f:
            output_bytes = f.read()

        docx_b64 = base64.b64encode(output_bytes).decode("utf-8")
        safe_name = sanitize_filename(market_input.market_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_filename = f"report_{safe_name}_{timestamp}.docx"

        audit_data = {
            "market_name": market_input.market_name,
            "market_name_upper": market_input.market_name_upper,
            "generated_at": datetime.now().isoformat(),
            "api_model": config.get("model"),
            "ai_content": ai_content,
            "payload": placeholder_dict,
        }

        return {
            "statusCode": 200,
            "headers": get_headers(),
            "body": json.dumps({
                "success": True,
                "market_name": market_input.market_name,
                "filename": download_filename,
                "docx_base64": docx_b64,
                "audit_json": audit_data
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": get_headers(),
            "body": json.dumps({
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        }

    finally:
        for p in temp_files_to_clean:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
