"""
Parser module for extracting market information from input DOCX files.
Extracts segments, regions, countries, key players, and custom requirements.
"""

import zipfile
import re
import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from xml.etree import ElementTree as ET

try:
    import docx as python_docx

    PYTHON_DOCX_AVAILABLE = True
except ImportError:
    PYTHON_DOCX_AVAILABLE = False


@dataclass
class MarketInput:
    """Structured market data extracted from input DOCX."""

    market_name: str
    market_name_title: str
    market_name_upper: str
    market_product_name: str
    cover_title_truncated: bool = False

    base_year: str = "2024"
    forecast_start_year: str = "2025"
    forecast_end_year: str = "2035"
    outlook_period: str = "2025 – 2030"
    data_source_year: str = "2025"
    report_geography: str = "Global"
    report_type_label: str = "MARKET INTELLIGENCE REPORT"
    report_subtitle: str = "Production Technologies, Equipment & Supplier Landscape"
    company_name: str = "NextGen Intelligence Stats and Consulting LLP"
    history_start_year: str = "2020"

    # Structured segments: list of (segment_dimension_name, [sub_segment_names])
    # e.g. [("Battery Type", ["Lithium-ion", "Lead-acid", ...]), ...]
    parsed_segments: List[Dict[str, Any]] = field(default_factory=list)

    # Regions: list of region names in order
    parsed_regions: List[str] = field(default_factory=list)

    # Countries for region 1
    parsed_region1_countries: List[str] = field(default_factory=list)

    # Key players in order
    parsed_players: List[str] = field(default_factory=list)

    # Custom requirements (Chapter 4 custom sections)
    custom_sections: List[Dict[str, str]] = field(default_factory=list)


def extract_text_from_element(element: ET.Element, namespaces: Dict[str, str]) -> str:
    """Extract all text from w:t elements within an XML element."""
    text_parts = []
    for t_elem in element.iter(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
    ):
        if t_elem.text:
            text_parts.append(t_elem.text)
    return "".join(text_parts)


def extract_core_product_name(raw_name: str) -> str:
    """
    Extract just the core product name from input like 'Toothbrush Market Segmentation'.

    Examples:
    - 'Toothbrush Market Segmentation' -> 'Toothbrush'
    - 'Facewash Market' -> 'Facewash'
    - 'Global Green Methanol Market' -> 'Green Methanol'
    - 'Sustainable Aviation Fuel Market' -> 'Sustainable Aviation Fuel'
    """
    if not raw_name:
        return raw_name

    name = raw_name

    # Remove parenthetical content: (USD Billion, 2025-2035)
    name = re.sub(r"\([^)]*\)", "", name)
    name = re.sub(r"\[[^\]]*\]", "", name)

    # Remove trailing numbers/dates
    name = re.sub(r"\s+\d{4}.*$", "", name)

    # Remove common prefix words - order matters (longer first)
    prefixes = [
        "Global ",
        "Worldwide ",
        "International ",
        "Regional ",
    ]
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix) :]

    # Filter out common non-product words
    words = name.split()
    non_product_words = [
        "Market",
        "Markets",
        "Segmentation",
        "Segment",
        "Industry",
        "Analysis",
        "Overview",
        "Report",
        "Study",
        "Research",
    ]

    core_words = []
    for word in words:
        if word in non_product_words:
            break
        core_words.append(word)

    if not core_words:
        core_words = words[:2] if len(words) >= 2 else words[:1]

    return " ".join(core_words).strip()


# Known region names for matching
KNOWN_REGIONS = [
    "North America",
    "Europe",
    "Asia-Pacific",
    "Asia Pacific",
    "South America",
    "Latin America",
    "Middle East & Africa",
    "Middle East and Africa",
    "MEA",
    "Africa",
    "APAC",
]


