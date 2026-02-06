"""
Autonomous Insurance Claims Processing Agent — Dynamic Dashboard.
Dark theme, pipeline visualization, KPI cards, session state, and full dashboard layout.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st

from src.extractor import extract_fnol_from_file
from src.output_format import (
    build_standard_output,
    get_field_value_for_form,
    get_missing_fields,
    CLAIM_FIELD_SPEC,
)
from src.router import route_fnol
from src.schema import FNOLDocument


# --- Session state keys ---
SK_LAST_FILE = "dashboard_last_file"
SK_RAW_TEXT = "dashboard_raw_text"
SK_FNOL_DOC = "dashboard_fnol_doc"
SK_DECISION = "dashboard_decision"
SK_ERROR = "dashboard_error"
SK_TRIGGER_SAMPLE = "dashboard_trigger_sample"


# --- Dashboard CSS ---
DASHBOARD_CSS = """
<style>
/* Base dark theme */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(160deg, #0f172a 0%, #1e1b4b 45%, #0f172a 100%);
    background-attachment: fixed;
}
[data-testid="stHeader"] { background: rgba(15, 23, 42, 0.92); }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
    border-right: 1px solid #334155;
}
[data-testid="stSidebar"] .stMarkdown { color: #cbd5e1; }

/* Dashboard header strip */
.dash-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
    padding: 0.75rem 0 1.25rem 0;
    border-bottom: 1px solid #334155;
    margin-bottom: 1.5rem;
}
.dash-title-block h1 { font-size: 1.6rem; font-weight: 700; color: #f8fafc; margin: 0; letter-spacing: -0.02em; }
.dash-title-block p { color: #94a3b8; font-size: 0.9rem; margin: 0.35rem 0 0 0; }
.dash-stats {
    display: flex;
    gap: 1rem;
    align-items: center;
    flex-wrap: wrap;
}
.dash-stat {
    background: rgba(30, 41, 59, 0.8);
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 0.5rem 1rem;
    font-size: 0.85rem;
    color: #cbd5e1;
}
.dash-stat strong { color: #f8fafc; margin-right: 0.35rem; }

/* Pipeline steps */
.pipeline-wrap {
    display: flex;
    align-items: center;
    justify-content: space-between;
    max-width: 480px;
    margin: 1rem 0 1.5rem 0;
    padding: 0.75rem 1rem;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid #334155;
    border-radius: 12px;
}
.pipeline-step {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: #64748b;
}
.pipeline-step.done { color: #22c55e; }
.pipeline-step.done .step-num { background: #22c55e; color: #0f172a; }
.pipeline-step.active { color: #0ea5e9; }
.pipeline-step.active .step-num { background: #0ea5e9; color: #fff; }
.step-num {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: #334155;
    color: #94a3b8;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.75rem;
}
.pipeline-conn { flex: 1; height: 2px; background: #334155; margin: 0 0.25rem; max-width: 40px; }
.pipeline-conn.done { background: #22c55e; }

/* KPI / summary cards row */
.kpi-row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin: 1rem 0; }
.kpi-card {
    flex: 1;
    min-width: 140px;
    background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.2);
}
.kpi-card .label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; margin-bottom: 0.35rem; }
.kpi-card .val { font-size: 1rem; font-weight: 600; color: #f1f5f9; word-break: break-word; }
.kpi-card .val.muted { color: #94a3b8; font-weight: 500; }

/* Decision cards */
.styled-card {
    background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin: 0.75rem 0;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.styled-card h4 { color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; margin: 0 0 0.5rem 0; }
.styled-card .value { font-size: 1.35rem; font-weight: 700; color: #f8fafc; }
.route-fast_track   { color: #22c55e !important; border-left: 4px solid #22c55e; }
.route-manual_review { color: #f59e0b !important; border-left: 4px solid #f59e0b; }
.route-investigation { color: #ef4444 !important; border-left: 4px solid #ef4444; }
.route-specialist    { color: #0ea5e9 !important; border-left: 4px solid #0ea5e9; }
.route-standard     { color: #94a3b8 !important; border-left: 4px solid #64748b; }
.badge-ready { background: #14532d; color: #86efac; padding: 0.25rem 0.6rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; }
.badge-review { background: #78350f; color: #fcd34d; padding: 0.25rem 0.6rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; }

.reasoning-list {
    background: #0f172a; border: 1px solid #334155; border-radius: 10px;
    padding: 1rem 1.25rem; margin: 0.75rem 0;
}
.reasoning-list li { color: #cbd5e1; margin: 0.4rem 0; line-height: 1.5; }

.upload-zone {
    border: 2px dashed #475569; border-radius: 12px; padding: 1.25rem;
    background: rgba(30, 41, 59, 0.4); margin-bottom: 1.25rem;
}
.section-title { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8; margin: 1rem 0 0.5rem 0; }

.stTabs [data-baseweb="tab-list"] { background: #1e293b; border-radius: 10px; padding: 4px; gap: 4px; }
.stTabs [data-baseweb="tab"] { color: #94a3b8; border-radius: 8px; }
.stTabs [aria-selected="true"] { background: #334155 !important; color: #f8fafc !important; }

.stButton > button {
    background: linear-gradient(135deg, #0ea5e9 0%, #0369a1 100%) !important;
    color: #fff !important; border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; padding: 0.5rem 1.25rem !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #38bdf8 0%, #0ea5e9 100%) !important;
    box-shadow: 0 4px 14px rgba(14, 165, 233, 0.4) !important;
}
[data-testid="stSidebar"] input { background: #0f172a !important; border: 1px solid #334155 !important; color: #f1f5f9 !important; }
[data-testid="stSidebar"] label { color: #cbd5e1 !important; }

.dash-section { margin-top: 1.5rem; }

/* Claim form */
.form-section {
    background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin: 0.75rem 0;
    box-shadow: 0 2px 12px rgba(0,0,0,0.2);
}
.form-section h5 { color: #0ea5e9; font-size: 0.85rem; margin: 0 0 0.75rem 0; text-transform: uppercase; letter-spacing: 0.06em; }
.form-row { display: flex; gap: 1rem; margin: 0.4rem 0; align-items: flex-start; }
.form-label { min-width: 160px; font-size: 0.8rem; color: #94a3b8; }
.form-value { flex: 1; font-size: 0.9rem; color: #f1f5f9; }
.form-value.missing { color: #64748b; font-style: italic; }
.missing-badge { background: #7f1d1d; color: #fecaca; padding: 0.2rem 0.5rem; border-radius: 6px; font-size: 0.75rem; margin: 0.25rem 0.25rem 0.25rem 0; display: inline-block; }
</style>
"""


def _inject_css():
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)


def _route_display_class(route: str) -> str:
    return f"route-{route}" if route else "route-standard"


def _decision_ready_badge(ready: bool) -> tuple[str, str]:
    return ("Decision ready", "badge-ready") if ready else ("Manual review required", "badge-review")


def _get_holder_name(doc: Optional[FNOLDocument]) -> str:
    if not doc or not doc.parties or not doc.parties.claimant:
        return doc.policy.holder_name if doc and doc.policy and doc.policy.holder_name else "—"
    return doc.parties.claimant.name or (doc.policy.holder_name if doc.policy else "") or "—"


def _get_estimated_damage(doc: Optional[FNOLDocument]) -> Optional[float]:
    if not doc:
        return None
    if doc.asset and doc.asset.estimated_damage is not None:
        return float(doc.asset.estimated_damage)
    if doc.status and doc.status.initial_estimate is not None:
        return float(doc.status.initial_estimate)
    return None


def _render_pipeline_steps(has_raw: bool, has_doc: bool, has_decision: bool):
    step1 = "done" if has_raw else "active" if not has_doc and not has_decision else ""
    step2 = "done" if has_doc else "active" if has_raw and not has_doc else ""
    step3 = "done" if has_decision else "active" if has_doc and not has_decision else ""
    c1 = "done" if has_raw else ""
    c2 = "done" if has_doc else ""
    st.markdown(
        f'<div class="pipeline-wrap">'
        f'<span class="pipeline-step {step1}"><span class="step-num">1</span> Extract</span>'
        f'<span class="pipeline-conn {c1}"></span>'
        f'<span class="pipeline-step {step2}"><span class="step-num">2</span> Validate</span>'
        f'<span class="pipeline-conn {c2}"></span>'
        f'<span class="pipeline-step {step3}"><span class="step-num">3</span> Route</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_kpi_cards(doc: FNOLDocument):
    policy_num = (doc.policy and doc.policy.number) or "—"
    holder = _get_holder_name(doc)
    inc_date = (doc.incident and doc.incident.date) and str(doc.incident.date) or "—"
    damage = _get_estimated_damage(doc)
    damage_str = f"${damage:,.0f}" if damage is not None else "—"
    claim_type = (doc.status and doc.status.claim_type) or "—"
    st.markdown(
        '<div class="kpi-row">'
        f'<div class="kpi-card"><div class="label">Policy #</div><div class="val">{policy_num}</div></div>'
        f'<div class="kpi-card"><div class="label">Holder / Claimant</div><div class="val muted">{holder[:24]}{"…" if len(holder) > 24 else ""}</div></div>'
        f'<div class="kpi-card"><div class="label">Incident date</div><div class="val">{inc_date}</div></div>'
        f'<div class="kpi-card"><div class="label">Est. damage</div><div class="val">{damage_str}</div></div>'
        f'<div class="kpi-card"><div class="label">Claim type</div><div class="val">{claim_type}</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_dashboard_header(last_file: Optional[str], decision: Any):
    route_label = "—"
    status_label = "—"
    if decision:
        route_label = decision.recommended_route.replace("_", " ").title()
        status_label = "Decision ready" if decision.is_decision_ready else "Manual review"
    stats_html = ""
    if last_file:
        stats_html = f'<span class="dash-stat"><strong>File</strong> {last_file}</span>'
    if decision:
        stats_html += f'<span class="dash-stat"><strong>Route</strong> {route_label}</span>'
        stats_html += f'<span class="dash-stat"><strong>Status</strong> {status_label}</span>'
    st.markdown(
        '<div class="dash-header">'
        '<div class="dash-title-block">'
        '<h1>📋 Autonomous Insurance Claims Processing Agent</h1>'
        '<p>First Notice of Loss (FNOL) — Extract, Validate, Route</p>'
        '</div>'
        f'<div class="dash-stats">{stats_html or "<span class=\"dash-stat\">Upload a file to start</span>"}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def run_app():
    st.set_page_config(
        page_title="FNOL Claims Agent",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_css()

    # Session state init
    if SK_LAST_FILE not in st.session_state:
        st.session_state[SK_LAST_FILE] = None
    if SK_RAW_TEXT not in st.session_state:
        st.session_state[SK_RAW_TEXT] = None
    if SK_FNOL_DOC not in st.session_state:
        st.session_state[SK_FNOL_DOC] = None
    if SK_DECISION not in st.session_state:
        st.session_state[SK_DECISION] = None
    if SK_ERROR not in st.session_state:
        st.session_state[SK_ERROR] = None
    if SK_TRIGGER_SAMPLE not in st.session_state:
        st.session_state[SK_TRIGGER_SAMPLE] = False

    last_file = st.session_state[SK_LAST_FILE]
    raw_text = st.session_state[SK_RAW_TEXT]
    fnol_doc: Optional[FNOLDocument] = st.session_state.get(SK_FNOL_DOC)
    decision = st.session_state.get(SK_DECISION)
    err_msg = st.session_state.get(SK_ERROR)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        api_key = st.text_input(
            "OpenAI API Key",
            value=os.environ.get("OPENAI_API_KEY", ""),
            type="password",
            help="Or set OPENAI_API_KEY in environment.",
        )
        model = st.text_input("Model", value="gpt-4o", help="Extraction model.")
        use_llm = st.checkbox("Use LLM extraction (GPT-4o)", value=True)
        st.markdown("---")
        st.subheader("Session")
        if last_file:
            st.caption(f"Last processed: **{last_file}**")
        if last_file or raw_text or fnol_doc or decision:
            if st.button("Clear session"):
                for key in [SK_LAST_FILE, SK_RAW_TEXT, SK_FNOL_DOC, SK_DECISION, SK_ERROR]:
                    st.session_state[key] = None
                st.rerun()
        else:
            st.caption("No claim processed yet.")
        st.markdown("---")
        st.subheader("Routing rules")
        st.caption(
            "• Damage < $25,000 → **Fast-track**\n"
            "• Mandatory field missing → **Manual review**\n"
            "• Words: fraud, inconsistent, staged → **Investigation**\n"
            "• Claim type = injury → **Specialist queue**"
        )
        st.markdown("---")
        st.caption("Upload a PDF or TXT FNOL, or load the sample claim.")

    # Header with dynamic stats
    _render_dashboard_header(last_file, decision)

    # Upload zone (always visible) + Load sample
    st.markdown('<p class="section-title">Upload document</p>', unsafe_allow_html=True)
    col_upload, col_sample = st.columns([3, 1])
    with col_upload:
        st.markdown('<div class="upload-zone">', unsafe_allow_html=True)
        uploaded = st.file_uploader(
            "Choose PDF or TXT",
            type=["pdf", "txt"],
            help="FNOL document to extract and route.",
            label_visibility="collapsed",
        )
        st.markdown('</div>', unsafe_allow_html=True)
    with col_sample:
        if st.button("📄 Load sample claim", help="Load sample FNOL with all fields populated"):
            st.session_state[SK_TRIGGER_SAMPLE] = True
            st.rerun()

    # If Load sample was triggered: run pipeline on sample file and update session
    if st.session_state.get(SK_TRIGGER_SAMPLE):
        st.session_state[SK_TRIGGER_SAMPLE] = False
        sample_path = _project_root / "sample_fnol_full.txt"
        if sample_path.exists():
            with st.spinner("Running pipeline on sample claim…"):
                raw_text, fnol_doc, err_msg = extract_fnol_from_file(
                    sample_path,
                    use_llm=use_llm,
                    model=model,
                    api_key=api_key or None,
                )
            st.session_state[SK_ERROR] = err_msg
            st.session_state[SK_RAW_TEXT] = raw_text
            st.session_state[SK_FNOL_DOC] = fnol_doc
            st.session_state[SK_DECISION] = route_fnol(fnol_doc) if fnol_doc else None
            st.session_state[SK_LAST_FILE] = "sample_fnol_full.txt" if not err_msg else last_file
            st.rerun()
        else:
            st.warning("Sample file not found: sample_fnol_full.txt")

    # If new file uploaded, run pipeline and update session
    if uploaded:
        temp_dir = Path(_project_root) / "temp_uploads"
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / uploaded.name
        try:
            temp_path.write_bytes(uploaded.getvalue())
        except Exception as e:
            st.session_state[SK_ERROR] = str(e)
            st.rerun()
        with st.spinner("Running pipeline: Extract → Validate → Route…"):
            raw_text, fnol_doc, err_msg = extract_fnol_from_file(
                temp_path,
                use_llm=use_llm,
                model=model,
                api_key=api_key or None,
            )
        # Uploaded file is kept in temp_uploads (not deleted)
        st.session_state[SK_ERROR] = err_msg
        st.session_state[SK_RAW_TEXT] = raw_text
        st.session_state[SK_FNOL_DOC] = fnol_doc
        st.session_state[SK_DECISION] = route_fnol(fnol_doc) if fnol_doc else None
        if not err_msg:
            st.session_state[SK_LAST_FILE] = uploaded.name
        st.rerun()

    # Show error from last run if any
    if err_msg and not uploaded:
        st.error(f"Extraction error: {err_msg}")
        if raw_text:
            with st.expander("Raw extracted text"):
                st.text_area("", value=raw_text, height=200, disabled=True, label_visibility="collapsed")

    # Pipeline steps (dynamic based on session)
    has_raw = bool(raw_text)
    has_doc = fnol_doc is not None
    has_decision = decision is not None
    _render_pipeline_steps(has_raw, has_doc, has_decision)

    # When we have no result yet, stop here (only upload + pipeline steps)
    if not has_doc and not decision:
        if not uploaded and not last_file:
            st.info("Upload a FNOL document to see extraction results and routing.")
        return

    # KPI summary cards (from last or current result)
    st.markdown('<p class="section-title">Claim summary</p>', unsafe_allow_html=True)
    if fnol_doc:
        _render_kpi_cards(fnol_doc)
    else:
        st.caption("No structured data (enable LLM extraction and process a file).")

    # Claim form — all extracted fields by section
    if fnol_doc:
        st.markdown('<p class="section-title">Claim form (all fields)</p>', unsafe_allow_html=True)
        missing_list = get_missing_fields(fnol_doc)
        sections = [
            ("Policy Information", ["Policy Number", "Policyholder Name", "Effective Date Start", "Effective Date End"]),
            ("Incident Information", ["Incident Date", "Incident Time", "Location", "Description"]),
            ("Involved Parties", ["Claimant", "Third Parties", "Contact Phone", "Contact Email", "Contact Address"]),
            ("Asset Details", ["Asset Type", "Asset ID", "Estimated Damage"]),
            ("Other Mandatory Fields", ["Claim Type", "Attachments", "Initial Estimate"]),
        ]
        for section_title, field_labels in sections:
            rows_html = ""
            for label in field_labels:
                val = get_field_value_for_form(fnol_doc, label)
                is_missing = label in missing_list
                val_class = "form-value missing" if is_missing else "form-value"
                val_esc = str(val).replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                rows_html += f'<div class="form-row"><span class="form-label">{label}</span><span class="{val_class}">{val_esc}</span></div>'
            st.markdown(
                f'<div class="form-section"><h5>{section_title}</h5>{rows_html}</div>',
                unsafe_allow_html=True,
            )
        if missing_list:
            st.markdown("**Missing fields**")
            missing_html = "".join(f'<span class="missing-badge">{m}</span>' for m in missing_list)
            st.markdown(f'<div>{missing_html}</div>', unsafe_allow_html=True)

    # Decision panel (main dashboard block)
    st.markdown('<p class="section-title">Routing decision</p>', unsafe_allow_html=True)
    if decision:
        route_label = decision.recommended_route.replace("_", " ").title()
        status_text, badge_class = _decision_ready_badge(decision.is_decision_ready)
        route_class = _route_display_class(decision.recommended_route)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f'<div class="styled-card {route_class}" style="padding-left: 1rem;">'
                f'<h4>Recommended route</h4><div class="value">{route_label}</div></div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f'<div class="styled-card"><h4>Status</h4><div><span class="{badge_class}">{status_text}</span></div></div>',
                unsafe_allow_html=True,
            )
        st.markdown("**Reasoning**")
        reasoning_html = "<ul class='reasoning-list' style='list-style: disc; margin-left: 1.25rem;'>"
        for r in decision.reasoning:
            reasoning_html += f"<li>{r}</li>"
        reasoning_html += "</ul>"
        st.markdown(reasoning_html, unsafe_allow_html=True)
        if decision.flags:
            st.markdown("**Flags**")
            st.code(", ".join(decision.flags), language=None)
        if fnol_doc:
            standard = build_standard_output(fnol_doc, decision)
            full_output = {
                "recommended_route": decision.recommended_route,
                "reasoning": decision.reasoning,
                "flags": decision.flags,
                "is_decision_ready": decision.is_decision_ready,
                "extracted_data": fnol_doc.model_dump(mode="json"),
            }
            cdl, cds = st.columns(2)
            with cdl:
                st.download_button(
                    "Download standard output (JSON)",
                    data=json.dumps(standard, indent=2, default=str),
                    file_name="fnol_standard_output.json",
                    mime="application/json",
                    key="standard_dl",
                )
            with cds:
                st.download_button(
                    "Download full decision JSON",
                    data=json.dumps(full_output, indent=2, default=str),
                    file_name="fnol_decision.json",
                    mime="application/json",
                    key="decision_dl",
                )

    # Tabs: Raw text | Structured JSON
    st.markdown('<p class="section-title">Data & export</p>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📄 Raw extraction", "📊 Structured JSON"])
    with tab1:
        st.text_area("Raw text", value=raw_text or "", height=300, disabled=True, label_visibility="collapsed")
    with tab2:
        if fnol_doc:
            data = fnol_doc.model_dump(mode="json")
            st.json(data)
            st.download_button(
                "Download extraction JSON",
                data=json.dumps(data, indent=2, default=str),
                file_name="fnol_extraction.json",
                mime="application/json",
                key="extraction_dl",
            )
        else:
            st.info("Enable LLM extraction and process a file to see structured data.")


if __name__ == "__main__":
    run_app()
