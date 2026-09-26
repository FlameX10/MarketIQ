"""
Payload builder for the updated full 16-chapter market report template.
Maps ai_content + market_input to the 64 placeholders in full_market_report_template_updated.docx.
Uses dynamic semantic segment categorization and 3-tier value selection.
"""

from typing import Dict, Any, Optional, List
from src.parser import MarketInput


def build_payload(
    ai_content: Dict[str, Any], market_input: MarketInput
) -> Dict[str, str]:
    core = market_input.market_name
    segments = market_input.parsed_segments or []
    ai = ai_content or {}

    def val(key: str, fallback: str = "") -> str:
        v = ai.get(key)
        if v and str(v).strip():
            return str(v).strip()
        return fallback

    # Helper: 3-tier priority (AI -> Parsed DOCX -> Fallback)
    def get_sub(ai_key: str, seg_obj: Optional[Dict[str, Any]], idx: int, fallback: str) -> str:
        # Tier 1: AI content if present and non-empty
        if ai_key and ai.get(ai_key):
            ai_val = str(ai[ai_key]).strip()
            # Avoid using generic AI fallback strings like "Soda Type 1" if parsed data exists
            is_generic = any(k in ai_val.lower() for k in ["type 1", "type 2", "type 3", "tech 1", "tech 2", "tech 3", "app 1", "app 2", "app 3", "app 4"])
            if ai_val and (not is_generic or not seg_obj):
                return ai_val

        # Tier 2: Parsed input DOCX sub-segment
        if seg_obj and "sub_segments" in seg_obj and len(seg_obj["sub_segments"]) > idx:
            return seg_obj["sub_segments"][idx]

        # Tier 3: Market fallback
        return fallback

    # -------------------------------------------------------------------------
    # 1. Semantic Segment Categorization (from parsed input DOCX)
    # -------------------------------------------------------------------------
    type_seg = None
    tech_seg = None
    app_seg = None
    end_user_seg = None
    dist_seg = None
    mat_seg = None

    assigned = set()

    for seg in segments:
        name_lower = seg["name"].lower()
        if not app_seg and any(k in name_lower for k in ["app", "end-use", "use", "application"]):
            app_seg = seg
            assigned.add(seg["name"])
        elif not type_seg and any(k in name_lower for k in ["type", "product", "form", "grade"]):
            type_seg = seg
            assigned.add(seg["name"])
        elif not tech_seg and any(k in name_lower for k in ["tech", "process", "method", "manufacturing"]):
            tech_seg = seg
            assigned.add(seg["name"])
        elif not end_user_seg and any(k in name_lower for k in ["end user", "user", "consumer"]):
            end_user_seg = seg
            assigned.add(seg["name"])
        elif not dist_seg and any(k in name_lower for k in ["distribut", "channel", "sales"]):
            dist_seg = seg
            assigned.add(seg["name"])
        elif not mat_seg and any(k in name_lower for k in ["material", "wood", "raw"]):
            mat_seg = seg
            assigned.add(seg["name"])

    # Assign remaining unassigned segments in order to unassigned slots
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
        "{{co1_name_upper}}": val("co1_name", "Featured Company").upper(),
        "{{co2_name}}": val("co2_name", "Competitor 2"),
        "{{co3_name}}": val("co3_name", "Competitor 3"),
        "{{co4_name}}": val("co4_name", "Competitor 4"),
        "{{co5_name}}": val("co5_name", "Competitor 5"),
        "{{co6_name}}": val("co6_name", "Competitor 6"),
        "{{co7_name}}": val("co7_name", "Competitor 7"),
        "{{co8_name}}": val("co8_name", "Competitor 8"),
        "{{co9_name}}": val("co9_name", "Competitor 9"),
        "{{co10_name}}": val("co10_name", "Competitor 10"),
        "{{CO1_NAME}}": val("co1_name", "Featured Company").upper(),
        "{{CO2_NAME}}": val("co2_name", "Competitor 2").upper(),
        "{{CO3_NAME}}": val("co3_name", "Competitor 3").upper(),
        "{{CO4_NAME}}": val("co4_name", "Competitor 4").upper(),
        "{{CO5_NAME}}": val("co5_name", "Competitor 5").upper(),
        "{{CO6_NAME}}": val("co6_name", "Competitor 6").upper(),
        "{{CO7_NAME}}": val("co7_name", "Competitor 7").upper(),
        "{{CO8_NAME}}": val("co8_name", "Competitor 8").upper(),
        "{{CO9_NAME}}": val("co9_name", "Competitor 9").upper(),
        "{{CO10_NAME}}": val("co10_name", "Competitor 10").upper(),
        "{{co1_seg1_name}}": val("co1_segment_1_name", f"{core} Segment 1"),
        "{{co1_seg2_name}}": val("co1_segment_2_name", f"{core} Segment 2"),
    }

    # -------------------------------------------------------------------------
    # 2. Map Type Sub-Segments (Chapter 6)
    # -------------------------------------------------------------------------
    payload["{{type_segment_1}}"] = get_sub("type_segment_1", type_seg, 0, f"{core} Type 1")
    payload["{{type_segment_2}}"] = get_sub("type_segment_2", type_seg, 1, f"{core} Type 2")
    payload["{{type_segment_3}}"] = get_sub("type_segment_3", type_seg, 2, f"{core} Type 3")

    # -------------------------------------------------------------------------
    # 3. Map Tech Sub-Segments (Chapter 5)
    # -------------------------------------------------------------------------
    payload["{{tech_segment_1}}"] = get_sub("tech_segment_1", tech_seg, 0, f"{core} Tech 1")
    payload["{{tech_segment_2}}"] = get_sub("tech_segment_2", tech_seg, 1, f"{core} Tech 2")
    payload["{{tech_segment_3}}"] = get_sub("tech_segment_3", tech_seg, 2, f"{core} Tech 3")

    # -------------------------------------------------------------------------
    # 4. Map Application Sub-Segments (Chapter 7)
    # -------------------------------------------------------------------------
    payload["{{app_segment_1}}"] = get_sub("app_segment_1", app_seg, 0, f"{core} App 1")
    payload["{{app_segment_2}}"] = get_sub("app_segment_2", app_seg, 1, f"{core} App 2")
    payload["{{app_segment_3}}"] = get_sub("app_segment_3", app_seg, 2, f"{core} App 3")
    payload["{{app_segment_4}}"] = get_sub("app_segment_4", app_seg, 3, get_sub("app_segment_1", app_seg, 0, f"{core} App 4"))

    # -------------------------------------------------------------------------
    # 5. Map Seg4 (End User / Chapter 8)
    # -------------------------------------------------------------------------
    seg4_name_val = end_user_seg["name"] if end_user_seg else val("seg4_name", "End User")
    payload["{{seg4_name}}"] = seg4_name_val
    payload["{{seg4_sub1}}"] = get_sub("seg4_sub1", end_user_seg, 0, f"{seg4_name_val} 1")
    payload["{{seg4_sub2}}"] = get_sub("seg4_sub2", end_user_seg, 1, f"{seg4_name_val} 2")
    payload["{{seg4_sub3}}"] = get_sub("seg4_sub3", end_user_seg, 2, f"{seg4_name_val} 3")

    # -------------------------------------------------------------------------
    # 6. Map Seg5 (Distribution Channel / Chapter 9)
    # -------------------------------------------------------------------------
    seg5_name_val = dist_seg["name"] if dist_seg else val("seg5_name", "Distribution Channel")
    payload["{{seg5_name}}"] = seg5_name_val
    payload["{{seg5_sub1}}"] = get_sub("seg5_sub1", dist_seg, 0, f"{seg5_name_val} 1")
    payload["{{seg5_sub2}}"] = get_sub("seg5_sub2", dist_seg, 1, f"{seg5_name_val} 2")
    payload["{{seg5_sub3}}"] = get_sub("seg5_sub3", dist_seg, 2, f"{seg5_name_val} 3")
    payload["{{segment5_marketshare1}}"] = get_sub("segment5_marketshare1", dist_seg, 0, f"{seg5_name_val} 1")
    payload["{{segment5_marketshare2}}"] = get_sub("segment5_marketshare2", dist_seg, 1, f"{seg5_name_val} 2")
    payload["{{segment5_marketshare3}}"] = get_sub("segment5_marketshare3", dist_seg, 2, f"{seg5_name_val} 3")
    payload["{{segment5_marketshare4}}"] = get_sub("segment5_marketshare4", dist_seg, 3, get_sub("segment5_marketshare1", dist_seg, 0, f"{seg5_name_val} 4"))

    # -------------------------------------------------------------------------
    # 7. Map Seg6 (Material / Chapter 10)
    # -------------------------------------------------------------------------
    seg6_name_val = mat_seg["name"] if mat_seg else val("seg6_name", "Material")
    payload["{{seg6_name}}"] = seg6_name_val
    payload["{{seg6_sub1}}"] = get_sub("seg6_sub1", mat_seg, 0, f"{seg6_name_val} 1")
    payload["{{seg6_sub2}}"] = get_sub("seg6_sub2", mat_seg, 1, f"{seg6_name_val} 2")
    payload["{{seg6_sub3}}"] = get_sub("seg6_sub3", mat_seg, 2, f"{seg6_name_val} 3")
    payload["{{segment6_marketshare1}}"] = get_sub("segment6_marketshare1", mat_seg, 0, f"{seg6_name_val} 1")
    payload["{{segment6_marketshare2}}"] = get_sub("segment6_marketshare2", mat_seg, 1, f"{seg6_name_val} 2")
    payload["{{segment6_marketshare3}}"] = get_sub("segment6_marketshare3", mat_seg, 2, f"{seg6_name_val} 3")
    payload["{{segment6_marketshare4}}"] = get_sub("segment6_marketshare4", mat_seg, 3, get_sub("segment6_marketshare1", mat_seg, 0, f"{seg6_name_val} 4"))

    # -------------------------------------------------------------------------
    # 8. Custom Requirements (Chapter 4)
    # -------------------------------------------------------------------------
    custom_reqs = market_input.custom_sections or []
    for i in range(1, 5):
        key = f"{{{{ch4_custom_section_{i}_title}}}}"
        if len(custom_reqs) >= i:
            payload[key] = custom_reqs[i - 1].get("title", "") if isinstance(custom_reqs[i - 1], dict) else str(custom_reqs[i - 1])
        else:
            payload[key] = f"Client Requirement {i}"

    payload["{{ch4_custom_subsection_4_1_title}}"] = val(
        "ch4_custom_subsection_4_1_title", "Client Requirement 4.1"
    )

    return payload


def payload_to_dict(payload: Dict[str, str]) -> Dict[str, str]:
    return dict(payload)
