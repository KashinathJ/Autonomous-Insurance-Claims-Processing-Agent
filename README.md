# 📋 Autonomous Insurance Claims Processing Agent

A **production-ready** pipeline for **First Notice of Loss (FNOL)** document intake and routing. Upload PDF or TXT claim documents, extract structured data with GPT-4o, validate mandatory fields, apply routing rules, and get a decision-ready JSON output—all through a dark-themed Streamlit dashboard.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [Usage](#usage)
- [Fields Extracted](#fields-extracted)
- [Routing Rules](#routing-rules)
- [Output Format](#output-format)
- [Uploaded Files Storage](#uploaded-files-storage)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

- **Document intake**: Upload PDF or TXT FNOL documents; files are stored in `temp_uploads/` for reference.
- **Text extraction**: PyMuPDF (with pdfplumber fallback) for reliable PDF/TXT text extraction.
- **LLM extraction**: GPT-4o via LangChain for high-accuracy structured extraction into a Pydantic schema.
- **Validation**: Pydantic v2 for strict schema enforcement and type-safe data.
- **Routing engine**: Deterministic, rule-based routing (fast-track, manual review, investigation, specialist, standard).
- **Dashboard**: Dark-themed Streamlit UI with pipeline steps, KPI cards, full claim form view, and missing-fields display.
- **Sample claim**: One-click “Load sample claim” using a fully populated sample FNOL.
- **Exports**: Standard output JSON (`extractedFields`, `missingFields`, `recommendedRoute`, `reasoning`) and full decision JSON.

---

## Tech Stack

| Component        | Technology |
|------------------|------------|
| PDF extraction   | PyMuPDF (fitz), fallback: pdfplumber |
| LLM extraction  | langchain-openai (GPT-4o) |
| Data validation | Pydantic v2 |
| Routing         | Python rule engine (`src/router.py`) |
| UI              | Streamlit (dark theme) |

---

## Project Structure

```
Assingment/
├── .streamlit/
│   └── config.toml          # Streamlit theme (dark) and server options
├── src/
│   ├── __init__.py
│   ├── schema.py            # Pydantic models (Policy, Incident, Parties, Asset, Status, FNOLDocument)
│   ├── extractor.py         # PDF/TXT → text, then GPT-4o → structured extraction
│   ├── router.py            # Routing rules (fast-track, manual review, investigation, specialist)
│   ├── output_format.py     # Standard output (extractedFields, missingFields, reasoning)
│   └── app.py               # Streamlit dashboard and claim form
├── temp_uploads/             # Uploaded documents stored here (created on first upload)
├── run_app.py               # Entry point (run from project root)
├── requirements.txt
├── sample_fnol.txt          # Minimal sample FNOL
├── sample_fnol_full.txt     # Full sample with all fields (all insights)
├── .gitignore
├── LICENSE
└── README.md
```

---

## Prerequisites

- **Python 3.9+**
- **OpenAI API key** (for GPT-4o extraction)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/KashinathJ/Autonomous-Insurance-Claims-Processing-Agent.git
cd Autonomous-Insurance-Claims-Processing-Agent
```

*(If you already have the project folder, just `cd` into it.)*

### 2. Create and activate a virtual environment

**Windows (PowerShell / CMD):**

```bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set your OpenAI API key

**Windows (PowerShell):**

```powershell
$env:OPENAI_API_KEY = "your-api-key-here"
```

**Windows (CMD):**

```cmd
set OPENAI_API_KEY=your-api-key-here
```

**macOS / Linux:**

```bash
export OPENAI_API_KEY=your-api-key-here
```

You can also enter the API key in the app sidebar after launching.

---

## Configuration

| Setting | Description |
|--------|-------------|
| **OpenAI API Key** | Required for LLM extraction. Set in env or in the sidebar. |
| **Model** | OpenAI model for extraction (default: `gpt-4o`). |
| **Use LLM extraction** | When checked, runs GPT-4o extraction; when unchecked, only raw text extraction is performed. |

---

## Running the App

From the **project root** (where `run_app.py` and `src/` are):

**Option A – Entry script (recommended):**

```bash
python run_app.py
```

**Option B – Streamlit CLI:**

```bash
streamlit run src/app.py
```

The app opens in your browser at **http://localhost:8501**.

---

## Usage

1. **Upload**: Use “Upload document” to choose a PDF or TXT FNOL file. It is saved under `temp_uploads/` and processed.
2. **Load sample**: Click **“Load sample claim”** to run the pipeline on `sample_fnol_full.txt` (all fields populated).
3. **Pipeline**: The UI shows **Extract → Validate → Route**; after processing you get:
   - **Claim summary** (KPI cards)
   - **Claim form (all fields)** with every extracted field by section
   - **Missing fields** (if any)
   - **Routing decision** (recommended route, reasoning, flags)
4. **Export**: Download **standard output (JSON)** or **full decision JSON** from the decision panel, and **extraction JSON** from the Data & export tab.

---

## Fields Extracted

| Section | Fields |
|---------|--------|
| **Policy** | Policy Number, Policyholder Name, Effective Date Start, Effective Date End |
| **Incident** | Incident Date, Time, Location, Description |
| **Parties** | Claimant, Third Parties, Contact Phone, Email, Address |
| **Asset** | Asset Type, Asset ID, Estimated Damage |
| **Other** | Claim Type, Attachments, Initial Estimate |

---

## Routing Rules

Rules are applied in this order:

| Priority | Condition | Route |
|----------|-----------|--------|
| 1 | Any mandatory field missing (Policy #, Policyholder/claimant name, Incident date) | **Manual review** |
| 2 | Description contains “fraud”, “inconsistent”, or “staged” | **Investigation** |
| 3 | Claim type = **injury** | **Specialist queue** |
| 4 | Estimated damage **&lt; $25,000** | **Fast-track** |
| 5 | Otherwise | **Standard** |

---

## Output Format

### Standard output JSON

Download **“Download standard output (JSON)”** to get:

```json
{
  "extractedFields": {
    "policy": { ... },
    "incident": { ... },
    "parties": { ... },
    "asset": { ... },
    "status": { ... }
  },
  "missingFields": ["Contact Email", "Attachments"],
  "recommendedRoute": "fast_track",
  "reasoning": "Estimated damage (18500) is below 25000. Fast-track eligible."
}
```

- **extractedFields**: Full extracted FNOL (nested).
- **missingFields**: List of field labels that were empty.
- **recommendedRoute**: One of `fast_track`, `manual_review`, `investigation`, `specialist`, `standard`.
- **reasoning**: Single string summarizing why that route was chosen.

---

## Uploaded Files Storage

All uploaded documents are saved in the **`temp_uploads/`** directory (created automatically on first upload). Files are **not** deleted after processing so you can keep a local record of submitted FNOLs. The folder is listed in `.gitignore` so uploads are not committed to the repository.

---

## Troubleshooting

| Issue | Suggestion |
|-------|------------|
| `pip install` fails with “file is being used” | Close other terminals/IDEs using the venv, then run `pip install -r requirements.txt` again. |
| `OPENAI_API_KEY` not set | Set the env variable or enter the key in the Streamlit sidebar. |
| “Sample file not found” | Ensure `sample_fnol_full.txt` exists in the project root (it is included in the repo). |
| Port 8501 in use | Run with `streamlit run src/app.py --server.port 8502` (or another port). |

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
"# Autonomous-Insurance-Claims-Processing-Agent" 
