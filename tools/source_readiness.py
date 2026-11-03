"""Validate and render a deliberately small, public-safe owner evidence record.

These are aggregate consistency checks, not public authentication of private
source bodies or reproduction of private probabilities. Unknown fields fail
closed so private records cannot silently ride along with a public summary.
"""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_READINESS = ROOT / "portfolio/source_readiness.json"
FIELDS = {
    "root": "schema_version project reviewed_on evidence_class execution status public_scope "
    "source_audit coverage resources matched_replay interpretation",
    "source_audit": "registered_locations complete_bodies_verified source_bytes_verified "
    "distinct_content_identities distinct_interpretations_completed reused_interpretations "
    "complete_json_container_traversals zip_text_members_semantically_uninspected "
    "interpretation_errors json_interpretations zip_interpretations parquet_schema_only "
    "payload_uninterpreted error_contract failed_payload_bytes metadata_snapshot_records "
    "metadata_snapshot_receipts metadata_snapshot_closure_verified metadata_is_current_census "
    "request_rows unresolved_requests prior_semantic_duplicates exact_request_matches "
    "new_debt_closures historical_features_admitted provider_calls provider_purchases "
    "new_private_model_fits",
    "coverage": "men_60m_edges covered_men_seasons men_2018_2019_edges women_edges "
    "cbbd_men_exact_game_joins cbbd_paired_stats cbbd_nonempty_lines "
    "new_historical_clock_witnesses all_provider_data_acquired",
    "resources": "head_calls get_calls sts_calls write_calls list_calls observed_sdk_retries "
    "verified_stored_bytes source_audit_seconds body_seconds_excluding_packaging "
    "total_seconds_from_live_log return_packaging_seconds_from_live_log "
    "free_disk_before_packaging_bytes free_disk_after_packaging_bytes_from_live_log "
    "peak_rss_kib os_cpus aws_cost postwrite_observations_are_outside_sealed_return",
    "matched_replay": "execution evidence_class games feature_games control_fallback_games "
    "development_games exposed_later_games bootstrap_replications bootstrap_seed "
    "candidate_development_screens_passed screens_per_candidate first_four_feature_games "
    "first_four_games first_four_metric_minimum accepted_control_changed untouched_holdout "
    "all_paired_candidate_vs_reference_intervals_include_zero aggregate_scores "
    "not_a_new_kaggle_score private_rows_or_recipes_published",
    "interpretation": "body_integrity_is_feature_eligibility "
    "schema_recognition_is_row_interpretation retrieval_time_is_historical_availability "
    "new_model_promotion all_time_fit_total next_source_scope",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_source_readiness(data: dict) -> dict:
    require(isinstance(data, dict), "Expected an aggregate object")
    for section, fields in FIELDS.items():
        obj = data if section == "root" else data.get(section)
        require(
            isinstance(obj, dict) and set(obj) == set(fields.split()),
            f"Unexpected or missing {section} fields",
        )
    require(data["schema_version"] == 1, "Unsupported aggregate schema")
    require(data["project"] == "independent_march_machine_learning_mania", "Wrong project")
    require(data["execution"] == "V019" and data["status"] == "PARTIAL", "Execution scope drift")
    require(data["evidence_class"] == "AUDITABLE_PRIVATE_AGGREGATE", "Evidence class drift")
    a, c, r, m, i = (
        data[key]
        for key in ("source_audit", "coverage", "resources", "matched_replay", "interpretation")
    )
    for obj in (a, c, r, m):
        for key, value in obj.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                require(math.isfinite(value) and value >= 0, f"Invalid numeric {key}")
    counts = (
        "registered_locations",
        "complete_bodies_verified",
        "distinct_content_identities",
        "distinct_interpretations_completed",
        "reused_interpretations",
        "interpretation_errors",
        "request_rows",
        "unresolved_requests",
        "prior_semantic_duplicates",
    )
    for key in counts:
        require(type(a[key]) is int, f"Count cannot be bool/fraction: {key}")
    require(
        a["complete_bodies_verified"] == a["registered_locations"] == 67,
        "Body custody population changed",
    )
    require(a["distinct_content_identities"] == 54, "Distinct content population changed")
    require(
        a["distinct_interpretations_completed"] + a["interpretation_errors"] == 54,
        "Interpretation partition changed",
    )
    require(
        a["distinct_content_identities"] + a["reused_interpretations"] == 67,
        "Duplicate interpretations counted as new content",
    )
    require(
        a["json_interpretations"] + a["zip_interpretations"] + a["parquet_schema_only"]
        == a["distinct_interpretations_completed"],
        "Container partition changed",
    )
    require(
        a["complete_json_container_traversals"] == 45
        and a["zip_text_members_semantically_uninspected"] == 7,
        "Container recognition is not full semantic interpretation",
    )
    require(
        a["payload_uninterpreted"] == a["interpretation_errors"] == 1,
        "Missing payload interpretation cannot be passed",
    )
    require(a["error_contract"] == "JSON_SCALAR_SIZE_BOUND", "Failure reason drift")
    require(
        a["unresolved_requests"] + a["prior_semantic_duplicates"] == a["request_rows"] == 3625,
        "Request accounting changed",
    )
    require(a["unresolved_requests"] == 3573, "Unproved request closure")
    require(
        a["metadata_snapshot_records"] == a["metadata_snapshot_receipts"] == 90886,
        "Dated metadata closure changed",
    )
    require(
        a["metadata_snapshot_closure_verified"] is True
        and a["metadata_is_current_census"] is False,
        "Snapshot relabeled as current census",
    )
    for key in (
        "exact_request_matches",
        "new_debt_closures",
        "historical_features_admitted",
        "provider_calls",
        "provider_purchases",
        "new_private_model_fits",
    ):
        require(type(a[key]) is int and a[key] == 0, f"Unsupported new-work claim: {key}")
    require(
        c["covered_men_seasons"] == list(range(2021, 2026)) and c["men_60m_edges"] == 6765,
        "Historical market population drift",
    )
    for key in ("men_2018_2019_edges", "women_edges", "new_historical_clock_witnesses"):
        require(type(c[key]) is int and c[key] == 0, f"Unproved coverage: {key}")
    require(c["all_provider_data_acquired"] is False, "Source completeness is not established")
    require(
        c["cbbd_nonempty_lines"] <= c["cbbd_paired_stats"] <= c["cbbd_men_exact_game_joins"],
        "CBBD populations are inconsistent",
    )
    require(
        r["head_calls"] == r["get_calls"] == 69 and r["sts_calls"] == 1,
        "Observed API call accounting changed",
    )
    require(
        r["write_calls"] == r["list_calls"] == r["observed_sdk_retries"] == 0,
        "Read-only operation scope changed",
    )
    require(
        r["verified_stored_bytes"] == 187256496 and a["source_bytes_verified"] == 148994102,
        "Stored source/metadata byte accounting changed",
    )
    require(
        r["source_audit_seconds"]
        <= r["body_seconds_excluding_packaging"]
        <= r["total_seconds_from_live_log"],
        "Nested timing scopes are inconsistent",
    )
    require(r["aws_cost"] == "UNKNOWN", "Unmeasured billing must remain unknown")
    require(
        r["postwrite_observations_are_outside_sealed_return"] is True,
        "Later live-log measurements cannot be inside an earlier sealed Return",
    )
    require(
        m["execution"] == "V018" and m["evidence_class"] == data["evidence_class"],
        "Replayed score must retain its separate invocation",
    )
    require(
        m["games"] == m["development_games"] + m["exposed_later_games"] == 925,
        "Matched cohort partition changed",
    )
    require(
        m["feature_games"] + m["control_fallback_games"] == m["games"]
        and m["feature_games"] == 218,
        "Coverage is not the full scoring denominator",
    )
    require(
        m["candidate_development_screens_passed"] == [0, 0] and m["screens_per_candidate"] == 5,
        "Candidate qualification changed",
    )
    require(
        m["first_four_feature_games"] == 6
        and m["first_four_games"] == 44
        and m["first_four_feature_games"] < m["first_four_metric_minimum"],
        "Small First Four cohort cannot emit qualified metrics",
    )
    require(
        m["accepted_control_changed"] is False and m["untouched_holdout"] is False,
        "Exposed scores do not authorize selection",
    )
    require(
        m["not_a_new_kaggle_score"] is True and m["private_rows_or_recipes_published"] is False,
        "Score provenance/publication boundary changed",
    )
    require(
        m["all_paired_candidate_vs_reference_intervals_include_zero"] is True,
        "Descriptive uncertainty qualification changed",
    )
    require(
        m["bootstrap_replications"] == 1024 and m["bootstrap_seed"] == 10010,
        "Bootstrap protocol drift",
    )
    expected_arms = {
        "Accepted control",
        "Registered reference",
        "Registered candidate A",
        "Registered candidate B",
    }
    require(len(m["aggregate_scores"]) == 4, "Four matched arms required")
    for row in m["aggregate_scores"]:
        require(
            isinstance(row, dict) and set(row) == {"arm", "brier", "log_loss"},
            "Only aggregate scores may be published",
        )
        require(
            type(row["brier"]) in (int, float) and 0 <= row["brier"] <= 1, "Invalid aggregate Brier"
        )
        require(
            type(row["log_loss"]) in (int, float)
            and math.isfinite(row["log_loss"])
            and row["log_loss"] >= 0,
            "Invalid aggregate log loss",
        )
    require({row["arm"] for row in m["aggregate_scores"]} == expected_arms, "Matched arm set drift")
    for key in (
        "body_integrity_is_feature_eligibility",
        "schema_recognition_is_row_interpretation",
        "retrieval_time_is_historical_availability",
        "new_model_promotion",
    ):
        require(i[key] is False, f"Unsupported inference: {key}")
    require(i["all_time_fit_total"] == "UNKNOWN", "Overlapping historical counts cannot be summed")
    return data


def load_source_readiness() -> dict:
    return validate_source_readiness(json.loads(SOURCE_READINESS.read_text(encoding="utf-8")))


def render_source_panel(data: dict) -> str:
    d = validate_source_readiness(data)
    a, m = d["source_audit"], d["matched_replay"]
    rows = "".join(
        "<tr><th scope='row'>" + html.escape(row["arm"]) + "</th>"
        f"<td>{row['brier']:.9f}</td><td>{row['log_loss']:.9f}</td></tr>"
        for row in m["aggregate_scores"]
    )
    return (
        "<section id='source-readiness' class='replay-panel' aria-labelledby='source-title'>"
        "<div class='eyebrow'>Authenticated private aggregates · November 3, 2026</div>"
        "<h2 id='source-title'>Verified bytes. Unresolved eligibility.</h2>"
        "<p>V019 is <strong>PARTIAL</strong>, not a successful model run. "
        "All source bodies passed full integrity verification. One payload remains "
        "uninterpreted; recognizing a Parquet schema does not qualify its rows. "
        "Seven tiny archive text members also remain semantically uninspected.</p>"
        "<div class='grid'><article><span>Original bodies verified</span>"
        f"<strong>{a['complete_bodies_verified']} / {a['registered_locations']}</strong>"
        "<span>Complete stored-byte and SHA checks</span></article>"
        "<article><span>Unresolved requests</span>"
        f"<strong>{a['unresolved_requests']:,}</strong><span>No fabricated closure</span></article>"
        "<article><span>New eligible features / model fits</span><strong>0 / 0</strong>"
        "<span>Preserve the accepted control</span></article></div>"
        "<details><summary>Earlier matched replay: 925 games, 218 feature-bearing</summary>"
        "<p>V018 completed this frozen descriptive replay. Development 523; exposed later 402; "
        "707 unchanged control fallbacks. Both candidates passed 0/5 development screens. "
        "All paired candidate-versus-reference intervals include zero. "
        "These are not a new Kaggle score or untouched holdout.</p>"
        "<div class='replay-table' tabindex='0' role='region' aria-label='Matched score table'>"
        "<table><caption>Same 925 predictions per arm; private rows and recipes withheld</caption>"
        "<thead><tr><th scope='col'>Registered arm</th><th scope='col'>Brier</th>"
        "<th scope='col'>Log loss</th></tr></thead><tbody>" + rows + "</tbody></table></div>"
        "</details><p>Public checks verify this aggregate contract, not withheld source bodies. "
        "The next private task targets only the failed payload and schema-only Parquet; "
        "the completed 67-body audit and metadata census are not repeated.</p></section>"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.parse_args()
    data = load_source_readiness()
    print(
        json.dumps(
            {
                "status": "PASS",
                "evidence_class": data["evidence_class"],
                "owner_status": data["status"],
                "new_private_model_fits": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
