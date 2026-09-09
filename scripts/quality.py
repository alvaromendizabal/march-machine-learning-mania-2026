"""Run all research gates with timestamped progress and machine-readable results."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import tomllib
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
        "scripts/portfolio_release.py",
        "scripts/archive.py",
        "scripts/update.py",
    ]
    typed_files = tomllib.loads((root / "pyproject.toml").read_text())["tool"]["mypy"]["files"]
    typed_files = [
        *typed_files,
        "src/march_mania/publication",
        *[
            "src/march_mania/" + name + ".py"
            for name in (
                "candidate_features",
                "coach_features",
                "feature_selection",
                "matchup_artifacts",
            )
        ],
    ]
    checks = [
        ("compile", [sys.executable, "-m", "compileall", "-q", *scopes]),
        ("lint", [sys.executable, "-m", "ruff", "check", *scopes]),
        ("format", [sys.executable, "-m", "ruff", "format", "--check", *scopes]),
        ("types", [sys.executable, "-m", "mypy", *typed_files]),
        (
            "tests",
            [
                sys.executable,
                "-m",
                "pytest",
                "--cov=march_mania.features",
                "--cov=march_mania.candidate_features",
                "--cov=march_mania.coach_features",
                "--cov=march_mania.feature_selection",
                "--cov=march_mania.matchup_artifacts",
                "--cov=march_mania.runtime",
                "--cov=march_mania.research",
                "--cov=march_mania.research_report",
                "--cov=march_mania.advanced_features",
                "--cov=march_mania.feature_store",
                "--cov=march_mania.data",
                "--cov=march_mania.rankings",
                "--cov=march_mania.encoding",
                "--cov=march_mania.context_features",
                "--cov=march_mania.data_review",
                "--cov=march_mania.modeling",
                "--cov=march_mania.model_report",
                "--cov=march_mania.publication.notebooks",
                "--cov=march_mania.notebook_support",
                "--cov=march_mania.publication.submission",
                "--cov=march_mania.publication.inference",
                "--cov=march_mania.publication.benchmark",
                "--cov=march_mania.publication.capacity",
                "--cov=march_mania.publication.ranking_systems",
                "--cov=march_mania.publication.followups",
                "--cov=march_mania.publication.artifacts",
                "--cov=march_mania.publication.workflow",
                "--cov=march_mania.publication.release",
                "--cov=march_mania.publication.portfolio",
                "--cov=march_mania.publication.production",
                "--cov=march_mania.publication.production_inputs",
                "--cov=march_mania.publication.production_release",
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
