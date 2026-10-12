"""Safe Python repository inspection module for LibTrial."""

import configparser
import os
import re
from pathlib import Path
from typing import List, Optional, Set, Tuple
import tomllib
from packaging.requirements import InvalidRequirement, Requirement

from libtrial.models import ProjectProfile, SourceExcerpt

# Directories to unconditionally ignore during inspection
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "ENV",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".nox",
    ".eggs",
    "eggs",
    "site-packages",
}

# Recognized configuration filenames
KNOWN_CONFIG_FILENAMES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.cfg",
    "setup.py",
    "Pipfile",
    "Pipfile.lock",
    "environment.yml",
    "runtime.txt",
}

# Known Python frameworks to identify strictly from declared dependencies
KNOWN_FRAMEWORKS = {
    "django",
    "fastapi",
    "flask",
    "starlette",
    "tornado",
    "litestar",
    "celery",
    "pytorch",
    "torch",
    "tensorflow",
    "pandas",
    "polars",
    "pydantic",
    "sqlalchemy",
    "sqlmodel",
    "streamlit",
}

# Safety & resource limits
MAX_FILE_SIZE_BYTES = 100 * 1024  # 100 KB
MAX_SCANNED_FILES = 300
MAX_EXCERPTS = 4
MAX_LINES_PER_EXCERPT = 50
MAX_TOTAL_EXCERPT_CHARS = 6000


def _is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """Verifies that target_path does not escape base_dir via symlinks or traversal."""
    try:
        resolved_target = target_path.resolve()
        resolved_base = base_dir.resolve()
        return resolved_target.is_relative_to(resolved_base)
    except (ValueError, RuntimeError, OSError):
        return False


def _clean_package_name(dep_str: str) -> Optional[str]:
    """Extracts a normalized package name from a dependency specification string."""
    dep_str = dep_str.strip()
    if not dep_str or dep_str.startswith("#"):
        return None
    try:
        return Requirement(dep_str).name.lower()
    except InvalidRequirement:
        # Fallback to regex splitting for non-standard or partial lines
        match = re.match(r"^([a-zA-Z0-9_\-\.]+)", dep_str)
        if match:
            return match.group(1).lower()
    return None


