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
