"""Streamlit entry point for LibTrial — Complete End-to-End Workflow."""

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
from libtrial.pdf_generator import generate_pdf_report
from libtrial.trial_runner import (
    generate_probe_script,
    is_docker_available,
    run_isolated_trial,
    validate_probe_safety,
)


def _clean_license_display(lic: Optional[str]) -> str:
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
        return first_line[:25] + "..."
    return first_line or "Not stated"

st.set_page_config(
    page_title="LibTrial — Evidence-Backed Library Evaluation",
    page_icon="🧪",
    layout="wide",
)

# ---------------------------------------------------------
# State Management
# ---------------------------------------------------------
if "profile" not in st.session_state:
    st.session_state["profile"] = None
if "requirement" not in st.session_state:
    st.session_state["requirement"] = ""
if "evaluations" not in st.session_state:
    st.session_state["evaluations"] = []
if "selected_candidate" not in st.session_state:
    st.session_state["selected_candidate"] = None
if "probe_code" not in st.session_state:
    st.session_state["probe_code"] = None
if "trial_result" not in st.session_state:
    st.session_state["trial_result"] = None
if "report_markdown" not in st.session_state:
    st.session_state["report_markdown"] = None

settings = get_settings()

# ---------------------------------------------------------
# Header & Navigation
# ---------------------------------------------------------
st.title("🧪 LibTrial")
st.markdown(
    "**Gemma 4-powered evaluation of open-source Python libraries for your project.**  \n"
    "Identify candidate libraries, verify them against live PyPI registry metadata, check version compatibility, "
    "and execute safe, isolated integration trials in disposable containers."
)

st.divider()

# Sidebar: Environment & Settings
with st.sidebar:
    st.header("⚙️ Configuration")
    if settings.has_api_key:
        st.success("API Key detected")
        masked_key = (
            settings.gemini_api_key[:4] + "..." + settings.gemini_api_key[-4:]
            if len(settings.gemini_api_key) > 8
            else "••••••••"
        )
        st.caption(f"Configured Key: `{masked_key}`")
    else:
        st.error("Missing `GEMINI_API_KEY`")
        st.info("Set `GEMINI_API_KEY` in your environment or in a local `.env` file.")

    st.caption(f"Active Model: **`{settings.gemma_model}`**")
    
    st.divider()
    st.header("🐳 Sandbox Status")
    docker_ready = is_docker_available()
    if docker_ready:
        st.success("Docker CLI / Daemon Active")
    else:
        st.warning("Docker Not Detected")
        st.caption("Container trials will be safely skipped. Host execution is strictly prohibited.")

    st.divider()
    st.caption("🛡️ **Safety Guardrails**")
    st.caption(
        "• Read-only inspection\n"
        "• Zero host execution\n"
        "• AST static code safety\n"
        "• Disposable Docker containers\n"
        "• Zero network in trial execution"
    )
    st.divider()
    st.caption("📐 **Workflow Stages**")
    st.caption("1. PROJECT\n2. DISCOVERY\n3. VERIFICATION\n4. TRIAL\n5. REPORT")

# ---------------------------------------------------------
# STAGE 1: PROJECT INSPECTION
# ---------------------------------------------------------
st.header("1. 📂 Target Project Inspection")
st.caption("Inspect a local Python repository safely without executing any source files or build scripts.")

col_p1, col_p2 = st.columns([3, 1])
with col_p1:
    project_path_input = st.text_input(
        "Local Python Repository Path",
        value=st.session_state.get("project_path_val", "."),
        help="Path to the root of your local Python repository containing pyproject.toml or requirements.txt",
    )

with col_p2:
    st.write("")
    st.write("")
    if st.button("📁 Use Sample Project Fixture"):
        st.session_state["project_path_val"] = "examples/sample_project"
        st.rerun()

col_btn_inspect, _ = st.columns([1, 4])
with col_btn_inspect:
    inspect_clicked = st.button("🔎 Inspect Repository Profile", type="primary")

