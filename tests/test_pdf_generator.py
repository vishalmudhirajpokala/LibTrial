"""Tests for PDF report generator."""
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
from libtrial.pdf_generator import generate_pdf_report


def test_generate_pdf_report_basic():
    profile = ProjectProfile(
        project_path="examples/sample_project",
        project_name="test-project",
        python_version=">=3.10",
        declared_dependencies=["fastapi", "pydantic"],
    )
    cand = CandidateSuggestion(
        name="polars",
        import_name="polars",
        capability="Fast CSV reader",
        fit_rationale="Matches requirement",
    )
    meta = PyPIMetadata(
        name="polars",
        version="1.0.0",
        requires_python=">=3.9",
        license="MIT License",
        requires_dist=["numpy"],
    )
    compat = CompatibilityCheck(
        verdict=CompatibilityVerdict.COMPATIBLE_WITH_AVAILABLE_EVIDENCE,
        python_compatibility_note="Python 3.10 is compatible",
    )
    eval_item = CandidateEvaluation(
        suggestion=cand,
        pypi_metadata=meta,
        compatibility=compat,
    )
    trial_res = TrialResult(
        candidate_name="polars",
        probe_code="import polars\nprint('ok')",
        outcome=TrialOutcome.PASS,
        exit_code=0,
        execution_time_seconds=1.25,
        docker_available=True,
    )

    pdf_bytes = generate_pdf_report(
        profile=profile,
        requirement="High performance CSV reader",
        evaluations=[eval_item],
        selected_candidate_name="polars",
        trial_result=trial_res,
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")
