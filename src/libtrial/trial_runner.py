"""Isolated integration probe generation and disposable Docker execution."""

import ast
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from typing import List, Optional, Tuple

from libtrial.llm_client import GemmaClient
from libtrial.models import (
    CandidateSuggestion,
    ProjectProfile,
    PyPIMetadata,
    TrialOutcome,
    TrialResult,
)

FORBIDDEN_IMPORT_MODULES = {
    "subprocess",
    "shutil",
    "socket",
    "urllib",
    "requests",
    "httpx",
    "http",
    "aiohttp",
    "ftplib",
    "smtplib",
    "telnetlib",
    "posix",
    "nt",
    "pty",
    "commands",
    "ctypes",
    "os",
}

FORBIDDEN_FUNCTIONS = {
    "eval",
    "exec",
    "compile",
    "__import__",
}


def validate_probe_safety(code: str) -> Tuple[bool, List[str]]:
    """Analyzes probe code AST for safety violations.
    
    Rejects:
    - Shell commands and subprocesses
    - Network libraries
    - Dynamic code evaluation (eval, exec)
    - File writing operations
    """
    reasons: List[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, [f"Probe contains syntax errors: {exc}"]

    for node in ast.walk(tree):
        # 1. Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0].lower()
                if mod in FORBIDDEN_IMPORT_MODULES:
                    reasons.append(f"Forbidden import: '{alias.name}' is prohibited in integration probes.")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mod = node.module.split(".")[0].lower()
                if mod in FORBIDDEN_IMPORT_MODULES:
                    reasons.append(f"Forbidden from-import: '{node.module}' is prohibited in integration probes.")

        # 2. Check function calls
        elif isinstance(node, ast.Call):
            # Prohibit eval, exec, compile
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_FUNCTIONS:
                reasons.append(f"Forbidden call: Dynamic execution '{node.func.id}()' is prohibited.")

            # Prohibit file write operations
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                for arg in node.args[1:]:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        if any(m in arg.value.lower() for m in ("w", "a", "x", "+")):
                            reasons.append("Forbidden call: Writing files via 'open()' is prohibited in probes.")
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        if any(m in kw.value.value.lower() for m in ("w", "a", "x", "+")):
                            reasons.append("Forbidden call: Writing files via 'open(mode=...)' is prohibited.")

            # Check method calls like write_text, write_bytes
            if isinstance(node.func, ast.Attribute) and node.func.attr in ("write_text", "write_bytes"):
                reasons.append(f"Forbidden method: '{node.func.attr}()' is prohibited in probes.")

    is_safe = len(reasons) == 0
    return is_safe, reasons


PROBE_PROMPT_TEMPLATE = """You are a software engineer writing a minimal, safe Python integration probe script.

TARGET CANDIDATE:
- Package Name: {package_name}
- Expected Import Name: {import_name}
- Verified Version: {version}
- License: {license}

PROJECT CONTEXT:
- Target Python Version: {python_version}
- Detected Frameworks: {frameworks}
- Requested Capability: "{requirement}"

SAFETY RESTRICTIONS:
1. Write 5 to 15 lines of clear, self-contained Python.
2. Import the candidate package and demonstrate minimal initialization or basic function call.
3. Print "PROBE_OK: <message>" on success.
4. STRICTLY PROHIBITED: Do NOT use os, sys, subprocess, network requests, sockets, or file writes.
5. Return ONLY executable Python code. Do not wrap in conversational markdown or explanation.
"""


def generate_probe_script(
    candidate: CandidateSuggestion,
    pypi_metadata: PyPIMetadata,
    profile: ProjectProfile,
    requirement: str,
    client: Optional[GemmaClient] = None,
) -> str:
    """Generates a minimal integration probe using Gemma or a safe fallback template."""
    import_name = candidate.import_name if candidate.import_name != "unknown" else candidate.name
    fallback_code = (
        f"# Minimal Smoke Probe for {candidate.name}\n"
        f"import {import_name}\n\n"
        f'print(f"PROBE_OK: Successfully imported {candidate.name}")\n'
    )

    if not client:
        return fallback_code

    prompt = PROBE_PROMPT_TEMPLATE.format(
        package_name=candidate.name,
        import_name=import_name,
        version=pypi_metadata.version or "unknown",
        license=pypi_metadata.license or "unknown",
        python_version=profile.python_version,
        frameworks=", ".join(profile.detected_frameworks) or "None",
        requirement=requirement,
    )

    try:
        raw = client.generate_text(prompt)
        cleaned = raw.strip()
        # Clean markdown fences
        if "```" in cleaned:
            match = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", cleaned)
            if match:
                cleaned = match.group(1).strip()
            else:
                cleaned = re.sub(r"^```(?:python)?|```$", "", cleaned, flags=re.MULTILINE).strip()

        # Pre-validate safety; if LLM produced unsafe code, reject and use safe fallback
        is_safe, _ = validate_probe_safety(cleaned)
        if is_safe:
            return cleaned
        return fallback_code
    except Exception:
        return fallback_code


def is_docker_available() -> bool:
    """Checks whether the Docker CLI and daemon are operational."""
    if not shutil.which("docker"):
        return False
    try:
        res = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=4,
            text=True,
        )
        return res.returncode == 0
    except (subprocess.TimeoutExpired, OSError, Exception):
        return False