def parse_segmentation_docx_content(paragraphs) -> Dict[str, Any]:
    """
    Parse a list of paragraph objects (from python-docx) to extract:
    - market_title
    - segmentations: dict of {segment_name: [sub_segments]}
    - regions: dict of {region_name: [countries]}
    - key_players: list of player names
    - custom_requirements: list of requirement strings

    Returns a dict with all parsed info.
    """
    market_title = ""
    segmentations = {}  # OrderedDict of {seg_name: [sub_segs]}
    current_segment = None
    regions = {}
    current_region = None
    key_players = []
    custom_requirements = []

    state = "NONE"  # SEGMENT, REGION, PLAYERS, CUSTOM, OTHER

    for p in paragraphs:
        text = p.text.strip() if hasattr(p, "text") else ""
        if not text:
            continue

        style = p.style.name if (hasattr(p, "style") and p.style) else "Normal"

        # Heading 1 → market title
        if style in ("Heading 1",) or (
            not market_title and style.startswith("Heading")
        ):
            market_title = text
            continue

        # Heading 2 or section-like patterns
        is_heading2 = style == "Heading 2"
        is_by_section = text.startswith("By ")
        is_named_section = text in (
            "Key Players",
            "Custom Requirements",
            "Custom Requirement",
            "Custom Requirements:",
        )

        if is_heading2 or is_by_section or is_named_section:
            if text.startswith("By Region") or text == "By Region":
                state = "REGION"
                current_region = None
            elif text in ("Key Players", "Key Players:"):
                state = "PLAYERS"
            elif text in (
                "Custom Requirements",
                "Custom Requirement",
                "Custom Requirements:",
            ):
                state = "CUSTOM"
            elif text.startswith("By "):
                state = "SEGMENT"
                seg_name = text.replace("By ", "").strip().rstrip(":")
                current_segment = seg_name
                if current_segment not in segmentations:
                    segmentations[current_segment] = []
            else:
                state = "OTHER"
            continue

        # Parse based on state
        if state == "SEGMENT" and current_segment:
            if text and text not in segmentations[current_segment]:
                segmentations[current_segment].append(text)

        elif state == "PLAYERS":
            if text:
                key_players.append(text)

        elif state == "CUSTOM":
            if text:
                custom_requirements.append(text)

        elif state == "REGION":
            # Distinguish region names from country names
            if text in KNOWN_REGIONS:
                current_region = text
                regions[current_region] = []
            elif current_region:
                regions[current_region].append(text)

    return {
        "market_title": market_title,
        "segmentations": segmentations,
        "regions": regions,
        "key_players": key_players,
        "custom_requirements": custom_requirements,
    }