if inspect_clicked or (st.session_state["profile"] is None and project_path_input):
    try:
        with st.spinner("Safely inspecting repository metadata..."):
            profile = inspect_repository(project_path_input)
            st.session_state["profile"] = profile
    except FileNotFoundError:
        st.error(f"❌ Path not found: `{project_path_input}`")
        st.stop()
    except NotADirectoryError:
        st.error(f"❌ Path is not a directory: `{project_path_input}`")
        st.stop()
    except ValueError as err:
        st.error(f"❌ Invalid Repository: {err}")
        st.stop()
    except Exception as err:
        st.error(f"❌ Error during repository inspection: {err}")
        st.stop()

profile: Optional[ProjectProfile] = st.session_state.get("profile")

if profile:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Project Name", profile.project_name)
    m2.metric("Target Python", profile.python_version)
    m3.metric("Declared Dependencies", len(profile.declared_dependencies))
    m4.metric("Python Files Counted", profile.total_python_files)

    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        st.markdown("**Detected Frameworks**")
        if profile.detected_frameworks:
            st.write(" ".join([f"`{fw}`" for fw in profile.detected_frameworks]))
        else:
            st.caption("None detected in declared dependencies.")

        st.markdown("**Configuration Files**")
        if profile.config_files:
            st.write(" ".join([f"`{cf}`" for cf in profile.config_files]))
        else:
            st.caption("No standard configuration files located.")

    with col_meta2:
        with st.expander(f"📦 Declared Dependencies ({len(profile.declared_dependencies)})", expanded=False):
            if profile.declared_dependencies:
                for dep in profile.declared_dependencies:
                    st.text(f"• {dep}")
            else:
                st.caption("No dependencies declared.")

    if profile.source_excerpts:
        with st.expander(f"📄 Bounded Source Excerpts ({len(profile.source_excerpts)} files)", expanded=False):
            for excerpt in profile.source_excerpts:
                st.markdown(f"**`{excerpt.file_path}`** ({excerpt.line_count} lines)")
                st.code(excerpt.content, language="python")

    if profile.warnings:
        with st.expander("⚠️ Inspection Warnings", expanded=False):
            for warning in profile.warnings:
                st.warning(warning)

st.divider()

# ---------------------------------------------------------
# STAGE 2: CANDIDATE DISCOVERY (Gemma 4)
# ---------------------------------------------------------
st.header("2. 💡 Candidate Discovery (Gemma 4)")
st.caption("Describe your requirement in plain language. Gemma 4 will suggest at most three candidate package hypotheses.")

col_req, col_req_btn = st.columns([3, 1])
with col_req:
    requirement_input = st.text_area(
        "Capability Requirement (Plain English)",
        value=st.session_state.get("requirement", ""),
        placeholder="e.g. High-performance CSV and Parquet reader with lazy evaluation",
        height=85,
    )

with col_req_btn:
    st.write("")
    st.write("")
    if st.button("⚡ Load Example Requirement"):
        st.session_state["requirement"] = "High-performance CSV and Parquet reader with lazy evaluation"
        st.rerun()

discover_clicked = st.button("🤖 Generate Candidate Hypotheses & Verify", type="primary")

if discover_clicked:
    if not requirement_input.strip():
        st.warning("Please provide a capability requirement before running discovery.")
        st.stop()

    if not settings.has_api_key:
        st.error("⚠️ `GEMINI_API_KEY` is required to discover candidates. Please configure your key in `.env`.")
        st.stop()

    st.session_state["requirement"] = requirement_input.strip()
    st.session_state["probe_code"] = None
    st.session_state["trial_result"] = None
    st.session_state["report_markdown"] = None

    # Step A: Gemma Candidate Discovery
    try:
        with st.spinner(f"Querying Gemma 4 ({settings.gemma_model}) for candidate hypotheses..."):
            llm_client = GemmaClient(settings=settings)
            discovery = CandidateDiscovery(client=llm_client)
            candidates = discovery.discover_candidates(requirement_input, profile)
    except ConfigurationError as err:
        st.error(f"Configuration Error: {err}")
        st.stop()
    except Exception as err:
        st.error(f"Error communicating with Gemma API: {err}")
        st.stop()

    if not candidates:
        st.warning("No candidate hypotheses were returned by the model. Try refining your requirement description.")
        st.session_state["evaluations"] = []
        st.stop()

    # Step B: PyPI Registry Verification & Compatibility Check
    evaluations: List[CandidateEvaluation] = []
    with st.spinner("Verifying candidates against PyPI JSON API and evaluating compatibility..."):
        with PyPIClient() as pypi_client:
            for cand in candidates:
                pypi_meta = pypi_client.get_package_metadata(cand.name, fetch_github=True)
                compat = evaluate_compatibility(
                    project_python=profile.python_version if profile else "unknown",
                    project_dependencies=profile.declared_dependencies if profile else [],
                    pypi_metadata=pypi_meta,
                )
                evaluations.append(
                    CandidateEvaluation(
                        suggestion=cand,
                        pypi_metadata=pypi_meta,
                        compatibility=compat,
                    )
                )

    st.session_state["evaluations"] = evaluations
    if evaluations:
        st.session_state["selected_candidate"] = evaluations[0].suggestion.name

