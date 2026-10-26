"""Validate and explain public acquisition transitions without private source data."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path
from string import Template

from evidence_contracts import require, validate_snapshot

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "portfolio/execution_history.json"
CURRENT = ROOT / "portfolio/acquisition_progress.json"
TRANSITION_FIELDS = {
    "from",
    "to",
    "box_candidates_added",
    "women_rows_added",
    "women_rows_removed",
    "prior_bodies_verified",
    "prior_bodies_reparsed",
    "prior_processing_errors_resolved",
    "notes",
}


def strict_json(text: str) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key: " + key)
            result[key] = value
        return result

    def constant(value):
        raise ValueError("Nonfinite JSON constant: " + value)

    value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    require(type(value) is dict, "Expected an evidence object")
    return value


def snapshot_digest(snapshot: dict) -> str:
    raw = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def validate_history(history: dict, current: dict | None = None) -> dict:
    require(
        set(history)
        == {"schema_version", "evidence_type", "reviewed_on", "snapshots", "transitions", "scope"},
        "Unexpected history fields",
    )
    require(
        type(history["schema_version"]) is int and history["schema_version"] == 1,
        "Unknown history schema",
    )
    require(history["evidence_type"] == "OWNER_EXECUTION_HISTORY", "Unknown history evidence class")
    reviewed = date.fromisoformat(history["reviewed_on"])
    require(
        isinstance(history["scope"], str) and 1 <= len(history["scope"]) <= 1000,
        "Missing bounded scope",
    )
    snapshots, transitions = history["snapshots"], history["transitions"]
    require(
        type(snapshots) is list and len(snapshots) >= 2, "Two or more observations are required"
    )
    require(
        type(transitions) is list and len(transitions) == len(snapshots) - 1,
        "Transition coverage differs",
    )
    executions = []
    for snapshot in snapshots:
        validate_snapshot(snapshot)
        match = re.fullmatch(r"v([1-9][0-9]*)", snapshot["execution"])
        require(match is not None, "Invalid execution identity")
        executions.append(int(match.group(1)))
        require(
            date.fromisoformat(snapshot["reviewed_on"]) <= reviewed,
            "Snapshot review is in the future",
        )
        require(snapshot["review_timezone"] == "America/Los_Angeles", "Review timezone changed")
        venue, interpretation = snapshot["venue"], snapshot["interpretation"]
        if snapshot["status"] == "SUCCESS":
            require(venue["source_errors"] == 0, "Successful acquisition hides source errors")
        if interpretation["acquisition_milestone_completed"]:
            require(
                venue["completed_units"] == venue["planned_units"],
                "Incomplete acquisition milestone",
            )
        require(
            type(snapshot["execution_counters"]["all_aggregate_caps_disabled"]) is bool,
            "Invalid cap declaration",
        )
    require(
        all(a < b for a, b in zip(executions, executions[1:], strict=False)),
        "History must be unique and ordered",
    )
    for before, after, transition in zip(snapshots, snapshots[1:], transitions, strict=False):
        require(set(transition) == TRANSITION_FIELDS, "Unexpected transition fields")
        require(
            transition["from"] == before["execution"] and transition["to"] == after["execution"],
            "Transition identity mismatch",
        )
        for key in TRANSITION_FIELDS - {"from", "to", "notes"}:
            require(
                type(transition[key]) is int and transition[key] >= 0,
                "Invalid transition count: " + key,
            )
        require(
            type(transition["notes"]) is str and len(transition["notes"]) <= 1000,
            "Unbounded transition notes",
        )
        b0, b1, v0, v1 = before["box_scores"], after["box_scores"], before["venue"], after["venue"]
        require(
            b0["original_missing"] == b1["original_missing"], "Box population changed between runs"
        )
        require(
            {r["season"]: r["original_missing"] for r in b0["by_season"]}
            == {r["season"]: r["original_missing"] for r in b1["by_season"]},
            "Season-level box populations changed between runs",
        )
        require(
            before["team_seasons"]["total"] == after["team_seasons"]["total"],
            "Team-season population changed between runs",
        )
        require(
            v0["women_rows_required"] == v1["women_rows_required"],
            "Venue population changed between runs",
        )
        require(
            v0["men_rows_carried"] == v1["men_rows_carried"], "Carried control population changed"
        )
        require(b1["previous_recovered"] == b0["recovered"], "Current delta has a different parent")
        require(
            transition["box_candidates_added"]
            == b1["new_recovered"]
            == b1["recovered"] - b0["recovered"],
            "Box additions were double counted",
        )
        require(
            transition["women_rows_removed"] <= v0["women_rows_qualified"],
            "Retractions exceed prior qualified population",
        )
        require(
            v0["women_rows_qualified"]
            + transition["women_rows_added"]
            - transition["women_rows_removed"]
            == v1["women_rows_qualified"],
            "Venue gain or retraction is unaccounted",
        )
        require(
            transition["prior_bodies_reparsed"] <= transition["prior_bodies_verified"],
            "Unverified bodies cannot be reparsed",
        )
        require(
            transition["prior_processing_errors_resolved"] <= v0["source_errors"],
            "Resolved errors exceed prior errors",
        )
    if current is not None:
        validate_snapshot(current)
        require(
            snapshots[-1] == current, "Latest history observation differs from current snapshot"
        )
    return history


def load_history() -> dict:
    return validate_history(strict_json(HISTORY.read_text()), strict_json(CURRENT.read_text()))


def summarize_history(history: dict) -> dict:
    validate_history(history)
    before, after = history["snapshots"][-2:]
    transition = history["transitions"][-1]
    return {
        "schema_version": 1,
        "status": "PASS",
        "scope": history["scope"],
        "observations": [
            {
                "execution": s["execution"],
                "status": s["status"],
                "digest": snapshot_digest(s),
                "box_recovered": s["box_scores"]["recovered"],
                "box_required": s["box_scores"]["original_missing"],
                "historical_admissions": s["box_scores"]["strict_historical_admissions"],
                "women_qualified": s["venue"]["women_rows_qualified"],
                "women_required": s["venue"]["women_rows_required"],
                "women_unknown": s["venue"]["women_rows_unknown"],
                "new_capture_bodies": s["venue"]["unique_new_captures"],
                "elapsed_seconds": s["execution_counters"]["elapsed_seconds"],
            }
            for s in history["snapshots"]
        ],
        "latest_change": {
            **transition,
            "women_net_gain": after["venue"]["women_rows_qualified"]
            - before["venue"]["women_rows_qualified"],
            "dated_court_net_gain": after["venue"]["dated_court_assignments"]
            - before["venue"]["dated_court_assignments"],
            "home_pod_net_gain": after["venue"]["qualified_home_pods"]
            - before["venue"]["qualified_home_pods"],
        },
        "no_global_completion_percentage": True,
        "private_provider_reacquisition_performed": False,
        "predictive_improvement_claimed": False,
    }


def render_history_panel(summary: dict) -> str:
    observations, change = summary["observations"], summary["latest_change"]
    tracks = "".join(
        '<div class="history-observation"><div class="history-label"><strong>'
        + html.escape(r["execution"])
        + '</strong><span class="history-value">'
        + f"{r['women_qualified']} / {r['women_required']} qualified"
        + '</span></div><div class="history-track"><span style="width:'
        + f"{100 * r['women_qualified'] / r['women_required']:.5f}%"
        + '"></span></div></div>'
        for r in observations
    )
    rows = "".join(
        "<tr><td>"
        + html.escape(r["execution"])
        + "</td><td>"
        + html.escape(r["status"])
        + f"</td><td>{r['box_recovered']}/{r['box_required']}</td>"
        + f"<td>{r['women_qualified']}/{r['women_required']}"
        + f"</td><td>{r['historical_admissions']}</td><td>{r['elapsed_seconds']:.1f}s</td></tr>"
        for r in observations
    )
    data = (
        json.dumps(observations, ensure_ascii=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    values = {
        "tracks": tracks,
        "rows": rows,
        "data": data,
        "women_added": change["women_rows_added"],
        "errors_resolved": change["prior_processing_errors_resolved"],
        "bodies_reparsed": change["prior_bodies_reparsed"],
        "qualified": observations[-1]["women_qualified"],
        "required": observations[-1]["women_required"],
        "unknown": observations[-1]["women_unknown"],
        "boxes_added": change["box_candidates_added"],
        "women_removed": change["women_rows_removed"],
        "courts": f"{change['dated_court_net_gain']:+d}",
        "home_pods": f"{change['home_pod_net_gain']:+d}",
        "scope": html.escape(summary["scope"]),
    }
    template = Path(__file__).with_name("evidence_history_template.html").read_text()
    return Template(template).substitute(values)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    del args
    result = summarize_history(load_history())
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
