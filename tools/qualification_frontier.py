"""Validate public qualification bottlenecks against the exact acquisition snapshot."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from string import Template

from evidence_contracts import require, validate_snapshot
from evidence_history import snapshot_digest, strict_json

ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "portfolio/qualification_frontier.json"
CURRENT = ROOT / "portfolio/acquisition_progress.json"
POPULATIONS = {
    2016: 63,
    2017: 63,
    2018: 63,
    2019: 63,
    2021: 63,
    2022: 67,
    2023: 67,
    2024: 67,
    2025: 67,
}
STATES = ("qualified", "missing_home_only", "missing_court_only", "missing_both")
LABELS = {
    "qualified": "Court and home context qualified",
    "missing_home_only": "Court qualified; home context unresolved",
    "missing_court_only": "Home context qualified; court unresolved",
    "missing_both": "Court and home context unqualified",
}


def validate_frontier(frontier: dict, snapshot: dict) -> dict:
    """Check disjoint accounting, frozen editions, exact parent and bounded disclosure."""
    validate_snapshot(snapshot)
    require(
        set(frontier)
        == {
            "schema_version",
            "evidence_type",
            "execution",
            "reviewed_on",
            "snapshot_sha256",
            "classification",
            "editions",
            "scope",
        },
        "Unexpected frontier fields",
    )
    require(
        type(frontier["schema_version"]) is int and frontier["schema_version"] == 1,
        "Unknown frontier schema",
    )
    require(
        frontier["evidence_type"] == "OWNER_QUALIFICATION_FRONTIER",
        "Unknown frontier evidence class",
    )
    require(frontier["execution"] == snapshot["execution"], "Stale frontier execution")
    require(frontier["reviewed_on"] == snapshot["reviewed_on"], "Frontier review date differs")
    require(
        frontier["snapshot_sha256"] == snapshot_digest(snapshot),
        "Frontier does not bind the exact published snapshot",
    )
    require(
        frontier["classification"] == "COURT_FIRST_QUALIFICATION_STATE",
        "Unknown qualification semantics",
    )
    require(
        type(frontier["scope"]) is str and 1 <= len(frontier["scope"]) <= 1000,
        "Missing bounded frontier scope",
    )
    editions = frontier["editions"]
    require(
        type(editions) is list and len(editions) == len(POPULATIONS),
        "All frozen editions must be represented",
    )
    for row in editions:
        require(
            type(row) is dict and set(row) == {"season", "required", *STATES},
            "Unexpected edition fields",
        )
        require(
            all(type(value) is int and value >= 0 for value in row.values()),
            "Invalid edition count",
        )
        require(
            row["season"] in POPULATIONS and row["required"] == POPULATIONS[row["season"]],
            "Frozen edition population changed",
        )
        require(
            sum(row[key] for key in STATES) == row["required"],
            "Qualification states do not partition the edition",
        )
        require(
            row["missing_court_only"] == 0,
            "Court-first classification cannot qualify home context without a court",
        )
    require(
        [r["season"] for r in editions] == list(POPULATIONS),
        "Editions must be complete, unique and ordered",
    )
    venue = snapshot["venue"]
    require(
        sum(r["required"] for r in editions) == venue["women_rows_required"],
        "Frontier population differs from snapshot",
    )
    require(
        sum(r["qualified"] for r in editions) == venue["women_rows_qualified"],
        "Qualified frontier total differs from snapshot",
    )
    require(
        sum(r[k] for r in editions for k in STATES[1:]) == venue["women_rows_unknown"],
        "Unknown frontier total differs from snapshot",
    )
    require(
        sum(r["qualified"] == r["required"] for r in editions) == venue["qualified_editions"],
        "Completed edition claim differs",
    )
    return frontier


def load_frontier() -> dict:
    return validate_frontier(strict_json(FRONTIER.read_text()), strict_json(CURRENT.read_text()))


def summarize_frontier(frontier: dict, snapshot: dict) -> dict:
    validate_frontier(frontier, snapshot)
    totals = {key: sum(row[key] for row in frontier["editions"]) for key in ("required", *STATES)}
    return {
        "schema_version": 1,
        "execution": frontier["execution"],
        "snapshot_sha256": frontier["snapshot_sha256"],
        "scope": frontier["scope"],
        "classification": frontier["classification"],
        "editions": frontier["editions"],
        "totals": totals,
        "unknown": sum(totals[key] for key in STATES[1:]),
        "completed_editions": sum(
            row["qualified"] == row["required"] for row in frontier["editions"]
        ),
        "private_source_reacquisition_performed": False,
        "predictive_improvement_claimed": False,
        "full_study_readiness_inferred": False,
    }


def render_frontier_panel(summary: dict) -> str:
    editions = summary["editions"]
    tracks = []
    for row in editions:
        segments = "".join(
            f'<span class="frontier-segment {key}" data-state="{key}" '
            f'style="width:{100 * row[key] / row["required"]:.6f}%" '
            f'title="{html.escape(LABELS[key])}: {row[key]}" aria-hidden="true"></span>'
            for key in STATES
        )
        description = "; ".join(f"{LABELS[key]}: {row[key]}" for key in STATES)
        tracks.append(
            f'<div class="frontier-edition" data-season="{row["season"]}">'
            f'<div class="frontier-label"><strong>{row["season"]}</strong>'
            f'<span class="frontier-value">{row["qualified"]} / {row["required"]} qualified</span>'
            f'</div><div class="frontier-track" role="img" aria-label="'
            f'{html.escape(str(row["season"]) + ". " + description)}">{segments}</div></div>'
        )
    rows = "".join(
        '<tr><th scope="row">'
        + str(r["season"])
        + "</th>"
        + "".join(f"<td>{r[k]}</td>" for k in ("required", *STATES))
        + "</tr>"
        for r in editions
    )
    totals = summary["totals"]
    values = {
        "execution": html.escape(summary["execution"]),
        "qualified": totals["qualified"],
        "required": totals["required"],
        "unknown": summary["unknown"],
        "home_only": totals["missing_home_only"],
        "both": totals["missing_both"],
        "completed": summary["completed_editions"],
        "tracks": "".join(tracks),
        "rows": rows,
        "scope": html.escape(summary["scope"]),
        "digest": html.escape(summary["snapshot_sha256"]),
        "data": json.dumps(summary, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c"),
        "script": (ROOT / "tools/qualification_frontier.js").read_text(),
    }
    template = (ROOT / "tools/qualification_frontier_template.html").read_text()
    return Template(template).substitute(values)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.parse_args()
    frontier, snapshot = load_frontier(), strict_json(CURRENT.read_text())
    summary = summarize_frontier(frontier, snapshot)
    print(
        json.dumps(
            {
                "status": "PASS",
                "execution": summary["execution"],
                "totals": summary["totals"],
                "unknown": summary["unknown"],
                "completed_editions": summary["completed_editions"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
