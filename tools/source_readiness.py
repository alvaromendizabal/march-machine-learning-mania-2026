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
    "source_audit coverage resources matched_replay interpretation latest_followup "
    "offline_qualification",
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

# This is a versioned, frozen evidence snapshot, not a user-editable telemetry
# endpoint. Exact public facts are pinned independently of the data file. The
# recursive contract rejects unknown fields at every depth, including fields
# hidden inside year histograms. It is not a substitute for private-body auth.
FOLLOWUP_EXPECTED = {
    "execution": "V020",
    "parent_execution": "V019",
    "status": "TWO_TARGET_DIAGNOSTICS_COMPLETE_GAPS_REMAIN",
    "evidence_class": "AUDITABLE_PRIVATE_AGGREGATE",
    "registered_targets": 2,
    "complete_bodies_verified": 2,
    "complete_format_or_row_inspections": 2,
    "fresh_verified_stored_bytes": 4423048,
    "original_locations_not_reread": 65,
    "metadata_snapshot_reread": False,
    "csv": {
        "format": "COMMA_DELIMITED_TEXT",
        "records": 2283,
        "columns": 96,
        "physical_lines": 15982,
        "unique_physical_games_proven": False,
        "independent_sport_identity_proven": False,
        "historical_feature_availability_proven": False,
        "raw_rows_published": False,
    },
    "parquet": {
        "rows": 1629,
        "columns": 83,
        "batches": 13,
        "canonical_typed_row_bytes": 4712668,
        "game_json_url_null": 1629,
        "provider_host_candidates": 0,
        "sport_token_candidates": 0,
        "season_candidates": {"2027": 1629},
        "event_years_as_stored": {
            "date": {"2026": 636, "2027": 993},
            "start_date": {"2026": 636, "2027": 993},
            "game_date_time": {"2026": 637, "2027": 992},
            "game_date": {"2026": 637, "2027": 992},
        },
        "event_year_basis": "CALENDAR_YEAR_AS_STORED_NO_TIMEZONE_NORMALIZATION",
        "event_value_classes": {
            "date": "AWARE_EVENT_NOT_FEATURE_AVAILABILITY",
            "start_date": "AWARE_EVENT_NOT_FEATURE_AVAILABILITY",
            "game_date_time": "AWARE_EVENT_NOT_FEATURE_AVAILABILITY",
            "game_date": "DATE_ONLY_NOT_FEATURE_AVAILABILITY",
        },
        "boolean_presence_fields": ["game_json", "PBP", "team_box", "player_box"],
        "presence_is_not_underlying_body_custody": True,
        "unique_physical_games_proven": False,
        "independent_sport_identity_proven": False,
        "historical_feature_availability_proven": False,
        "raw_rows_published": False,
    },
    "resources": {
        "head_calls": 2,
        "get_calls": 2,
        "sts_calls": 1,
        "observed_http_attempts": 5,
        "observed_sdk_retries": 0,
        "write_calls": 0,
        "list_calls": 0,
        "provider_calls": 0,
        "provider_purchases": 0,
        "source_body_strategy": "TWO_TARGETS_SEQUENTIAL",
        "raw_local_mirror": False,
        "verified_stored_bytes": 4423048,
        "source_audit_seconds": 0.8570781009999564,
        "body_seconds_excluding_packaging": 11.079313356,
        "return_packaging_seconds_from_live_log": 0.6167312489999972,
        "total_seconds_from_live_log": 11.786151601999961,
        "free_disk_before_packaging_bytes": 1245544448,
        "free_disk_after_packaging_bytes_from_live_log": 1165094912,
        "peak_rss_kib": 1154084,
        "os_cpus": 4,
        "aws_cost": "UNKNOWN",
        "postwrite_observations_are_outside_sealed_return": True,
    },
    "request_rows": 3625,
    "unresolved_objects": 67,
    "unresolved_requests": 3573,
    "prior_semantic_duplicates": 52,
    "exact_request_candidates": 0,
    "new_debt_closures": 0,
    "new_historical_features": 0,
    "new_private_model_fits": 0,
    "accepted_control_changed": False,
    "next_action": "NO_SOURCE_REREAD_EVIDENCE_QUALIFICATION_AND_FROZEN_PUBLIC_DELIVERY_PARITY",
}