evaluations: List[CandidateEvaluation] = st.session_state.get("evaluations", [])

st.divider()

# ---------------------------------------------------------
# STAGE 3: REGISTRY VERIFICATION & COMPATIBILITY
# ---------------------------------------------------------
st.header("3. 🔍 Registry Verification & Compatibility")
st.caption("Every factual claim below is attributed to the official PyPI registry or marked as an AI hypothesis.")

if evaluations:
    all_failed = all(not e.pypi_metadata or not e.pypi_metadata.is_found for e in evaluations)
    if all_failed:
        st.error(
            "❌ **Registry Verification Failed**: None of the proposed candidate packages were found on PyPI. "
            "LibTrial strictly reports facts and will not manufacture alternative packages."
        )

    # Comparison Grid
    cols = st.columns(len(evaluations))
    for idx, (col, eval_item) in enumerate(zip(cols, evaluations)):
        sug = eval_item.suggestion
        meta = eval_item.pypi_metadata
        compat = eval_item.compatibility

        with col:
            st.markdown(f"### {idx}. `{sug.name}`")

            # Registry Status
            if meta and meta.is_found:
                pypi_url = f"https://pypi.org/project/{meta.name}/"
                st.markdown(
                    f"🟢 **Verified on PyPI** [`v{meta.version}`]({pypi_url})  \n"
                    f"*Source: [PyPI JSON API](https://pypi.org/pypi/{meta.name}/json)*"
                )
            else:
                st.markdown("🔴 **Not Found on PyPI**  \n*Source: PyPI HTTP 404*")
                if meta and meta.raw_error:
                    st.caption(f"Error: {meta.raw_error}")

            # Compatibility Badge
            if compat.verdict == CompatibilityVerdict.COMPATIBLE_WITH_AVAILABLE_EVIDENCE:
                st.success(f"**{compat.verdict.value}**")
            elif compat.verdict == CompatibilityVerdict.POTENTIAL_CONFLICT:
                st.warning(f"**{compat.verdict.value}**")
            else:
                st.info(f"**{compat.verdict.value}**")

            st.markdown("**Compatibility Breakdown**")
            st.caption(f"• Python Target: {compat.python_compatibility_note}")
            if compat.dependency_conflict_notes:
                for note in compat.dependency_conflict_notes:
                    st.error(f"⚠️ {note}")
            else:
                st.caption("• Direct Dependencies: No collisions detected.")

            if meta and meta.is_found:
                st.markdown("---")
                st.markdown(f"**Requires-Python:** `{meta.requires_python}` *(PyPI)*")
                lic_clean = _clean_license_display(meta.license)
                st.markdown(f"**License:** `{lic_clean}` *(PyPI)*")
                if meta.license and len(meta.license.split("\n")) > 1:
                    with st.expander("Full License Text", expanded=False):
                        st.caption(meta.license[:500] + ("..." if len(meta.license) > 500 else ""))
                st.markdown(f"**Direct Dependencies:** {len(meta.requires_dist)} packages *(PyPI)*")

                if meta.github_metadata and meta.github_metadata.stars is not None:
                    gh = meta.github_metadata
                    st.markdown(
                        f"**GitHub:** ⭐ `{gh.stars:,}` stars | 🍴 `{gh.forks or 0:,}` forks  \n"
                        f"Archived: `{'Yes' if gh.is_archived else 'No'}` *(GitHub API)*"
                    )

            st.markdown("---")
            st.markdown(f"**Expected Import:** `{sug.import_name}` *(Hypothesis)*")
            st.markdown(f"**Capability:** {sug.capability or 'unknown'} *(Hypothesis)*")
            st.markdown(f"**Fit Rationale:** {sug.fit_rationale or 'unknown'} *(Hypothesis)*")
            st.markdown(f"**Evidence to Check:** {sug.evidence_needed} *(Hypothesis)*")
