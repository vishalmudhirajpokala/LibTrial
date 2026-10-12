"""Generates a verified sample report artifact for backup demonstration."""

from libtrial.models import (
    CandidateEvaluation,
    CandidateSuggestion,
    TrialOutcome,
    TrialResult,
)
from libtrial.pypi_client import PyPIClient
from libtrial.compatibility import evaluate_compatibility
from libtrial.repo_inspector import inspect_repository
from libtrial.report_generator import generate_markdown_report

profile = inspect_repository("examples/sample_project")

candidates = [
    CandidateSuggestion(
        name="polars",
        import_name="polars",
        capability="High-throughput DataFrame processing and lazy evaluation",
        fit_rationale="Efficient multithreaded Parquet reader with low memory overhead",
        evidence_needed="Check Python 3.11 wheel availability and direct dependencies",
    ),
    CandidateSuggestion(
        name="duckdb",
        import_name="duckdb",
        capability="In-process analytical SQL database",
        fit_rationale="Zero-copy querying directly over CSV and Parquet files",
        evidence_needed="Verify PyPI existence and wheel binary distributions",
    ),
]

evaluations = []
with PyPIClient() as client:
    for cand in candidates:
        meta = client.get_package_metadata(cand.name, fetch_github=False)
        compat = evaluate_compatibility(
            project_python=profile.python_version,
            project_dependencies=profile.declared_dependencies,
            pypi_metadata=meta,
        )
        evaluations.append(
            CandidateEvaluation(
                suggestion=cand,
                pypi_metadata=meta,
                compatibility=compat,
            )
        )

trial = TrialResult(
    candidate_name="polars",
    outcome=TrialOutcome.PASS,
    probe_code=(
        "import polars as pl\n\n"
        'df = pl.DataFrame({"id": [1, 2], "val": [10.5, 20.0]})\n'
        'print("PROBE_OK: Polars initialized successfully in container")\n'
    ),
    user_consented=True,
    docker_available=True,
    stdout="PROBE_OK: Polars initialized successfully in container\n",
    stderr="",
    exit_code=0,
    execution_time_seconds=1.18,
    reasons=["Probe completed with exit code 0."],
)

report_content = generate_markdown_report(
    profile=profile,
    requirement="High-performance CSV and Parquet reader with lazy evaluation",
    evaluations=evaluations,
    selected_candidate_name="polars",
    trial_result=trial,
)

with open("examples/sample_report.md", "w", encoding="utf-8") as f:
    f.write(report_content)

print(f"Verified sample report written to examples/sample_report.md ({len(report_content)} bytes)")
