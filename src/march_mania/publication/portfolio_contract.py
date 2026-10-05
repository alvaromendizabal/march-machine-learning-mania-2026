"""Validate the curated employer-facing portfolio contract.

This module intentionally checks only public aggregate evidence. It does not load
private predictions, source archives, fitted competition models, or AWS-local state.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

EXPECTED_CONTROL_BRIER = 0.1206458343253354
EXPECTED_FRONTIER_BRIER = 0.1067095543
EXPECTED_HISTORICAL_GAMES = 566
EXPECTED_SAVED_CONTROLS = 558
EXPECTED_RESTORED_GAMES = 8

CURATED_DOCS = (
    "README.md",
    "START_HERE.md",
    "docs/architecture.md",
    "docs/employer_walkthrough.md",
    "docs/current_research.md",
    "docs/post_merge_research_log.md",
    "docs/reproduction_matrix.md",
    "docs/supplemental_source_ownership.md",
    "portfolio/owned_frontier_2027.md",
)

CANONICAL_NOTEBOOKS = tuple(
    f"notebooks/{name}"
    for name in (
        "00_data_audit_and_preparation.ipynb",
        "01_split_protocol_and_pre_tournament_snapshots.ipynb",
        "02_feature_store_and_diagnostics.ipynb",
        "03_model_comparison_and_diagnostics.ipynb",
        "04_locked_benchmark_and_final_submission.ipynb",
        "05_feature_research.ipynb",
    )
)

FORBIDDEN_NARRATIVE_PATTERNS = (
    re.compile(r"\btop score\b", re.IGNORECASE),
    re.compile(r"\bstretch target\b", re.IGNORECASE),
    re.compile(r"\bsecret sauce\b", re.IGNORECASE),
    re.compile(r"(?<![0-9])0\.09(?:0+)?(?![0-9])"),
)


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []

    frontier_path = root / "portfolio/reconstruction_frontier.json"
    try:
        frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"frontier JSON is unreadable: {exc}"]

    control = frontier.get("accepted_control", {})
    experimental = frontier.get("strongest_reconstructed_experimental", {})
    historical = frontier.get("historical_control", {})

    if control.get("system") != "v26":
        errors.append("accepted control must remain v26")
    if control.get("exact_offline_brier") != EXPECTED_CONTROL_BRIER:
        errors.append("accepted-control exact Brier drifted")
    if experimental.get("system") != "v54":
        errors.append("reconstructed experimental frontier must remain v54")
    if experimental.get("combined_brier") != EXPECTED_FRONTIER_BRIER:
        errors.append("reconstructed experimental Brier drifted")
    if experimental.get("lifecycle") != "EXPERIMENTAL":
        errors.append("reconstructed frontier lifecycle must remain EXPERIMENTAL")
    if experimental.get("promoted") is not False:
        errors.append("reconstructed frontier must not be marked promoted")

    if historical.get("played_main_bracket_games") != EXPECTED_HISTORICAL_GAMES:
        errors.append("historical main-bracket population drifted")
    if historical.get("previously_saved_predictions_reproduced") != EXPECTED_SAVED_CONTROLS:
        errors.append("saved-control reproduction count drifted")
    if historical.get("restored_legitimate_equal_seed_games") != EXPECTED_RESTORED_GAMES:
        errors.append("restored equal-seed count drifted")
    if EXPECTED_SAVED_CONTROLS + EXPECTED_RESTORED_GAMES != EXPECTED_HISTORICAL_GAMES:
        errors.append("historical cohort arithmetic is inconsistent")

    milestones = _load_csv(root / "portfolio/owned_frontier_milestones.csv")
    milestone_v54 = [row for row in milestones if row.get("milestone", "").startswith("v54 ")]
    if len(milestone_v54) != 1:
        errors.append("milestone ledger must contain exactly one v54 row")
    elif float(milestone_v54[0]["brier"]) != EXPECTED_FRONTIER_BRIER:
        errors.append("v54 milestone Brier does not match frontier JSON")

    experiments = _load_csv(root / "portfolio/owned_frontier_experiments.csv")
    states = {row.get("milestone"): row.get("scientific_state") for row in experiments}
    for milestone in ("v66", "v67"):
        if states.get(milestone) != "rejected":
            errors.append(f"{milestone} must remain a rejected historical experiment")

    source_rows = _load_csv(root / "portfolio/supplemental_source_status_2027.csv")
    source_names = {row.get("source_family") for row in source_rows}
    required_sources = {
        "Official competition data",
        "Bart Torvik Time Machine",
        "AP polling archive",
        "Archived ESPN BPI / pregame predictions",
        "Original publisher bracket probability tables",
    }
    missing_sources = sorted(required_sources - source_names)
    if missing_sources:
        errors.append(f"source ownership matrix is missing: {missing_sources}")

    readme = (root / "README.md").read_text(encoding="utf-8")
    for required_link in ("START_HERE.md", "docs/architecture.md"):
        if required_link not in readme:
            errors.append(f"README is missing employer navigation link: {required_link}")

    for relative in CURATED_DOCS:
        path = root / relative
        if not path.exists():
            errors.append(f"curated public document is missing: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_NARRATIVE_PATTERNS:
            if pattern.search(text):
                errors.append(f"curated narrative contains forbidden framing: {relative}")

    for relative in CANONICAL_NOTEBOOKS:
        if not (root / relative).exists():
            errors.append(f"canonical notebook is missing: {relative}")

    for retired_path in ("research/workspace", "research/publication_archive"):
        if (root / retired_path).exists():
            errors.append(f"noncanonical workspace leaked into current public tree: {retired_path}")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    errors = validate_repository(root)
    if errors:
        print("EMPLOYER PORTFOLIO CONTRACT: FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("EMPLOYER PORTFOLIO CONTRACT: PASSED")
    print(f"- accepted control Brier: {EXPECTED_CONTROL_BRIER:.10f}")
    print(f"- reconstructed experimental Brier: {EXPECTED_FRONTIER_BRIER:.10f}")
    print(f"- historical control games: {EXPECTED_HISTORICAL_GAMES}")
    print(
        "- curated navigation, source matrix, lifecycle states, "
        "and public/private boundary verified"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
