"""Tests for isolated integration probe runner and AST safety verification."""

import subprocess
import pytest

from libtrial.models import (
    CandidateSuggestion,
    ProjectProfile,
    PyPIMetadata,
    TrialOutcome,
)
from libtrial.trial_runner import (
    generate_probe_script,
    run_isolated_trial,
    validate_probe_safety,
)


def test_safe_probe_passes_validation():
    """Clean probe importing library and calling basic API must pass AST validation."""
    safe_code = """
import polars as pl

df = pl.DataFrame({"a": [1, 2, 3]})
assert df.shape == (3, 1)
print("PROBE_OK: Polars initialized successfully")
"""
    is_safe, reasons = validate_probe_safety(safe_code)
    assert is_safe is True
    assert reasons == []


def test_unsafe_probe_rejected_subprocess():
    """Probe attempting to import subprocess or shell execution must be rejected."""
    bad_code = """
import subprocess
subprocess.run(["echo", "hacked"])
"""
    is_safe, reasons = validate_probe_safety(bad_code)
    assert is_safe is False
    assert any("subprocess" in r for r in reasons)


def test_unsafe_probe_rejected_eval_and_exec():
    """Probe calling eval or exec dynamically must be rejected."""
    bad_code = """
import polars
eval("__import__('os').system('ls')")
"""
    is_safe, reasons = validate_probe_safety(bad_code)
    assert is_safe is False
    assert any("eval" in r for r in reasons)


def test_unsafe_probe_rejected_file_write():
    """Probe attempting to write to files must be rejected."""
    bad_code = """
import polars
with open("test.txt", "w") as f:
    f.write("hello")
"""
    is_safe, reasons = validate_probe_safety(bad_code)
    assert is_safe is False
    assert any("open()" in r for r in reasons)


def test_user_refusal_returns_not_run():
    """If user consent is False, execution must not be attempted."""
    result = run_isolated_trial(
        candidate_name="polars",
        candidate_version="1.0.0",
        probe_code="import polars\nprint('PROBE_OK')",
        user_consented=False,
    )
    assert result.outcome == TrialOutcome.NOT_RUN
    assert result.user_consented is False
    assert any("consent was not granted" in r for r in result.reasons)


def test_docker_unavailable_returns_not_run():
    """When Docker is unavailable, return NOT_RUN and strictly avoid host execution."""
    result = run_isolated_trial(
        candidate_name="polars",
        candidate_version="1.0.0",
        probe_code="import polars\nprint('PROBE_OK')",
        user_consented=True,
        docker_check_fn=lambda: False,  # Mock Docker unavailable
    )
    assert result.outcome == TrialOutcome.NOT_RUN
    assert result.docker_available is False
    assert any("Docker is unavailable" in r for r in result.reasons)


def test_unsafe_probe_blocks_execution():
    """Unsafe probe with user consent is blocked before invoking Docker."""
    unsafe_code = "import subprocess\nsubprocess.run(['rm', '-rf', '/'])"
    result = run_isolated_trial(
        candidate_name="bad-lib",
        candidate_version="1.0.0",
        probe_code=unsafe_code,
        user_consented=True,
        docker_check_fn=lambda: True,
    )
    assert result.outcome == TrialOutcome.NOT_RUN
    assert any("Safety check rejected probe" in r for r in result.reasons)


def test_probe_generation_fallback():
    """When GemmaClient is None, probe generator provides a clean import fallback."""
    cand = CandidateSuggestion(
        name="polars",
        import_name="polars",
        capability="DataFrame library",
        fit_rationale="Fast",
        evidence_needed="Check",
    )
    meta = PyPIMetadata(name="polars", version="1.0.0")
    profile = ProjectProfile(project_path=".")

    probe = generate_probe_script(cand, meta, profile, "Fast data reader", client=None)
    assert "import polars" in probe
    assert "PROBE_OK" in probe
    is_safe, _ = validate_probe_safety(probe)
    assert is_safe is True
