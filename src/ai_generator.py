"""
AI Generator module for OpenRouter API integration.
Single-pass content generation for the 16-chapter template (30 data-only fields).
"""

import json
import time
import re
from typing import Dict, Any, Optional
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
        "Global",
        "Market",
        "Segmentation",
        "Industry",
        "Analysis",
        "Overview",
    ]
    core_name = raw_name
    for word in words_to_remove:
        # Use regex pattern to replace whole word
        core_name = re.sub(rf"\b{re.escape(word)}\b", "", core_name, flags=re.IGNORECASE)

    core_name = " ".join(core_name.split())

    if not core_name.strip():
        parts = raw_name.split()
        core_name = " ".join(parts[:2]) if len(parts) > 1 else raw_name

    return core_name.strip()


class AIGenerator:
    """Handles content generation via OpenRouter API."""

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
    ) -> Optional[Dict[str, Any]]:
        if not market_name_title:
            market_name_title = market_name.title()

        prompt = self._build_prompt(market_name, market_name_title)

        for attempt in range(self.max_retries):
            try:
                print(f"Generating content for {market_name}...")

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
                    return self._get_fallback_content(market_name, market_name_title)

            except Exception as e:
                print(f"API error: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return self._get_fallback_content(market_name, market_name_title)

        return self._get_fallback_content(market_name, market_name_title)

    def _build_prompt(self, market_name: str, market_name_title: str) -> str:
        core = extract_core_product_name(market_name_title)

        return f"""You are generating structured data fields for a {core} market report template. The template has hardcoded narrative — you only need to supply short labels and names.

INPUT MARKET: "{market_name_title}"
CORE PRODUCT: "{core}"

Generate a JSON object with these fields (all short strings, max lengths noted). All values MUST be specific to the {core} market — do NOT copy the examples verbatim, they are only format illustrations.

=== SEGMENT NAMES (for charts and tables) ===
type_segment_1 (max 30 chars): Type-based segment 1 name.
type_segment_2 (max 35 chars): Type-based segment 2 name.
type_segment_3 (max 50 chars): Type-based segment 3 name.
tech_segment_1 (max 30 chars): Technology segment 1.
tech_segment_2 (max 30 chars): Technology segment 2.
tech_segment_3 (max 40 chars): Technology segment 3.
app_segment_1 (max 30 chars): Application segment 1.
app_segment_2 (max 30 chars): Application segment 2.
app_segment_3 (max 30 chars): Application segment 3.
app_segment_4 (max 30 chars): Application segment 4.

=== COMPANY NAMES (real companies from the {core} industry) ===
co1_name (max 20 chars): Top company in the {core} industry.
co2_name (max 20 chars): Second major company in the {core} industry.
co3_name (max 20 chars): Third company.
co4_name (max 30 chars): Fourth company.
co5_name (max 15 chars): Fifth company.
co6_name (max 15 chars): Sixth company.
co7_name (max 20 chars): Seventh company.
co8_name (max 15 chars): Eighth company.
co9_name (max 15 chars): Ninth company.
co10_name (max 15 chars): Tenth company.

=== CO1 SEGMENT NAMES (for co1 revenue breakdown chart) ===
co1_segment_1_name (max 50 chars): Primary business segment for {core}. Must be a real product or service category within the {core} market.
co1_segment_2_name (max 50 chars): Secondary business segment for {core}.

=== SEGMENT 4/5/6 NAMES AND SUB-SEGMENTS (additional segmentation dimensions) ===
seg4_name (max 30 chars): Name of the 4th market segmentation dimension. Must NOT be "Type", "Technology", or "Application".
seg4_sub1 (max 30 chars): First sub-segment within seg4.
seg4_sub2 (max 30 chars): Second sub-segment within seg4.
seg4_sub3 (max 30 chars): Third sub-segment within seg4.
seg5_name (max 30 chars): Name of the 5th market segmentation dimension. Must NOT be "Type", "Technology", or "Application".
seg5_sub1 (max 30 chars): First sub-segment within seg5.
seg5_sub2 (max 30 chars): Second sub-segment within seg5.
seg5_sub3 (max 30 chars): Third sub-segment within seg5.
seg6_name (max 30 chars): Name of the 6th market segmentation dimension. Must NOT be "Type", "Technology", or "Application".
seg6_sub1 (max 30 chars): First sub-segment within seg6.
seg6_sub2 (max 30 chars): Second sub-segment within seg6.
seg6_sub3 (max 30 chars): Third sub-segment within seg6.

=== MARKET SHARE LABELS (for pie/bar chart data labels) ===
segment5_marketshare1 (max 30 chars): First sub-segment label for the seg5 market share chart.
segment5_marketshare2 (max 30 chars): Second sub-segment label.
segment5_marketshare3 (max 30 chars): Third sub-segment label.
segment5_marketshare4 (max 30 chars): Fourth sub-segment label.
segment6_marketshare1 (max 30 chars): First sub-segment label for the seg6 market share chart.
segment6_marketshare2 (max 30 chars): Second sub-segment label.
segment6_marketshare3 (max 30 chars): Third sub-segment label.
segment6_marketshare4 (max 30 chars): Fourth sub-segment label.

=== CUSTOM SECTION ===
ch4_custom_subsection_4_1_title (max 50 chars): Title for a custom subsection (Chapter 4, Section 4.1).

IMPORTANT: ALL values must be realistic for the {core} market. Do NOT use generic placeholders or industry-hopping from other sectors. Research real products, companies, and categories in the {core} industry.

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
        self, market_name: str, market_name_title: str
    ) -> Dict[str, Any]:
        print(f"Using fallback content for {market_name}")

        core = extract_core_product_name(market_name_title)

        return {
            "type_segment_1": f"{core} Standard Grade",
            "type_segment_2": f"{core} Premium Grade",
            "type_segment_3": f"{core} Specialized Grade",
            "tech_segment_1": "Advanced Automated Processing",
            "tech_segment_2": "NextGen Manufacturing",
            "tech_segment_3": "High-Efficiency Production",
            "app_segment_1": "Industrial Applications",
            "app_segment_2": "Commercial Sector",
            "app_segment_3": "Residential Sector",
            "app_segment_4": "Specialty Applications",
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
            "segment5_marketshare1": "Direct Enterprise Sales",
            "segment5_marketshare2": "Distributor Network",
            "segment5_marketshare3": "Online Channels",
            "segment6_marketshare1": "Premium Material",
            "segment6_marketshare2": "Standard Material",
            "segment6_marketshare3": "Composite Material",
            "segment6_marketshare4": "Eco-friendly Material",
            "seg4_name": "End User",
            "seg4_sub1": "Industrial End Users",
            "seg4_sub2": "Commercial End Users",
            "seg4_sub3": "Individual Consumers",
            "seg5_name": "Distribution Channel",
            "seg5_sub1": "Direct Enterprise Sales",
            "seg5_sub2": "Distributor Network",
            "seg5_sub3": "Online E-Commerce",
            "seg6_name": "Material",
            "seg6_sub1": "Premium Material",
            "seg6_sub2": "Standard Material",
            "seg6_sub3": "Composite Material",
            "ch4_custom_subsection_4_1_title": f"Strategic Analysis of {core} Market Opportunities",
        }
