"""Tests for Markdown investigation report generator."""

import pytest
from libtrial.models import (
    CandidateEvaluation,
    CandidateSuggestion,
    CompatibilityCheck,
    CompatibilityVerdict,
    ProjectProfile,
    PyPIMetadata,
    TrialOutcome,
    TrialResult,
)
from libtrial.report_generator import generate_markdown_report


def test_generate_markdown_report_full():
    """Verify complete report with project, candidates, trial, and disclaimers."""
    profile = ProjectProfile(
        project_path="./my_project",
        project_name="fast-analytics",
        python_version=">=3.11",
        declared_dependencies=["fastapi>=0.100.0", "urllib3==1.26.15"],
        detected_frameworks=["fastapi"],
        config_files=["pyproject.toml"],
        total_python_files=5,
    )
    req = "High performance CSV and Parquet reader"
    sug = CandidateSuggestion(
        name="polars",
        import_name="polars",
        capability="Fast DataFrame engine",
        fit_rationale="Efficient memory usage",
        evidence_needed="Check wheels",
    )
    pypi_meta = PyPIMetadata(
        name="polars",
        version="1.0.0",
        requires_python=">=3.9",
        license="MIT",
        requires_dist=["pyarrow>=14.0.0"],
        is_found=True,
    )
    compat = CompatibilityCheck(
        verdict=CompatibilityVerdict.COMPATIBLE_WITH_AVAILABLE_EVIDENCE,
        python_compatibility_note="Overlaps on Python 3.11",
        dependency_conflict_notes=[],
    )
    eval_item = CandidateEvaluation(suggestion=sug, pypi_metadata=pypi_meta, compatibility=compat)

    trial = TrialResult(
        candidate_name="polars",
        outcome=TrialOutcome.PASS,
        probe_code="import polars\nprint('PROBE_OK')",
        user_consented=True,
        docker_available=True,
        stdout="PROBE_OK",
        exit_code=0,
        execution_time_seconds=1.25,
    )

    report = generate_markdown_report(
        profile=profile,
        requirement=req,
        evaluations=[eval_item],
        selected_candidate_name="polars",
        trial_result=trial,
    )

    assert "# 🧪 LibTrial — Evidence-Backed Investigation Report" in report
    assert "fast-analytics" in report
    assert ">=3.11" in report
    assert "polars" in report
    assert "https://pypi.org/project/polars/" in report
    assert "COMPATIBLE WITH AVAILABLE EVIDENCE" in report
    assert "PASS" in report
    assert "PROBE_OK" in report
    assert "Trust, Scope, and Safety Disclaimers" in report


def test_generate_markdown_report_not_run():
    """Verify report handles NOT_RUN trial and 404 package cleanly."""
    profile = ProjectProfile(project_path=".")
    req = "Some tool"
    sug = CandidateSuggestion(name="missing-lib")
    pypi_meta = PyPIMetadata(name="missing-lib", is_found=False, raw_error="HTTP 404")
    compat = CompatibilityCheck(
        verdict=CompatibilityVerdict.INSUFFICIENT_EVIDENCE,
        python_compatibility_note="Package not found on PyPI",
    )
    eval_item = CandidateEvaluation(suggestion=sug, pypi_metadata=pypi_meta, compatibility=compat)

    trial = TrialResult(
        candidate_name="missing-lib",
        outcome=TrialOutcome.NOT_RUN,
        probe_code="# probe",
        user_consented=False,
        reasons=["User consent was not granted."],
    )

    report = generate_markdown_report(
        profile=profile,
        requirement=req,
        evaluations=[eval_item],
        selected_candidate_name="missing-lib",
        trial_result=trial,
    )

    assert "NOT RUN" in report
    assert "Not Found (404)" in report
    assert "User consent was not granted." in report