OFFLINE_QUALIFICATION_EXPECTED = {
    "execution": "V021",
    "parent_execution": "V020",
    "status": "OFFLINE_QUALIFICATION_COMPLETE_GAPS_REMAIN",
    "evidence_class": "AUDITABLE_PRIVATE_AGGREGATE",
    "registered_stages_completed": 6,
    "original_locations": 67,
    "distinct_content_identities": 54,
    "excluded_previously_closed_objects": 4,
    "complete_content_masks": 47,
    "complete_location_masks": 60,
    "uninspected_archive_text_members": 7,
    "original_request_rows": 3625,
    "unresolved_requests": 3573,
    "prior_semantic_duplicates": 52,
    "new_debt_closures": 0,
    "new_historical_feature_admissions": 0,
    "new_private_model_fits": 0,
    "masks_are_not_source_identity_or_feature_admission": True,
    "public_inference": {
        "scope": "PUBLIC_SYNTHETIC_IN_PROCESS",
        "frozen_models": 3,
        "label_free_predictions": 198,
        "exact_response_byte_parity": True,
        "new_fits": 0,
        "new_label_scoring": 0,
        "fresh_subprocess_proof": False,
        "private_model_parity_claimed": False,
    },
    "operations": {
        "source_rereads": 0,
        "source_bytes_read": 0,
        "s3_calls": 0,
        "sts_calls": 0,
        "provider_calls": 0,
        "provider_purchases": 0,
        "subprocesses": 0,
        "blocked_offline_attempts": 0,
    },
    "owner_tests": {
        "passed": 118,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "scope": "INVENTED_CONTRACT_FIXTURES_NOT_RESEARCH",
    },
    "resources": {
        "body_seconds_before_packaging": 14.338099397000008,
        "total_seconds_from_postwrite_log": 15.147032547000038,
        "postwrite_observations_outside_sealed_return": True,
        "cost": "UNKNOWN",
    },
    "next_action": "OFFLINE_PUBLIC_EXECUTION_EVIDENCE_CUSTODY_AUDIT_NO_SOURCE_REREADS_OR_REFITS",
}


FROZEN_HISTORY_COUNTS = {
    "source_audit": {
        "registered_locations": 67,
        "complete_bodies_verified": 67,
        "source_bytes_verified": 148994102,
        "distinct_content_identities": 54,
        "distinct_interpretations_completed": 53,
        "reused_interpretations": 13,
        "complete_json_container_traversals": 45,
        "zip_text_members_semantically_uninspected": 7,
        "interpretation_errors": 1,
        "json_interpretations": 40,
        "zip_interpretations": 12,
        "parquet_schema_only": 1,
        "payload_uninterpreted": 1,
        "failed_payload_bytes": 4289729,
        "metadata_snapshot_records": 90886,
        "metadata_snapshot_receipts": 90886,
        "request_rows": 3625,
        "unresolved_requests": 3573,
        "prior_semantic_duplicates": 52,
        "exact_request_matches": 0,
        "new_debt_closures": 0,
        "historical_features_admitted": 0,
        "provider_calls": 0,
        "provider_purchases": 0,
        "new_private_model_fits": 0,
    },
    "coverage": {
        "men_60m_edges": 6765,
        "men_2018_2019_edges": 0,
        "women_edges": 0,
        "cbbd_men_exact_game_joins": 15028,
        "cbbd_paired_stats": 15027,
        "cbbd_nonempty_lines": 14704,
        "new_historical_clock_witnesses": 0,
    },
    "resources": {
        "head_calls": 69,
        "get_calls": 69,
        "sts_calls": 1,
        "write_calls": 0,
        "list_calls": 0,
        "observed_sdk_retries": 0,
        "verified_stored_bytes": 187256496,
        "source_audit_seconds": 69.36314928799993,
        "body_seconds_excluding_packaging": 78.816266397,
        "total_seconds_from_live_log": 79.5091949109999,
        "return_packaging_seconds_from_live_log": 0.606110172,
        "free_disk_before_packaging_bytes": 1406443520,
        "free_disk_after_packaging_bytes_from_live_log": 1327349760,
        "peak_rss_kib": 882536,
        "os_cpus": 4,
    },
    "matched_replay": {
        "games": 925,
        "feature_games": 218,
        "control_fallback_games": 707,
        "development_games": 523,
        "exposed_later_games": 402,
        "bootstrap_replications": 1024,
        "bootstrap_seed": 10010,
        "screens_per_candidate": 5,
        "first_four_feature_games": 6,
        "first_four_games": 44,
        "first_four_metric_minimum": 20,
    },
}

