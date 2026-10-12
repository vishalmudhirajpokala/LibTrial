"""Deterministic compatibility and collision checking module."""

from typing import List, Tuple
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from libtrial.models import CompatibilityCheck, CompatibilityVerdict, PyPIMetadata

PYTHON_SAMPLE_VERSIONS = [
    Version("3.8"),
    Version("3.9"),
    Version("3.10"),
    Version("3.11"),
    Version("3.12"),
    Version("3.13"),
    Version("3.14"),
]


def _check_python_version_compatibility(
    project_python: str, candidate_python: str
) -> Tuple[CompatibilityVerdict, str]:
    """Evaluates whether project Python requirements and candidate Requires-Python overlap."""
    if not project_python or project_python.lower() == "unknown":
        return (
            CompatibilityVerdict.INSUFFICIENT_EVIDENCE,
            "Project Python version is unknown; cannot verify Python compatibility.",
        )
    if not candidate_python or candidate_python.lower() == "unknown":
        return (
            CompatibilityVerdict.INSUFFICIENT_EVIDENCE,
            "Candidate package does not declare Requires-Python metadata; compatibility is unverified.",
        )

    try:
        proj_spec = SpecifierSet(project_python)
    except InvalidSpecifier:
        return (
            CompatibilityVerdict.INSUFFICIENT_EVIDENCE,
            f"Invalid project Python specifier '{project_python}'.",
        )

    try:
        cand_spec = SpecifierSet(candidate_python)
    except InvalidSpecifier:
        return (
            CompatibilityVerdict.INSUFFICIENT_EVIDENCE,
            f"Invalid candidate Requires-Python specifier '{candidate_python}'.",
        )

    proj_supported = {v for v in PYTHON_SAMPLE_VERSIONS if v in proj_spec}
    cand_supported = {v for v in PYTHON_SAMPLE_VERSIONS if v in cand_spec}

    # If both defined constraints within the Python 3.8-3.14 envelope
    if proj_supported and cand_supported:
        common = proj_supported & cand_supported
        if not common:
            return (
                CompatibilityVerdict.POTENTIAL_CONFLICT,
                f"Direct Python mismatch: Project requires '{project_python}', but candidate requires '{candidate_python}'.",
            )
        return (
            CompatibilityVerdict.COMPATIBLE_WITH_AVAILABLE_EVIDENCE,
            f"Python versions overlap ({', '.join(str(v) for v in sorted(common))}). Project '{project_python}' compatible with Candidate '{candidate_python}'.",
        )

    return (
        CompatibilityVerdict.INSUFFICIENT_EVIDENCE,
        f"Unable to verify version overlap between '{project_python}' and '{candidate_python}'.",
    )


