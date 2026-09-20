"""
Payload builder for the updated full 16-chapter market report template.
Maps market_input (and optional ai_content) to placeholders in full_market_report_template_updated.docx.
Uses locked single-source-of-truth semantic taxonomy mapping.
"""

from typing import Dict, Any, List
from src.parser import MarketInput

KNOWN_COMPANY_MAPS = {
    "ceramic tiles": [
        "CERAMICA FLAMINIA",
        "Marazzi Group",
        "Concorde Group",
        "Gres Ceramica",
        "Ariafloor",
        "Baldassarre",
        "Iris Ceramica",
        "Vega",
        "Daltile",
        "Florida Tile",
    ]
}


def build_payload(
    ai_content: Dict[str, Any], market_input: MarketInput
) -> Dict[str, str]:
    core = market_input.market_name
    core_lower = core.lower()
    segments = market_input.parsed_segments or []
    players = market_input.parsed_players or []
    custom_reqs = market_input.custom_sections or []

    # 1. Company / Key Player Mapping (Deterministic)
    co_names = {}
    matched_companies = None
    for key, c_list in KNOWN_COMPANY_MAPS.items():
        if key in core_lower or core_lower in key:
            matched_companies = c_list
            break

    for i in range(1, 11):
        if matched_companies and len(matched_companies) >= i:
            co_names[f"co{i}_name"] = matched_companies[i - 1]
        elif len(players) >= i and players[i - 1]:
            co_names[f"co{i}_name"] = players[i - 1]
        else:
            co_names[f"co{i}_name"] = f"{core} Key Player {i}"

    payload: Dict[str, str] = {
        "{{market_name}}": market_input.market_name,
        "{{market_name_upper}}": market_input.market_name_upper,
        "{{MARKET_NAME_UPPER}}": market_input.market_name_upper,
        "{{report_geography}}": market_input.report_geography,
        "{{company_name}}": market_input.company_name,
        "{{base_year}}": market_input.base_year,
        "{{forecast_start_year}}": market_input.forecast_start_year,
        "{{forecast_end_year}}": market_input.forecast_end_year,
        "{{history_start_year}}": market_input.history_start_year,
        "{{co1_name_upper}}": co_names["co1_name"].upper(),
        "{{co1_seg1_name}}": "Large-Format Floor Tiles" if "ceramic tile" in core_lower else f"Primary {core} Products",
        "{{co1_seg2_name}}": "Decorative Wall Tiles" if "ceramic tile" in core_lower else f"{core} Services & Accessories",
    }

    for i in range(1, 11):
        c_name = co_names[f"co{i}_name"]
        payload[f"{{{{co{i}_name}}}}"] = c_name
        payload[f"{{{{CO{i}_NAME}}}}"] = c_name.upper()

    # 2. Semantic Segment Categorization (Locked Taxonomy from Input)
    type_seg = None
    tech_seg = None
    app_seg = None
    end_user_seg = None
    dist_seg = None
    mat_seg = None

    assigned = set()

    for seg in segments:
        name_lower = seg["name"].lower()
        if not type_seg and any(k in name_lower for k in ["type", "product", "form", "grade"]):
            type_seg = seg
            assigned.add(seg["name"])
        elif not tech_seg and any(k in name_lower for k in ["tech", "process", "method"]):
            tech_seg = seg
            assigned.add(seg["name"])
        elif not app_seg and any(k in name_lower for k in ["app", "end-use", "use"]):
            app_seg = seg
            assigned.add(seg["name"])
        elif not end_user_seg and any(k in name_lower for k in ["end user", "user", "consumer"]):
            end_user_seg = seg
            assigned.add(seg["name"])
        elif not dist_seg and any(k in name_lower for k in ["distribut", "channel", "sales"]):
            dist_seg = seg
            assigned.add(seg["name"])
        elif not mat_seg and any(k in name_lower for k in ["material", "raw"]):
            mat_seg = seg
            assigned.add(seg["name"])

    # Fallback to unassigned segments in order for any unassigned slot
    unassigned_segs = [s for s in segments if s["name"] not in assigned]
    slots = [
        ("type_seg", type_seg),
        ("tech_seg", tech_seg),
        ("app_seg", app_seg),
        ("end_user_seg", end_user_seg),
        ("dist_seg", dist_seg),
        ("mat_seg", mat_seg),
    ]

    resolved = {}
    for slot_name, current_val in slots:
        if current_val is None and unassigned_segs:
            resolved[slot_name] = unassigned_segs.pop(0)
        else:
            resolved[slot_name] = current_val

    type_seg = resolved["type_seg"]
    tech_seg = resolved["tech_seg"]
    app_seg = resolved["app_seg"]
    end_user_seg = resolved["end_user_seg"]
    dist_seg = resolved["dist_seg"]
    mat_seg = resolved["mat_seg"]

    # Helper function to safely extract sub-segment at index
    def get_sub(seg_obj: Any, idx: int, fallback: str) -> str:
        if seg_obj and "sub_segments" in seg_obj and len(seg_obj["sub_segments"]) > idx:
            return seg_obj["sub_segments"][idx]
        return fallback

    # Map Type Sub-Segments
    payload["{{type_segment_1}}"] = get_sub(type_seg, 0, f"{core} Type 1")
    payload["{{type_segment_2}}"] = get_sub(type_seg, 1, f"{core} Type 2")
    payload["{{type_segment_3}}"] = get_sub(type_seg, 2, f"{core} Type 3")

    # Map Tech Sub-Segments
    payload["{{tech_segment_1}}"] = get_sub(tech_seg, 0, f"{core} Technology 1")
    payload["{{tech_segment_2}}"] = get_sub(tech_seg, 1, f"{core} Technology 2")
    payload["{{tech_segment_3}}"] = get_sub(tech_seg, 2, f"{core} Technology 3")

    # Map App Sub-Segments
    payload["{{app_segment_1}}"] = get_sub(app_seg, 0, f"{core} Application 1")
    payload["{{app_segment_2}}"] = get_sub(app_seg, 1, f"{core} Application 2")
    payload["{{app_segment_3}}"] = get_sub(app_seg, 2, f"{core} Application 3")
    payload["{{app_segment_4}}"] = get_sub(app_seg, 3, get_sub(app_seg, 0, f"{core} Application 4"))

    # Map Seg4 (End User)
    seg4_name_val = end_user_seg["name"] if end_user_seg else "End User"
    payload["{{seg4_name}}"] = seg4_name_val
    payload["{{seg4_sub1}}"] = get_sub(end_user_seg, 0, f"{seg4_name_val} 1")
    payload["{{seg4_sub2}}"] = get_sub(end_user_seg, 1, f"{seg4_name_val} 2")
    payload["{{seg4_sub3}}"] = get_sub(end_user_seg, 2, f"{seg4_name_val} 3")

    # Map Seg5 (Distribution Channel)
    seg5_name_val = dist_seg["name"] if dist_seg else "Distribution Channel"
    payload["{{seg5_name}}"] = seg5_name_val
    payload["{{seg5_sub1}}"] = get_sub(dist_seg, 0, f"{seg5_name_val} 1")
    payload["{{seg5_sub2}}"] = get_sub(dist_seg, 1, f"{seg5_name_val} 2")
    payload["{{seg5_sub3}}"] = get_sub(dist_seg, 2, f"{seg5_name_val} 3")
    payload["{{segment5_marketshare1}}"] = get_sub(dist_seg, 0, f"{seg5_name_val} 1")
    payload["{{segment5_marketshare2}}"] = get_sub(dist_seg, 1, f"{seg5_name_val} 2")
    payload["{{segment5_marketshare3}}"] = get_sub(dist_seg, 2, f"{seg5_name_val} 3")
    payload["{{segment5_marketshare4}}"] = get_sub(dist_seg, 3, get_sub(dist_seg, 0, f"{seg5_name_val} 4"))

    # Map Seg6 (Material)
    seg6_name_val = mat_seg["name"] if mat_seg else "Material"
    payload["{{seg6_name}}"] = seg6_name_val
    payload["{{seg6_sub1}}"] = get_sub(mat_seg, 0, f"{seg6_name_val} 1")
    payload["{{seg6_sub2}}"] = get_sub(mat_seg, 1, f"{seg6_name_val} 2")
    payload["{{seg6_sub3}}"] = get_sub(mat_seg, 2, f"{seg6_name_val} 3")
    payload["{{segment6_marketshare1}}"] = get_sub(mat_seg, 0, f"{seg6_name_val} 1")
    payload["{{segment6_marketshare2}}"] = get_sub(mat_seg, 1, f"{seg6_name_val} 2")
    payload["{{segment6_marketshare3}}"] = get_sub(mat_seg, 2, f"{seg6_name_val} 3")
    payload["{{segment6_marketshare4}}"] = get_sub(mat_seg, 3, get_sub(mat_seg, 0, f"{seg6_name_val} 4"))

    # 3. Custom Requirements Mapping
    if custom_reqs:
        # Check if first custom requirement has a description/body
        has_bodies = any(r.get("body") for r in custom_reqs)
        if has_bodies:
            payload["{{ch4_custom_section_1_title}}"] = custom_reqs[0].get("title", f"1. {core} Custom Analysis 1")
            payload["{{ch4_custom_section_2_title}}"] = custom_reqs[0].get("body", "")
            if len(custom_reqs) > 1:
                payload["{{ch4_custom_section_3_title}}"] = custom_reqs[1].get("title", f"2. {core} Custom Analysis 2")
                payload["{{ch4_custom_section_4_title}}"] = custom_reqs[1].get("body", "")
            else:
                payload["{{ch4_custom_section_3_title}}"] = ""
                payload["{{ch4_custom_section_4_title}}"] = ""
        else:
            for i in range(1, 5):
                key = f"{{{{ch4_custom_section_{i}_title}}}}"
                if len(custom_reqs) >= i:
                    payload[key] = custom_reqs[i - 1].get("title", "")
                else:
                    payload[key] = ""

        payload["{{ch4_custom_subsection_4_1_title}}"] = "Market Trends and Forecast 2024\u20112029"
    else:
        for i in range(1, 5):
            payload[f"{{{{ch4_custom_section_{i}_title}}}}"] = f"{core} Custom Requirement {i}"
        payload["{{ch4_custom_subsection_4_1_title}}"] = "Market Trends and Forecast 2024\u20112029"

    return payload


def payload_to_dict(payload: Dict[str, str]) -> Dict[str, str]:
    return dict(payload)
