"""PyPI JSON API client and metadata verification module."""

import re
from typing import Dict, List, Optional
import httpx

from libtrial.models import GitHubMetadata, PyPIMetadata


class PyPIClient:
    """Queries official PyPI JSON API and optional GitHub repository metadata."""

    def __init__(self, timeout: float = 8.0, client: Optional[httpx.Client] = None):
        self._timeout = timeout
        self._client = client or httpx.Client(
            timeout=timeout,
            headers={"User-Agent": "LibTrial/0.1.0 (Hackathon MVP; https://github.com/libtrial)"},
            follow_redirects=True,
        )

    def close(self):
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_package_metadata(self, package_name: str, fetch_github: bool = True) -> PyPIMetadata:
        """Fetches registry metadata from the official PyPI JSON API.
        
        Never invents missing metadata; missing fields are recorded as 'unknown'.
        """
        clean_name = package_name.strip()
        if not clean_name:
            return PyPIMetadata(
                name=package_name,
                is_found=False,
                raw_error="Package name is empty or invalid.",
            )

        url = f"https://pypi.org/pypi/{clean_name}/json"
        try:
            response = self._client.get(url)
            if response.status_code == 404:
                return PyPIMetadata(
                    name=clean_name,
                    is_found=False,
                    raw_error=f"Package '{clean_name}' was not found on PyPI (HTTP 404).",
                )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            return PyPIMetadata(
                name=clean_name,
                is_found=False,
                raw_error=f"HTTP {exc.response.status_code} error from PyPI API: {exc}",
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            return PyPIMetadata(
                name=clean_name,
                is_found=False,
                raw_error=f"Network error querying PyPI for '{clean_name}': {exc}",
            )
        except Exception as exc:
            return PyPIMetadata(
                name=clean_name,
                is_found=False,
                raw_error=f"Malformed data or unexpected error from PyPI: {exc}",
            )

        info = data.get("info")
        if not isinstance(info, dict):
            return PyPIMetadata(
                name=clean_name,
                is_found=False,
                raw_error="PyPI response missing 'info' metadata object.",
            )

        # Extract version
        version = info.get("version") or "unknown"

        # Extract summary
        summary = info.get("summary") or "unknown"

        # Extract requires_python
        requires_python = info.get("requires_python")
        if not requires_python or not str(requires_python).strip():
            requires_python = "unknown"

        # Extract dependencies (requires_dist)
        requires_dist = info.get("requires_dist")
        clean_dist: List[str] = []
        if isinstance(requires_dist, list):
            clean_dist = [str(d) for d in requires_dist if d]

        # Extract license (never invent)
        license_str = info.get("license")
        if not license_str or not str(license_str).strip() or str(license_str).strip().upper() == "UNKNOWN":
            license_str = self._extract_license_from_classifiers(info.get("classifiers", []))

        # Extract project URLs
        raw_urls = info.get("project_urls")
        project_urls: Dict[str, str] = {}
        if isinstance(raw_urls, dict):
            for k, v in raw_urls.items():
                if isinstance(k, str) and isinstance(v, str):
                    project_urls[k] = v

        # Add home_page if present
        home_page = info.get("home_page")
        if home_page and isinstance(home_page, str) and "Homepage" not in project_urls:
            project_urls["Homepage"] = home_page

        # Optional GitHub metadata fetch
        github_meta: Optional[GitHubMetadata] = None
        if fetch_github:
            github_url = self._find_github_url(project_urls)
            if github_url:
                github_meta = self._fetch_github_metadata(github_url)

        return PyPIMetadata(
            name=clean_name,
            version=str(version).strip(),
            summary=str(summary).strip(),
            requires_python=str(requires_python).strip(),
            requires_dist=clean_dist,
            license=str(license_str).strip(),
            project_urls=project_urls if project_urls else None,
            github_metadata=github_meta,
            is_found=True,
        )

    def _extract_license_from_classifiers(self, classifiers: List[str]) -> str:
        """Finds license string from PyPI classifiers if available."""
        if not isinstance(classifiers, list):
            return "unknown"
        for c in classifiers:
            if isinstance(c, str) and c.startswith("License :: OSI Approved :: "):
                return c.replace("License :: OSI Approved :: ", "").strip()
            if isinstance(c, str) and c.startswith("License :: "):
                return c.replace("License :: ", "").strip()
        return "unknown"

    def _find_github_url(self, urls: Dict[str, str]) -> Optional[str]:
        """Identifies a valid GitHub repository URL from project URLs."""
        github_pattern = re.compile(r"https?://(?:www\.)?github\.com/([a-zA-Z0-9_\-]+)/([a-zA-Z0-9_\-]+)")
        for url in urls.values():
            if isinstance(url, str) and "github.com" in url:
                match = github_pattern.search(url)
                if match:
                    owner, repo = match.group(1), match.group(2)
                    # Clean trailing suffixes like .git
                    repo = repo.removesuffix(".git")
                    return f"https://github.com/{owner}/{repo}"
        return None

    def _fetch_github_metadata(self, repo_url: str) -> Optional[GitHubMetadata]:
        """Safely queries public GitHub repository API for non-critical context."""
        match = re.search(r"github\.com/([a-zA-Z0-9_\-]+)/([a-zA-Z0-9_\-]+)", repo_url)
        if not match:
            return None
        owner, repo = match.group(1), match.group(2)
        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        try:
            res = self._client.get(api_url, timeout=3.0)
            if res.status_code == 200:
                data = res.json()
                return GitHubMetadata(
                    repo_url=repo_url,
                    stars=data.get("stargazers_count"),
                    forks=data.get("forks_count"),
                    is_archived=data.get("archived"),
                    pushed_at=data.get("pushed_at"),
                    open_issues=data.get("open_issues_count"),
                )
        except Exception:
            # Fall back safely; never abort the evaluation on GitHub API failures or rate limits
            pass
        return GitHubMetadata(repo_url=repo_url)
