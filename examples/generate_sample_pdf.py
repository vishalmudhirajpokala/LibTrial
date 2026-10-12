"""Generate verified sample PDF report for demonstration and backup."""
from libtrial.models import (
    CandidateEvaluation,
    CandidateSuggestion,
    CompatibilityCheck,
    CompatibilityVerdict,
    PyPIMetadata,
    TrialOutcome,
    TrialResult,
)
from libtrial.pdf_generator import generate_pdf_report
from libtrial.repo_inspector import inspect_repository


def create_sample_pdf():
    profile = inspect_repository("examples/sample_project")

    c1 = CandidateSuggestion(
        name="polars",
        import_name="polars",
        capability="High-performance DataFrame library with dedicated Lazy API for query optimization and efficient CSV/Parquet reading.",
        fit_rationale="Directly addresses fast analytics requirement with lazy streaming engine.",
    )
    m1 = PyPIMetadata(
        name="polars",
        version="1.24.0",
        requires_python=">=3.9",
        license="MIT License",
        requires_dist=["numpy", "pyarrow"],
    )
    comp1 = CompatibilityCheck(
        verdict=CompatibilityVerdict.COMPATIBLE_WITH_AVAILABLE_EVIDENCE,
        python_compatibility_note="Python target overlaps [3.11, 3.12, 3.13, 3.14]. Project >=3.10 compatible.",
    )
    ev1 = CandidateEvaluation(suggestion=c1, pypi_metadata=m1, compatibility=comp1)

    c2 = CandidateSuggestion(
        name="duckdb",
        import_name="duckdb",
        capability="In-process analytical database engine with vectorized SQL and Parquet execution.",
        fit_rationale="In-process SQL querying over CSV and Parquet files.",
    )
    m2 = PyPIMetadata(
        name="duckdb",
        version="1.2.0",
        requires_python=">=3.8",
        license="MIT License",
        requires_dist=[],
    )
    comp2 = CompatibilityCheck(
        verdict=CompatibilityVerdict.COMPATIBLE_WITH_AVAILABLE_EVIDENCE,
        python_compatibility_note="Python target overlaps [3.8, 3.9, 3.10, 3.11, 3.12, 3.13].",
    )
    ev2 = CandidateEvaluation(suggestion=c2, pypi_metadata=m2, compatibility=comp2)

    c3 = CandidateSuggestion(
        name="dask",
        import_name="dask",
        capability="Parallel computing library with task graphs for large-scale CSV/Parquet datasets.",
        fit_rationale="Scaling beyond single-machine memory constraints.",
    )
    m3 = PyPIMetadata(
        name="dask",
        version="2024.12.0",
        requires_python=">=3.10",
        license="BSD-3-Clause",
        requires_dist=["pandas", "pyarrow"],
    )
    comp3 = CompatibilityCheck(
        verdict=CompatibilityVerdict.COMPATIBLE_WITH_AVAILABLE_EVIDENCE,
        python_compatibility_note="Python target overlaps [3.10, 3.11, 3.12].",
    )
    ev3 = CandidateEvaluation(suggestion=c3, pypi_metadata=m3, compatibility=comp3)

    trial_res = TrialResult(
        candidate_name="polars",
        probe_code="import polars as pl\ndf = pl.DataFrame({'col': [1, 2, 3]})\nprint('Probe success')",
        outcome=TrialOutcome.PASS,
        exit_code=0,
        execution_time_seconds=1.85,
        docker_available=True,
        reasons=[
            "Process exited normally with returncode 0.",
            "Minimal DataFrame evaluation passed.",
        ],
        stdout="Probe success\n",
    )

    pdf_bytes = generate_pdf_report(
        profile=profile,
        requirement="High-performance CSV and Parquet reader with lazy evaluation",
        evaluations=[ev1, ev2, ev3],
        selected_candidate_name="polars",
        trial_result=trial_res,
    )

    with open("examples/sample_report.pdf", "wb") as f:
        f.write(pdf_bytes)

    print(f"Generated examples/sample_report.pdf ({len(pdf_bytes)} bytes)")


if __name__ == "__main__":
    create_sample_pdf()