def parse_docx(docx_path: str) -> Optional[MarketInput]:
    """
    Parse input DOCX and extract market information, segmentations, regions,
    key players, and custom requirements.
    """
    if not docx_path or not os.path.exists(docx_path):
        if docx_path:
            print(f"Error: File not found: {docx_path}")
        return None

    try:
        parsed = {}

        if PYTHON_DOCX_AVAILABLE:
            # Use python-docx for richer style access
            import docx as python_docx_module

            doc = python_docx_module.Document(docx_path)
            parsed = parse_segmentation_docx_content(doc.paragraphs)
        else:
            # Fallback: use zipfile + XML
            with zipfile.ZipFile(docx_path, "r") as zf:
                document_xml = zf.read("word/document.xml").decode("utf-8")
                root = ET.fromstring(document_xml)
                body = root.find(
                    ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body"
                )
                if body is None:
                    print("Error: Could not find document body")
                    return None

                paragraphs_xml = body.findall(
                    ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
                )

                # Build minimal paragraph-like objects
                class SimplePara:
                    def __init__(self, text, style_name):
                        self.text = text
                        self.style = type("Style", (), {"name": style_name})()

                def get_style(para_el):
                    ns = (
                        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                    )
                    pStyle = para_el.find(f".//{ns}pStyle")
                    if pStyle is not None:
                        return pStyle.get(f"{ns}val", "Normal")
                    return "Normal"

                simple_paras = []
                for p_el in paragraphs_xml:
                    text = extract_text_from_element(p_el, {}).strip()
                    style_name = get_style(p_el)
                    simple_paras.append(SimplePara(text, style_name))

                parsed = parse_segmentation_docx_content(simple_paras)

        # Extract and process results
        raw_market_name = parsed.get("market_title", "")
        if not raw_market_name:
            # Fallback: try to extract from the filename
            import re as _re

            base = os.path.splitext(os.path.basename(docx_path))[0]
            # Remove common suffixes like "_segmentation", "-Segmentation", etc.
            base = _re.sub(
                r"[_\- ]*(segmentation|segment|input|template|market|report|data)$",
                "",
                base,
                flags=_re.IGNORECASE,
            )
            # Replace underscores/hyphens with spaces, title-case
            base = base.replace("_", " ").replace("-", " ").strip().title()
            raw_market_name = base if base else "Unknown Market"
            print(
                f"  Warning: No heading-style title found in DOCX. "
                f"Using filename-derived market name: '{raw_market_name}'"
            )

        core_product = extract_core_product_name(raw_market_name)
        needs_truncation = len(core_product) > 20

        # Build structured segments list (maintain insertion order)
        segmentations = parsed.get("segmentations", {})
        parsed_segments = []
        for seg_name, sub_segs in segmentations.items():
            parsed_segments.append(
                {
                    "name": seg_name,
                    "sub_segments": sub_segs[:6],  # cap at 6 sub-segments per dimension
                }
            )

        # Regions
        regions_dict = parsed.get("regions", {})
        region_names = list(regions_dict.keys())
        region1_countries = []
        if region_names:
            region1_countries = regions_dict[region_names[0]][:3]  # max 3 countries

        # Key players
        key_players = parsed.get("key_players", [])[:10]  # max 10

        # Custom requirements → custom sections for Chapter 4
        custom_reqs = parsed.get("custom_requirements", [])
        custom_sections = [{"title": r, "body": ""} for r in custom_reqs[:10]]

        print(f"  Detected segments: {[s['name'] for s in parsed_segments]}")
        print(f"  Detected regions: {region_names}")
        print(f"  Region 1 countries: {region1_countries}")
        print(f"  Key players ({len(key_players)}): {key_players[:5]}")
        print(f"  Custom requirements: {[s['title'] for s in custom_sections]}")

        market_input = MarketInput(
            market_name=core_product,
            market_name_title=core_product,
            market_name_upper=core_product.upper(),
            market_product_name=core_product,
            cover_title_truncated=needs_truncation,
            parsed_segments=parsed_segments,
            parsed_regions=region_names[:5],
            parsed_region1_countries=region1_countries,
            parsed_players=key_players,
            custom_sections=custom_sections,
        )

        print(
            f"  Extracted market name: '{core_product}' (from raw: '{raw_market_name}')"
        )
        return market_input

    except Exception as e:
        print(f"Error parsing DOCX: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    import sys

    print("Extraction tests:")
    tests = [
        "Toothbrush Market Segmentation (USD Billion, 2025-2035)",
        "Facewash Market Segmentation",
        "Global Green Methanol Market",
        "Sustainable Aviation Fuel Market Analysis",
        "Global Battery Energy Storage System Market Segmentation (USD Billion, 2025-2035)",
    ]
    for test in tests:
        result = extract_core_product_name(test)
        print(f"  '{test}' -> '{result}'")

    # Test filename-based fallback
    print()
    for fname in [
        "lithium_ion_battery_input.docx",
        "Global_Glycerin_Market_Segmentation.docx",
        "my_custom_data.docx",
        "input.docx",
    ]:
        base = os.path.splitext(os.path.basename(fname))[0]
        base = re.sub(
            r"[_\- ]*(segmentation|segment|input|template|market|report|data)$",
            "",
            base,
            flags=re.IGNORECASE,
        )
        base = base.replace("_", " ").replace("-", " ").strip().title()
        name = base if base else "Unknown Market"
        print(
            f"  '{fname}' -> filename fallback: '{name}' -> core: '{extract_core_product_name(name)}'"
        )

    print()
    if len(sys.argv) > 1:
        result = parse_docx(sys.argv[1])
        if result:
            print(f"\nParsed Result:")
            print(f"  Market Name: {result.market_name}")
            print(f"  Upper: {result.market_name_upper}")
            print(f"  Segments: {[s['name'] for s in result.parsed_segments]}")
            print(f"  Regions: {result.parsed_regions}")
            print(f"  Region 1 Countries: {result.parsed_region1_countries}")
            print(f"  Players: {result.parsed_players}")