def _parse_pyproject(path: Path) -> Tuple[Optional[str], Optional[str], List[str]]:
    """Parses pyproject.toml safely using standard library tomllib."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None, None, []

    name = None
    python_ver = None
    deps: List[str] = []

    # Standard PEP 621 [project] table
    project_table = data.get("project", {})
    if isinstance(project_table, dict):
        if "name" in project_table and isinstance(project_table["name"], str):
            name = project_table["name"]
        if "requires-python" in project_table and isinstance(project_table["requires-python"], str):
            python_ver = project_table["requires-python"]
        if "dependencies" in project_table and isinstance(project_table["dependencies"], list):
            deps.extend([str(d) for d in project_table["dependencies"]])

    # Poetry support [tool.poetry]
    poetry_table = data.get("tool", {}).get("poetry", {})
    if isinstance(poetry_table, dict):
        if not name and "name" in poetry_table and isinstance(poetry_table["name"], str):
            name = poetry_table["name"]
        poetry_deps = poetry_table.get("dependencies", {})
        if isinstance(poetry_deps, dict):
            for pkg, ver in poetry_deps.items():
                if pkg.lower() == "python":
                    if not python_ver and isinstance(ver, str):
                        python_ver = ver
                else:
                    deps.append(f"{pkg} {ver}" if ver else pkg)

    return name, python_ver, deps


def _parse_requirements_txt(path: Path) -> List[str]:
    """Parses requirements.txt lines safely without executing pip."""
    deps: List[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return deps

    for line in content.splitlines():
        line = line.strip()
        # Skip empty lines, comments, and pip options (-r, -i, etc.)
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Strip inline comments
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        if line:
            deps.append(line)
    return deps


def _parse_setup_cfg(path: Path) -> Tuple[Optional[str], Optional[str], List[str]]:
    """Parses setup.cfg safely using standard configparser."""
    config = configparser.ConfigParser()
    try:
        config.read_string(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None, None, []

    name = config.get("metadata", "name", fallback=None)
    python_ver = config.get("options", "python_requires", fallback=None)
    deps = []
    install_requires = config.get("options", "install_requires", fallback="")
    for line in install_requires.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            deps.append(line)
    return name, python_ver, deps


def inspect_repository(repo_path: str) -> ProjectProfile:
    """Inspects a local Python repository safely and returns a bounded ProjectProfile.
    
    Raises:
        FileNotFoundError: If the path does not exist.
        NotADirectoryError: If the path is not a directory.
        ValueError: If the directory does not appear to be a Python repository.
    """
    base_dir = Path(repo_path).resolve()
    if not base_dir.exists():
        raise FileNotFoundError(f"Path does not exist: {repo_path}")
    if not base_dir.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {repo_path}")

    # Preliminary sanity check for Python repository markers
    has_repo_markers = False
    project_name: Optional[str] = None
    python_version: Optional[str] = None
    declared_dependencies: List[str] = []
    config_files: List[str] = []
    warnings: List[str] = []

    # Check for .git marker
    if (base_dir / ".git").is_dir():
        has_repo_markers = True

    # Scan top-level config files first
    pyproject_path = base_dir / "pyproject.toml"
    if pyproject_path.is_file():
        has_repo_markers = True
        config_files.append("pyproject.toml")
        name, py_ver, deps = _parse_pyproject(pyproject_path)
        if name:
            project_name = name
        if py_ver:
            python_version = py_ver
        declared_dependencies.extend(deps)

    req_path = base_dir / "requirements.txt"
    if req_path.is_file():
        has_repo_markers = True
        config_files.append("requirements.txt")
        req_deps = _parse_requirements_txt(req_path)
        declared_dependencies.extend(req_deps)

    setup_cfg_path = base_dir / "setup.cfg"
    if setup_cfg_path.is_file():
        has_repo_markers = True
        config_files.append("setup.cfg")
        cfg_name, cfg_py_ver, cfg_deps = _parse_setup_cfg(setup_cfg_path)
        if not project_name and cfg_name:
            project_name = cfg_name
        if not python_version and cfg_py_ver:
            python_version = cfg_py_ver
        declared_dependencies.extend(cfg_deps)

    runtime_path = base_dir / "runtime.txt"
    if runtime_path.is_file():
        config_files.append("runtime.txt")
        try:
            content = runtime_path.read_text(encoding="utf-8", errors="replace").strip()
            if content.startswith("python-"):
                python_version = python_version or content.replace("python-", "")
        except Exception:
            pass

    # Scan python files and excerpt candidates
    all_python_files: List[Path] = []
    scanned_count = 0

    for root, dirs, files in os.walk(base_dir):
        # Prune excluded directories in-place
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]

        current_dir = Path(root)

        # Check for symlink escaping repository root
        if current_dir.is_symlink() and not _is_safe_path(base_dir, current_dir):
            warnings.append(f"Skipped symlink directory escaping repository root: {current_dir.name}")
            dirs[:] = []
            continue

        for file_name in files:
            scanned_count += 1
            if scanned_count > MAX_SCANNED_FILES:
                warnings.append(f"Scanned file count exceeded limit ({MAX_SCANNED_FILES}); scan truncated.")
                break

            file_path = current_dir / file_name

            # Check if symlink escapes
            if file_path.is_symlink() and not _is_safe_path(base_dir, file_path):
                warnings.append(f"Skipped symlink file escaping repository root: {file_name}")
                continue

            # Record config files found in subdirectories if relevant
            if file_name in KNOWN_CONFIG_FILENAMES and file_name not in config_files:
                rel_cfg = str(file_path.relative_to(base_dir))
                if rel_cfg not in config_files:
                    config_files.append(rel_cfg)

            if file_name.endswith(".py"):
                has_repo_markers = True
                all_python_files.append(file_path)

        if scanned_count > MAX_SCANNED_FILES:
            break

    # If neither .git, config files, nor any Python files were found, reject
    if not has_repo_markers and not all_python_files:
        raise ValueError(
            f"Directory '{repo_path}' does not appear to be a Python repository "
            "(no Python files, .git, or configuration files found)."
        )

    # Detect frameworks strictly from declared dependencies (never from filenames)
    detected_frameworks: Set[str] = set()
    cleaned_deps_set: Set[str] = set()

    for dep_str in declared_dependencies:
        clean_name = _clean_package_name(dep_str)
        if clean_name:
            cleaned_deps_set.add(clean_name)
            if clean_name in KNOWN_FRAMEWORKS:
                detected_frameworks.add(clean_name)

    # Select representative excerpts safely (prioritizing entry points)
    def _priority(p: Path) -> int:
        name = p.name.lower()
        if name in {"app.py", "main.py", "cli.py", "server.py", "api.py"}:
            return 0
        if name == "__init__.py":
            return 1
        if len(p.relative_to(base_dir).parts) == 1:
            return 2
        return 3

    sorted_py_files = sorted(all_python_files, key=_priority)
    excerpts: List[SourceExcerpt] = []
    total_chars = 0

    for py_file in sorted_py_files:
        if len(excerpts) >= MAX_EXCERPTS:
            break

        rel_path = str(py_file.relative_to(base_dir))

        # Check file size limit
        try:
            stat_result = py_file.stat()
            if stat_result.st_size > MAX_FILE_SIZE_BYTES:
                warnings.append(f"Skipped oversized file ({stat_result.st_size} bytes): {rel_path}")
                continue
        except OSError:
            continue

        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lines = text.splitlines()[:MAX_LINES_PER_EXCERPT]
        excerpt_content = "\n".join(lines)

        # Enforce total characters boundary
        if total_chars + len(excerpt_content) > MAX_TOTAL_EXCERPT_CHARS:
            remaining_chars = MAX_TOTAL_EXCERPT_CHARS - total_chars
            if remaining_chars > 200:
                excerpt_content = excerpt_content[:remaining_chars] + "\n... [truncated]"
            else:
                break

        total_chars += len(excerpt_content)
        excerpts.append(
            SourceExcerpt(
                file_path=rel_path,
                content=excerpt_content,
                line_count=len(lines),
            )
        )

    # Deduplicate dependencies
    deduped_deps = list(dict.fromkeys(declared_dependencies))

    return ProjectProfile(
        project_path=str(base_dir),
        project_name=project_name or "unknown",
        python_version=python_version or "unknown",
        declared_dependencies=deduped_deps,
        detected_frameworks=sorted(list(detected_frameworks)),
        config_files=config_files,
        source_excerpts=excerpts,
        total_python_files=len(all_python_files),
        warnings=warnings,
    )
