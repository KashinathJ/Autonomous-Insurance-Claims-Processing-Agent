"""
FNOL document extraction: PDF/TXT to text, then GPT-4o for structured extraction.
Uses PyMuPDF for PDF and langchain-openai for LLM extraction with Pydantic output.
"""

import json
import logging
from pathlib import Path
from typing import Union

import fitz  # PyMuPDF

from .schema import FNOLDocument

logger = logging.getLogger(__name__)

# Optional: try pdfplumber if fitz fails (fallback)
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


def extract_text_from_file(file_path: Union[str, Path]) -> str:
    """
    Extract raw text from a PDF or TXT file.
    Uses PyMuPDF (fitz) for PDF; falls back to pdfplumber if needed.
    Path can be a string or Path; works with uploaded Streamlit file objects
    via a temporary path when saved to disk.
    """
    path = Path(file_path) if not isinstance(file_path, Path) else file_path
    suffix = path.suffix.lower()

    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")

    if suffix == ".pdf":
        try:
            doc = fitz.open(path)
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            return "\n".join(text_parts).strip() or "(No text extracted from PDF)"
        except Exception as e:
            logger.warning("PyMuPDF failed for %s: %s", path, e)
            if HAS_PDFPLUMBER:
                with pdfplumber.open(path) as pdf:
                    text_parts = []
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            text_parts.append(t)
                    return "\n".join(text_parts).strip() or "(No text extracted from PDF)"
            raise RuntimeError(f"PDF extraction failed: {e}") from e

    raise ValueError(f"Unsupported file type: {suffix}. Use .pdf or .txt.")


def _parse_date(value: str | None):
    """Parse date string to YYYY-MM-DD for Pydantic date fields."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    from datetime import datetime
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y"):
        try:
            s = value[:10] if len(value) > 10 else value
            return datetime.strptime(s, fmt).date()
        except (ValueError, TypeError):
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


def _normalize_llm_json(raw: dict) -> dict:
    """Normalize LLM output so it fits our schema (e.g. date strings -> date)."""
    def walk(obj):
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                key = k.replace(" ", "_").replace("-", "_").lower()
                if "date" in key and isinstance(v, str) and "time" not in key:
                    out[k] = _parse_date(v)
                else:
                    out[k] = walk(v)
            return out
        if isinstance(obj, list):
            return [walk(x) for x in obj]
        return obj
    return walk(raw)


def extract_fnol_with_llm(
    raw_text: str,
    *,
    model: str = "gpt-4o",
    api_key: str | None = None,
    temperature: float = 0.0,
) -> FNOLDocument:
    """
    Send raw FNOL text to GPT-4o and get a structured FNOLDocument.
    Uses langchain-openai and enforces schema via prompt + JSON parsing.
    """
    import os
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage
    from langchain_core.output_parsers import PydanticOutputParser

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "OPENAI_API_KEY not set. Set it in environment or pass api_key=..."
        )

    parser = PydanticOutputParser(pydantic_object=FNOLDocument)
    format_instructions = parser.get_format_instructions()

    prompt = f"""You are an expert insurance claims analyst. Extract structured data from the following First Notice of Loss (FNOL) document text.

Output ONLY valid JSON that conforms to this schema. Use null for missing values. For dates use YYYY-MM-DD.

Schema summary:
- policy: number, holder_name, effective_date_start, effective_date_end
- incident: date, time, location, description
- parties: claimant (name, role, contact), third_parties (list), contact_details
- asset: type, id, estimated_damage, currency
- status: claim_type, attachments (list), initial_estimate, initial_estimate_currency

{format_instructions}

FNOL document text:
---
{raw_text[:12000]}
---

JSON output:"""

    llm = ChatOpenAI(model=model, temperature=temperature, api_key=key)
    response = llm.invoke([HumanMessage(content=prompt)])
    text = response.content.strip()

    # Strip markdown code block if present
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.exception("LLM returned invalid JSON: %s", text[:500])
        raise ValueError(f"LLM response was not valid JSON: {e}") from e

    data = _normalize_llm_json(data)
    return FNOLDocument.model_validate(data)


def extract_fnol_from_file(
    file_path: Union[str, Path],
    *,
    use_llm: bool = True,
    model: str = "gpt-4o",
    api_key: str | None = None,
) -> tuple[str, FNOLDocument | None, str | None]:
    """
    Extract text from file and optionally run LLM extraction.
    Returns (raw_text, fnol_document or None, error_message or None).
    """
    raw_text = extract_text_from_file(file_path)
    if not use_llm:
        return raw_text, None, None
    try:
        doc = extract_fnol_with_llm(raw_text, model=model, api_key=api_key)
        return raw_text, doc, None
    except Exception as e:
        logger.exception("LLM extraction failed")
        return raw_text, None, str(e)
