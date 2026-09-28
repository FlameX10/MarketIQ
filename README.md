# MarketIQ - AI-Powered Market Research Report Generator

An automated, end-to-end system that ingests raw market segmentation DOCX files, queries LLMs via the OpenRouter API to generate tailored industry content, and renders professional 16-chapter market intelligence reports in Word (`.docx`) format with audit JSON metadata.

---

## Key Features

- **Automated Input Parsing**: Extracts product names, multi-dimensional segmentations, regions, countries, top industry players, and custom client requirements directly from input `.docx` documents.
- **AI Content Generation**: Powered by OpenRouter API single-pass generation to supply realistic industry data, segment names, key competitors, and custom section titles.
- **Smart Caching Engine**: File-based TTL cache reduces latency and eliminates duplicate API calls for identical markets.
- **High-Fidelity DOCX Rendering**:
  - Safe XML manipulation preserving complex word processing styles, headers, footers, and tables.
  - Resolves split-run XML placeholders seamlessly.
  - Updates embedded Excel `.xlsx` chart data and labels automatically.
  - Auto-adjusts title font sizes on cover pages for long product names.
- **Dual Interfaces**:
  - **Command Line Interface (CLI)**: Fast batch processing and scripting.
  - **Graphical Interface (GUI)**: Desktop app built with CustomTkinter.
  - **Web & Local Server**: Integrated dev server (`server.py`) and Netlify serverless deployment support.
- **Offline Mode**: Supported via `--no-api` flag with built-in realistic fallback data.

---

## Directory Structure

```
Market Report Genarator d3/
├── src/
│   ├── parser.py          # Extracts structured market data from input DOCX
│   ├── ai_generator.py    # Integrates with OpenRouter API
│   ├── payload_builder.py # Maps AI content & input data to template placeholders
│   ├── renderer.py        # Safe DOCX XML & embedded Excel placeholder replacement
│   ├── cache_manager.py   # Handles TTL caching for API responses
│   └── validator.py       # Pre-rendering payload validation module
├── templates/
│   └── master_template_v1.docx # Master 16-chapter report template
├── prompts/
│   └── generation_prompt.json  # LLM prompt configuration & schema
├── tests/                 # Unit test suite
├── output/                # Output generated DOCX and audit JSON files
├── cache/                 # Cached API responses
├── run.py                 # CLI entry point
├── gui.py                 # Desktop GUI application
├── server.py              # Web API server for local dev or deployment
├── config.json            # Configuration settings
├── .env                   # Environment credentials (API keys & models)
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
```

---

## Prerequisites & Installation

### 1. Requirements
- Python 3.8+
- Node.js (optional, for Web UI / JS frontend integration)

### 2. Environment Setup

Clone or place the project folder on your system and install Python dependencies:

```bash
pip install -r requirements.txt
```

### 3. API Credentials Setup

Create or verify the `.env` file in the project root:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
MODEL=openrouter/free
```

*Note: You can also specify settings in `config.json`.*

---

## Usage Guide

### 1. Command Line Interface (CLI)

Run report generation using an input DOCX document:

```bash
# Basic usage (auto-generates output file name based on market name)
python run.py "Global_BESS_Market_Segmentation.docx"

# Custom output name
python run.py "Global_BESS_Market_Segmentation.docx" "bess_report"

# Offline / Fallback mode (bypasses LLM API calls)
python run.py "Global_BESS_Market_Segmentation.docx" "bess_report" --no-api
```

Output files will be saved to the `output/` directory:
- Word Report: `output/report_<market_name>_<timestamp>.docx`
- Audit JSON: `output/report_<market_name>_<timestamp>.json`

### 2. Desktop GUI Interface

Launch the graphical user interface:

```bash
python gui.py
```

### 3. Web & Local Server

Start the local API development server:

```bash
python server.py
```
The server will start at `http://localhost:8080`.

---

## Running Unit Tests

Run the test suite to verify system integrity:

```bash
python -m unittest discover tests
```

---

## License

Internal Enterprise Application.