def _check_dependency_collisions(
    project_dependencies: List[str],
    candidate_name: str,
    candidate_version: str,
    candidate_requires_dist: List[str],
) -> Tuple[List[str], List[str]]:
    """Checks for direct collisions between project dependencies and candidate requirements."""
    conflict_notes: List[str] = []
    conflicting_deps: List[str] = []

    # Parse project dependencies into normalized dictionary
    proj_reqs = {}
    for dep_str in project_dependencies:
        try:
            req = Requirement(dep_str)
            proj_reqs[req.name.lower()] = req
        except InvalidRequirement:
            continue

    # 1. Check if candidate itself is already pinned in the project
    cand_norm_name = candidate_name.lower()
    if cand_norm_name in proj_reqs:
        existing_req = proj_reqs[cand_norm_name]
        if candidate_version and candidate_version != "unknown":
            try:
                cand_ver = Version(candidate_version)
                if not existing_req.specifier.contains(cand_ver, prereleases=True):
                    conflict_notes.append(
                        f"Project pins '{existing_req}', which directly rejects candidate latest version {candidate_version}."
                    )
                    conflicting_deps.append(existing_req.name)
            except InvalidVersion:
                pass

    # 2. Check candidate dependencies against project declared dependencies
    for cand_dep_str in candidate_requires_dist:
        try:
            cand_req = Requirement(cand_dep_str)
        except InvalidRequirement:
            continue

        pkg_name = cand_req.name.lower()
        if pkg_name in proj_reqs:
            proj_req = proj_reqs[pkg_name]

            # If project pinned an exact version (e.g. foo==1.0.0)
            pinned_ver = None
            for spec in proj_req.specifier:
                if spec.operator in ("==", "==="):
                    pinned_ver = spec.version
                    break

            if pinned_ver:
                try:
                    if not cand_req.specifier.contains(pinned_ver, prereleases=True):
                        conflict_notes.append(
                            f"Collision on '{pkg_name}': Project pins {proj_req}, but candidate requires {cand_req}."
                        )
                        conflicting_deps.append(pkg_name)
                except InvalidVersion:
                    pass
            elif proj_req.specifier and cand_req.specifier:
                # Check for obvious opposite bound collisions (e.g. <2.0 vs >=2.0)
                # Sample a few version numbers to test if any can satisfy both
                test_versions = [
                    Version("0.1.0"), Version("1.0.0"), Version("1.26.15"),
                    Version("2.0.0"), Version("2.1.0"), Version("3.0.0"), Version("4.0.0")
                ]
                both_satisfiable = any(
                    proj_req.specifier.contains(v) and cand_req.specifier.contains(v)
                    for v in test_versions
                )
                if not both_satisfiable and str(proj_req.specifier) != str(cand_req.specifier):
                    conflict_notes.append(
                        f"Potential conflict on '{pkg_name}': Project specifies '{proj_req}', candidate requires '{cand_req}'."
                    )
                    conflicting_deps.append(pkg_name)

    return conflict_notes, conflicting_deps


def evaluate_compatibility(
    project_python: str,
    project_dependencies: List[str],
    pypi_metadata: PyPIMetadata,
) -> CompatibilityCheck:
    """Evaluates compatibility between a project and verified PyPI metadata.
    
    Distinguishes:
    - COMPATIBLE WITH AVAILABLE EVIDENCE
    - POTENTIAL CONFLICT
    - INSUFFICIENT EVIDENCE
    """
    if not pypi_metadata.is_found:
        return CompatibilityCheck(
            verdict=CompatibilityVerdict.INSUFFICIENT_EVIDENCE,
            python_compatibility_note="Package was not found on PyPI; compatibility cannot be evaluated.",
            dependency_conflict_notes=[],
            conflicting_dependencies=[],
        )

    # Check Python version
    py_verdict, py_note = _check_python_version_compatibility(
        project_python=project_python,
        candidate_python=pypi_metadata.requires_python or "unknown",
    )

    # Check direct dependency collisions
    dep_conflict_notes, conflicting_deps = _check_dependency_collisions(
        project_dependencies=project_dependencies,
        candidate_name=pypi_metadata.name,
        candidate_version=pypi_metadata.version or "unknown",
        candidate_requires_dist=pypi_metadata.requires_dist,
    )

    # Determine overall verdict
    if py_verdict == CompatibilityVerdict.POTENTIAL_CONFLICT or dep_conflict_notes:
        overall_verdict = CompatibilityVerdict.POTENTIAL_CONFLICT
    elif (
        py_verdict == CompatibilityVerdict.COMPATIBLE_WITH_AVAILABLE_EVIDENCE
        and not dep_conflict_notes
    ):
        overall_verdict = CompatibilityVerdict.COMPATIBLE_WITH_AVAILABLE_EVIDENCE
    else:
        overall_verdict = CompatibilityVerdict.INSUFFICIENT_EVIDENCE

    return CompatibilityCheck(
        verdict=overall_verdict,
        python_compatibility_note=py_note,
        dependency_conflict_notes=dep_conflict_notes,
        conflicting_dependencies=conflicting_deps,
    )
