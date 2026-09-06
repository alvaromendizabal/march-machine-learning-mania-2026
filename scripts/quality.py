"""Run all research gates with timestamped progress and machine-readable results."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from bootstrap import command


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    destination = root / "outputs/validation"
    destination.mkdir(parents=True, exist_ok=True)
    scopes = [
        "src",
        "tests",
        "scripts/bootstrap.py",
        "scripts/quality.py",
        "scripts/inspect_data.py",
        "scripts/notebook.py",
    ]
    checks = [
        ("compile", [sys.executable, "-m", "compileall", "-q", *scopes]),
        ("lint", [sys.executable, "-m", "ruff", "check", *scopes]),
        ("format", [sys.executable, "-m", "ruff", "format", "--check", *scopes]),
        ("types", [sys.executable, "-m", "mypy"]),
        (
            "tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov=march_mania.features",
                "--cov=march_mania.runtime",
                "--cov=march_mania.research",
                "--cov=march_mania.research_report",
                "--cov-report=term-missing",
                "--cov-report=xml:outputs/validation/coverage.xml",
                "--junitxml=outputs/validation/junit.xml",
            ],
        ),
    ]
    records = []
    started = time.monotonic()
    for name, argv in checks:
        begin = time.monotonic()
        try:
            command(argv, root)
            status = "passed"
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            status = "failed"
        records.append({"check": name, "status": status, "seconds": time.monotonic() - begin})
        result = {"checks": records, "elapsed_seconds": time.monotonic() - started}
        (destination / "quality.json").write_text(json.dumps(result, indent=2))
        if status == "failed":
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
