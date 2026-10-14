"""EPUBCheck integration — never reports success when the tool did not run."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from converter.contracts import ValidationMessage, ValidationResult


def _find_epubcheck() -> tuple[str | None, str | None]:
    jar = os.environ.get("EPUBCHECK_JAR")
    if jar and Path(jar).is_file():
        return "java", jar
    which = shutil.which("epubcheck")
    if which:
        return which, None
    return None, None


def run_epubcheck(epub_path: Path) -> ValidationResult:
    tool, jar_or_none = _find_epubcheck()
    if not tool:
        return ValidationResult(
            tool="epubcheck",
            tool_version=None,
            available=False,
            passed=None,
            skipped_reason=(
                "EPUBCheck not configured. Set EPUBCHECK_JAR to the validator JAR path "
                "or install epubcheck on PATH."
            ),
        )

    cmd: list[str] = (
        ["java", "-jar", jar_or_none, str(epub_path)]
        if jar_or_none
        else [tool, str(epub_path)]
    )

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ValidationResult(
            tool="epubcheck",
            tool_version=None,
            available=True,
            passed=False,
            messages=[
                ValidationMessage(severity="error", message=f"EPUBCheck execution failed: {exc}")
            ],
        )

    combined = (proc.stdout or "") + (proc.stderr or "")
    passed = proc.returncode == 0
    messages: list[ValidationMessage] = []
    for line in combined.splitlines():
        line = line.strip()
        if not line:
            continue
        sev = "info"
        if "ERROR" in line or "FATAL" in line:
            sev = "error"
        elif "WARNING" in line:
            sev = "warning"
        messages.append(ValidationMessage(severity=sev, message=line))

    version_line = next((m.message for m in messages if "EPUBCheck" in m.message), None)
    return ValidationResult(
        tool="epubcheck",
        tool_version=version_line,
        available=True,
        passed=passed,
        messages=messages[:200],
    )
