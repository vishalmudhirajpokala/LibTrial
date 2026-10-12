"""Gemma 4-powered candidate package hypothesis generation."""

import json
import re
from typing import List, Optional

from libtrial.llm_client import GemmaClient
from libtrial.models import CandidateSuggestion, ProjectProfile

DISCOVERY_PROMPT_TEMPLATE = """You are a Python packaging expert assisting a developer.
The developer has a specific capability requirement for their project.

PROJECT CONTEXT:
- Project Name: {project_name}
- Target Python Version: {python_version}
- Detected Frameworks: {frameworks}
- Declared Direct Dependencies: {dependencies}

DEVELOPER REQUIREMENT:
"{requirement}"

TASK:
Suggest at most THREE (<= 3) plausible Python candidate packages published on PyPI that might fulfill this requirement.

CRITICAL RULES:
1. Treat your recommendations as HYPOTHESES, not verified facts.
2. Do NOT claim that a package definitely exists or works without registry verification.
3. Suggest the official PyPI distribution name (e.g. "polars", "httpx", "pillow").
4. Provide the expected import name (e.g. "PIL" for "pillow", "httpx" for "httpx").
5. Return ONLY a valid JSON array of objects. Do not wrap in markdown or prose.

JSON SCHEMA:
[
  {{
    "name": "<exact PyPI distribution name>",
    "import_name": "<expected import name if known, else 'unknown'>",
    "capability": "<concise description of specific capability provided>",
    "fit_rationale": "<why this may fit the user's project context>",
    "evidence_needed": "<what evidence needs checking (e.g. active maintenance, PyPI presence, Python version support)>"
  }}
]
"""


class CandidateDiscovery:
    """Generates candidate package hypotheses using Gemma."""

    def __init__(self, client: Optional[GemmaClient] = None):
        self.client = client or GemmaClient()

    def discover_candidates(
        self, requirement: str, profile: ProjectProfile
    ) -> List[CandidateSuggestion]:
        """Queries Gemma to generate at most 3 candidate package suggestions."""
        prompt = DISCOVERY_PROMPT_TEMPLATE.format(
            project_name=profile.project_name,
            python_version=profile.python_version,
            frameworks=", ".join(profile.detected_frameworks) or "None detected",
            dependencies=", ".join(profile.declared_dependencies[:15]) or "None declared",
            requirement=requirement.strip(),
        )

        raw_response = self.client.generate_text(prompt)
        return self._parse_response(raw_response)

    def _parse_response(self, text: str) -> List[CandidateSuggestion]:
        """Extracts and validates candidate hypotheses from LLM JSON output."""
        cleaned = text.strip()

        # Strip markdown code blocks if the model wrapped output
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", cleaned)
            if match:
                cleaned = match.group(1).strip()
            else:
                cleaned = re.sub(r"^```(?:json)?|```$", "", cleaned, flags=re.MULTILINE).strip()

        try:
            items = json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback regex search for JSON array
            array_match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", cleaned)
            if array_match:
                try:
                    items = json.loads(array_match.group(0))
                except json.JSONDecodeError:
                    return []
            else:
                return []

        if not isinstance(items, list):
            return []

        candidates: List[CandidateSuggestion] = []
        for item in items[:3]:  # Enforce at most 3
            if not isinstance(item, dict):
                continue
            raw_name = str(item.get("name") or item.get("distribution_name") or "")
            # Strip backticks, quotes, and punctuation
            clean_name = re.sub(r"[`'\"]", "", raw_name).strip()
            # Remove trailing comments, version specifiers, or parentheses (e.g. 'polars (recommended)' or 'polars>=1.0')
            clean_name = re.split(r"[><=~;!\[\(\s]", clean_name)[0].strip()

            if not clean_name:
                continue

            candidates.append(
                CandidateSuggestion(
                    name=clean_name,
                    import_name=str(item.get("import_name") or "unknown").strip(),
                    capability=str(item.get("capability") or "").strip(),
                    fit_rationale=str(item.get("fit_rationale") or item.get("rationale") or "").strip(),
                    evidence_needed=str(item.get("evidence_needed") or "Verify PyPI metadata").strip(),
                    summary=str(item.get("capability") or "").strip(),
                    rationale=str(item.get("fit_rationale") or "").strip(),
                )
            )

        return candidates
