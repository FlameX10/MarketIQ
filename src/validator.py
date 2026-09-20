"""
Pre-rendering payload validation module for MarketIQ.
Guarantees that no unresolved generic placeholder strings or fake company URLs
reach the final DOCX template renderer.
"""

import re
from typing import Dict, List, Tuple


# Regex patterns matching unresolved generic placeholder strings
GENERIC_PATTERNS = [
    (r"\b(Type|Tech|App)\s+\d+\b", "Generic segment placeholder (e.g. Type 1, Tech 2, App 3)"),
    (r"\bSegment\s+[456]\b", "Generic dimension name (e.g. Segment 4, Segment 5, Segment 6)"),
    (r"\bSub-Segment\s*\d*\b", "Generic sub-segment label (e.g. Sub-Segment 1)"),
    (r"\bClient Requirement\s*\d*(\.\d+)?\b", "Generic client requirement title"),
    (r"\bFEATURED COMPANY\b", "Generic company placeholder"),
    (r"\bCompetitor\s+\d+\b", "Generic competitor placeholder"),
    (r"www\.FEATURED\s*COMPANY\.com", "Fake company URL"),
]


def validate_payload(payload_dict: Dict[str, str]) -> Tuple[bool, List[str]]:
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
                # Allow if the market name itself naturally contains "Type" or "Segment" in rare product names,
                # but flag generic placeholders.
                errors.append(f"Unresolved placeholder value in '{placeholder}': '{val_str}' ({desc})")

    is_valid = len(errors) == 0
    return is_valid, errors
