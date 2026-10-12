"""Focused unit tests for repository inspection and security guardrails."""

import os
from pathlib import Path
import pytest

from libtrial.models import ProjectProfile
from libtrial.repo_inspector import inspect_repository, _is_safe_path, MAX_FILE_SIZE_BYTES


def test_missing_path_raises_file_not_found(tmp_path):
    """Inspecting a non-existent path must raise FileNotFoundError."""
    missing = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        inspect_repository(str(missing))


def test_file_path_raises_not_a_directory(tmp_path):
    """Supplying a file instead of a directory must raise NotADirectoryError."""
    some_file = tmp_path / "regular_file.txt"
    some_file.write_text("hello", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        inspect_repository(str(some_file))


def test_non_python_directory_raises_value_error(tmp_path):
    """Directories with no Python files or repo configs must be rejected."""
    empty_folder = tmp_path / "empty_dir"
    empty_folder.mkdir()
    (empty_folder / "random.txt").write_text("just text", encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        inspect_repository(str(empty_folder))
    assert "does not appear to be a Python repository" in str(exc.value)


def test_excluded_directories_are_skipped(tmp_path):
    """Files inside .venv, .git, node_modules, and build dirs must be ignored."""
    repo = tmp_path / "my_project"
    repo.mkdir()
    (repo / "pyproject.toml").write_text('[project]\nname = "test-pkg"\n', encoding="utf-8")

    # Legitimate root source file
    (repo / "app.py").write_text("print('legitimate')", encoding="utf-8")

    # Excluded directories with python files
    for excluded in [".venv", "venv", "node_modules", "build", "dist", "__pycache__", ".git"]:
        exc_dir = repo / excluded
        exc_dir.mkdir(parents=True, exist_ok=True)
        (exc_dir / "hidden.py").write_text("print('should be ignored')", encoding="utf-8")

    profile = inspect_repository(str(repo))

    assert profile.project_name == "test-pkg"
    assert profile.total_python_files == 1  # Only app.py counted
    excerpt_files = [e.file_path for e in profile.source_excerpts]
    assert "app.py" in excerpt_files
    for e_file in excerpt_files:
        for excluded in [".venv", "venv", "node_modules", "build", "dist", "__pycache__"]:
            assert excluded not in e_file


def test_dependency_parsing_and_unknown_fallbacks(tmp_path):
    """Dependencies from pyproject.toml and requirements.txt are cleanly parsed."""
    repo = tmp_path / "dep_project"
    repo.mkdir()

    # pyproject.toml with PEP 621
    pyproject_content = """
[project]
name = "awesome-api"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.100.0",
    "pydantic>=2.0",
]
"""
    (repo / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")

    # requirements.txt with comments, pip flags, and inline comments
    reqs_content = """
# Production requirements
-i https://pypi.org/simple
httpx==0.27.0 # http client
pytest>=8.0.0
"""
    (repo / "requirements.txt").write_text(reqs_content, encoding="utf-8")
    (repo / "main.py").write_text("import fastapi", encoding="utf-8")

    profile = inspect_repository(str(repo))

    assert profile.project_name == "awesome-api"
    assert profile.python_version == ">=3.11"
    assert "fastapi>=0.100.0" in profile.declared_dependencies
    assert "pydantic>=2.0" in profile.declared_dependencies
    assert "httpx==0.27.0" in profile.declared_dependencies
    assert "pytest>=8.0.0" in profile.declared_dependencies
    # Frameworks detected strictly from declared dependencies
    assert "fastapi" in profile.detected_frameworks
    assert "pydantic" in profile.detected_frameworks


def test_framework_not_inferred_merely_from_filename(tmp_path):
    """A filename like 'django_helper.py' must NOT infer Django if Django is not declared."""
    repo = tmp_path / "clean_repo"
    repo.mkdir()
    (repo / "requirements.txt").write_text("requests>=2.28.0\n", encoding="utf-8")
    # File naming temptation
    (repo / "django_compat.py").write_text("# Not actually using django", encoding="utf-8")

    profile = inspect_repository(str(repo))

    assert "django" not in profile.detected_frameworks
    assert profile.project_name == "unknown"  # No pyproject or setup.cfg
    assert profile.python_version == "unknown"


def test_oversized_files_are_skipped(tmp_path):
    """Source files larger than MAX_FILE_SIZE_BYTES must be skipped for excerpts with a warning."""
    repo = tmp_path / "oversized_repo"
    repo.mkdir()
    (repo / "requirements.txt").write_text("six\n", encoding="utf-8")

    # Normal file
    (repo / "small.py").write_text("x = 1\n", encoding="utf-8")

    # Huge file (exceeding MAX_FILE_SIZE_BYTES)
    huge_file = repo / "huge.py"
    huge_file.write_text("a = 1\n" * (MAX_FILE_SIZE_BYTES // 4), encoding="utf-8")

    profile = inspect_repository(str(repo))

    excerpt_paths = [e.file_path for e in profile.source_excerpts]
    assert "small.py" in excerpt_paths
    assert "huge.py" not in excerpt_paths
    assert any("Skipped oversized file" in w for w in profile.warnings)


def test_path_traversal_and_symlink_safety(tmp_path):
    """Symlinks escaping the repository directory must be detected and rejected."""
    outside_dir = tmp_path / "outside_dir"
    outside_dir.mkdir()
    secret_file = outside_dir / "secret.py"
    secret_file.write_text("SECRET = 42", encoding="utf-8")

    repo = tmp_path / "safe_repo"
    repo.mkdir()
    (repo / "app.py").write_text("print('safe')", encoding="utf-8")

    # Test path safety helper directly
    assert _is_safe_path(repo, repo / "app.py") is True
    assert _is_safe_path(repo, secret_file) is False

    # Attempt to create an escaping symlink inside repo
    symlink_path = repo / "escaping_link.py"
    try:
        os.symlink(str(secret_file), str(symlink_path))
        profile = inspect_repository(str(repo))
        assert "escaping_link.py" not in [e.file_path for e in profile.source_excerpts]
        assert any("Skipped symlink" in w for w in profile.warnings)
    except (OSError, NotImplementedError):
        # On Windows without developer mode/admin rights, symlink creation may raise OSError.
        # Direct safety logic is verified above.
        pass
