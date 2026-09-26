"""
AI Generator module for OpenRouter API integration.
Single-pass content generation for the 16-chapter template (30 data-only fields).
Preserves and incorporates user-provided segmentations from input documents.
"""

import json
import time
import re
from typing import Dict, Any, Optional, List
from openai import OpenAI


LENGTH_LIMITS = {
    "type_segment_1": 30,
    "type_segment_2": 35,
    "type_segment_3": 50,
    "tech_segment_1": 30,
    "tech_segment_2": 30,
    "tech_segment_3": 40,
    "app_segment_1": 30,
    "app_segment_2": 30,
    "app_segment_3": 30,
    "app_segment_4": 30,
    "co1_name": 20,
    "co2_name": 20,
    "co3_name": 20,
    "co4_name": 30,
    "co5_name": 15,
    "co6_name": 15,
    "co7_name": 20,
    "co8_name": 15,
    "co9_name": 15,
    "co10_name": 15,
    "co1_segment_1_name": 50,
    "co1_segment_2_name": 50,
    "segment5_marketshare1": 30,
    "segment5_marketshare2": 30,
    "segment5_marketshare3": 30,
    "segment5_marketshare4": 30,
    "segment6_marketshare1": 30,
    "segment6_marketshare2": 30,
    "segment6_marketshare3": 30,
    "segment6_marketshare4": 30,
    "seg4_name": 30,
    "seg4_sub1": 30,
    "seg4_sub2": 30,
    "seg4_sub3": 30,
    "seg5_name": 30,
    "seg5_sub1": 30,
    "seg5_sub2": 30,
    "seg5_sub3": 30,
    "seg6_name": 30,
    "seg6_sub1": 30,
    "seg6_sub2": 30,
    "seg6_sub3": 30,
    "ch4_custom_subsection_4_1_title": 50,
}


def truncate_text(text: str, max_length: int) -> str:
    if not text:
        return text
    text = str(text).strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].strip() + "..."


def validate_and_truncate_content(content: Dict[str, Any]) -> Dict[str, Any]:
    validated = {}
    for key, value in content.items():
        if key in LENGTH_LIMITS and isinstance(value, str):
            validated[key] = truncate_text(value, LENGTH_LIMITS[key])
        else:
            validated[key] = value
    return validated


def extract_core_product_name(raw_name: str) -> str:
    words_to_remove = [
        "Global ",
        "Market ",
        "Segmentation ",
        "Industry ",
        "Analysis ",
        "Overview ",
    ]
    core_name = raw_name
    for word in words_to_remove:
        core_name = core_name.replace(word, "")

    if not core_name.strip():
        parts = raw_name.split()
        core_name = " ".join(parts[:2]) if len(parts) > 1 else raw_name

    return core_name.strip()


