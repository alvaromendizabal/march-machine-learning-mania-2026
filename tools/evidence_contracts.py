"""Public aggregate schema: explicit denominators and bounded claims."""

from __future__ import annotations

import math

FIELDS = {
    "schema_version",
    "evidence_type",
    "reviewed_on",
    "review_timezone",
    "execution",
    "status",
    "scope",
    "provenance",
    "box_scores",
    "team_seasons",
    "venue",
    "execution_counters",
    "interpretation",
}


BOX_FIELDS = {
    "original_missing",
    "previous_recovered",
    "recovered",
    "new_recovered",
    "remaining",
    "unresolved",
    "unverified",
    "quarantined",
    "strict_historical_admissions",
    "by_season",
}


VENUE_FIELDS = {
    "planned_units",
    "completed_units",
    "unique_new_captures",
    "source_errors",
    "qualified_editions",
    "qualified_home_pods",
    "dated_court_assignments",
    "women_rows_required",
    "women_rows_qualified",
    "women_rows_unknown",
    "men_rows_carried",
    "measure",
}


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def validate_snapshot(d: dict) -> dict:
    """Enforce a narrow public schema and explicit, internally consistent denominators."""
    require(set(d) == FIELDS, "Unexpected snapshot fields")
    require(
        type(d["schema_version"]) is int and d["schema_version"] == 1, "Unknown snapshot schema"
    )
    require(d["evidence_type"] == "OWNER_EXECUTION_AGGREGATES", "Unknown evidence class")
    require(d["status"] in {"SUCCESS", "PARTIAL", "FAILED", "STOPPED"}, "Unknown execution status")
    b, v, t = (d[k] for k in ("box_scores", "venue", "team_seasons"))
    c, i, p = (d[k] for k in ("execution_counters", "interpretation", "provenance"))
    require(set(b) == BOX_FIELDS and set(v) == VENUE_FIELDS, "Unexpected source fields")
    require(set(t) == {"total", "complete", "affected", "measure"}, "Unexpected history fields")
    require(
        set(c)
        == {
            "elapsed_seconds",
            "source_elapsed_seconds",
            "source_http_requests",
            "venue_http_requests",
            "new_model_fits",
            "new_submissions",
            "champion_changed",
            "all_aggregate_caps_disabled",
        },
        "Unexpected execution fields",
    )
    require(
        set(i)
        == {
            "acquisition_milestone_completed",
            "full_model_study_completed",
            "prospective_validation_claimed",
            "next_data_work",
        },
        "Unexpected interpretation fields",
    )
    require(
        set(p)
        == {
            "source",
            "manifest_members_verified",
            "manifest_checks",
            "raw_source_data_public",
            "public_checks",
        },
        "Unexpected provenance fields",
    )
    for group in (b, v, t):
        for key, value in group.items():
            if key not in {"by_season", "measure"}:
                require(type(value) is int and value >= 0, "Invalid count: " + key)
    require(b["recovered"] + b["remaining"] == b["original_missing"], "Box denominator changed")
    require(b["previous_recovered"] + b["new_recovered"] == b["recovered"], "Delta disagrees")
    require(
        sum(b[k] for k in ("unresolved", "unverified", "quarantined")) == b["remaining"],
        "Residual states do not partition the gap",
    )
    require(b["strict_historical_admissions"] <= b["recovered"], "Admissions exceed recovery")
    seasons = b["by_season"]
    require(len({r["season"] for r in seasons}) == len(seasons), "Duplicate season")
    for row in seasons:
        require(
            set(row) == {"season", "original_missing", "recovered", "remaining"},
            "Unexpected season fields",
        )
        require(all(type(x) is int and x >= 0 for x in row.values()), "Invalid season counts")
        require(
            row["recovered"] + row["remaining"] == row["original_missing"],
            "Season denominator changed",
        )
    for key in ("original_missing", "recovered", "remaining"):
        require(sum(row[key] for row in seasons) == b[key], "Season totals disagree")
    require(t["complete"] + t["affected"] == t["total"], "History denominator changed")
    require(
        v["women_rows_qualified"] + v["women_rows_unknown"] == v["women_rows_required"],
        "Women's representation denominator changed",
    )
    require(v["completed_units"] <= v["planned_units"], "Units exceed the plan")
    require(v["source_errors"] <= v["completed_units"], "Errors exceed attempts")
    require(v["qualified_home_pods"] <= v["dated_court_assignments"], "Home facts exceed courts")
    require(type(i["acquisition_milestone_completed"]) is bool, "Invalid acquisition milestone")
    require(type(c["all_aggregate_caps_disabled"]) is bool, "Invalid cap declaration")
    require(
        type(p["manifest_members_verified"]) is int and p["manifest_members_verified"] >= 0,
        "Invalid verified member count",
    )
    if d["status"] == "SUCCESS":
        require(
            v["completed_units"] == v["planned_units"]
            and v["source_errors"] == 0
            and i["acquisition_milestone_completed"] is True,
            "Successful acquisition must complete its units without processing errors",
        )
    require(
        c["new_model_fits"] == c["new_submissions"] == 0 and c["champion_changed"] is False,
        "This acquisition snapshot cannot claim a new model or score",
    )
    require(
        i["full_model_study_completed"] is False and i["prospective_validation_claimed"] is False,
        "Unsupported scientific completion claim",
    )
    require(p["raw_source_data_public"] is False, "Raw disclosure is outside this public schema")
    for key in ("elapsed_seconds", "source_elapsed_seconds"):
        require(
            type(c[key]) in (float, int) and math.isfinite(c[key]) and c[key] >= 0,
            "Invalid duration",
        )
    for key in ("source_http_requests", "venue_http_requests", "new_model_fits", "new_submissions"):
        require(type(c[key]) is int and c[key] >= 0, "Invalid execution count")
    return d
