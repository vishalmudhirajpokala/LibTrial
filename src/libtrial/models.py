"""Pydantic schemas and domain models for LibTrial."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    NOT_FOUND = "NOT_FOUND"


class CompatibilityVerdict(str, Enum):
    COMPATIBLE_WITH_AVAILABLE_EVIDENCE = "COMPATIBLE WITH AVAILABLE EVIDENCE"
    POTENTIAL_CONFLICT = "POTENTIAL CONFLICT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT EVIDENCE"


class SourceExcerpt(BaseModel):
    """A bounded excerpt from a source file for inspection context."""
    file_path: str
    content: str
    line_count: int


class ProjectProfile(BaseModel):
    """Compact and verified repository profile."""
    project_path: str
    project_name: str = "unknown"
    python_version: str = "unknown"
    declared_dependencies: List[str] = Field(default_factory=list)
    detected_frameworks: List[str] = Field(default_factory=list)
    config_files: List[str] = Field(default_factory=list)
    source_excerpts: List[SourceExcerpt] = Field(default_factory=list)
    total_python_files: int = 0
    warnings: List[str] = Field(default_factory=list)


class ProjectSpec(BaseModel):
    """Metadata extracted from the user's local Python repository."""
    project_path: str
    python_version: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    has_pyproject: bool = False
    has_requirements: bool = False


class CandidateSuggestion(BaseModel):
    """A package hypothesis recommended by Gemma for the requirement."""
    name: str = Field(description="Distribution name on PyPI")
    import_name: str = Field(default="unknown", description="Expected import name, if known")
    capability: str = Field(default="", description="Specific capability provided")
    fit_rationale: str = Field(default="", description="Why it may fit the project")
    evidence_needed: str = Field(default="Verify PyPI existence, Python compatibility, and dependency conflicts", description="Evidence still needing checking")
    summary: Optional[str] = None
    rationale: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Structured response container for LLM suggestions."""
    candidates: List[CandidateSuggestion] = Field(
        default_factory=list,
        max_length=3,
        description="At most 3 candidate recommendations",
    )


class GitHubMetadata(BaseModel):
    """Public repository facts retrieved from GitHub API."""
    repo_url: Optional[str] = None
    stars: Optional[int] = None
    forks: Optional[int] = None
    is_archived: Optional[bool] = None
    pushed_at: Optional[str] = None
    open_issues: Optional[int] = None


class PyPIMetadata(BaseModel):
    """Direct ground-truth metadata from the PyPI JSON API."""
    name: str
    version: Optional[str] = "unknown"
    summary: Optional[str] = "unknown"
    requires_python: Optional[str] = "unknown"
    requires_dist: List[str] = Field(default_factory=list)
    license: Optional[str] = "unknown"
    project_urls: Optional[Dict[str, str]] = None
    github_metadata: Optional[GitHubMetadata] = None
    is_found: bool = True
    raw_error: Optional[str] = None


class CompatibilityCheck(BaseModel):
    """Deterministic compatibility evaluation against project spec."""
    verdict: CompatibilityVerdict = CompatibilityVerdict.INSUFFICIENT_EVIDENCE
    python_compatibility_note: str = "Not evaluated"
    dependency_conflict_notes: List[str] = Field(default_factory=list)
    conflicting_dependencies: List[str] = Field(default_factory=list)
    limitations_disclaimer: str = (
        "Evaluation covers declared direct constraints only. "
        "Transitive dependencies, native system libraries, and platform-specific wheels are unverified."
    )
    # Backward compatibility attributes
    python_version_status: VerificationStatus = VerificationStatus.UNKNOWN
    python_version_details: str = "Not evaluated"
    dependency_collision_status: VerificationStatus = VerificationStatus.UNKNOWN
    dependency_collision_details: str = "Not evaluated"


class CandidateEvaluation(BaseModel):
    """Full evaluation record for one candidate package."""
    suggestion: CandidateSuggestion
    pypi_metadata: Optional[PyPIMetadata] = None
    compatibility: CompatibilityCheck = Field(default_factory=CompatibilityCheck)


class TrialOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT RUN"
    INCONCLUSIVE = "INCONCLUSIVE"


class TrialStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    SKIPPED_DOCKER_UNAVAILABLE = "SKIPPED_DOCKER_UNAVAILABLE"


class TrialResult(BaseModel):
    """Results from evaluating an isolated integration probe in Docker."""
    candidate_name: str
    outcome: TrialOutcome = TrialOutcome.NOT_RUN
    probe_code: str
    user_consented: bool = False
    docker_available: bool = False
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    execution_time_seconds: Optional[float] = None
    reasons: List[str] = Field(default_factory=list)
    disclaimer: str = (
        "A minimal integration probe checks isolated syntax and basic API execution only. "
        "It does NOT prove full application compatibility, production readiness, or lack of regression."
    )
    # Backward compatibility attribute
    status: Optional[TrialStatus] = None