class AIGenerator:
    """Handles content generation via OpenRouter API with full input segment context."""

    def __init__(
        self,
        api_key: str,
        model: str = "nvidia/nemotron-3-nano-30b-a3b:free",
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def generate(
        self,
        market_name: str,
        market_name_title: str = "",
        custom_sections: Optional[list] = None,
        parsed_segments: Optional[list] = None,
    ) -> Optional[Dict[str, Any]]:
        if not market_name_title:
            market_name_title = market_name.title()

        prompt = self._build_prompt(market_name, market_name_title, parsed_segments)

        for attempt in range(self.max_retries):
            try:
                print(f"Generating content for {market_name} (attempt {attempt + 1})...")

                response = self.client.chat.completions.create(
                    model=self.model, messages=[{"role": "user", "content": prompt}]
                )

                message_content = response.choices[0].message.content
                content = str(message_content).strip() if message_content else ""

                parsed = self._parse_response(content)

                if parsed:
                    validated = validate_and_truncate_content(parsed)
                    return validated

            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return self._get_fallback_content(market_name, market_name_title, parsed_segments)

            except Exception as e:
                print(f"API error: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return self._get_fallback_content(market_name, market_name_title, parsed_segments)

        return self._get_fallback_content(market_name, market_name_title, parsed_segments)

    def _build_prompt(
        self,
        market_name: str,
        market_name_title: str,
        parsed_segments: Optional[list] = None,
    ) -> str:
        core = extract_core_product_name(market_name_title)

        segment_context = ""
        if parsed_segments:
            segment_context = "\n=== EXTRACTED INPUT SEGMENTATIONS FROM USER DOCUMENT ===\n"
            for seg in parsed_segments:
                seg_name = seg.get("name", "Segment")
                subs = seg.get("sub_segments", [])
                segment_context += f"- Dimension: {seg_name} -> Sub-segments: {', '.join(subs)}\n"

        return f"""You are generating structured data fields for a {core} market report template. The template has hardcoded narrative — you only need to supply short labels and names.

INPUT MARKET: "{market_name_title}"
CORE PRODUCT: "{core}"
{segment_context}

Generate a JSON object with these fields (all short strings, max lengths noted).

CRITICAL INSTRUCTION FOR SEGMENTS:
You MUST map the actual EXTRACTED INPUT SEGMENTATIONS listed above directly to the output fields.
- Use the sub-segments from the 1st input dimension for type_segment_1, type_segment_2, type_segment_3.
- Use the sub-segments from the 2nd input dimension for tech_segment_1, tech_segment_2, tech_segment_3.
- Use the sub-segments from the 3rd input dimension (e.g., Application: Drawing, Writing, Sketching, Carpentry) for app_segment_1, app_segment_2, app_segment_3, app_segment_4.
- Use the 4th, 5th, 6th input dimensions for seg4_name/sub1..3, seg5_name/sub1..3, seg6_name/sub1..3.
Do NOT invent generic placeholders (like "Standard Grade", "Type 1", "Tech 1") when actual segmentations are provided in the input document above!

=== SEGMENT NAMES (for charts and tables) ===
type_segment_1 (max 30 chars): First sub-segment of type/product dimension.
type_segment_2 (max 35 chars): Second sub-segment of type/product dimension.
type_segment_3 (max 50 chars): Third sub-segment of type/product dimension.
tech_segment_1 (max 30 chars): First sub-segment of technology dimension.
tech_segment_2 (max 30 chars): Second sub-segment of technology dimension.
tech_segment_3 (max 40 chars): Third sub-segment of technology dimension.
app_segment_1 (max 30 chars): First sub-segment of application dimension.
app_segment_2 (max 30 chars): Second sub-segment of application dimension.
app_segment_3 (max 30 chars): Third sub-segment of application dimension.
app_segment_4 (max 30 chars): Fourth sub-segment of application dimension.

=== COMPANY NAMES (real top companies in the {core} industry) ===
co1_name (max 20 chars): Top company in the {core} industry.
co2_name (max 20 chars): Second company.
co3_name (max 20 chars): Third company.
co4_name (max 30 chars): Fourth company.
co5_name (max 15 chars): Fifth company.
co6_name (max 15 chars): Sixth company.
co7_name (max 20 chars): Seventh company.
co8_name (max 15 chars): Eighth company.
co9_name (max 15 chars): Ninth company.
co10_name (max 15 chars): Tenth company.

=== CO1 SEGMENT NAMES ===
co1_segment_1_name (max 50 chars): Primary business segment for {core}.
co1_segment_2_name (max 50 chars): Secondary business segment for {core}.

=== SEGMENT 4/5/6 NAMES AND SUB-SEGMENTS ===
seg4_name (max 30 chars): Name of the 4th segmentation dimension from input document.
seg4_sub1 (max 30 chars): First sub-segment within seg4.
seg4_sub2 (max 30 chars): Second sub-segment within seg4.
seg4_sub3 (max 30 chars): Third sub-segment within seg4.
seg5_name (max 30 chars): Name of the 5th segmentation dimension from input document.
seg5_sub1 (max 30 chars): First sub-segment within seg5.
seg5_sub2 (max 30 chars): Second sub-segment within seg5.
seg5_sub3 (max 30 chars): Third sub-segment within seg5.
seg6_name (max 30 chars): Name of the 6th segmentation dimension from input document.
seg6_sub1 (max 30 chars): First sub-segment within seg6.
seg6_sub2 (max 30 chars): Second sub-segment within seg6.
seg6_sub3 (max 30 chars): Third sub-segment within seg6.

=== MARKET SHARE LABELS ===
segment5_marketshare1 (max 30 chars): Label for seg5 market share chart.
segment5_marketshare2 (max 30 chars): Label for seg5 market share chart.
segment5_marketshare3 (max 30 chars): Label for seg5 market share chart.
segment5_marketshare4 (max 30 chars): Label for seg5 market share chart.
segment6_marketshare1 (max 30 chars): Label for seg6 market share chart.
segment6_marketshare2 (max 30 chars): Label for seg6 market share chart.
segment6_marketshare3 (max 30 chars): Label for seg6 market share chart.
segment6_marketshare4 (max 30 chars): Label for seg6 market share chart.

=== CUSTOM SECTION ===
ch4_custom_subsection_4_1_title (max 50 chars): Title for custom subsection 4.1.

Return ONLY valid JSON with these exact keys, starting with {{ and ending with }}. No markdown, no explanation."""

    def _parse_response(self, content: str) -> Optional[Dict[str, Any]]:
        json_str = content.strip()

        if "```" in content:
            parts = content.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("{"):
                    json_str = part
                    break

        if not json_str.startswith("{"):
            start = json_str.find("{")
            if start != -1:
                json_str = json_str[start:]

        last_brace = json_str.rfind("}")
        if last_brace != -1:
            json_str = json_str[: last_brace + 1]

        return json.loads(json_str)

    def _get_fallback_content(
        self,
        market_name: str,
        market_name_title: str,
        parsed_segments: Optional[list] = None,
    ) -> Dict[str, Any]:
        print(f"Using input-derived fallback content for {market_name}")
        core = extract_core_product_name(market_name_title)
        segments = parsed_segments or []

        def _get_sub(seg_idx: int, sub_idx: int, fallback: str) -> str:
            if len(segments) > seg_idx:
                subs = segments[seg_idx].get("sub_segments", [])
                if len(subs) > sub_idx:
                    return subs[sub_idx]
            return fallback

        def _get_seg_name(seg_idx: int, fallback: str) -> str:
            if len(segments) > seg_idx:
                return segments[seg_idx].get("name", fallback)
            return fallback

        return {
            "type_segment_1": _get_sub(0, 0, f"{core} Type 1"),
            "type_segment_2": _get_sub(0, 1, f"{core} Type 2"),
            "type_segment_3": _get_sub(0, 2, f"{core} Type 3"),
            "tech_segment_1": _get_sub(1, 0, f"{core} Tech 1"),
            "tech_segment_2": _get_sub(1, 1, f"{core} Tech 2"),
            "tech_segment_3": _get_sub(1, 2, f"{core} Tech 3"),
            "app_segment_1": _get_sub(2, 0, f"{core} App 1"),
            "app_segment_2": _get_sub(2, 1, f"{core} App 2"),
            "app_segment_3": _get_sub(2, 2, f"{core} App 3"),
            "app_segment_4": _get_sub(2, 3, _get_sub(2, 0, f"{core} App 4")),
            "co1_name": f"Global {core} Leaders",
            "co2_name": f"{core} Innovations Inc",
            "co3_name": f"Apex {core} Solutions",
            "co4_name": f"Prime {core} Corp",
            "co5_name": f"Vanguard {core}",
            "co6_name": f"United {core}",
            "co7_name": f"International {core}",
            "co8_name": f"Strategic {core}",
            "co9_name": f"Pioneer {core}",
            "co10_name": f"Global {core} Enterprise",
            "co1_segment_1_name": f"Core {core} Products",
            "co1_segment_2_name": f"{core} Services & Accessories",
            "seg4_name": _get_seg_name(3, f"{core} Segment 4"),
            "seg4_sub1": _get_sub(3, 0, "Sub-Segment 1"),
            "seg4_sub2": _get_sub(3, 1, "Sub-Segment 2"),
            "seg4_sub3": _get_sub(3, 2, "Sub-Segment 3"),
            "seg5_name": _get_seg_name(4, f"{core} Segment 5"),
            "seg5_sub1": _get_sub(4, 0, "Sub-Segment 1"),
            "seg5_sub2": _get_sub(4, 1, "Sub-Segment 2"),
            "seg5_sub3": _get_sub(4, 2, "Sub-Segment 3"),
            "segment5_marketshare1": _get_sub(4, 0, "Sub-Segment 1"),
            "segment5_marketshare2": _get_sub(4, 1, "Sub-Segment 2"),
            "segment5_marketshare3": _get_sub(4, 2, "Sub-Segment 3"),
            "segment5_marketshare4": _get_sub(4, 3, _get_sub(4, 0, "Sub-Segment 4")),
            "seg6_name": _get_seg_name(5, f"{core} Segment 6"),
            "seg6_sub1": _get_sub(5, 0, "Sub-Segment 1"),
            "seg6_sub2": _get_sub(5, 1, "Sub-Segment 2"),
            "seg6_sub3": _get_sub(5, 2, "Sub-Segment 3"),
            "segment6_marketshare1": _get_sub(5, 0, "Sub-Segment 1"),
            "segment6_marketshare2": _get_sub(5, 1, "Sub-Segment 2"),
            "segment6_marketshare3": _get_sub(5, 2, "Sub-Segment 3"),
            "segment6_marketshare4": _get_sub(5, 3, _get_sub(5, 0, "Sub-Segment 4")),
            "ch4_custom_subsection_4_1_title": f"Strategic Analysis of {core} Market Opportunities",
        }