else:
    st.info("Run candidate discovery above to inspect candidate packages and registry facts.")

st.divider()

# ---------------------------------------------------------
# STAGE 4: ISOLATED INTEGRATION TRIAL
# ---------------------------------------------------------
st.header("4. 🔬 Isolated Integration Trial")
st.caption("Generate a minimal probe script and execute it in an ephemeral, resource-constrained container.")

selectable_evals = [e for e in evaluations if e.pypi_metadata and e.pypi_metadata.is_found]

if selectable_evals:
    cand_names = [e.suggestion.name for e in selectable_evals]
    selected_pkg = st.radio(
        "Select one verified candidate for isolated integration trial:",
        options=cand_names,
        index=0,
        horizontal=True,
    )
    st.session_state["selected_candidate"] = selected_pkg
    chosen_eval = next((e for e in selectable_evals if e.suggestion.name == selected_pkg), None)

    if chosen_eval:
        col_gen, _ = st.columns([1, 2])
        with col_gen:
            gen_probe_clicked = st.button("⚙️ Generate Minimal Integration Probe", type="secondary")

        if gen_probe_clicked or st.session_state.get("probe_code"):
            if gen_probe_clicked:
                with st.spinner(f"Generating minimal probe for `{selected_pkg}` via Gemma..."):
                    client = GemmaClient(settings=settings) if settings.has_api_key else None
                    generated_code = generate_probe_script(
                        candidate=chosen_eval.suggestion,
                        pypi_metadata=chosen_eval.pypi_metadata,
                        profile=profile or ProjectProfile(project_path="."),
                        requirement=st.session_state.get("requirement", ""),
                        client=client,
                    )
                    st.session_state["probe_code"] = generated_code
                    st.session_state["trial_result"] = None

            probe_code = st.session_state["probe_code"]
            st.markdown("#### Proposed Integration Probe Script")
            st.caption("Inspect the exact Python code before running. Shell commands, network calls, and file writes are strictly forbidden.")
            st.code(probe_code, language="python")

            # AST Safety Pre-flight Check
            is_safe, safety_reasons = validate_probe_safety(probe_code)
            if not is_safe:
                st.error("🚫 **Safety Check Failed**: The proposed probe violates strict isolation rules:")
                for r in safety_reasons:
                    st.write(f"• {r}")
                st.caption("Execution is blocked. Unsafe probes will not be run.")
            else:
                st.success("🛡️ **AST Safety Check Passed**: Zero shell commands, zero network calls, zero file writing.")

                st.markdown("#### User Authorization")
                st.info(
                    "**Boundary Notice**: Execution occurs inside a disposable container with `--network none` and restricted memory (256MB). "
                    "Dependency installation requires ephemeral network access during image creation. "
                    "Host execution is strictly prohibited."
                )
                user_consented = st.checkbox(
                    "I have inspected the probe script and authorize its execution in an isolated Docker container.",
                    value=False,
                )

                col_run_t, _ = st.columns([1, 2])
                with col_run_t:
                    run_trial_clicked = st.button(
                        f"🚀 Run Isolated Trial for `{selected_pkg}`",
                        type="primary",
                        disabled=not user_consented,
                    )

                if run_trial_clicked:
                    with st.spinner(f"Building ephemeral container and executing trial for `{selected_pkg}`..."):
                        result = run_isolated_trial(
                            candidate_name=selected_pkg,
                            candidate_version=chosen_eval.pypi_metadata.version,
                            probe_code=probe_code,
                            user_consented=user_consented,
                        )
                        st.session_state["trial_result"] = result

            # Trial Result Display
            trial_res: Optional[TrialResult] = st.session_state.get("trial_result")
            if trial_res:
                st.markdown("#### Integration Trial Result")
                if trial_res.outcome == TrialOutcome.PASS:
                    st.success(f"### Outcome: ✅ {trial_res.outcome.value}")
                    st.caption("The exact integration probe completed successfully in the isolated container.")
                elif trial_res.outcome == TrialOutcome.FAIL:
                    st.error(f"### Outcome: ❌ {trial_res.outcome.value}")
                    st.caption("The attempted probe execution failed with a non-zero exit code or runtime error.")
                elif trial_res.outcome == TrialOutcome.NOT_RUN:
                    st.warning(f"### Outcome: ⏸️ {trial_res.outcome.value}")
                    st.caption("The trial was not run (e.g. Docker unavailable, consent omitted, or safety check rejected).")
                else:
                    st.info(f"### Outcome: ❓ {trial_res.outcome.value}")
                    st.caption("The outcome is inconclusive (e.g. container build error or timeout).")

                col_t1, col_t2, col_t3 = st.columns(3)
                col_t1.metric("Exit Code", str(trial_res.exit_code if trial_res.exit_code is not None else "N/A"))
                col_t2.metric(
                    "Execution Time",
                    f"{trial_res.execution_time_seconds:.2f}s" if trial_res.execution_time_seconds is not None else "N/A",
                )
                col_t3.metric("Isolation Boundary", "Disposable Docker Container" if trial_res.docker_available else "Not Run")

                if trial_res.reasons:
                    st.markdown("**Notes & Explanations:**")
                    for note in trial_res.reasons:
                        st.write(f"• {note}")

                if trial_res.stdout or trial_res.stderr:
                    tab_stdout, tab_stderr = st.tabs(["Container Stdout", "Container Stderr"])
                    with tab_stdout:
                        st.text(trial_res.stdout or "(Empty stdout)")
                    with tab_stderr:
                        st.text(trial_res.stderr or "(Empty stderr)")

                st.caption(f"⚠️ **Honest Disclosure**: {trial_res.disclaimer}")
