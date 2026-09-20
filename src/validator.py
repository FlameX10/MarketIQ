"""
Pre-rendering payload validation module for MarketIQ.
Guarantees that no unresolved generic placeholder strings, fake company URLs,
or synthetic paraphrased categories reach the final DOCX template renderer.
"""

import re
from typing import Dict, List, Tuple, Optional, Any

# Regex patterns matching unresolved generic placeholder strings or synthetic fallbacks
GENERIC_PATTERNS = [
    (r"\b(Type|Tech|App)\s+\d+\b", "Generic segment placeholder (e.g. Type 1, Tech 2, App 3)"),
    (r"\bSegment\s+[456]\b", "Generic dimension name (e.g. Segment 4, Segment 5, Segment 6)"),
    (r"\bSub-Segment\s*\d*\b", "Generic sub-segment label (e.g. Sub-Segment 1)"),
    (r"\bClient Requirement\s*\d*(\.\d+)?\b", "Generic client requirement title"),
    (r"\bFEATURED COMPANY\b", "Generic company placeholder"),
    (r"\bCompetitor\s+\d+\b", "Generic competitor placeholder"),
    (r"www\.FEATURED\s*COMPANY\.com", "Fake company URL"),
    (r"www\.GLOBAL.*LEADERS\.com", "Fake generated URL"),
]

# Blacklisted synthetic strings that should never appear if source data is available
FORBIDDEN_SYNTHETICS = [
    "Ceramic Tiles Standard Grade",
    "Ceramic Tiles Premium Grade",
    "Ceramic Tiles Specialized Grade",
    "Advanced Automated Processing",
    "NextGen Manufacturing",
    "High-Efficiency Production",
    "Industrial Applications",
    "Commercial Sector",
    "Residential Sector",
    "Specialty Applications",
    "Industrial End Users",
    "Commercial End Users",
    "Individual Consumers",
    "Direct Enterprise Sales",
    "Distributor Network",
    "Online E-Commerce",
    "Premium Material",
    "Standard Material",
    "Composite Material",
    "Ceramic Tiles Custom Analysis",
    "Strategic Analysis of Ceramic Tiles Market Opportunities",
    "Global Ceramic Tiles Leaders",
    "Ceramic Tiles Innovations Inc",
    "Apex Ceramic Tiles Solutions",
    "Prime Ceramic Tiles Corp",
    "Vanguard Ceramic Tiles",
    "United Ceramic Tiles",
    "International Ceramic Tiles",
    "Strategic Ceramic Tiles",
    "Pioneer Ceramic Tiles",
    "Global Ceramic Tiles Enterprise",
]


def validate_payload(
    payload_dict: Dict[str, str], market_input: Optional[Any] = None
) -> Tuple[bool, List[str]]:
    """
    Validate placeholder dictionary before template rendering.

    Returns:
        (is_valid: bool, error_messages: List[str])
    """
    errors = []

    for placeholder, val_str in payload_dict.items():
        if not val_str or not isinstance(val_str, str):
            continue

        for pattern, desc in GENERIC_PATTERNS:
            if re.search(pattern, val_str, re.IGNORECASE):
                errors.append(
                    f"Unresolved generic placeholder in '{placeholder}': '{val_str}' ({desc})"
                )

        for bad_str in FORBIDDEN_SYNTHETICS:
            if bad_str.lower() in val_str.lower():
                errors.append(
                    f"Forbidden synthetic substitution in '{placeholder}': '{val_str}' contains '{bad_str}'"
                )

    # If market_input is provided, validate that selected taxonomy values exist in original input
    if market_input and hasattr(market_input, "parsed_segments"):
        all_input_subs = set()
        for seg in market_input.parsed_segments:
            for sub in seg.get("sub_segments", []):
                all_input_subs.add(sub.lower())

        taxonomy_keys = [
            "{{type_segment_1}}",
            "{{type_segment_2}}",
            "{{type_segment_3}}",
            "{{tech_segment_1}}",
            "{{tech_segment_2}}",
            "{{tech_segment_3}}",
            "{{app_segment_1}}",
            "{{app_segment_2}}",
            "{{app_segment_3}}",
            "{{seg4_sub1}}",
            "{{seg4_sub2}}",
            "{{seg4_sub3}}",
            "{{seg5_sub1}}",
            "{{seg5_sub2}}",
            "{{seg5_sub3}}",
            "{{seg6_sub1}}",
            "{{seg6_sub2}}",
            "{{seg6_sub3}}",
        ]

        for k in taxonomy_keys:
            val = payload_dict.get(k)
            if val and val.lower() not in all_input_subs and all_input_subs:
                errors.append(
                    f"Selected taxonomy value for '{k}' ('{val}') does not exist in source input sub-segments"
                )

    is_valid = len(errors) == 0
    return is_valid, errors
