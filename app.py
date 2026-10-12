"""LibTrial — Professional Evidence-Backed Library Evaluation Suite."""
import os
from typing import List, Optional
import streamlit as st

from libtrial.candidate_discovery import CandidateDiscovery
from libtrial.compatibility import evaluate_compatibility
from libtrial.config import get_settings
from libtrial.llm_client import ConfigurationError, GemmaClient
from libtrial.models import (
    CandidateEvaluation,
    CompatibilityVerdict,
    ProjectProfile,
    TrialOutcome,
    TrialResult,
)
from libtrial.pypi_client import PyPIClient
from libtrial.repo_inspector import inspect_repository
from libtrial.report_generator import generate_markdown_report
from libtrial.trial_runner import (
    generate_probe_script,
    is_docker_available,
    run_isolated_trial,
    validate_probe_safety,
)

st.set_page_config(
    page_title="LibTrial — Evidence-Backed Library Evaluation",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

_THEME_CSS = """
<style>
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap");

html, body, [class*="css"] {
    font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif !important;
}

.stApp {
    background: radial-gradient(circle at 10% 20%, #0d1527 0%, #080d1a 100%) !important;
    color: #e2e8f0 !important;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton, [data-testid="stToolbar"] { display: none; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b1120 0%, #0f172a 100%) !important;
    border-right: 1px solid rgba(99, 179, 237, 0.12) !important;
}
[data-testid="stSidebar"] * { color: #cbd5e0 !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #f1f5f9 !important;
    font-weight: 700 !important;
}

.block-container {
    padding: 1.25rem 2.5rem 3.5rem !important;
    max-width: 1440px !important;
}

/* NAVBAR */
.top-navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(15, 23, 42, 0.75);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(99, 179, 237, 0.15);
    border-radius: 16px;
    padding: 0.85rem 1.5rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}
.nav-brand-group {
    display: flex;
    align-items: center;
    gap: 0.85rem;
}
.nav-logo-box {
    width: 42px;
    height: 42px;
    background: linear-gradient(135deg, rgba(99, 179, 237, 0.2), rgba(139, 92, 246, 0.25));
    border: 1px solid rgba(99, 179, 237, 0.35);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.35rem;
}
.nav-brand-title {
    font-size: 1.35rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #60a5fa, #c084fc, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.1;
}
.nav-brand-sub {
    font-size: 0.74rem;
    color: #94a3b8;
    font-weight: 500;
}
.nav-meta-group {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    flex-wrap: wrap;
}
.nav-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.nav-badge-blue {
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.3);
    color: #93c5fd;
}
.nav-badge-purple {
    background: rgba(168, 85, 247, 0.12);
    border: 1px solid rgba(168, 85, 247, 0.3);
    color: #d8b4fe;
}
.nav-badge-green {
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #6ee7b7;
}

/* WORKFLOW PROGRESS STEPPER */
.stepper-container {
    display: flex;
    align-items: center;
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(99, 179, 237, 0.12);
    border-radius: 14px;
    padding: 0.85rem 1.75rem;
    margin-bottom: 1.75rem;
}
.stepper-step {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    position: relative;
}
.stepper-step:not(:last-child)::after {
    content: "";
    position: absolute;
    top: 16px;
    left: calc(50% + 22px);
    right: calc(-50% + 22px);
    height: 2px;
    background: rgba(99, 179, 237, 0.15);
    z-index: 0;
}
.stepper-step.done:not(:last-child)::after {
    background: rgba(16, 185, 129, 0.45);
}
.stepper-icon {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 700;
    border: 2px solid rgba(99, 179, 237, 0.2);
    background: rgba(15, 23, 42, 0.9);
    color: #64748b;
    z-index: 1;
}
.stepper-icon.done {
    background: rgba(16, 185, 129, 0.2);
    border-color: #34d399;
    color: #34d399;
}
.stepper-icon.active {
    background: rgba(59, 130, 246, 0.25);
    border-color: #60a5fa;
    color: #60a5fa;
    box-shadow: 0 0 14px rgba(96, 165, 250, 0.35);
}
.stepper-label {
    font-size: 0.68rem;
    margin-top: 0.35rem;
    color: #64748b;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.stepper-label.done { color: #34d399; }
.stepper-label.active { color: #60a5fa; font-weight: 700; }

/* SECTION CARDS */
.section-panel {
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(99, 179, 237, 0.14);
    border-radius: 16px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.25rem;
    backdrop-filter: blur(8px);
}
.section-header-title {
    font-size: 1.22rem;
    font-weight: 700;
    color: #f1f5f9;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section-header-sub {
    color: #94a3b8;
    font-size: 0.82rem;
    margin-top: 0.2rem;
    margin-bottom: 0.85rem;
}

/* METRICS */
.metric-row {
    display: flex;
    gap: 0.85rem;
    flex-wrap: wrap;
    margin: 0.85rem 0 1.25rem;
}
.metric-tile {
    flex: 1;
    min-width: 130px;
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(99, 179, 237, 0.15);
    border-radius: 12px;
    padding: 0.9rem 1rem;
    text-align: center;
}
.metric-value {
    font-size: 1.45rem;
    font-weight: 800;
    color: #60a5fa;
    line-height: 1.1;
    word-break: break-all;
}
.metric-label {
    font-size: 0.68rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 0.3rem;
    font-weight: 600;
}

/* STAGE 3 CARDS — BALANCED & COLLISION-FREE */
.cand-card {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(99, 179, 237, 0.18);
    border-radius: 14px;
    padding: 1.25rem;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 440px;
    height: 100%;
    margin-bottom: 0.5rem;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.25);
    transition: transform 0.2s, border-color 0.2s;
    overflow: hidden;
    word-break: break-word;
}
.cand-card:hover {
    border-color: rgba(99, 179, 237, 0.45);
    transform: translateY(-2px);
}
.cand-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.75rem;
    gap: 0.5rem;
}
.cand-title {
    font-size: 1.2rem;
    font-weight: 800;
    color: #f8fafc;
    font-family: "JetBrains Mono", monospace;
}
.cand-ver-badge {
    font-size: 0.75rem;
    color: #34d399;
    font-weight: 600;
    background: rgba(52, 211, 153, 0.1);
    border: 1px solid rgba(52, 211, 153, 0.25);
    border-radius: 6px;
    padding: 0.1rem 0.45rem;
    margin-left: 0.4rem;
}
.status-pill-ok {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 700;
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.35);
    white-space: nowrap;
}
.status-pill-err {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    font-size: 0.68rem;
    font-weight: 700;
    background: rgba(239, 68, 68, 0.15);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.35);
    white-space: nowrap;
}
.compat-banner {
    padding: 0.35rem 0.65rem;
    border-radius: 8px;
    font-size: 0.74rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.compat-green {
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #6ee7b7;
}
.compat-yellow {
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.3);
    color: #fcd34d;
}
.compat-blue {
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.3);
    color: #93c5fd;
}
.cand-details-table {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    margin-bottom: 0.75rem;
}
.cand-row {
    display: flex;
    align-items: flex-start;
    font-size: 0.8rem;
    gap: 0.5rem;
    width: 100%;
}
.cand-lbl {
    color: #64748b;
    font-size: 0.74rem;
    min-width: 96px;
    max-width: 96px;
    flex-shrink: 0;
    font-weight: 500;
}
.cand-val {
    color: #e2e8f0;
    flex: 1 1 0%;
    min-width: 0;
    word-break: break-word;
    overflow-wrap: anywhere;
}
.cand-src {
    color: #64748b;
    font-size: 0.68rem;
    font-style: italic;
    margin-left: 0.35rem;
}
.cand-hypo-box {
    background: rgba(30, 41, 59, 0.45);
    border: 1px solid rgba(99, 179, 237, 0.1);
    border-radius: 10px;
    padding: 0.65rem 0.8rem;
    font-size: 0.78rem;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    margin-top: auto;
}

/* FOOTER */
.app-footer {
    background: rgba(15, 23, 42, 0.75);
    border-top: 1px solid rgba(99, 179, 237, 0.15);
    border-radius: 16px;
    padding: 2rem 2.25rem 1.5rem;
    margin-top: 3rem;
}
.footer-grid {
    display: grid;
    grid-template-columns: 2fr 1.3fr 1.3fr;
    gap: 2rem;
    margin-bottom: 1.5rem;
}
@media (max-width: 900px) {
    .footer-grid { grid-template-columns: 1fr; gap: 1.25rem; }
}
.footer-title {
    font-size: 1.15rem;
    font-weight: 800;
    color: #f1f5f9;
    margin-bottom: 0.4rem;
}
.footer-desc {
    color: #94a3b8;
    font-size: 0.82rem;
    line-height: 1.6;
    margin-bottom: 0.85rem;
}
.footer-col-head {
    font-size: 0.85rem;
    font-weight: 700;
    color: #e2e8f0;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.65rem;
}
.footer-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
}
.footer-list li {
    font-size: 0.78rem;
    color: #94a3b8;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.footer-bottom {
    border-top: 1px solid rgba(99, 179, 237, 0.1);
    padding-top: 1rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.74rem;
    color: #64748b;
    flex-wrap: wrap;
    gap: 0.5rem;
}

/* BUTTONS & CONTROLS */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb, #6366f1) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="secondary"] {
    background: rgba(99, 179, 237, 0.08) !important;
    border: 1px solid rgba(99, 179, 237, 0.3) !important;
    color: #93c5fd !important;
}
.stTextInput input, .stTextArea textarea {
    background: rgba(15, 23, 42, 0.8) !important;
    border: 1px solid rgba(99, 179, 237, 0.2) !important;
    border-radius: 10px !important;
    color: #f1f5f9 !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: rgba(99, 179, 237, 0.5) !important;
    box-shadow: 0 0 0 3px rgba(99, 179, 237, 0.12) !important;
}
.stDownloadButton > button {
    border-radius: 10px !important;
    background: linear-gradient(135deg, #059669, #10b981) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3) !important;
}
.stExpander {
    border: 1px solid rgba(99, 179, 237, 0.12) !important;
    border-radius: 10px !important;
    background: rgba(15, 23, 42, 0.45) !important;
}
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.5); }
::-webkit-scrollbar-thumb { background: rgba(99, 179, 237, 0.25); border-radius: 99px; }
</style>
"""

st.markdown(_THEME_CSS, unsafe_allow_html=True)

# Helper functions
def clean_license_display(lic: Optional[str]) -> str:
    """Safely extracts a clean license name from potentially long PyPI legal text."""
    if not lic:
        return "Not stated"
    lic_upper = lic.upper()
    if "MIT" in lic_upper:
        return "MIT License"
    if "APACHE" in lic_upper:
        return "Apache 2.0"
    if "BSD" in lic_upper:
        return "BSD License"
    if "GPL" in lic_upper:
        return "GPL License"
    if "MPL" in lic_upper or "MOZILLA" in lic_upper:
        return "MPL 2.0"
    first_line = lic.split("\n")[0].strip()
    if len(first_line) > 28:
        return first_line[:25] + "…"
    return first_line or "Not stated"

# Session State Initialization
_DEFAULTS = {
    "profile": None,
    "requirement": "",
    "project_path_val": "examples/sample_project",
    "evaluations": [],
    "selected_candidate": None,
    "probe_code": None,
    "trial_result": None,
    "report_markdown": None,
}
for key, default in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

settings = get_settings()

def is_step_done(num: int) -> bool:
    if num == 1:
        return st.session_state["profile"] is not None
    if num in (2, 3):
        return bool(st.session_state["evaluations"])
    if num == 4:
        return st.session_state["trial_result"] is not None
    return False

def current_active_step() -> int:
    for n in (1, 2, 4, 5):
        if not is_step_done(n):
            return n
    return 5

def _h(html_str: str) -> None:
    st.markdown(html_str, unsafe_allow_html=True)

# =========================================================
# TOP NAVIGATION HEADER
# =========================================================
docker_ok = is_docker_available()
api_key_ok = settings.has_api_key

_h(f"""
<header class="top-navbar">
  <div class="nav-brand-group">
    <div class="nav-logo-box">🧪</div>
    <div>
      <div class="nav-brand-title">LibTrial</div>
      <div class="nav-brand-sub">Evidence-Backed Python Library Evaluation Suite</div>
    </div>
  </div>
  <div class="nav-meta-group">
    <span class="nav-badge nav-badge-blue">🤖 {settings.gemma_model}</span>
    <span class="nav-badge nav-badge-purple">📦 PyPI JSON API</span>
    <span class="nav-badge nav-badge-green">{'🐳 Docker Ready' if docker_ok else '⚠️ Host-Safe Mode'}</span>
  </div>
</header>
""")

# =========================================================
# WORKFLOW STEPPER BAR
# =========================================================
stepper_html = '<div class="stepper-container">'
steps_meta = [
    (1, "PROJECT"),
    (2, "DISCOVER"),
    (3, "VERIFY"),
    (4, "TRIAL"),
    (5, "REPORT"),
]
active_idx = current_active_step()
for n, label in steps_meta:
    done = is_step_done(n)
    active = (n == active_idx and not done)
    css = "done" if done else ("active" if active else "")
    icon_text = "✓" if done else str(n)
    stepper_html += f"""
    <div class="stepper-step {css}">
      <div class="stepper-icon {css}">{icon_text}</div>
      <div class="stepper-label {css}">{label}</div>
    </div>
    """
stepper_html += '</div>'
_h(stepper_html)

# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    _h('<div style="font-size:1.25rem;font-weight:800;color:#f1f5f9;margin-bottom:0.25rem;">🧪 LibTrial Control</div>')
    _h('<div style="color:#64748b;font-size:0.75rem;margin-bottom:1rem;">Empirical Verification Engine</div>')

    if api_key_ok:
        k = settings.gemini_api_key
        masked_key = k[:4] + "···" + k[-4:] if len(k) > 8 else "••••••••"
        _h(f"""
        <div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);border-radius:10px;padding:0.65rem 0.85rem;margin-bottom:0.75rem;">
          <div style="color:#34d399;font-size:0.72rem;font-weight:700;">✅ GEMINI API CONNECTED</div>
          <div style="color:#94a3b8;font-size:0.7rem;font-family:monospace;margin-top:0.2rem;">{masked_key}</div>
          <div style="color:#c084fc;font-size:0.68rem;margin-top:0.15rem;">Model: {settings.gemma_model}</div>
        </div>
        """)
    else:
        _h("""
        <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:10px;padding:0.65rem 0.85rem;margin-bottom:0.75rem;">
          <div style="color:#f87171;font-size:0.72rem;font-weight:700;">❌ API KEY REQUIRED</div>
          <div style="color:#94a3b8;font-size:0.7rem;margin-top:0.2rem;">Add GEMINI_API_KEY to your .env file</div>
        </div>
        """)

    if docker_ok:
        _h("""
        <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);border-radius:10px;padding:0.6rem 0.85rem;margin-bottom:1rem;">
          <div style="color:#34d399;font-size:0.72rem;font-weight:700;">🐳 DOCKER DAEMON ACTIVE</div>
          <div style="color:#94a3b8;font-size:0.68rem;margin-top:0.15rem;">Disposable container execution enabled</div>
        </div>
        """)
    else:
        _h("""
        <div style="background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.25);border-radius:10px;padding:0.6rem 0.85rem;margin-bottom:1rem;">
          <div style="color:#fbbf24;font-size:0.72rem;font-weight:700;">⚠️ DOCKER NOT RUNNING</div>
          <div style="color:#94a3b8;font-size:0.68rem;margin-top:0.15rem;">Trial execution will safely skip (host safe)</div>
        </div>
        """)

    st.divider()
    _h('<div style="color:#94a3b8;font-size:0.7rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.4rem;">SAFETY GUARDRAILS</div>')
    for icon, guard in [
        ("🔒", "Read-only static repo scan"),
        ("🚫", "Zero host execution guaranteed"),
        ("🧬", "AST probe safety screening"),
        ("📦", "Ephemeral Docker containers"),
        ("🌐", "Network-disabled sandbox"),
        ("🔑", "User consent before execution"),
    ]:
        _h(f'<div style="font-size:0.74rem;color:#64748b;display:flex;gap:0.4rem;align-items:center;margin-bottom:0.25rem;"><span>{icon}</span><span>{guard}</span></div>')

    st.divider()
    _h('<div style="color:#475569;font-size:0.7rem;text-align:center;">LibTrial v1.0 &middot; MIT License</div>')

# =========================================================
# STAGE 1 — PROJECT PROFILE INSPECTION
# =========================================================
_h("""
<div class="section-panel">
  <div class="section-header-title">📂 Stage 1 — Target Project Inspection</div>
  <div class="section-header-sub">Read-only static analysis — inspects Python version, frameworks, and declared dependencies without executing code.</div>
</div>
""")

col_p1, col_p2 = st.columns([4, 1])
with col_p1:
    project_path_input = st.text_input(
        "repo_path",
        value=st.session_state.get("project_path_val", "examples/sample_project"),
        placeholder="e.g. examples/sample_project or /path/to/my-repo",
        label_visibility="collapsed",
    )
with col_p2:
    if st.button("📁 Load Sample Project", use_container_width=True):
        st.session_state["project_path_val"] = "examples/sample_project"
        st.rerun()

if st.button("🔎 Inspect Repository Profile", type="primary"):
    try:
        with st.spinner("Safely analyzing repository structure and dependencies…"):
            profile_data = inspect_repository(project_path_input)
            st.session_state["profile"] = profile_data
    except FileNotFoundError:
        st.error(f"❌ Target path not found: `{project_path_input}`")
        st.stop()
    except (NotADirectoryError, ValueError) as err:
        st.error(f"❌ Invalid repository path: {err}")
        st.stop()
    except Exception as err:
        st.error(f"❌ Inspection error: {err}")
        st.stop()

profile: Optional[ProjectProfile] = st.session_state.get("profile")

if profile:
    frameworks_str = ", ".join(profile.detected_frameworks) if profile.detected_frameworks else "None detected"
    _h(f"""
    <div class="metric-row">
      <div class="metric-tile"><div class="metric-value">{profile.project_name}</div><div class="metric-label">Project</div></div>
      <div class="metric-tile"><div class="metric-value">{profile.python_version}</div><div class="metric-label">Python Target</div></div>
      <div class="metric-tile"><div class="metric-value">{len(profile.declared_dependencies)}</div><div class="metric-label">Dependencies</div></div>
      <div class="metric-tile"><div class="metric-value">{profile.total_python_files}</div><div class="metric-label">Python Files</div></div>
      <div class="metric-tile" style="flex:2;"><div class="metric-value" style="font-size:1.15rem;color:#c084fc;">{frameworks_str}</div><div class="metric-label">Frameworks</div></div>
    </div>
    """)
    sc1, sc2 = st.columns(2)
    with sc1:
        if profile.declared_dependencies:
            with st.expander(f"📦 Declared Dependencies ({len(profile.declared_dependencies)})", expanded=False):
                for dep in profile.declared_dependencies:
                    st.markdown(f"`{dep}`")
        if profile.config_files:
            with st.expander(f"⚙️ Config Files Found ({len(profile.config_files)})", expanded=False):
                for cfg in profile.config_files:
                    st.markdown(f"`{cfg}`")
    with sc2:
        if profile.source_excerpts:
            with st.expander(f"📄 Source Excerpts ({len(profile.source_excerpts)} scanned)", expanded=False):
                for exc in profile.source_excerpts:
                    st.markdown(f"**`{exc.file_path}`** ({exc.line_count} lines)")
                    st.code(exc.content, language="python")
        if profile.warnings:
            with st.expander("⚠️ Static Analysis Warnings", expanded=False):
                for warn in profile.warnings:
                    st.warning(warn)
else:
    _h("""
    <div style="background:rgba(30,41,59,0.35);border:1px dashed rgba(99,179,237,0.2);border-radius:12px;padding:2rem;text-align:center;color:#64748b;">
      <div style="font-size:2rem;margin-bottom:0.4rem;">📂</div>
      <div style="font-weight:600;color:#94a3b8;">No repository profile loaded</div>
      <div style="font-size:0.8rem;margin-top:0.25rem;">Enter a repository path above or click <strong>Load Sample Project</strong> to begin.</div>
    </div>
    """)

_h("<br>")

# =========================================================
# STAGE 2 — CANDIDATE DISCOVERY VIA GEMMA 4
# =========================================================
_h("""
<div class="section-panel">
  <div class="section-header-title">💡 Stage 2 — Candidate Discovery via Gemma 4</div>
  <div class="section-header-sub">Provide your plain-English capability requirement. Gemma 4 suggests up to 3 candidate packages as hypotheses.</div>
</div>
""")

col_r1, col_r2 = st.columns([4, 1])
with col_r1:
    user_req = st.text_area(
        "requirement_input",
        value=st.session_state.get("requirement", ""),
        placeholder="e.g. High-performance CSV and Parquet reader with lazy evaluation and minimal memory overhead",
        height=85,
        label_visibility="collapsed",
    )
with col_r2:
    _h("<br>")
    if st.button("⚡ Example Requirement", use_container_width=True):
        st.session_state["requirement"] = "High-performance CSV and Parquet reader with lazy evaluation"
        st.rerun()

if st.button("🤖 Discover Candidates & Verify on PyPI", type="primary"):
    if not user_req.strip():
        st.warning("Please specify a capability requirement first.")
        st.stop()
    if not settings.has_api_key:
        st.error("❌ GEMINI_API_KEY is missing. Please configure it in .env")
        st.stop()

    st.session_state["requirement"] = user_req.strip()
    st.session_state.update({"probe_code": None, "trial_result": None, "report_markdown": None})

    with st.spinner(f"Querying {settings.gemma_model} for candidate package hypotheses…"):
        try:
            client = GemmaClient(settings=settings)
            discovery = CandidateDiscovery(client=client)
            candidates = discovery.discover_candidates(user_req, profile)
        except ConfigurationError as err:
            st.error(f"Configuration error: {err}")
            st.stop()
        except Exception as err:
            st.error(f"Gemma API error: {err}")
            st.stop()

    if not candidates:
        st.warning("No package candidates proposed. Try refining your requirement description.")
        st.session_state["evaluations"] = []
        st.stop()

    with st.spinner("Cross-referencing candidates with official PyPI JSON registry…"):
        evaluations_list: List[CandidateEvaluation] = []
        with PyPIClient() as pypi_client:
            for cand in candidates:
                pypi_meta = pypi_client.get_package_metadata(cand.name, fetch_github=True)
                compat_eval = evaluate_compatibility(
                    project_python=profile.python_version if profile else "unknown",
                    project_dependencies=profile.declared_dependencies if profile else [],
                    pypi_metadata=pypi_meta,
                )
                evaluations_list.append(
                    CandidateEvaluation(
                        suggestion=cand,
                        pypi_metadata=pypi_meta,
                        compatibility=compat_eval,
                    )
                )
        st.session_state["evaluations"] = evaluations_list
        if evaluations_list:
            st.session_state["selected_candidate"] = evaluations_list[0].suggestion.name

evaluations: List[CandidateEvaluation] = st.session_state.get("evaluations", [])

if not evaluations:
    _h("""
    <div style="background:rgba(30,41,59,0.35);border:1px dashed rgba(99,179,237,0.2);border-radius:12px;padding:2rem;text-align:center;color:#64748b;">
      <div style="font-size:2rem;margin-bottom:0.4rem;">💡</div>
      <div style="font-weight:600;color:#94a3b8;">Awaiting capability requirement</div>
      <div style="font-size:0.8rem;margin-top:0.25rem;">Type your need or click Example, then run Discovery.</div>
    </div>
    """)

_h("<br>")

# =========================================================
# STAGE 3 — REGISTRY VERIFICATION & COMPATIBILITY
# =========================================================
_h("""
<div class="section-panel">
  <div class="section-header-title">🔍 Stage 3 — Registry Verification & Compatibility Findings</div>
  <div class="section-header-sub">Every factual claim is directly attributed to official PyPI metadata. Model claims are explicitly tagged <em>(Hypothesis)</em>.</div>
</div>
""")

if evaluations:
    all_unverified = all(not e.pypi_metadata or not e.pypi_metadata.is_found for e in evaluations)
    if all_unverified:
        st.error("❌ None of the suggested packages exist on PyPI. LibTrial refuses to fabricate alternatives.")

    cols = st.columns(len(evaluations))
    for col, ev in zip(cols, evaluations):
        sug, meta, compat = ev.suggestion, ev.pypi_metadata, ev.compatibility
        with col:
            is_found = bool(meta and meta.is_found)
            ver_html = f'<span class="cand-ver-badge">v{meta.version}</span>' if (is_found and meta) else ""
            status_badge = (
                '<span class="status-pill-ok">✓ PyPI VERIFIED</span>'
                if is_found
                else '<span class="status-pill-err">✗ NOT FOUND</span>'
            )

            # Compatibility banner styling
            if compat.verdict == CompatibilityVerdict.COMPATIBLE_WITH_AVAILABLE_EVIDENCE:
                compat_banner = f'<div class="compat-banner compat-green">🟢 {compat.verdict.value}</div>'
            elif compat.verdict == CompatibilityVerdict.POTENTIAL_CONFLICT:
                compat_banner = f'<div class="compat-banner compat-yellow">🟡 {compat.verdict.value}</div>'
            else:
                compat_banner = f'<div class="compat-banner compat-blue">🔵 {compat.verdict.value}</div>'

            # Clean license display
            lic_clean = clean_license_display(meta.license if meta else None)
            req_py = meta.requires_python or "Not specified" if meta else "N/A"
            deps_count = len(meta.requires_dist) if meta else 0
            pypi_link = f"https://pypi.org/project/{meta.name}/" if meta else "#"

            # Render self-contained card
            card_html = f"""
            <div class="cand-card">
              <div>
                <div class="cand-header">
                  <div>
                    <span class="cand-title">{sug.name}</span>
                    {ver_html}
                  </div>
                  {status_badge}
                </div>
                {compat_banner}
                <div class="cand-details-table">
                  <div class="cand-row">
                    <span class="cand-lbl">Requires-Py:</span>
                    <span class="cand-val"><code>{req_py}</code><span class="cand-src">(PyPI)</span></span>
                  </div>
                  <div class="cand-row">
                    <span class="cand-lbl">License:</span>
                    <span class="cand-val"><code>{lic_clean}</code><span class="cand-src">(PyPI)</span></span>
                  </div>
                  <div class="cand-row">
                    <span class="cand-lbl">Dependencies:</span>
                    <span class="cand-val">{deps_count} declared<span class="cand-src">(PyPI)</span></span>
                  </div>
                  <div class="cand-row">
                    <span class="cand-lbl">Registry Link:</span>
                    <span class="cand-val"><a href="{pypi_link}" target="_blank" style="color:#60a5fa;text-decoration:none;">pypi.org ↗</a></span>
                  </div>
            """
            if meta and meta.github_metadata and meta.github_metadata.stars is not None:
                gh = meta.github_metadata
                card_html += f"""
                  <div class="cand-row">
                    <span class="cand-lbl">GitHub Stats:</span>
                    <span class="cand-val">⭐ {gh.stars:,} &nbsp;🍴 {gh.forks or 0:,}<span class="cand-src">(GitHub)</span></span>
                  </div>
                """

            card_html += f"""
                </div>
              </div>
              <div class="cand-hypo-box">
                <div><strong style="color:#94a3b8;">Import Name:</strong> <code>{sug.import_name or '?'}</code> <span class="cand-src">(Hypothesis)</span></div>
                <div><strong style="color:#94a3b8;">Capability:</strong> {(sug.capability or 'N/A')[:90]} <span class="cand-src">(Hypothesis)</span></div>
                <div><strong style="color:#94a3b8;">Fit Rationale:</strong> {(sug.fit_rationale or 'N/A')[:90]} <span class="cand-src">(Hypothesis)</span></div>
              </div>
            </div>
            """
            _h(card_html)

            if compat.dependency_conflict_notes:
                for conf_note in compat.dependency_conflict_notes:
                    st.caption(f"⚠️ {conf_note}")
else:
    _h("""
    <div style="background:rgba(30,41,59,0.35);border:1px dashed rgba(99,179,237,0.2);border-radius:12px;padding:2rem;text-align:center;color:#64748b;">
      <div style="font-size:2rem;margin-bottom:0.4rem;">🔍</div>
      <div style="font-weight:600;color:#94a3b8;">No candidate verification results yet</div>
      <div style="font-size:0.8rem;margin-top:0.25rem;">Candidate cards with verified registry facts will appear here after discovery.</div>
    </div>
    """)

_h("<br>")

# =========================================================
# STAGE 4 — ISOLATED INTEGRATION TRIAL
# =========================================================
_h("""
<div class="section-panel">
  <div class="section-header-title">🔬 Stage 4 — Isolated Integration Trial</div>
  <div class="section-header-sub">Gemma generates a minimal integration probe. Inspect code, verify AST safety, and authorize execution in an ephemeral Docker container. Host environment remains untouched.</div>
</div>
""")

verified_candidates = [e for e in evaluations if e.pypi_metadata and e.pypi_metadata.is_found]

if verified_candidates:
    cand_names = [e.suggestion.name for e in verified_candidates]
    curr_sel = st.session_state.get("selected_candidate")
    sel_index = cand_names.index(curr_sel) if curr_sel in cand_names else 0

    t_col1, t_col2 = st.columns([2, 3])
    with t_col1:
        chosen_pkg = st.radio("Select Candidate Package for Trial:", options=cand_names, index=sel_index)
        st.session_state["selected_candidate"] = chosen_pkg

    chosen_eval = next((e for e in verified_candidates if e.suggestion.name == chosen_pkg), None)

    with t_col2:
        if chosen_eval and chosen_eval.pypi_metadata:
            cm = chosen_eval.pypi_metadata
            _h(f"""
            <div style="background:rgba(30,41,59,0.5);border:1px solid rgba(99,179,237,0.15);border-radius:10px;padding:0.85rem 1.1rem;">
              <div style="color:#60a5fa;font-weight:700;font-size:0.95rem;margin-bottom:0.35rem;">📦 Selected: {chosen_pkg} v{cm.version}</div>
              <div style="font-size:0.8rem;color:#94a3b8;">Requires-Python: <code>{cm.requires_python or 'Not specified'}</code> &middot; License: <code>{clean_license_display(cm.license)}</code></div>
              <div style="font-size:0.8rem;color:#94a3b8;margin-top:0.2rem;">Import identifier: <code>{chosen_eval.suggestion.import_name or chosen_pkg}</code></div>
            </div>
            """)

    if chosen_eval:
        if st.button("⚙️ Generate Minimal Integration Probe via Gemma 4", type="secondary"):
            with st.spinner(f"Generating integration probe for `{chosen_pkg}`…"):
                probe_client = GemmaClient(settings=settings) if settings.has_api_key else None
                generated_probe = generate_probe_script(
                    candidate=chosen_eval.suggestion,
                    pypi_metadata=chosen_eval.pypi_metadata,
                    profile=profile or ProjectProfile(project_path="."),
                    requirement=st.session_state.get("requirement", ""),
                    client=probe_client,
                )
                st.session_state["probe_code"] = generated_probe
                st.session_state["trial_result"] = None

        probe_script = st.session_state.get("probe_code")
        if probe_script:
            pr_col1, pr_col2 = st.columns([3, 2])
            with pr_col1:
                st.markdown("**Generated Probe Code** — Review before authorizing:")
                st.code(probe_script, language="python")

            with pr_col2:
                is_safe, safety_reasons = validate_probe_safety(probe_script)
                if is_safe:
                    _h("""
                    <div style="background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.25);border-radius:10px;padding:1rem;">
                      <div style="color:#34d399;font-weight:700;font-size:0.88rem;margin-bottom:0.4rem;">🛡️ AST Safety Inspection Passed</div>
                      <div style="font-size:0.78rem;color:#94a3b8;line-height:1.6;">
                        ✓ No unauthorized subprocesses or shell calls<br>
                        ✓ No filesystem write operations<br>
                        ✓ No network sockets or requests<br>
                        ✓ No dangerous eval/exec builtins
                      </div>
                    </div>
                    """)
                else:
                    _h("""
                    <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:10px;padding:1rem;">
                      <div style="color:#f87171;font-weight:700;font-size:0.88rem;margin-bottom:0.4rem;">🚫 AST Safety Scan Rejected Probe</div>
                    </div>
                    """)
                    for fail_reason in safety_reasons:
                        _h(f'<div style="color:#f87171;font-size:0.75rem;">• {fail_reason}</div>')

                if is_safe:
                    _h("<br>")
                    st.info("🔒 Execution boundary: Disposable Docker container &middot; `--network none` &middot; 256MB RAM &middot; 60s timeout &middot; Host FS unmounted")
                    user_consented = st.checkbox("✅ I have reviewed the probe code and authorize execution in an isolated Docker sandbox.")

                    if user_consented:
                        if st.button(f"🚀 Execute Isolated Trial for `{chosen_pkg}`", type="primary", use_container_width=True):
                            with st.spinner("Building ephemeral container and executing probe…"):
                                result = run_isolated_trial(
                                    candidate_name=chosen_pkg,
                                    candidate_version=chosen_eval.pypi_metadata.version,
                                    probe_code=probe_script,
                                    user_consented=True,
                                )
                                st.session_state["trial_result"] = result

            trial_res: Optional[TrialResult] = st.session_state.get("trial_result")
            if trial_res:
                _h("<br>")
                if trial_res.outcome == TrialOutcome.PASS:
                    bg_css, txt_css, title_txt = "rgba(16,185,129,0.12)", "#34d399", "✅ PASS"
                elif trial_res.outcome == TrialOutcome.FAIL:
                    bg_css, txt_css, title_txt = "rgba(239,68,68,0.12)", "#f87171", "❌ FAIL"
                elif trial_res.outcome == TrialOutcome.NOT_RUN:
                    bg_css, txt_css, title_txt = "rgba(245,158,11,0.12)", "#fbbf24", "⏸️ NOT RUN"
                else:
                    bg_css, txt_css, title_txt = "rgba(245,158,11,0.12)", "#fbbf24", "❓ INCONCLUSIVE"

                exit_str = str(trial_res.exit_code) if trial_res.exit_code is not None else "N/A"
                runtime_str = f"{trial_res.execution_time_seconds:.2f}s" if trial_res.execution_time_seconds else "N/A"
                boundary_str = "Disposable Docker Container" if trial_res.docker_available else "Skipped (Docker absent, host safe)"

                _h(f"""
                <div style="background:{bg_css};border:1px solid {txt_css};border-radius:12px;padding:1.1rem 1.4rem;">
                  <div style="display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap;">
                    <div style="font-size:1.6rem;font-weight:800;color:{txt_css};">{title_txt}</div>
                    <div><span style="color:#64748b;font-size:0.7rem;text-transform:uppercase;">Exit Code</span><br><strong style="color:#f1f5f9;">{exit_str}</strong></div>
                    <div><span style="color:#64748b;font-size:0.7rem;text-transform:uppercase;">Runtime</span><br><strong style="color:#f1f5f9;">{runtime_str}</strong></div>
                    <div><span style="color:#64748b;font-size:0.7rem;text-transform:uppercase;">Sandbox Boundary</span><br><strong style="color:#f1f5f9;font-size:0.85rem;">{boundary_str}</strong></div>
                  </div>
                </div>
                """)

                for note in (trial_res.reasons or []):
                    _h(f'<div style="color:#94a3b8;font-size:0.82rem;margin-top:0.35rem;">• {note}</div>')

                if trial_res.stdout or trial_res.stderr:
                    tab_out, tab_err = st.tabs(["📤 Container stdout", "📥 Container stderr"])
                    with tab_out:
                        st.code(trial_res.stdout or "(empty)", language="text")
                    with tab_err:
                        st.code(trial_res.stderr or "(empty)", language="text")

                _h(f'<div style="color:#475569;font-size:0.72rem;margin-top:0.5rem;">⚠️ {trial_res.disclaimer}</div>')
else:
    _h("""
    <div style="background:rgba(30,41,59,0.35);border:1px dashed rgba(99,179,237,0.2);border-radius:12px;padding:2rem;text-align:center;color:#64748b;">
      <div style="font-size:2rem;margin-bottom:0.4rem;">🔬</div>
      <div style="font-weight:600;color:#94a3b8;">Trial requires verified candidates</div>
      <div style="font-size:0.8rem;margin-top:0.25rem;">Only packages confirmed on PyPI can be trialed in isolated sandbox containers.</div>
    </div>
    """)

_h("<br>")

# =========================================================
# STAGE 5 — INVESTIGATION REPORT & AUDIT TRAIL
# =========================================================
_h("""
<div class="section-panel">
  <div class="section-header-title">📄 Stage 5 — Auditable Investigation Report</div>
  <div class="section-header-sub">Export a complete, self-contained Markdown report with clear demarcation between model hypotheses and verified empirical registry facts.</div>
</div>
""")

if profile and evaluations:
    report_md = generate_markdown_report(
        profile=profile,
        requirement=st.session_state.get("requirement", ""),
        evaluations=evaluations,
        selected_candidate_name=st.session_state.get("selected_candidate"),
        trial_result=st.session_state.get("trial_result"),
    )
    st.session_state["report_markdown"] = report_md

    rep_col1, rep_col2 = st.columns([2, 3])
    with rep_col1:
        st.download_button(
            label="💾 Download Report (libtrial_report.md)",
            data=report_md,
            file_name="libtrial_report.md",
            mime="text/markdown",
            type="primary",
            use_container_width=True,
        )
    with rep_col2:
        t_res = st.session_state.get("trial_result")
        trial_status_badge = f" &middot; Trial Outcome: <strong>{t_res.outcome.value}</strong>" if t_res else ""
        _h(f"""
        <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);border-radius:10px;padding:0.75rem 1rem;font-size:0.82rem;color:#e2e8f0;">
          <span style="color:#34d399;font-weight:700;">✅ Report generated</span> &nbsp;&middot;&nbsp;
          <span>{report_md.count(chr(10))} lines</span> &nbsp;&middot;&nbsp;
          <span>{len(evaluations)} candidate packages</span>{trial_status_badge}
        </div>
        """)

    with st.expander("👁️ Preview Generated Markdown Report", expanded=False):
        st.markdown(report_md)
else:
    backup_path = "examples/sample_report.md"
    _h("""
    <div style="background:rgba(30,41,59,0.35);border:1px dashed rgba(99,179,237,0.2);border-radius:12px;padding:1.5rem;color:#64748b;">
      <div style="font-weight:600;color:#94a3b8;margin-bottom:0.25rem;">📄 Report is generated once Stages 1–3 are evaluated</div>
      <div style="font-size:0.8rem;">Includes: project profile, candidate findings, verified registry metadata, container trial status, and explicit limitations.</div>
    </div>
    """)
    if os.path.exists(backup_path):
        _h("<br>")
        _h('<div style="color:#64748b;font-size:0.78rem;font-weight:600;">BACKUP DEMO &mdash; Load Pre-Generated Report:</div>')
        bc1, _ = st.columns([2, 3])
        with bc1:
            if st.button("📁 Load Sample Report", use_container_width=True):
                with open(backup_path, "r", encoding="utf-8") as bf:
                    loaded_md = bf.read()
                st.session_state["report_markdown"] = loaded_md
                st.download_button(
                    "💾 Download Sample Report",
                    data=loaded_md,
                    file_name="libtrial_report.md",
                    mime="text/markdown",
                )
                with st.expander("👁️ Preview Sample Report", expanded=True):
                    st.markdown(loaded_md)

# =========================================================
# PROFESSIONAL FOOTER
# =========================================================
_h("""
<footer class="app-footer">
  <div class="footer-grid">
    <div>
      <div class="footer-title">🧪 LibTrial</div>
      <p class="footer-desc">
        An evidence-backed library evaluation workflow designed for safe, verifiable Python package discovery. Gemma 4 provides initial candidate hypotheses; live PyPI registry metadata and disposable Docker containers establish empirical evidence.
      </p>
      <div style="display:flex;gap:0.4rem;flex-wrap:wrap;">
        <span class="nav-badge nav-badge-blue">Google GenAI SDK</span>
        <span class="nav-badge nav-badge-purple">PyPI JSON API</span>
        <span class="nav-badge nav-badge-green">Docker Isolation</span>
      </div>
    </div>
    <div>
      <div class="footer-col-head">Safety Architecture</div>
      <ul class="footer-list">
        <li>🔒 Read-only target repository inspection</li>
        <li>🚫 Zero code execution on host developer machine</li>
        <li>🛡️ AST static safety scan before trial execution</li>
        <li>📦 Disposable sandbox container (--network none)</li>
        <li>🔑 Explicit user consent required before execution</li>
      </ul>
    </div>
    <div>
      <div class="footer-col-head">5-Stage Workflow</div>
      <ul class="footer-list">
        <li>1. Target Project Inspection</li>
        <li>2. Gemma 4 Candidate Discovery</li>
        <li>3. Registry Verification & Compatibility</li>
        <li>4. Isolated Integration Trial</li>
        <li>5. Auditable Markdown Report</li>
      </ul>
    </div>
  </div>
  <div class="footer-bottom">
    <div>© 2026 LibTrial Team &middot; Released under MIT License</div>
    <div style="color:#475569;">⚠️ AI suggestions are hypotheses until validated by registry metadata and container trial results.</div>
  </div>
</footer>
""")
