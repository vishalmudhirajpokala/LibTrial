"""Tests for Pydantic schema validation in LibTrial."""

import pytest
from pydantic import ValidationError
from libtrial.models import (
    CandidateSuggestion,
    RecommendationResponse,
    ProjectSpec,
    PyPIMetadata,
    VerificationStatus,
    TrialResult,
    TrialStatus,
)


def test_candidate_suggestion_schema():
    """Verify CandidateSuggestion model validates required fields."""
    cand = CandidateSuggestion(
        name="polars",
        summary="Blazingly fast DataFrame library",
        rationale="Superior performance on large Parquet files",
    )
    assert cand.name == "polars"
    assert "DataFrame" in cand.summary


def test_recommendation_response_max_candidates():
    """Ensure RecommendationResponse allows at most 3 candidates."""
    candidates = [
        CandidateSuggestion(name=f"lib_{i}", summary="summary", rationale="rationale")
        for i in range(3)
    ]
    resp = RecommendationResponse(candidates=candidates)
    assert len(resp.candidates) == 3

    # Attempting to add a 4th candidate must fail validation
    with pytest.raises(ValidationError):
        RecommendationResponse(
            candidates=candidates + [CandidateSuggestion(name="lib_4", summary="s", rationale="r")]
        )


def test_project_spec_defaults():
    """Verify ProjectSpec initializes expected default values."""
    spec = ProjectSpec(project_path="./my_project")
    assert spec.dependencies == []
    assert spec.python_version is None
    assert spec.has_pyproject is False


def test_pypi_metadata_and_trial_result():
    """Verify registry metadata and trial result enums."""
    meta = PyPIMetadata(
        name="requests",
        version="2.31.0",
        requires_python=">=3.8",
        requires_dist=["urllib3", "certifi"],
        license="Apache 2.0",
    )
    assert meta.is_found is True
    assert meta.version == "2.31.0"

    trial = TrialResult(
        candidate_name="requests",
        status=TrialStatus.SUCCESS,
        probe_code="import requests; print(requests.__version__)",
        stdout="2.31.0",
        exit_code=0,
    )
    assert trial.status == TrialStatus.SUCCESS
    assert trial.exit_code == 0
