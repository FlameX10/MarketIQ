"""
Payload builder for the updated full 16-chapter market report template.
Maps ai_content + market_input to the 64 placeholders in full_market_report_template_updated.docx.
"""

from typing import Dict, Any, Optional
from src.parser import MarketInput


def get(ai_content: Dict[str, Any], key: str, default: str = "") -> str:
    val = ai_content.get(key)
    return str(val) if val else default


def build_payload(
    ai_content: Dict[str, Any], market_input: MarketInput
) -> Dict[str, str]:
    core = market_input.market_name
    segments = market_input.parsed_segments

    def val(key: str, fallback: str = "") -> str:
        return get(ai_content, key, fallback)

    players = market_input.parsed_players  # real names from input DOCX

    def player(idx: int, ai_key: str, max_len: int = 30) -> str:
        """Return AI-provided name, then parsed player, then generic fallback."""
        ai_val = ai_content.get(ai_key, "")
        if ai_val and str(ai_val).strip():
            return str(ai_val).strip()
        if idx < len(players) and players[idx]:
            return players[idx][:max_len]
        return f"Competitor {idx + 1}"

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
        "{{co1_name_upper}}": player(0, "co1_name", 20).upper(),
        "{{co2_name}}": player(1, "co2_name", 20),
        "{{co3_name}}": player(2, "co3_name", 20),
        "{{co4_name}}": player(3, "co4_name", 30),
        "{{co5_name}}": player(4, "co5_name", 15),
        "{{co6_name}}": player(5, "co6_name", 15),
        "{{co7_name}}": player(6, "co7_name", 20),
        "{{co8_name}}": player(7, "co8_name", 15),
        "{{co9_name}}": player(8, "co9_name", 15),
        "{{co10_name}}": player(9, "co10_name", 15),
        "{{CO1_NAME}}": player(0, "co1_name", 20).upper(),
        "{{CO2_NAME}}": player(1, "co2_name", 20).upper(),
        "{{CO3_NAME}}": player(2, "co3_name", 20).upper(),
        "{{CO4_NAME}}": player(3, "co4_name", 30).upper(),
        "{{CO5_NAME}}": player(4, "co5_name", 15).upper(),
        "{{CO6_NAME}}": player(5, "co6_name", 15).upper(),
        "{{CO7_NAME}}": player(6, "co7_name", 20).upper(),
        "{{CO8_NAME}}": player(7, "co8_name", 15).upper(),
        "{{CO9_NAME}}": player(8, "co9_name", 15).upper(),
        "{{CO10_NAME}}": player(9, "co10_name", 15).upper(),
        "{{co1_seg1_name}}": val("co1_segment_1_name", f"{core} Segment 1"),
        "{{co1_seg2_name}}": val("co1_segment_2_name", f"{core} Segment 2"),
        "{{segment5_marketshare1}}": val("segment5_marketshare1", "Sub-Segment 1"),
        "{{segment5_marketshare2}}": val("segment5_marketshare2", "Sub-Segment 2"),
        "{{segment5_marketshare3}}": val("segment5_marketshare3", "Sub-Segment 3"),
        "{{segment5_marketshare4}}": val("segment5_marketshare4", "Sub-Segment 4"),
        "{{segment6_marketshare1}}": val("segment6_marketshare1", "Sub-Segment 1"),
        "{{segment6_marketshare2}}": val("segment6_marketshare2", "Sub-Segment 2"),
        "{{segment6_marketshare3}}": val("segment6_marketshare3", "Sub-Segment 3"),
        "{{segment6_marketshare4}}": val("segment6_marketshare4", "Sub-Segment 4"),
    }

    # type/tech/app sub-segments from parsed_segments with AI fallback
    for i, ai_key in enumerate(["type_segment_1", "type_segment_2", "type_segment_3"]):
        if len(segments) > 0 and len(segments[0]["sub_segments"]) > i:
            payload[f"{{{{{ai_key}}}}}"] = segments[0]["sub_segments"][i]
        else:
            payload[f"{{{{{ai_key}}}}}"] = val(ai_key, f"{core} Type {i + 1}")

    for i, ai_key in enumerate(["tech_segment_1", "tech_segment_2", "tech_segment_3"]):
        if len(segments) > 1 and len(segments[1]["sub_segments"]) > i:
            payload[f"{{{{{ai_key}}}}}"] = segments[1]["sub_segments"][i]
        else:
            payload[f"{{{{{ai_key}}}}}"] = val(ai_key, f"{core} Tech {i + 1}")

    for i, ai_key in enumerate(
        ["app_segment_1", "app_segment_2", "app_segment_3", "app_segment_4"]
    ):
        if len(segments) > 2 and len(segments[2]["sub_segments"]) > i:
            payload[f"{{{{{ai_key}}}}}"] = segments[2]["sub_segments"][i]
        else:
            payload[f"{{{{{ai_key}}}}}"] = val(ai_key, f"{core} App {i + 1}")

    # seg4/5/6 names and sub-segments from parsed_segments with AI fallback
    HARDCODED_CHAPTER_NAMES = {"Type", "Technology", "Application"}
    seg_mapping = [
        (3, "seg4_name", ["seg4_sub1", "seg4_sub2", "seg4_sub3"]),
        (4, "seg5_name", ["seg5_sub1", "seg5_sub2", "seg5_sub3"]),
        (5, "seg6_name", ["seg6_sub1", "seg6_sub2", "seg6_sub3"]),
    ]
    for idx, name_key, sub_keys in seg_mapping:
        if len(segments) > idx and segments[idx]["name"] not in HARDCODED_CHAPTER_NAMES:
            payload[f"{{{{{name_key}}}}}"] = segments[idx]["name"]
        else:
            payload[f"{{{{{name_key}}}}}"] = val(name_key, f"Segment {idx + 1}")

        for i, sub_key in enumerate(sub_keys):
            if len(segments) > idx and len(segments[idx]["sub_segments"]) > i:
                payload[f"{{{{{sub_key}}}}}"] = segments[idx]["sub_segments"][i]
            else:
                payload[f"{{{{{sub_key}}}}}"] = val(sub_key, f"Sub-Segment {i + 1}")

    # Custom sections from market_input
    for i in range(1, 5):
        key = f"{{{{ch4_custom_section_{i}_title}}}}"
        if len(market_input.custom_sections) >= i:
            payload[key] = market_input.custom_sections[i - 1]["title"]
        else:
            payload[key] = f"Client Requirement {i}"

    payload["{{ch4_custom_subsection_4_1_title}}"] = val(
        "ch4_custom_subsection_4_1_title", "Client Requirement 4.1"
    )

    return payload


def payload_to_dict(payload: Dict[str, str]) -> Dict[str, str]:
    return dict(payload)