def run_isolated_trial(
    candidate_name: str,
    candidate_version: Optional[str],
    probe_code: str,
    user_consented: bool,
    timeout_seconds: float = 25.0,
    docker_check_fn=is_docker_available,
) -> TrialResult:
    """Executes an isolated integration probe in a disposable, resource-constrained container.
    
    SAFETY PRINCIPLES:
    - Never executes on host.
    - Requires explicit user consent.
    - Container runs with --network none, memory caps, and unprivileged user.
    """
    # 1. Require user consent
    if not user_consented:
        return TrialResult(
            candidate_name=candidate_name,
            outcome=TrialOutcome.NOT_RUN,
            probe_code=probe_code,
            user_consented=False,
            reasons=["Trial skipped: Explicit user consent was not granted."],
        )

    # 2. Check probe safety restrictions
    is_safe, safety_reasons = validate_probe_safety(probe_code)
    if not is_safe:
        return TrialResult(
            candidate_name=candidate_name,
            outcome=TrialOutcome.NOT_RUN,
            probe_code=probe_code,
            user_consented=True,
            reasons=[f"Safety check rejected probe: {r}" for r in safety_reasons],
        )

    # 3. Check Docker availability
    if not docker_check_fn():
        return TrialResult(
            candidate_name=candidate_name,
            outcome=TrialOutcome.NOT_RUN,
            probe_code=probe_code,
            user_consented=True,
            docker_available=False,
            reasons=[
                "Docker is unavailable or inactive on host. "
                "Execution on the host machine is strictly prohibited by safety policy."
            ],
        )

    # 4. Prepare isolated disposable container
    tag = f"libtrial-probe-{uuid.uuid4().hex[:8]}"
    start_time = time.time()

    with tempfile.TemporaryDirectory() as temp_dir:
        probe_path = os.path.join(temp_dir, "probe.py")
        with open(probe_path, "w", encoding="utf-8") as f:
            f.write(probe_code)

        # Build-stage install specification
        install_target = f"{candidate_name}=={candidate_version}" if candidate_version and candidate_version != "unknown" else candidate_name

        dockerfile_content = (
            "FROM python:3.11-slim\n"
            "WORKDIR /sandbox\n"
            "COPY probe.py /sandbox/probe.py\n"
            f"RUN pip install --no-cache-dir {install_target}\n"
            "USER nobody\n"
            'CMD ["python", "/sandbox/probe.py"]\n'
        )
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(dockerfile_content)

        # Build image
        try:
            build_res = subprocess.run(
                ["docker", "build", "-t", tag, temp_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                text=True,
            )
            if build_res.returncode != 0:
                return TrialResult(
                    candidate_name=candidate_name,
                    outcome=TrialOutcome.INCONCLUSIVE,
                    probe_code=probe_code,
                    user_consented=True,
                    docker_available=True,
                    stdout=build_res.stdout[:2000],
                    stderr=build_res.stderr[:2000],
                    exit_code=build_res.returncode,
                    execution_time_seconds=time.time() - start_time,
                    reasons=["Container image build or package installation failed inside container."],
                )
        except subprocess.TimeoutExpired:
            return TrialResult(
                candidate_name=candidate_name,
                outcome=TrialOutcome.INCONCLUSIVE,
                probe_code=probe_code,
                user_consented=True,
                docker_available=True,
                reasons=[f"Container build timed out after {timeout_seconds}s."],
            )
        except (OSError, Exception) as exc:
            return TrialResult(
                candidate_name=candidate_name,
                outcome=TrialOutcome.INCONCLUSIVE,
                probe_code=probe_code,
                user_consented=True,
                docker_available=True,
                reasons=[f"Docker build process error: {exc}"],
            )

        # Execute container with strict limits and zero network
        try:
            run_res = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "--network",
                    "none",
                    "--memory",
                    "256m",
                    "--cpus",
                    "1.0",
                    "--pids-limit",
                    "64",
                    tag,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                text=True,
            )
            elapsed = time.time() - start_time
            stdout = run_res.stdout[:4000]
            stderr = run_res.stderr[:4000]

            outcome = TrialOutcome.PASS if run_res.returncode == 0 else TrialOutcome.FAIL

            return TrialResult(
                candidate_name=candidate_name,
                outcome=outcome,
                probe_code=probe_code,
                user_consented=True,
                docker_available=True,
                stdout=stdout,
                stderr=stderr,
                exit_code=run_res.returncode,
                execution_time_seconds=elapsed,
            )
        except subprocess.TimeoutExpired:
            return TrialResult(
                candidate_name=candidate_name,
                outcome=TrialOutcome.INCONCLUSIVE,
                probe_code=probe_code,
                user_consented=True,
                docker_available=True,
                execution_time_seconds=time.time() - start_time,
                reasons=[f"Probe execution timed out after {timeout_seconds}s in isolated container."],
            )
        except (OSError, Exception) as exc:
            return TrialResult(
                candidate_name=candidate_name,
                outcome=TrialOutcome.INCONCLUSIVE,
                probe_code=probe_code,
                user_consented=True,
                docker_available=True,
                execution_time_seconds=time.time() - start_time,
                reasons=[f"Docker execution process error: {exc}"],
            )
        finally:
            # Clean up ephemeral image
            try:
                subprocess.run(
                    ["docker", "rmi", tag],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
            except Exception:
                pass