FROZEN_SCORES = [
    {"arm": "Accepted control", "brier": 0.16940939326558535, "log_loss": 0.504349701696621},
    {"arm": "Registered reference", "brier": 0.16762873051435492, "log_loss": 0.4972804843645902},
    {"arm": "Registered candidate A", "brier": 0.16758810464578947, "log_loss": 0.4972281959983217},
    {"arm": "Registered candidate B", "brier": 0.16764848874668442, "log_loss": 0.4973564428498034},
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_frozen_tree(actual: object, expected: object, path: str) -> None:
    """Reject type drift, unknown nested keys and altered registered values."""
    require(type(actual) is type(expected), f"Unexpected type at {path}")
    if isinstance(expected, dict):
        require(set(actual) == set(expected), f"Unexpected or missing fields at {path}")
        for key, value in expected.items():
            require_frozen_tree(actual[key], value, f"{path}.{key}")
    elif isinstance(expected, list):
        require(len(actual) == len(expected), f"Unexpected list length at {path}")
        for index, (value, registered) in enumerate(zip(actual, expected, strict=True)):
            require_frozen_tree(value, registered, f"{path}[{index}]")
    else:
        require(actual == expected, f"Registered value changed at {path}")


def validate_source_readiness(data: dict) -> dict:
    require(isinstance(data, dict), "Expected an aggregate object")
    for section, fields in FIELDS.items():
        obj = data if section == "root" else data.get(section)
        require(
            isinstance(obj, dict) and set(obj) == set(fields.split()),
            f"Unexpected or missing {section} fields",
        )
    require_frozen_tree(data["schema_version"], 3, "schema_version")
    require_frozen_tree(data["reviewed_on"], "2026-11-03", "reviewed_on")
    require_frozen_tree(
        data["public_scope"],
        "Sanitized authenticated owner aggregates; public checks do not access or independently "
        "reauthenticate withheld source bodies.",
        "public_scope",
    )
    require_frozen_tree(data["latest_followup"], FOLLOWUP_EXPECTED, "latest_followup")
    require_frozen_tree(
        data["offline_qualification"], OFFLINE_QUALIFICATION_EXPECTED, "offline_qualification"
    )
    require(data["project"] == "independent_march_machine_learning_mania", "Wrong project")
    require(data["execution"] == "V019" and data["status"] == "PARTIAL", "Execution scope drift")
    require(data["evidence_class"] == "AUDITABLE_PRIVATE_AGGREGATE", "Evidence class drift")
    a, c, r, m, i = (
        data[key]
        for key in ("source_audit", "coverage", "resources", "matched_replay", "interpretation")
    )
    for section, values in FROZEN_HISTORY_COUNTS.items():
        for key, value in values.items():
            require_frozen_tree(data[section][key], value, f"{section}.{key}")
    require_frozen_tree(c["covered_men_seasons"], list(range(2021, 2026)), "covered_men_seasons")
    require_frozen_tree(m["candidate_development_screens_passed"], [0, 0], "development_screens")
    require_frozen_tree(m["aggregate_scores"], FROZEN_SCORES, "matched_replay.aggregate_scores")
    require_frozen_tree(
        i["next_source_scope"],
        "Only the one bounded-parser payload and the previously schema-only Parquet object; "
        "no repeat of the complete 67-body audit or metadata census.",
        "interpretation.next_source_scope",
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
    a, m, followup = d["source_audit"], d["matched_replay"], d["latest_followup"]
    csv, parquet = followup["csv"], followup["parquet"]
    q = d["offline_qualification"]
    rows = "".join(
        "<tr><th scope='row'>" + html.escape(row["arm"]) + "</th>"
        f"<td>{row['brier']:.9f}</td><td>{row['log_loss']:.9f}</td></tr>"
        for row in m["aggregate_scores"]
    )
    return (
        "<section id='source-readiness' class='replay-panel' aria-labelledby='source-title'>"
        "<div class='eyebrow'>Authenticated private aggregates · November 3, 2026</div>"
        "<h2 id='source-title'>Verified bytes. Unresolved eligibility.</h2>"
        "<p><strong>V021 completed the offline qualification audit</strong> for all "
        f"{q['original_locations']} original locations and {q['original_request_rows']:,} "
        "request rows, with no new source reads or private fits. "
        f"{q['complete_content_masks']} / {q['distinct_content_identities']} content masks "
        f"and {q['complete_location_masks']} / {q['original_locations']} location masks "
        "are complete interpretations—not proven source identity or feature eligibility. "
        "Three frozen public teaching models reproduced 198 label-free responses exactly "
        "in process; the fresh-process public demonstration below is a separate scope.</p>"
        "<p>V020 completed <strong>2 / 2 bounded source diagnostics</strong>, not a model run. "
        f"The earlier parser-blocked object is complete CSV: {csv['records']:,} records, "
        f"{csv['columns']} columns and {csv['physical_lines']:,} physical lines. "
        f"The Parquet inspection read {parquet['rows']:,} rows across {parquet['columns']} "
        "columns. Record counts are not proven unique physical games.</p>"
        "<p>All Parquet season values are 2027 candidates; every source-URL field is null. "
        "Stored event years are 2026–2027, not historical feature-availability clocks. "
        "Four presence fields are booleans, not custody of underlying JSON, play-by-play "
        "or box-score bodies. No new historical feature qualifies.</p>"
        "<div class='grid'><article><span>Original bodies verified</span>"
        f"<strong>{a['complete_bodies_verified']} / {a['registered_locations']}</strong>"
        "<span>V019 custody; only two bodies re-read in V020</span></article>"
        "<article><span>Unresolved requests</span>"
        f"<strong>{a['unresolved_requests']:,}</strong><span>No fabricated closure</span></article>"
        "<article><span>New eligible features / model fits</span><strong>0 / 0</strong>"
        "<span>Preserve the accepted control</span></article></div>"
        "<details><summary>Preserved V019 history: PARTIAL, November 3, 2026</summary>"
        "<p>V019's <strong>PARTIAL</strong> status is unchanged: it verified 67 stored bodies "
        "representing 54 content identities, with one grammar-blocked object and one "
        "schema-only Parquet inspection. V020 completed those two follow-up inspections; "
        "it did not relabel the earlier run. Seven tiny archive text members remain "
        "semantically uninspected. All 67 original object debts remain unresolved.</p></details>"
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
        "The next bounded, zero-source-read task audits retained public CI execution evidence, "
        "without "
        "repeating completed source inspections, qualification algorithms or model inference. "
        "Private source identity and clock gaps remain unresolved.</p></section>"
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
                "owner_execution": data["execution"],
                "latest_followup_execution": data["latest_followup"]["execution"],
                "latest_followup_status": data["latest_followup"]["status"],
                "offline_qualification_execution": data["offline_qualification"]["execution"],
                "offline_qualification_status": data["offline_qualification"]["status"],
                "new_private_model_fits": 0,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
