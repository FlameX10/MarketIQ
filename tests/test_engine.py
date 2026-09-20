import unittest
import os
import sys
import base64
import json
import zipfile
import tempfile

# Ensure root directory is in sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.parser import parse_docx, MarketInput
from src.ai_generator import (
    AIGenerator,
    truncate_text,
    validate_and_truncate_content,
    extract_core_product_name,
)
from src.payload_builder import build_payload, payload_to_dict
from src.renderer import render_report
from netlify.functions.generate import handler as netlify_handler


class TestParser(unittest.TestCase):
    def test_parse_bess(self):
        sample_path = os.path.join(ROOT_DIR, "Global_BESS_Market_Segmentation.docx")
        self.assertTrue(os.path.exists(sample_path), "Sample BESS file missing")
        result = parse_docx(sample_path)
        self.assertIsNotNone(result)
        self.assertIn("Battery Energy Storage System", result.market_name)
        self.assertGreater(len(result.parsed_segments), 0)
        self.assertGreater(len(result.parsed_regions), 0)
        self.assertGreater(len(result.parsed_players), 0)

    def test_parse_screw(self):
        sample_path = os.path.join(ROOT_DIR, "Global_Screw_Market_Segmentation.docx")
        self.assertTrue(os.path.exists(sample_path), "Sample Screw file missing")
        result = parse_docx(sample_path)
        self.assertIsNotNone(result)
        self.assertIn("Screw", result.market_name)

    def test_parse_soda(self):
        sample_path = os.path.join(ROOT_DIR, "Global_Soda_Market_Segmentation.docx")
        self.assertTrue(os.path.exists(sample_path), "Sample Soda file missing")
        result = parse_docx(sample_path)
        self.assertIsNotNone(result)
        self.assertIn("Soda", result.market_name)


class TestAIGeneratorUtils(unittest.TestCase):
    def test_truncate_text(self):
        self.assertEqual(truncate_text("Short text", 20), "Short text")
        self.assertEqual(truncate_text("This is a very long text that exceeds limit", 15), "This is a ve...")

    def test_extract_core_product_name(self):
        self.assertEqual(
            extract_core_product_name("Global Battery Energy Storage System Market Segmentation"),
            "Battery Energy Storage System",
        )

    def test_validate_and_truncate_content(self):
        sample_dict = {
            "type_segment_1": "A" * 100,  # Limit is 30
            "custom_key": "Normal text",
        }
        validated = validate_and_truncate_content(sample_dict)
        self.assertEqual(len(validated["type_segment_1"]), 30)
        self.assertTrue(validated["type_segment_1"].endswith("..."))
        self.assertEqual(validated["custom_key"], "Normal text")


class TestPayloadBuilder(unittest.TestCase):
    def test_payload_builder(self):
        market_input = MarketInput(
            market_name="Battery Energy Storage System",
            market_name_title="Battery Energy Storage System Market",
            market_name_upper="BATTERY ENERGY STORAGE SYSTEM",
            market_product_name="Battery Energy Storage System",
        )
        ai_content = {
            "type_segment_1": "Lithium-ion",
            "co1_name": "Tesla",
        }
        payload = build_payload(ai_content, market_input)
        dict_payload = payload_to_dict(payload)

        self.assertEqual(dict_payload["{{market_name}}"], "Battery Energy Storage System")
        self.assertEqual(dict_payload["{{co1_name_upper}}"], "TESLA")
        self.assertEqual(dict_payload["{{type_segment_1}}"], "Lithium-ion")


class TestRenderer(unittest.TestCase):
    def test_render_docx_template(self):
        template_path = os.path.join(ROOT_DIR, "full_market_report_template_updated.docx")
        self.assertTrue(os.path.exists(template_path), "Template docx missing")

        placeholders = {
            "{{market_name}}": "Test Battery System",
            "{{market_name_upper}}": "TEST BATTERY SYSTEM",
            "{{MARKET_NAME_UPPER}}": "TEST BATTERY SYSTEM",
        }

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            output_path = tmp.name

        try:
            success = render_report(template_path, placeholders, output_path, adjust_cover_title=False)
            self.assertTrue(success, "DOCX rendering failed")
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 1000)

            # Verify rendered docx is valid zip archive containing word/document.xml
            with zipfile.ZipFile(output_path, "r") as zip_ref:
                namelist = zip_ref.namelist()
                self.assertIn("word/document.xml", namelist)
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestNetlifyServerlessHandler(unittest.TestCase):
    def test_handler_get_samples(self):
        event = {"httpMethod": "GET"}
        res = netlify_handler(event, None)
        self.assertEqual(res["statusCode"], 200)
        body = json.loads(res["body"])
        self.assertEqual(body["status"], "online")
        self.assertIn("samples", body)
        self.assertGreater(len(body["samples"]), 0)

    def test_handler_post_sample(self):
        payload = {
            "sample_name": "Global_BESS_Market_Segmentation.docx",
            "use_api": False
        }
        event = {
            "httpMethod": "POST",
            "body": json.dumps(payload),
            "isBase64Encoded": False
        }
        res = netlify_handler(event, None)
        self.assertEqual(res["statusCode"], 200)
        body = json.loads(res["body"])
        self.assertTrue(body["success"])
        self.assertIn("docx_base64", body)
        self.assertTrue(body["docx_base64"].startswith("UEsDB"))  # Zip header PK..

        # Validate decoded docx binary
        docx_bytes = base64.b64decode(body["docx_base64"])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            tmp.write(docx_bytes)
            tmp_path = tmp.name

        try:
            with zipfile.ZipFile(tmp_path, "r") as zip_ref:
                self.assertIn("word/document.xml", zip_ref.namelist())
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_handler_post_file_upload(self):
        sample_path = os.path.join(ROOT_DIR, "Global_Screw_Market_Segmentation.docx")
        with open(sample_path, "rb") as f:
            file_b64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "file_data": file_b64,
            "filename": "Global_Screw_Market_Segmentation.docx",
            "use_api": False
        }
        event = {
            "httpMethod": "POST",
            "body": json.dumps(payload),
            "isBase64Encoded": False
        }
        res = netlify_handler(event, None)
        self.assertEqual(res["statusCode"], 200)
        body = json.loads(res["body"])
        self.assertTrue(body["success"])
        self.assertIn("Screw", body["market_name"])


if __name__ == "__main__":
    unittest.main()
