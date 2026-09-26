"""
Market Report Generator - Main Entry Point

Usage:
    python run.py <input_docx> [output_name] [--no-api]

Example:
    python run.py "market_data.docx"
    python run.py "market_data.docx" "my_report"
    python run.py "market_data.docx" "my_report" --no-api
"""

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.parser import parse_docx, MarketInput
from src.cache_manager import CacheManager
from src.ai_generator import AIGenerator
from src.payload_builder import build_payload, payload_to_dict
from src.renderer import render_report


def load_env_file(env_path: str = ".env"):
    """Parse local .env file if present."""
    if not os.path.isabs(env_path):
        env_path = os.path.join(os.path.dirname(__file__), env_path)

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = value


def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file with env var fallbacks."""
    load_env_file()
    config = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    env_key = os.environ.get("OPENROUTER_API_KEY")
    if env_key:
        config["openrouter_api_key"] = env_key

    env_model = os.environ.get("MODEL")
    if env_model:
        config["model"] = env_model

    return config


def save_json(data: dict, output_path: str):
    """Save data as JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved JSON: {output_path}")


def sanitize_filename(name: str) -> str:
    """Convert string to safe filename."""
    safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)
    return safe.strip().replace(" ", "_")


def _get_fallback_content(market_input: MarketInput) -> dict:
    """Get fallback content when API is unavailable."""
    core = market_input.market_name

    return {
        "type_segment_1": f"{core} Type 1",
        "type_segment_2": f"{core} Type 2",
        "type_segment_3": f"{core} Type 3",
        "tech_segment_1": f"{core} Tech 1",
        "tech_segment_2": f"{core} Tech 2",
        "tech_segment_3": f"{core} Tech 3",
        "app_segment_1": f"{core} App 1",
        "app_segment_2": f"{core} App 2",
        "app_segment_3": f"{core} App 3",
        "app_segment_4": f"{core} App 4",
        "co1_name": "Featured Company",
        "co2_name": "Competitor 2",
        "co3_name": "Competitor 3",
        "co4_name": "Competitor 4",
        "co5_name": "Co5",
        "co6_name": "Co6",
        "co7_name": "Competitor 7",
        "co8_name": "Co8",
        "co9_name": "Co9",
        "co10_name": "Co10",
        "co1_segment_1_name": f"{core} Segment 1",
        "co1_segment_2_name": f"{core} Segment 2",
        "segment5_marketshare1": "Sub-Segment 1",
        "segment5_marketshare2": "Sub-Segment 2",
        "segment5_marketshare3": "Sub-Segment 3",
        "segment6_marketshare1": "Sub-Segment 1",
        "segment6_marketshare2": "Sub-Segment 2",
        "segment6_marketshare3": "Sub-Segment 3",
        "segment6_marketshare4": "Sub-Segment 4",
        "seg4_name": f"{core} Segment 4",
        "seg4_sub1": "Sub-Segment 1",
        "seg4_sub2": "Sub-Segment 2",
        "seg4_sub3": "Sub-Segment 3",
        "seg5_name": f"{core} Segment 5",
        "seg5_sub1": "Sub-Segment 1",
        "seg5_sub2": "Sub-Segment 2",
        "seg5_sub3": "Sub-Segment 3",
        "seg6_name": f"{core} Segment 6",
        "seg6_sub1": "Sub-Segment 1",
        "seg6_sub2": "Sub-Segment 2",
        "seg6_sub3": "Sub-Segment 3",
        "ch4_custom_subsection_4_1_title": "Client Requirement 4.1",
    }


def main():
    print("=" * 60)
    print("MARKET REPORT GENERATOR")
    print("=" * 60)

    # Check arguments
    if len(sys.argv) < 2:
        print("\nUsage: python run.py <input_docx> [output_name] [--no-api]")
        print("\nExample:")
        print('  python run.py "market_data.docx"')
        print('  python run.py "market_data.docx" "my_report"')
        print('  python run.py "market_data.docx" "my_report" --no-api')
        sys.exit(1)

    input_docx = sys.argv[1]
    output_name = None
    use_api = True

    for arg in sys.argv[2:]:
        if arg == "--no-api":
            use_api = False
        elif not arg.startswith("-"):
            output_name = arg

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    config = load_config(config_path)
    print(f"\nConfiguration loaded")
    print(f"  Model: {config.get('model', 'openrouter/free')}")
    print(f"  Cache TTL: {config.get('cache_ttl_hours', 24)} hours")
    print(f"  API Enabled: {use_api}")

    # Step 1: Parse input DOCX
    print("\n[1/5] Parsing input DOCX...")
    market_input = parse_docx(input_docx)
    if not market_input:
        print("Error: Failed to parse input DOCX")
        sys.exit(1)

    print(f"  Detected market: {market_input.market_name}")

    # Step 2: Check cache
    print("\n[2/5] Checking cache...")
    cache = CacheManager(cache_dir="cache", ttl_hours=config.get("cache_ttl_hours", 24))
    cached_content = cache.get(market_input.market_name_upper, market_input.base_year)

    if cached_content:
        print("  Using cached content (0 API calls)")
        ai_content = cached_content
    elif use_api:
        # Step 3: Generate content via OpenRouter
        print("\n[3/5] Generating content via OpenRouter...")
        generator = AIGenerator(
            api_key=config.get("openrouter_api_key", ""),
            model=config.get("model", "openrouter/free"),
            max_retries=config.get("max_retries", 3),
            retry_delay=config.get("retry_delay", 2),
        )

        ai_content = generator.generate(
            market_input.market_name,
            market_input.market_name_title,
            market_input.custom_sections,
        )

        if ai_content:
            # Save to cache
            cache.save(
                market_input.market_name_upper, ai_content, market_input.base_year
            )
            print("  Content generated and cached")
        else:
            print("Warning: API generation failed, using fallback content")
            ai_content = _get_fallback_content(market_input)
    else:
        print("  API disabled, using fallback content")
        ai_content = _get_fallback_content(market_input)

    # Step 4: Build payload and render DOCX
    print("\n[4/5] Building payload and rendering DOCX...")
    payload = build_payload(ai_content, market_input)
    placeholder_dict = payload_to_dict(payload)

    print(f"  Placeholders to replace: {len(placeholder_dict)}")

    # Determine output paths
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_name:
        safe_name = sanitize_filename(output_name)
    else:
        safe_name = sanitize_filename(market_input.market_name)

    output_docx = os.path.join("output", f"report_{safe_name}_{timestamp}.docx")
    output_json = os.path.join("output", f"report_{safe_name}_{timestamp}.json")

    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)

    # Render DOCX
    template_path = config.get("template_file", "templates/master_template_v1.docx")
    if not os.path.isabs(template_path):
        template_path = os.path.join(os.path.dirname(__file__), template_path)

    # Adjust cover title font size if title is long (>20 chars)
    adjust_cover = market_input.cover_title_truncated

    success = render_report(
        template_path, placeholder_dict, output_docx, adjust_cover_title=adjust_cover
    )

    if success:
        # Save JSON audit copy
        save_json(
            {
                "market_name": market_input.market_name,
                "market_name_upper": market_input.market_name_upper,
                "generated_at": datetime.now().isoformat(),
                "api_model": config.get("model", "openrouter/free"),
                "ai_content": ai_content,
                "payload": placeholder_dict,
            },
            output_json,
        )

        print("\n" + "=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"\nOutput files:")
        print(f"  DOCX: {output_docx}")
        print(f"  JSON: {output_json}")
    else:
        print("\nError: Failed to render DOCX")
        sys.exit(1)


if __name__ == "__main__":
    main()
