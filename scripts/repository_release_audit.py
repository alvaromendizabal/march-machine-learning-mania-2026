"""
Repository release audit for the March Mania forecasting project.

The script can:
1. Rename notebook 02 to a professional canonical filename.
2. Update references to that filename.
3. Replace prohibited promotional wording with "research-grade".
4. Detect duplicate or backup notebook versions.
5. Audit required portfolio/reproducibility files.
6. Detect tracked data, caches, secrets, oversized files, or generated models.
7. Write machine-readable CSV and JSON audit reports.

Audit only:
    python scripts\repository_release_audit.py --root .

Apply safe text/filename cleanup, then audit:
    python scripts\repository_release_audit.py --root . --apply

This script never deletes data, model caches, submissions, or notebooks.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


CANONICAL_NOTEBOOKS = [
    "00_data_audit_and_preparation.ipynb",
    "01_split_protocol_and_pre_tournament_snapshots.ipynb",
    "02_feature_store_and_diagnostics.ipynb",
    "03_model_comparison_and_diagnostics.ipynb",
    "04_locked_benchmark_and_final_submission.ipynb",
]

OLD_NOTEBOOK_02 = "02_" + "research-grade" + "_feature_store.ipynb"
NEW_NOTEBOOK_02 = "02_feature_store_and_diagnostics.ipynb"

# Constructed in pieces so the unwanted wording does not occur verbatim
# in this source file.
PROMOTIONAL_PATTERN = re.compile(
    r"state" + r"[_\s-]+" + r"of" + r"[_\s-]+" + r"the" + r"[_\s-]+" + r"art",
    flags=re.IGNORECASE,
)

TEXT_SUFFIXES = {
    ".md",
    ".rst",
    ".txt",
    ".py",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".ipynb",
    ".html",
}

SKIP_DIRECTORY_NAMES = {
    ".git",
    ".ipynb_checkpoints",
    "__pycache__",
    "data",
    "models",
    "outputs",
    "submissions",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
}

DUPLICATE_NOTEBOOK_PATTERN = re.compile(
    r"(?:\(\d+\)|_v\d+|_clean|_repaired|_working|_copy|_old|_backup)",
    flags=re.IGNORECASE,
)

REQUIRED_CORE_PATHS = [
    "README.md",
    "LICENSE",
    "pyproject.toml",
    ".gitignore",
    "environment.yml",
    "requirements-pip.txt",
    "configs/splits.yaml",
    "configs/features.yaml",
    "configs/modeling.yaml",
    "configs/model_recipe.yaml",
    "configs/benchmark_production.yaml",
    "reports/final_2026/MODEL_CARD.md",
]

RECOMMENDED_PORTFOLIO_PATHS = [
    ".github/workflows/ci.yml",
    ".pre-commit-config.yaml",
    "docs/DATA_CARD.md",
    "docs/VALIDATION_PROTOCOL.md",
    "docs/RESULTS.md",
    "docs/REPRODUCIBILITY.md",
    "CITATION.cff",
]

FORBIDDEN_TRACKED_PREFIXES = (
    "data/raw/",
    "data/interim/",
    "data/processed/",
    "data/model_cache/",
    "models/",
    "outputs/",
)

FORBIDDEN_TRACKED_BASENAMES = {
    ".env",
    "kaggle.json",
    "credentials.json",
}


@dataclass
class AuditRecord:
    category: str
    check: str
    status: str
    details: str
    blocking: bool


def run_git(
    root: Path,
    arguments: list[str],
    *,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
        check=check,
    )


def is_git_repository(root: Path) -> bool:
    result = run_git(root, ["rev-parse", "--is-inside-work-tree"])
    return result.returncode == 0 and result.stdout.strip() == "true"


def iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = set(path.relative_to(root).parts[:-1])
        if relative_parts.intersection(SKIP_DIRECTORY_NAMES):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def replace_text_safely(path: Path) -> tuple[bool, int]:
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False, 0

    updated = original.replace(OLD_NOTEBOOK_02, NEW_NOTEBOOK_02)
    updated, replacements = PROMOTIONAL_PATTERN.subn(
        "research-grade",
        updated,
    )
    filename_reference_replacements = int(
        original.count(OLD_NOTEBOOK_02)
    )

    if updated == original:
        return False, 0

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(path)
    return True, replacements + filename_reference_replacements


def rename_notebook_02(root: Path, git_repo: bool) -> str:
    notebooks = root / "notebooks"
    source = notebooks / OLD_NOTEBOOK_02
    destination = notebooks / NEW_NOTEBOOK_02

    if destination.exists() and source.exists():
        return (
            "Both old and new notebook-02 filenames exist; "
            "no automatic rename was attempted."
        )
    if destination.exists():
        return "Canonical notebook-02 filename already exists."
    if not source.exists():
        alternate_candidates = sorted(
            path
            for path in notebooks.glob("02*.ipynb")
            if PROMOTIONAL_PATTERN.search(path.name)
        )
        if len(alternate_candidates) != 1:
            return (
                "No unique notebook-02 source could be identified. "
                f"Candidates={list(map(str, alternate_candidates))}"
            )
        source = alternate_candidates[0]

    if git_repo:
        result = run_git(
            root,
            [
                "mv",
                str(source.relative_to(root)),
                str(destination.relative_to(root)),
            ],
        )
        if result.returncode == 0:
            return f"Renamed with git mv: {source.name} -> {destination.name}"

    source.replace(destination)
    return f"Renamed on disk: {source.name} -> {destination.name}"


def tracked_files(root: Path, git_repo: bool) -> list[str]:
    if not git_repo:
        return []
    result = run_git(root, ["ls-files", "-z"])
    if result.returncode != 0:
        return []
    return [
        item.replace("\\", "/")
        for item in result.stdout.split("\0")
        if item
    ]


def phrase_matches(root: Path) -> list[str]:
    matches: list[str] = []
    for path in iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if PROMOTIONAL_PATTERN.search(text) or PROMOTIONAL_PATTERN.search(
            path.name
        ):
            matches.append(str(path.relative_to(root)))
    return sorted(set(matches))


def duplicate_notebooks(root: Path) -> list[str]:
    notebooks = root / "notebooks"
    if not notebooks.exists():
        return []
    return sorted(
        str(path.relative_to(root))
        for path in notebooks.glob("*.ipynb")
        if DUPLICATE_NOTEBOOK_PATTERN.search(path.stem)
    )


def oversized_tracked_files(
    root: Path,
    tracked: list[str],
    threshold_mb: float = 20.0,
) -> list[str]:
    records: list[str] = []
    for relative in tracked:
        path = root / relative
        if not path.is_file():
            continue
        size_mb = path.stat().st_size / 1024**2
        if size_mb > threshold_mb:
            records.append(f"{relative} ({size_mb:.1f} MB)")
    return sorted(records)


def audit_repository(root: Path) -> list[AuditRecord]:
    records: list[AuditRecord] = []
    git_repo = is_git_repository(root)
    tracked = tracked_files(root, git_repo)

    records.append(
        AuditRecord(
            "repository",
            "Git repository detected",
            "PASS" if git_repo else "FAIL",
            str(root),
            True,
        )
    )

    for notebook in CANONICAL_NOTEBOOKS:
        exists = (root / "notebooks" / notebook).exists()
        records.append(
            AuditRecord(
                "notebooks",
                f"Canonical notebook exists: {notebook}",
                "PASS" if exists else "FAIL",
                str(root / "notebooks" / notebook),
                True,
            )
        )

    duplicates = duplicate_notebooks(root)
    records.append(
        AuditRecord(
            "notebooks",
            "No duplicate or backup notebook versions",
            "PASS" if not duplicates else "FAIL",
            json.dumps(duplicates),
            True,
        )
    )

    wording_matches = phrase_matches(root)
    records.append(
        AuditRecord(
            "wording",
            "Promotional wording absent from documentation and notebooks",
            "PASS" if not wording_matches else "FAIL",
            json.dumps(wording_matches),
            True,
        )
    )

    for relative in REQUIRED_CORE_PATHS:
        exists = (root / relative).exists()
        records.append(
            AuditRecord(
                "core_artifact",
                f"Required file exists: {relative}",
                "PASS" if exists else "FAIL",
                str(root / relative),
                True,
            )
        )

    for relative in RECOMMENDED_PORTFOLIO_PATHS:
        exists = (root / relative).exists()
        records.append(
            AuditRecord(
                "portfolio_artifact",
                f"Recommended file exists: {relative}",
                "PASS" if exists else "WARN",
                str(root / relative),
                False,
            )
        )

    forbidden_tracked = sorted(
        relative
        for relative in tracked
        if relative.startswith(FORBIDDEN_TRACKED_PREFIXES)
        or Path(relative).name.lower()
        in {name.lower() for name in FORBIDDEN_TRACKED_BASENAMES}
    )
    records.append(
        AuditRecord(
            "git_hygiene",
            "Raw/interim/processed data, caches, models, and secrets are not tracked",
            "PASS" if not forbidden_tracked else "FAIL",
            json.dumps(forbidden_tracked),
            True,
        )
    )

    checkpoints = sorted(
        str(path.relative_to(root))
        for path in root.rglob(".ipynb_checkpoints")
    )
    records.append(
        AuditRecord(
            "git_hygiene",
            "No notebook checkpoint directories in working tree",
            "PASS" if not checkpoints else "WARN",
            json.dumps(checkpoints),
            False,
        )
    )

    large_files = oversized_tracked_files(root, tracked)
    records.append(
        AuditRecord(
            "git_hygiene",
            "No tracked file exceeds 20 MB",
            "PASS" if not large_files else "WARN",
            json.dumps(large_files),
            False,
        )
    )

    tests_directory = root / "tests"
    test_files = (
        list(tests_directory.rglob("test_*.py"))
        if tests_directory.exists()
        else []
    )
    records.append(
        AuditRecord(
            "testing",
            "Automated tests are present",
            "PASS" if test_files else "FAIL",
            json.dumps(
                [str(path.relative_to(root)) for path in test_files]
            ),
            True,
        )
    )

    final_readiness = (
        root
        / "reports"
        / "final_2026"
        / "04_readiness_summary.json"
    )
    if final_readiness.exists():
        try:
            readiness = json.loads(
                final_readiness.read_text(encoding="utf-8")
            )
            final_ok = (
                readiness.get("status") == "complete"
                and int(
                    readiness.get(
                        "blocking_final_check_failures",
                        1,
                    )
                )
                == 0
            )
            details = json.dumps(
                {
                    "status": readiness.get("status"),
                    "blocking_final_check_failures":
                        readiness.get(
                            "blocking_final_check_failures"
                        ),
                    "stage2_rows": readiness.get("stage2_rows"),
                    "bracket_reporting_completed":
                        readiness.get(
                            "bracket_reporting_completed"
                        ),
                }
            )
        except Exception as exc:
            final_ok = False
            details = repr(exc)
    else:
        final_ok = False
        details = str(final_readiness)

    records.append(
        AuditRecord(
            "final_pipeline",
            "Notebook 04 readiness report is complete",
            "PASS" if final_ok else "FAIL",
            details,
            True,
        )
    )

    return records


def write_reports(root: Path, records: list[AuditRecord]) -> None:
    report_directory = (
        root / "reports" / "repository_release"
    )
    report_directory.mkdir(parents=True, exist_ok=True)

    table = [asdict(record) for record in records]
    csv_path = report_directory / "repository_release_audit.csv"
    json_path = report_directory / "repository_release_audit.json"

    with csv_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "category",
                "check",
                "status",
                "details",
                "blocking",
            ],
        )
        writer.writeheader()
        writer.writerows(table)

    summary = {
        "status": (
            "PASS"
            if not any(
                record.blocking and record.status == "FAIL"
                for record in records
            )
            else "FAIL"
        ),
        "blocking_failures": [
            record.check
            for record in records
            if record.blocking and record.status == "FAIL"
        ],
        "warnings": [
            record.check
            for record in records
            if record.status == "WARN"
        ],
        "records": table,
    }
    json_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply safe rename and text cleanup before auditing.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.exists():
        raise FileNotFoundError(root)

    git_repo = is_git_repository(root)

    if args.apply:
        print(rename_notebook_02(root, git_repo))
        changed_files = 0
        replacements = 0
        for path in list(iter_text_files(root)):
            changed, count = replace_text_safely(path)
            if changed:
                changed_files += 1
                replacements += count
        print(
            "Updated text files:",
            changed_files,
            "| replacements:",
            replacements,
        )

    records = audit_repository(root)
    write_reports(root, records)

    for record in records:
        print(
            f"{record.status:4} | "
            f"{record.category:18} | "
            f"{record.check}"
        )

    blocking_failures = [
        record
        for record in records
        if record.blocking and record.status == "FAIL"
    ]
    print()
    print(
        "Repository release audit:",
        "PASS" if not blocking_failures else "FAIL",
    )
    if blocking_failures:
        print("Blocking failures:")
        for record in blocking_failures:
            print("-", record.check, "|", record.details)

    return 1 if blocking_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
