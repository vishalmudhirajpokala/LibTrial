"""Tests for candidate hypothesis parsing and capping."""

import pytest
from libtrial.candidate_discovery import CandidateDiscovery
from libtrial.models import ProjectProfile


class DummyGemmaClient:
    def __init__(self, response_text: str):
        self.response_text = response_text
        self.model_name = "test-gemma"

    def generate_text(self, prompt: str) -> str:
        return self.response_text


def test_parse_valid_json_candidates():
    """Verify clean parsing of valid JSON candidate array."""
    json_text = """
    [
      {
        "name": "polars",
        "import_name": "polars",
        "capability": "Blazingly fast DataFrame processing",
        "fit_rationale": "Matches high-throughput requirements",
        "evidence_needed": "Check Python 3.11 wheel availability"
      },
      {
        "name": "duckdb",
        "import_name": "duckdb",
        "capability": "In-process analytical SQL database",
        "fit_rationale": "Provides zero-copy Parquet querying",
        "evidence_needed": "Check package size and C-extension needs"
      }
    ]
    """
    discovery = CandidateDiscovery(client=DummyGemmaClient(json_text))
    profile = ProjectProfile(project_path=".")
    candidates = discovery.discover_candidates("Fast DataFrame library", profile)

    assert len(candidates) == 2
    assert candidates[0].name == "polars"
    assert candidates[0].import_name == "polars"
    assert candidates[1].name == "duckdb"


def test_parse_markdown_wrapped_json():
    """Ensure markdown code fences (```json ... ```) are cleanly stripped."""
    wrapped_text = """
    ```json
    [
      {
        "name": "httpx",
        "import_name": "httpx",
        "capability": "Async and sync HTTP client",
        "fit_rationale": "Drop-in replacement for requests",
        "evidence_needed": "Verify HTTP/2 dependencies"
      }
    ]
    ```
    """
    discovery = CandidateDiscovery(client=DummyGemmaClient(wrapped_text))
    profile = ProjectProfile(project_path=".")
    candidates = discovery.discover_candidates("HTTP client", profile)

    assert len(candidates) == 1
    assert candidates[0].name == "httpx"


def test_candidates_strictly_capped_at_three():
    """Output must never exceed 3 candidates even if model returned more."""
    five_items = """
    [
      {"name": "lib1"}, {"name": "lib2"}, {"name": "lib3"}, {"name": "lib4"}, {"name": "lib5"}
    ]
    """
    discovery = CandidateDiscovery(client=DummyGemmaClient(five_items))
    profile = ProjectProfile(project_path=".")
    candidates = discovery.discover_candidates("Tools", profile)

    assert len(candidates) == 3


def test_handles_malformed_llm_output_gracefully():
    """Non-JSON or broken text from the LLM returns an empty list without raising."""
    broken_text = "I apologize, but I cannot fulfill this request at this time."
    discovery = CandidateDiscovery(client=DummyGemmaClient(broken_text))
    profile = ProjectProfile(project_path=".")
    candidates = discovery.discover_candidates("Tools", profile)

    assert candidates == []


def test_candidate_name_sanitization():
    """Verify that quotes, backticks, and version comments are cleanly stripped."""
    messy_text = """
    [
      {"name": "`polars` (recommended)"},
      {"name": "duckdb>=0.9"},
      {"name": "'pyarrow'"}
    ]
    """
    discovery = CandidateDiscovery(client=DummyGemmaClient(messy_text))
    profile = ProjectProfile(project_path=".")
    candidates = discovery.discover_candidates("Data tools", profile)

    assert len(candidates) == 3
    assert candidates[0].name == "polars"
    assert candidates[1].name == "duckdb"
    assert candidates[2].name == "pyarrow"

