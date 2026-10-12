"""LibTrial package root."""

from libtrial.candidate_discovery import CandidateDiscovery
from libtrial.compatibility import evaluate_compatibility
from libtrial.config import Settings, get_settings
from libtrial.llm_client import GemmaClient
from libtrial.models import (
    CandidateEvaluation,
    CandidateSuggestion,
    CompatibilityCheck,
    CompatibilityVerdict,
    ProjectProfile,
    PyPIMetadata,
    SourceExcerpt,
    TrialOutcome,
    TrialResult,
)
from libtrial.pypi_client import PyPIClient
from libtrial.repo_inspector import inspect_repository
from libtrial.report_generator import generate_markdown_report
from libtrial.trial_runner import (
    generate_probe_script,
    is_docker_available,
    run_isolated_trial,
    validate_probe_safety,
)

__version__ = "0.1.0"
__all__ = [
    "CandidateDiscovery",
    "CandidateEvaluation",
    "CandidateSuggestion",
    "CompatibilityCheck",
    "CompatibilityVerdict",
    "GemmaClient",
    "ProjectProfile",
    "PyPIClient",
    "Settings",
    "SourceExcerpt",
    "TrialOutcome",
    "TrialResult",
    "evaluate_compatibility",
    "generate_markdown_report",
    "generate_probe_script",
    "get_settings",
    "inspect_repository",
    "is_docker_available",
    "run_isolated_trial",
    "validate_probe_safety",
]
