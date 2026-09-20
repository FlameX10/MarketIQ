"""
Payload builder for the updated full 16-chapter market report template.
Maps ai_content + market_input to the 64 placeholders in full_market_report_template_updated.docx.
Uses normalized single-source-of-truth semantic mapping.
"""

from typing import Dict, Any, List
from src.parser import MarketInput


def get(ai_content: Dict[str, Any], key: str, default: str = "") -> str:
    val = ai_content.get(key)
    return str(val) if val else default


def build_payload(
    ai_content: Dict[str, Any], market_input: MarketInput
) -> Dict[str, str]:
    core = market_input.market_name
    segments = market_input.parsed_segments or []
    players = market_input.parsed_players or []
    custom_reqs = market_input.custom_sections or []

    def val(key: str, fallback: str = "") -> str:
        return get(ai_content, key, fallback)

    # 1. Company / Key Player Mapping (Priority: Parsed players > AI content > Fallbacks)
    co_names = {}
    for i in range(1, 11):
        if len(players) >= i and players[i - 1]:
            co_names[f"co{i}_name"] = players[i - 1]
        else:
            co_names[f"co{i}_name"] = val(f"co{i}_name", f"{core} Key Player {i}")

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
        "{{co1_seg1_name}}": val("co1_segment_1_name", f"{core} Primary Segment"),
        "{{co1_seg2_name}}": val("co1_segment_2_name", f"{core} Secondary Segment"),
    }

    for i in range(1, 11):
        c_name = co_names[f"co{i}_name"]
        payload[f"{{{{co{i}_name}}}}"] = c_name
        payload[f"{{{{CO{i}_NAME}}}}"] = c_name.upper()

    # 2. Semantic Segment Categorization
    type_seg = None
    tech_seg = None
    app_seg = None
    other_segs: List[Dict[str, Any]] = []

    for seg in segments:
        name_lower = seg["name"].lower()
        if not type_seg and any(k in name_lower for k in ["type", "product", "form", "grade"]):
            type_seg = seg
        elif not tech_seg and any(k in name_lower for k in ["tech", "process", "method"]):
            tech_seg = seg
        elif not app_seg and any(k in name_lower for k in ["app", "end-use", "use"]):
            app_seg = seg
        else:
            other_segs.append(seg)

    # Fallbacks by index if semantic match was unassigned
    remaining_segs = [s for s in segments if s not in (type_seg, tech_seg, app_seg)]
    if not type_seg and remaining_segs:
        type_seg = remaining_segs.pop(0)
    if not tech_seg and remaining_segs:
        tech_seg = remaining_segs.pop(0)
    if not app_seg and remaining_segs:
        app_seg = remaining_segs.pop(0)

    # Remaining segments go to seg4, seg5, seg6
    unused_segs = [s for s in segments if s not in (type_seg, tech_seg, app_seg)]

    # Map Type Sub-Segments
    for i, ai_key in enumerate(["type_segment_1", "type_segment_2", "type_segment_3"]):
        if type_seg and len(type_seg["sub_segments"]) > i:
            payload[f"{{{{{ai_key}}}}}"] = type_seg["sub_segments"][i]
        else:
            payload[f"{{{{{ai_key}}}}}"] = val(ai_key, f"{core} Segment Variant {i + 1}")

    # Map Tech Sub-Segments
    for i, ai_key in enumerate(["tech_segment_1", "tech_segment_2", "tech_segment_3"]):
        if tech_seg and len(tech_seg["sub_segments"]) > i:
            payload[f"{{{{{ai_key}}}}}"] = tech_seg["sub_segments"][i]
        else:
            payload[f"{{{{{ai_key}}}}}"] = val(ai_key, f"{core} Technology {i + 1}")

    # Map App Sub-Segments
    for i, ai_key in enumerate(["app_segment_1", "app_segment_2", "app_segment_3", "app_segment_4"]):
        if app_seg and len(app_seg["sub_segments"]) > i:
            payload[f"{{{{{ai_key}}}}}"] = app_seg["sub_segments"][i]
        else:
            payload[f"{{{{{ai_key}}}}}"] = val(ai_key, f"{core} Application {i + 1}")

    # Map Segments 4, 5, 6
    seg_configs = [
        ("seg4_name", ["seg4_sub1", "seg4_sub2", "seg4_sub3"], None),
        ("seg5_name", ["seg5_sub1", "seg5_sub2", "seg5_sub3"], ["segment5_marketshare1", "segment5_marketshare2", "segment5_marketshare3", "segment5_marketshare4"]),
        ("seg6_name", ["seg6_sub1", "seg6_sub2", "seg6_sub3"], ["segment6_marketshare1", "segment6_marketshare2", "segment6_marketshare3", "segment6_marketshare4"]),
    ]

    for idx, (name_key, sub_keys, share_keys) in enumerate(seg_configs):
        curr_seg = unused_segs[idx] if len(unused_segs) > idx else None

        if curr_seg and curr_seg["name"]:
            dimension_name = curr_seg["name"]
        else:
            dimension_name = val(name_key, f"{core} Category {idx + 4}")

        payload[f"{{{{{name_key}}}}}"] = dimension_name

        for i, sub_key in enumerate(sub_keys):
            if curr_seg and len(curr_seg["sub_segments"]) > i:
                val_sub = curr_seg["sub_segments"][i]
            else:
                val_sub = val(sub_key, f"{dimension_name} Option {i + 1}")
            payload[f"{{{{{sub_key}}}}}"] = val_sub

        if share_keys:
            for i, share_key in enumerate(share_keys):
                if curr_seg and len(curr_seg["sub_segments"]) > i:
                    val_share = curr_seg["sub_segments"][i]
                else:
                    val_share = val(share_key, f"{dimension_name} Option {i + 1}")
                payload[f"{{{{{share_key}}}}}"] = val_share

    # 3. Client Requirements Mapping
    for i in range(1, 5):
        key = f"{{{{ch4_custom_section_{i}_title}}}}"
        if len(custom_reqs) >= i and custom_reqs[i - 1].get("title"):
            payload[key] = custom_reqs[i - 1]["title"]
        else:
            payload[key] = val(f"ch4_custom_section_{i}_title", f"{core} Custom Analysis {i}")

    if len(custom_reqs) >= 1 and custom_reqs[0].get("title"):
        payload["{{ch4_custom_subsection_4_1_title}}"] = custom_reqs[0]["title"]
    else:
        payload["{{ch4_custom_subsection_4_1_title}}"] = val("ch4_custom_subsection_4_1_title", f"{core} In-Depth Requirement Analysis")

    return payload


def payload_to_dict(payload: Dict[str, str]) -> Dict[str, str]:
    return dict(payload)