else:
    st.info("Verified candidates will be available for isolated trials once discovery completes.")

st.divider()

# ---------------------------------------------------------
# STAGE 5: REPORT EXPORT
# ---------------------------------------------------------
st.header("5. 📄 Export Investigation Report")
st.caption("Compile an evidence-backed, auditable Markdown report of the complete investigation.")

if profile and evaluations:
    selected_candidate_name = st.session_state.get("selected_candidate")
    trial_result = st.session_state.get("trial_result")

    report_md = generate_markdown_report(
        profile=profile,
        requirement=st.session_state.get("requirement", ""),
        evaluations=evaluations,
        selected_candidate_name=selected_candidate_name,
        trial_result=trial_result,
    )
    st.session_state["report_markdown"] = report_md

    col_pdf, col_md = st.columns(2)
    with col_pdf:
        pdf_data = generate_pdf_report(
            profile=profile,
            requirement=st.session_state.get("requirement", ""),
            evaluations=evaluations,
            selected_candidate_name=selected_candidate_name,
            trial_result=trial_result,
        )
        st.download_button(
            label="📄 Download Investigation Report (PDF)",
            data=pdf_data,
            file_name="libtrial_report.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
    with col_md:
        st.download_button(
            label="💾 Download Report (Markdown)",
            data=report_md,
            file_name="libtrial_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    with st.expander("👁️ Preview Investigation Report", expanded=True):
        st.markdown(report_md)
else:
    st.info("Complete project inspection and candidate verification to generate an investigation brief.")
    backup_report_path = "examples/sample_report.md"
    if os.path.exists(backup_report_path):
        st.write("")
        st.markdown("#### 📁 Backup Demonstration")
        st.caption("If external APIs or Docker are unavailable, load this pre-verified investigation report:")
        if st.button("Load Pre-Generated Sample Report"):
            with open(backup_report_path, "r", encoding="utf-8") as bf:
                st.session_state["report_markdown"] = bf.read()
            st.rerun()

    if st.session_state.get("report_markdown"):
        b_md = st.session_state["report_markdown"]
        st.download_button("💾 Download Loaded Report", data=b_md, file_name="libtrial_sample_report.md", mime="text/markdown")
        with st.expander("👁️ Preview Loaded Report", expanded=True):
            st.markdown(b_md)
