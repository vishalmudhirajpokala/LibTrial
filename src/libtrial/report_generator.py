"""Markdown investigation report generator for LibTrial."""

from datetime import datetime, timezone
from typing import List, Optional

from libtrial.models import (
    CandidateEvaluation,
    CompatibilityVerdict,
    ProjectProfile,
    TrialOutcome,
    TrialResult,
)


def generate_markdown_report(
    profile: ProjectProfile,
    requirement: str,
    evaluations: List[CandidateEvaluation],
    selected_candidate_name: Optional[str] = None,
    trial_result: Optional[TrialResult] = None,
) -> str:
    """Generates an auditable, evidence-backed Markdown investigation report.
    
    Adheres to strict trust rules:
    - Distinguishes model hypotheses from verified facts.
    - Explicitly marks missing metadata as unknown.
    - Includes mandatory boundaries and limitations disclaimers.
    """
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    lines: List[str] = []
    lines.append("# 🧪 LibTrial — Evidence-Backed Investigation Report")
    lines.append(f"*Generated on: {now_str}*")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 1. Project Profile
    lines.append("## 1. Inspected Target Project Profile")
    lines.append(f"- **Project Name:** `{profile.project_name}`")
    lines.append(f"- **Target Python Version:** `{profile.python_version}`")
    lines.append(f"- **Detected Frameworks:** {', '.join(f'`{f}`' for f in profile.detected_frameworks) if profile.detected_frameworks else 'None declared'}")
    lines.append(f"- **Configuration Files Located:** {', '.join(f'`{c}`' for c in profile.config_files) if profile.config_files else 'None'}")
    lines.append(f"- **Total Python Files Scanned:** {profile.total_python_files}")
    lines.append("")
    lines.append("### Declared Project Dependencies")
    if profile.declared_dependencies:
        for dep in profile.declared_dependencies:
            lines.append(f"- `{dep}`")
    else:
        lines.append("*No dependencies declared in project configuration files.*")
    lines.append("")

    if profile.warnings:
        lines.append("### Inspection Warnings")
        for w in profile.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    # 2. Capability Requirement
    lines.append("## 2. Developer Capability Requirement")
    lines.append(f"> \"{requirement.strip()}\"")
    lines.append("")

    # 3. Candidate Comparison & Registry Facts
    lines.append("## 3. Candidate Library Comparison & Registry Verification")
    lines.append("All package proposals originate as **Gemma 4 hypotheses** and are checked against the official **PyPI JSON API**.")
    lines.append("")
    lines.append("| Candidate | Registry Status | Latest Version | Requires-Python | License | Compatibility Finding |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

    for ev in evaluations:
        sug = ev.suggestion
        meta = ev.pypi_metadata
        compat = ev.compatibility

        if meta and meta.is_found:
            reg_status = f"[Found on PyPI](https://pypi.org/project/{meta.name}/)"
            ver = f"`{meta.version}`"
            req_py = f"`{meta.requires_python}`"
            lic = f"`{meta.license}`"
        else:
            reg_status = "**Not Found (404)**"
            ver = "N/A"
            req_py = "N/A"
            lic = "N/A"

        verdict_icon = "🟢" if compat.verdict == CompatibilityVerdict.COMPATIBLE_WITH_AVAILABLE_EVIDENCE else "🟠" if compat.verdict == CompatibilityVerdict.POTENTIAL_CONFLICT else "⚪"
        finding = f"{verdict_icon} {compat.verdict.value}"

        lines.append(f"| **`{sug.name}`** | {reg_status} | {ver} | {req_py} | {lic} | {finding} |")
    lines.append("")

    # Detailed candidate breakdowns
    lines.append("### Detailed Candidate Evidence")
    for idx, ev in enumerate(evaluations, 1):
        sug = ev.suggestion
        meta = ev.pypi_metadata
        compat = ev.compatibility

        lines.append(f"#### {idx}. `{sug.name}`")
        lines.append(f"- **Expected Import Name:** `{sug.import_name}` *(Hypothesis)*")
        lines.append(f"- **Proposed Capability:** {sug.capability or 'unknown'} *(Hypothesis)*")
        lines.append(f"- **Project Fit Rationale:** {sug.fit_rationale or 'unknown'} *(Hypothesis)*")
        lines.append(f"- **Evidence Required:** {sug.evidence_needed} *(Hypothesis)*")

        if meta and meta.is_found:
            lines.append(f"- **PyPI Registry URL:** https://pypi.org/project/{meta.name}/ *(PyPI API)*")
            lines.append(f"- **Direct Dependencies Declared:** {len(meta.requires_dist)} packages *(PyPI API)*")
            lines.append(f"- **Python Compatibility Details:** {compat.python_compatibility_note}")

            if compat.dependency_conflict_notes:
                lines.append("- **Direct Dependency Collisions:**")
                for note in compat.dependency_conflict_notes:
                    lines.append(f"  - ⚠️ {note}")
            else:
                lines.append("- **Direct Dependency Collisions:** None detected against declared project pins.")

            if meta.github_metadata and meta.github_metadata.stars is not None:
                gh = meta.github_metadata
                lines.append(f"- **GitHub Context:** ⭐ {gh.stars:,} stars | 🍴 {gh.forks or 0:,} forks | Archived: {gh.is_archived} *(GitHub API)*")
        else:
            lines.append(f"- **Verification Failure:** Package was not found on PyPI ({meta.raw_error if meta else 'No metadata'}).")
        lines.append("")

    # 4. Isolated Integration Trial
    lines.append("## 4. Isolated Integration Trial")
    if selected_candidate_name:
        lines.append(f"- **Selected Candidate:** `{selected_candidate_name}`")
    else:
        lines.append("- **Selected Candidate:** None selected.")

    if trial_result:
        lines.append(f"- **Trial Outcome:** **`{trial_result.outcome.value}`**")
        lines.append(f"- **User Consent Granted:** {'Yes' if trial_result.user_consented else 'No'}")
        lines.append(f"- **Docker Boundary Used:** {'Disposable Docker Container' if trial_result.docker_available else 'Not Run (Docker Unavailable)'}")
        lines.append(f"- **Exit Code:** `{trial_result.exit_code if trial_result.exit_code is not None else 'N/A'}`")
        lines.append(f"- **Execution Runtime:** `{f'{trial_result.execution_time_seconds:.2f}s' if trial_result.execution_time_seconds is not None else 'N/A'}`")
        lines.append("")

        if trial_result.reasons:
            lines.append("### Trial Notes")
            for r in trial_result.reasons:
                lines.append(f"- {r}")
            lines.append("")

        lines.append("### Proposed Integration Probe Script")
        lines.append("```python")
        lines.append(trial_result.probe_code.strip())
        lines.append("```")
        lines.append("")

        if trial_result.stdout:
            lines.append("### Container Standard Output")
            lines.append("```text")
            lines.append(trial_result.stdout.strip())
            lines.append("```")
            lines.append("")

        if trial_result.stderr:
            lines.append("### Container Standard Error")
            lines.append("```text")
            lines.append(trial_result.stderr.strip())
            lines.append("```")
            lines.append("")
    else:
        lines.append("*No integration trial has been executed.*")
        lines.append("")

    # 5. Trust & Limitations Disclaimers
    lines.append("## 5. Trust, Scope, and Safety Disclaimers")
    lines.append("1. **Hypothesis vs. Fact:** AI-generated recommendations are hypotheses. Evidence in this brief is derived solely from official PyPI registry responses, declared project files, and isolated container execution.")
    lines.append("2. **No Guarantee of Production Readiness:** A `PASS` outcome in a minimal integration probe confirms isolated syntax and basic initialization only. It does not establish full application compatibility, performance characteristics, or freedom from regressions.")
    lines.append("3. **Scope of Dependency Analysis:** LibTrial evaluates direct version constraints declared in project configuration files. Transitive dependency resolution, C-extension build dependencies, and system-level shared libraries are unverified.")
    lines.append("4. **Host Environment Protection:** Host environments remain untouched; candidate packages are never installed or run on the host system.")
    lines.append("")

    return "\n".join(lines)
