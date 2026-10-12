"""Tests for compatibility evaluation and collision detection."""

import pytest
from libtrial.compatibility import evaluate_compatibility
from libtrial.models import CompatibilityVerdict, PyPIMetadata


def test_compatible_with_available_evidence():
    """Package with overlapping Python version and no collisions is COMPATIBLE."""
    meta = PyPIMetadata(
        name="polars",
        version="1.0.0",
        requires_python=">=3.9",
        requires_dist=["pyarrow>=14.0.0"],
        license="MIT",
        is_found=True,
    )
    project_deps = ["fastapi>=0.100.0", "pydantic>=2.0"]
    result = evaluate_compatibility(
        project_python=">=3.11",
        project_dependencies=project_deps,
        pypi_metadata=meta,
    )

    assert result.verdict == CompatibilityVerdict.COMPATIBLE_WITH_AVAILABLE_EVIDENCE
    assert result.conflicting_dependencies == []
    assert "compatible" in result.python_compatibility_note.lower()


def test_potential_conflict_python_mismatch():
    """Conflicting Python version ranges must trigger POTENTIAL_CONFLICT."""
    meta = PyPIMetadata(
        name="legacy-lib",
        version="0.5.0",
        requires_python="<3.10",
        requires_dist=[],
        is_found=True,
    )
    result = evaluate_compatibility(
        project_python=">=3.11",
        project_dependencies=[],
        pypi_metadata=meta,
    )

    assert result.verdict == CompatibilityVerdict.POTENTIAL_CONFLICT
    assert "Direct Python mismatch" in result.python_compatibility_note


def test_potential_conflict_direct_dependency_collision():
    """Direct conflict on pinned dependency version triggers POTENTIAL_CONFLICT."""
    meta = PyPIMetadata(
        name="modern-client",
        version="2.0.0",
        requires_python=">=3.10",
        requires_dist=["urllib3>=2.0.0"],
        is_found=True,
    )
    # Project explicitly pins legacy urllib3
    project_deps = ["urllib3==1.26.15", "requests>=2.28"]
    result = evaluate_compatibility(
        project_python=">=3.11",
        project_dependencies=project_deps,
        pypi_metadata=meta,
    )

    assert result.verdict == CompatibilityVerdict.POTENTIAL_CONFLICT
    assert "urllib3" in result.conflicting_dependencies
    assert any("Collision on 'urllib3'" in note for note in result.dependency_conflict_notes)


def test_potential_conflict_candidate_pinned_by_project():
    """If project pins candidate to an incompatible older version, triggers conflict."""
    meta = PyPIMetadata(
        name="polars",
        version="1.0.0",
        requires_python=">=3.9",
        requires_dist=[],
        is_found=True,
    )
    project_deps = ["polars<0.19.0"]
    result = evaluate_compatibility(
        project_python=">=3.11",
        project_dependencies=project_deps,
        pypi_metadata=meta,
    )

    assert result.verdict == CompatibilityVerdict.POTENTIAL_CONFLICT
    assert "polars" in result.conflicting_dependencies


def test_insufficient_evidence_when_python_unknown():
    """When either Python requirement is unknown, return INSUFFICIENT_EVIDENCE."""
    meta = PyPIMetadata(
        name="untyped-pkg",
        version="0.1.0",
        requires_python="unknown",
        requires_dist=[],
        is_found=True,
    )
    result = evaluate_compatibility(
        project_python="unknown",
        project_dependencies=[],
        pypi_metadata=meta,
    )

    assert result.verdict == CompatibilityVerdict.INSUFFICIENT_EVIDENCE
    assert "unknown" in result.python_compatibility_note.lower()


def test_insufficient_evidence_when_package_not_found():
    """Unregistered or hallucinated packages result in INSUFFICIENT_EVIDENCE."""
    meta = PyPIMetadata(
        name="ghost-pkg",
        is_found=False,
    )
    result = evaluate_compatibility(
        project_python=">=3.11",
        project_dependencies=[],
        pypi_metadata=meta,
    )

    assert result.verdict == CompatibilityVerdict.INSUFFICIENT_EVIDENCE
    assert "not found on PyPI" in result.python_compatibility_note
