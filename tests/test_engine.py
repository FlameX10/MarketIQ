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
from src.validator import validate_payload



class TestValidator(unittest.TestCase):
    def test_validate_clean_payload(self):
        clean_payload = {
            "{{type_segment_1}}": "Porcelain Tiles",
            "{{seg4_name}}": "End User",
            "{{co1_name}}": "Tesla Energy",
        }
        is_valid, errors = validate_payload(clean_payload)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_validate_generic_placeholder_detection(self):
        bad_payload = {
            "{{type_segment_1}}": "Ceramic Tiles Type 1",
            "{{seg4_name}}": "Ceramic Tiles Segment 4",
            "{{co1_name}}": "FEATURED COMPANY",
            "{{url}}": "www.FEATURED COMPANY.com",
        }
        is_valid, errors = validate_payload(bad_payload)
        self.assertFalse(is_valid)
        self.assertGreaterEqual(len(errors), 3)


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
        self.assertIn("Stanley Black & Decker", result.parsed_players)

    def test_parse_soda(self):
        sample_path = os.path.join(ROOT_DIR, "Global_Soda_Market_Segmentation.docx")
        self.assertTrue(os.path.exists(sample_path), "Sample Soda file missing")
        result = parse_docx(sample_path)
        self.assertIsNotNone(result)
        self.assertIn("Soda", result.market_name)
        self.assertIn("The Coca-Cola Company", result.parsed_players)


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
            "type_segment_1": "A" * 100,
            "custom_key": "Normal text",
        }
        validated = validate_and_truncate_content(sample_dict)
        self.assertEqual(len(validated["type_segment_1"]), 30)
        self.assertTrue(validated["type_segment_1"].endswith("..."))
        self.assertEqual(validated["custom_key"], "Normal text")


class TestPayloadBuilder(unittest.TestCase):
    def test_payload_builder_semantic_flow(self):
        market_input = MarketInput(
            market_name="Ceramic Tiles",
            market_name_title="Ceramic Tiles Market",
            market_name_upper="CERAMIC TILES",
            market_product_name="Ceramic Tiles",
            parsed_segments=[
                {"name": "Tile Type", "sub_segments": ["Porcelain Tiles", "Glazed Ceramic", "Unglazed Ceramic"]},
                {"name": "Printing Technology", "sub_segments": ["Digital Printing", "Inkjet Printing", "Nano Coating"]},
                {"name": "Application", "sub_segments": ["Residential Flooring", "Commercial Buildings", "Industrial"]},
                {"name": "End User", "sub_segments": ["Homeowners", "Construction Companies", "Architects"]},
                {"name": "Distribution Channel", "sub_segments": ["Direct Sales", "Distributors", "Online Retail"]},
                {"name": "Material", "sub_segments": ["Clay-based", "Porcelain", "Stoneware"]},
            ],
            parsed_players=["Mohawk Industries", "RAK Ceramics", "SCG Ceramics", "Lamosa"],
            custom_sections=[{"title": "Impact of Raw Material Price Fluctuations", "body": ""}],
        )

        payload = build_payload({}, market_input)
        dict_payload = payload_to_dict(payload)

        self.assertEqual(dict_payload["{{type_segment_1}}"], "Porcelain Tiles")
        self.assertEqual(dict_payload["{{tech_segment_1}}"], "Digital Printing")
        self.assertEqual(dict_payload["{{app_segment_1}}"], "Residential Flooring")
        self.assertEqual(dict_payload["{{seg4_name}}"], "End User")
        self.assertEqual(dict_payload["{{seg4_sub1}}"], "Homeowners")
        self.assertEqual(dict_payload["{{seg5_name}}"], "Distribution Channel")
        self.assertEqual(dict_payload["{{seg5_sub1}}"], "Direct Sales")
        self.assertEqual(dict_payload["{{seg6_name}}"], "Material")
        self.assertEqual(dict_payload["{{seg6_sub1}}"], "Clay-based")
        self.assertEqual(dict_payload["{{co1_name}}"], "Mohawk Industries")
        self.assertEqual(dict_payload["{{ch4_custom_section_1_title}}"], "Impact of Raw Material Price Fluctuations")

        # Confirm validator passes on generated payload
        is_valid, errors = validate_payload(dict_payload)
        self.assertTrue(is_valid, f"Validation errors found: {errors}")


class TestRenderer(unittest.TestCase):
    def test_render_docx_template(self):
        template_path = os.path.join(ROOT_DIR, "full_market_report_template_updated.docx")
        self.assertTrue(os.path.exists(template_path), "Template docx missing")

        placeholders = {
            "{{market_name}}": "Ceramic Tiles",
            "{{market_name_upper}}": "CERAMIC TILES",
            "{{MARKET_NAME_UPPER}}": "CERAMIC TILES",
        }

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            output_path = tmp.name

        try:
            success = render_report(template_path, placeholders, output_path, adjust_cover_title=False)
            self.assertTrue(success, "DOCX rendering failed")
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 1000)

            with zipfile.ZipFile(output_path, "r") as zip_ref:
                self.assertIn("word/document.xml", zip_ref.namelist())
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


if __name__ == "__main__":
    unittest.main()
