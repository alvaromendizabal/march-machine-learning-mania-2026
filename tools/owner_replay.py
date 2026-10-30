"""Validate and render a private execution's explicitly public aggregate evidence.

This module reads no private prediction, checkpoint, source body or cloud path.
It checks the published accounting and selection rule; hashes identify withheld
evidence and are not a public rerun or proof of upstream publisher authenticity.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from pathlib import Path

from evidence_contracts import require

ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "portfolio/owner_replay.json"


def fields(value: dict, expected: str, label: str) -> None:
    require(type(value) is dict and set(value) == set(expected.split()), label + " fields")


def count(value, label: str) -> None:
    require(type(value) is int and value >= 0, "Invalid count: " + label)


def number(value, label: str, maximum: float | None = None) -> None:
    require(
        type(value) in (int, float) and math.isfinite(value) and value >= 0,
        "Invalid number: " + label,
    )
    require(maximum is None or value <= maximum, "Out of range: " + label)


def validate_replay(d: dict) -> dict:
    """Reject disclosure, incompatible denominators and unsupported promotion."""
    fields(
        d,
        "schema_version evidence_type execution reviewed_on status reason provenance "
        "execution_accounting cohort scorecards market coverage decision "
        "systems storage comparison source_transition execution_ledger",
        "Replay",
    )
    require(type(d["schema_version"]) is int and d["schema_version"] == 3, "Replay schema")
    require(d["evidence_type"] == "AUDITABLE_PRIVATE_RUN_AGGREGATES", "Evidence class")
    require(re.fullmatch(r"v[0-9]+", d["execution"]) is not None, "Execution label")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", d["reviewed_on"]) is not None, "Review date")
    require(d["status"] == "PARTIAL", "Incomplete source closure cannot be success")
    require(d["reason"] == "OWNED_SOURCE_CLOSURE_INCOMPLETE", "Unqualified stop reason")
    p, e, c, m, coverage, decision = (
        d[k]
        for k in ("provenance", "execution_accounting", "cohort", "market", "coverage", "decision")
    )
    fields(
        p,
        "summary_sha256 qualification_sha256 prediction_artifact_sha256 return_parts "
        "manifest_payload_entries logical_files all_uploaded_payloads_verified "
        "raw_source_data_public check_scope",
        "Provenance",
    )
    for key in ("summary_sha256", "qualification_sha256", "prediction_artifact_sha256"):
        require(re.fullmatch(r"[a-f0-9]{64}", p[key]) is not None, "Evidence hash")
    require(p["all_uploaded_payloads_verified"] is True, "Unverified return payloads")
    require(p["raw_source_data_public"] is False, "Private source disclosure")
    require(
        p["check_scope"]
        == (
            "Public checks verify aggregate consistency; "
            "private payloads were authenticated separately."
        ),
        "Public verification scope changed",
    )
    for key in ("manifest_payload_entries", "logical_files"):
        count(p[key], key)
    require(p["logical_files"] <= p["manifest_payload_entries"], "Logical payload count")
    require(type(p["return_parts"]) is list and bool(p["return_parts"]), "Return parts required")
    for ordinal, part in enumerate(p["return_parts"], 1):
        fields(part, "part bytes sha256", "Return part")
        count(part["part"], "part")
        count(part["bytes"], "bytes")
        require(part["part"] == ordinal, "Parts must be unique and consecutive")
        require(0 < part["bytes"] < 150_000_000, "Upload part exceeds strict bound")
        require(re.fullmatch(r"[a-f0-9]{64}", part["sha256"]) is not None, "Part hash")
    require(
        len({x["sha256"] for x in p["return_parts"]}) == len(p["return_parts"]),
        "Duplicate return content",
    )
    fields(
        e,
        "coordinator_seconds start_to_return_status_seconds effective_cpus mean_cpu_cores_used "
        "source_workers research_fits_reused science_fits_reused new_model_fits new_submissions "
        "final_free_disk_bytes old_return_source_bytes_preserved "
        "old_return_allocated_bytes_released "
        "return_bytes bulk_derived_bytes_in_return",
        "Execution",
    )
    for key, value in e.items():
        if key in {"coordinator_seconds", "start_to_return_status_seconds", "mean_cpu_cores_used"}:
            number(value, key)
        else:
            count(value, key)
    require(e["effective_cpus"] > 0 and e["source_workers"] > 0, "Missing execution capacity")
    require(e["mean_cpu_cores_used"] <= e["effective_cpus"], "CPU utilization exceeds capacity")
    require(e["start_to_return_status_seconds"] >= e["coordinator_seconds"], "Runtime intervals")
    require(e["new_model_fits"] == e["new_submissions"] == 0, "Replay cannot claim new training")
    require(e["return_bytes"] == sum(x["bytes"] for x in p["return_parts"]), "Return sum")
    require(e["bulk_derived_bytes_in_return"] <= e["return_bytes"], "Return byte partition")
    # Logical bytes and allocated disk bytes intentionally have no equality rule.
    fields(
        c,
        "unit development_seasons later_seasons development_games later_games total_games arms "
        "prediction_rows identical_arm_populations_verified all_windows_previously_examined "
        "fresh_holdout",
        "Cohort",
    )
    require(c["unit"] == "physical_games", "Prediction rows are not independent games")
    for key in ("development_games", "later_games", "total_games", "arms", "prediction_rows"):
        count(c[key], key)
        require(c[key] > 0, "Empty evaluation population")
    for key in ("development_seasons", "later_seasons"):
        require(type(c[key]) is list and bool(c[key]), "Missing season population")
        require(all(type(x) is int for x in c[key]), "Season must be an integer")
        require(c[key] == sorted(set(c[key])), "Repeated or unordered seasons")
    require(max(c["development_seasons"]) < min(c["later_seasons"]), "Season leakage")
    require(c["development_games"] + c["later_games"] == c["total_games"], "Game denominator")
    require(c["prediction_rows"] == c["total_games"] * c["arms"], "Matched arm denominator")
    require(c["identical_arm_populations_verified"] is True, "Unmatched arm populations")
    require(c["all_windows_previously_examined"] is True, "Consumed windows mislabeled")
    require(c["fresh_holdout"] is False, "A replay does not create a fresh holdout")
    require(type(d["scorecards"]) is list and len(d["scorecards"]) == c["arms"], "Arm count")
    require(len({x["arm"] for x in d["scorecards"]}) == c["arms"], "Duplicated arm identity")
    accepted = []
    for row in d["scorecards"]:
        fields(row, "arm role development_brier later_brier", "Scorecard")
        require(row["role"] in {"accepted", "challenger"}, "Unknown arm role")
        require(
            row["arm"] == "Accepted control" or re.fullmatch(r"Challenger [A-Z]", row["arm"]),
            "Public arm labels must not expose private recipes",
        )
        for key in ("development_brier", "later_brier"):
            number(row[key], key, maximum=1)
        if row["role"] == "accepted":
            accepted.append(row)
    require(len(accepted) == 1 and accepted[0]["arm"] == "Accepted control", "Accepted control")
    require(
        all(
            x["development_brier"] > accepted[0]["development_brier"]
            for x in d["scorecards"]
            if x["role"] == "challenger"
        ),
        "Retained-control rationale contradicts development evidence",
    )
    fields(
        m,
        "selection_records men_selection_records women_selection_records "
        "priced_pregame_selection_records training_admissions unknown_owned_containers "
        "candidate_requests semantic_duplicates unresolved_requests eligible_paid_requests "
        "paid_requests paid_credits source_closure_complete",
        "Market",
    )
    for key, value in m.items():
        if key != "source_closure_complete":
            count(value, key)
    require(
        m["men_selection_records"] + m["women_selection_records"] == m["selection_records"],
        "Market selection partition",
    )
    require(
        m["priced_pregame_selection_records"] <= m["selection_records"], "Priced selection count"
    )
    require(m["source_closure_complete"] is False, "Incomplete inventory mislabeled")
    require(m["unknown_owned_containers"] > 0, "Missing incomplete-inventory evidence")
    require(
        m["semantic_duplicates"] + m["unresolved_requests"] == m["candidate_requests"],
        "Candidate request partition",
    )
    require(
        m["training_admissions"]
        == m["eligible_paid_requests"]
        == m["paid_requests"]
        == m["paid_credits"]
        == 0,
        "Unsupported admission or purchase claim",
    )
    fields(
        coverage,
        "measurement defined_study_seasons required_men_detailed_games "
        "required_women_detailed_games required_study_detail_complete "
        "broader_project_data_complete future_2027_data_complete residuals",
        "Coverage",
    )
    require(
        coverage["measurement"] == "CARRIED_AUTHENTICATED_COVERAGE_NOT_A_NEW_RAW_CENSUS",
        "Carried coverage must stay labeled",
    )
    require(coverage["defined_study_seasons"] == "2013–2025 excluding 2020", "Study scope")
    require(coverage["required_study_detail_complete"] is True, "Study readiness changed")
    require(
        coverage["broader_project_data_complete"] is False
        and coverage["future_2027_data_complete"] is False,
        "Unsupported project completion",
    )
    for key in ("required_men_detailed_games", "required_women_detailed_games"):
        count(coverage[key], key)
    require(type(coverage["residuals"]) is list and bool(coverage["residuals"]), "Coverage gaps")
    for row in coverage["residuals"]:
        fields(row, "family unit have required missing", "Coverage residual")
        require(type(row["family"]) is str and len(row["family"]) <= 80, "Coverage label")
        require(
            row["unit"]
            in {
                "game_rows",
                "tournament_game_rows",
                "team_game_reconciliations",
                "seeded_team_seasons",
                "team_seasons",
            },
            "Coverage unit",
        )
        for key in ("have", "required", "missing"):
            count(row[key], key)
        require(row["have"] + row["missing"] == row["required"], "Coverage denominator")
    require(
        len({r["family"] for r in coverage["residuals"]}) == len(coverage["residuals"]),
        "Duplicate coverage family",
    )
    fields(
        decision, "selected_arm champion_changed new_prospective_score_claimed reason", "Decision"
    )
    require(decision["selected_arm"] == accepted[0]["arm"], "Invalid promotion")
    require(
        decision["champion_changed"] is False
        and decision["new_prospective_score_claimed"] is False,
        "Unsupported scientific claim",
    )
    require(
        decision["reason"]
        == (
            "All three challengers worsen the declared development Brier; "
            "the later window is already exposed."
        ),
        "Decision rationale changed",
    )
    require(c["arms"] == 4, "Decision describes exactly three challengers")
    validate_systems(d)
    validate_transitions(d)
    validate_execution_ledger(d)
    require(
        re.search(
            r"s3://|arn:aws|/home/|/mnt/|sagemaker-|api[_-]?key|access[_-]?token",
            json.dumps(d),
            re.I,
        )
        is None,
        "Private locator or credential field in aggregate",
    )
    return d


def validate_systems(d: dict) -> None:
    """Keep measured savings, retained evidence and uncontrolled effects distinct."""
    e, m, systems, storage, comparison = (
        d[k] for k in ("execution_accounting", "market", "systems", "storage", "comparison")
    )
    fields(
        systems,
        "measurement request_scope fastest_possible_proven odds_seconds s3_get_responses "
        "s3_listing_pages s3_http_attempts_including_retries download_bytes "
        "exact_request_binding_reuses frozen_index_body_reuses prior_positive_checkpoint_reuses "
        "negative_cache_entries_written negative_cache_hits adapter_unresolved_objects "
        "adapter_error_reasons phase_seconds",
        "Systems",
    )
    require(
        systems["measurement"] == "OBSERVED_SEQUENTIAL_EXECUTIONS_NOT_A_CONTROLLED_BENCHMARK",
        "Sequential execution must not become a controlled benchmark",
    )
    require(
        systems["request_scope"] == "ODDS_WORKER_ONLY_EXCLUDES_STORAGE_ARCHIVAL",
        "Request accounting scope changed",
    )
    require(systems["fastest_possible_proven"] is False, "Unproven optimality claim")
    number(systems["odds_seconds"], "odds seconds")
    for key in (
        "s3_get_responses",
        "s3_listing_pages",
        "s3_http_attempts_including_retries",
        "download_bytes",
        "exact_request_binding_reuses",
        "frozen_index_body_reuses",
        "prior_positive_checkpoint_reuses",
        "negative_cache_entries_written",
        "negative_cache_hits",
        "adapter_unresolved_objects",
    ):
        count(systems[key], key)
    require(
        systems["s3_http_attempts_including_retries"]
        >= systems["s3_get_responses"] + systems["s3_listing_pages"],
        "Incomplete request accounting",
    )
    require(
        systems["negative_cache_entries_written"] + systems["negative_cache_hits"]
        == systems["adapter_unresolved_objects"],
        "New negative checkpoints are not cache hits",
    )
    require(
        systems["adapter_unresolved_objects"] <= m["unknown_owned_containers"],
        "Adapter attempts and broader source population differ",
    )
    fields(
        systems["adapter_error_reasons"],
        "CONTENT_ADDRESSED_OBJECT_HASH_MISMATCH TEXT_ENCODING_INVALID UNSUPPORTED_JSON_ROOT",
        "Adapter error reasons",
    )
    for key, value in systems["adapter_error_reasons"].items():
        count(value, key)
    require(
        sum(systems["adapter_error_reasons"].values()) == systems["adapter_unresolved_objects"],
        "Error reason partition",
    )
    fields(
        systems["phase_seconds"],
        "legacy_request_inventory baseline_price_restoration exact_metadata_reconciliation "
        "inventory_listing paid_request_proof source_diagnostics",
        "Measured phases",
    )
    for key, value in systems["phase_seconds"].items():
        number(value, key)
    require(sum(systems["phase_seconds"].values()) <= systems["odds_seconds"], "Phase intervals")
    fields(
        storage,
        "first_free_bytes final_free_bytes net_free_increase_bytes "
        "old_deliveries_allocated_bytes_released duplicate_estimator_allocated_bytes_released "
        "total_allocated_bytes_released source_bytes_remotely_preserved archived_deliveries "
        "verified_remote_body_and_manifest_readback consolidated_history_files "
        "duplicate_estimator_files_removed cache_files_removed cache_allocated_bytes_released "
        "unmanifested_cache_extras_preserved consolidated_history_roots "
        "unique_scientific_bytes_discarded "
        "all_historical_work_folders_removed",
        "Storage",
    )
    for key, value in storage.items():
        if key not in {
            "verified_remote_body_and_manifest_readback",
            "all_historical_work_folders_removed",
        }:
            count(value, key)
    require(
        storage["final_free_bytes"] - storage["first_free_bytes"]
        == storage["net_free_increase_bytes"],
        "Observed free-space change",
    )
    require(
        storage["old_deliveries_allocated_bytes_released"]
        + storage["duplicate_estimator_allocated_bytes_released"]
        + storage["cache_allocated_bytes_released"]
        == storage["total_allocated_bytes_released"],
        "Physical release is the action sum, not net free-space change",
    )
    require(
        storage["old_deliveries_allocated_bytes_released"]
        == e["old_return_allocated_bytes_released"]
        and storage["source_bytes_remotely_preserved"] == e["old_return_source_bytes_preserved"]
        and storage["final_free_bytes"] == e["final_free_disk_bytes"],
        "Storage summary disagrees with execution",
    )
    require(storage["archived_deliveries"] > 0, "Missing archival population")
    require(storage["verified_remote_body_and_manifest_readback"] is True, "Unverified custody")
    require(storage["unique_scientific_bytes_discarded"] == 0, "Lossy cleanup cannot be advertised")
    require(
        storage["all_historical_work_folders_removed"] is False, "Unsupported cleanup completion"
    )
    require(
        storage["unmanifested_cache_extras_preserved"] > 0, "Retained-content exception omitted"
    )
    fields(
        comparison,
        "baseline reduction_percent same_scientific_result same_cpu_and_worker_counts "
        "one_time_cleanup_in_current_duration provider_latency_and_background_load_controlled",
        "Comparison",
    )
    fields(
        comparison["baseline"],
        "execution summary_sha256 end_to_end_seconds odds_seconds s3_get_responses "
        "s3_http_attempts_including_retries download_bytes return_bytes effective_cpus "
        "source_workers reused_fits new_fits source_closure_complete",
        "Baseline",
    )
    b = comparison["baseline"]
    require(re.fullmatch(r"v[0-9]+", b["execution"]) is not None, "Baseline execution label")
    require(int(b["execution"][1:]) < int(d["execution"][1:]), "Comparison chronology")
    require(
        re.fullmatch(r"[a-f0-9]{64}", b["summary_sha256"]) is not None, "Baseline evidence hash"
    )
    for key in ("end_to_end_seconds", "odds_seconds"):
        number(b[key], key)
    for key in (
        "s3_get_responses",
        "s3_http_attempts_including_retries",
        "download_bytes",
        "return_bytes",
        "effective_cpus",
        "source_workers",
        "reused_fits",
        "new_fits",
    ):
        count(b[key], key)
    require(
        b["effective_cpus"] == e["effective_cpus"]
        and b["source_workers"] == e["source_workers"]
        and comparison["same_cpu_and_worker_counts"] is True,
        "Capacity comparison changed",
    )
    require(
        b["new_fits"] == 0
        and b["reused_fits"] == e["research_fits_reused"] + e["science_fits_reused"]
        and b["source_closure_complete"] is False
        and comparison["same_scientific_result"] is True,
        "Different work cannot be called the same replay",
    )
    require(comparison["one_time_cleanup_in_current_duration"] is True, "Cleanup cost omitted")
    require(
        comparison["provider_latency_and_background_load_controlled"] is False,
        "Observed conditions were not controlled",
    )
    fields(
        comparison["reduction_percent"],
        "end_to_end_seconds odds_seconds s3_get_responses s3_http_attempts_including_retries "
        "download_bytes return_bytes",
        "Performance deltas",
    )
    for key, current in comparison_values(d).items():
        require(b[key] > 0, "Missing positive comparison denominator")
        reduction = comparison["reduction_percent"][key]
        require(
            type(reduction) in (int, float) and math.isfinite(reduction) and reduction <= 100,
            "Invalid signed reduction: " + key,
        )
        require(
            math.isclose(reduction, 100 * (b[key] - current) / b[key], abs_tol=1e-9),
            "Wrong reduction denominator or interval: " + key,
        )


def validate_transitions(d: dict) -> None:
    """A repaired decoder does not establish source interpretation or admission."""
    t = d["source_transition"]
    fields(
        t,
        "prior_negative_objects prior_hash_mismatch_objects decoder_change_reinspections "
        "remaining_negative_objects remaining_prior_hash_mismatch_keys "
        "unchanged_other_failure_keys_and_body_hashes "
        "all_former_failures_semantically_resolved complete_positive_catalog_public "
        "representative_diagnostic_reads",
        "Source transition",
    )
    for key, value in t.items():
        if key not in {
            "all_former_failures_semantically_resolved",
            "complete_positive_catalog_public",
        }:
            count(value, key)
    require(
        t["prior_hash_mismatch_objects"] + t["unchanged_other_failure_keys_and_body_hashes"]
        == t["prior_negative_objects"]
        == t["decoder_change_reinspections"],
        "Decoder reinspection population",
    )
    require(
        t["remaining_negative_objects"]
        == d["systems"]["adapter_unresolved_objects"]
        == t["unchanged_other_failure_keys_and_body_hashes"],
        "Remaining decode failure population",
    )
    require(t["remaining_prior_hash_mismatch_keys"] == 0, "Hash failure transition changed")
    require(
        d["systems"]["adapter_error_reasons"]["CONTENT_ADDRESSED_OBJECT_HASH_MISMATCH"] == 0,
        "Current hash failure count disagrees",
    )
    require(
        t["all_former_failures_semantically_resolved"] is False
        and t["complete_positive_catalog_public"] is False,
        "Decode success cannot claim full semantic source closure",
    )


def validate_execution_ledger(d: dict) -> None:
    """Count whole invocations once; keep phases and reported historical totals separate."""
    ledger = d["execution_ledger"]
    fields(
        ledger,
        "scope deduplication records counts latest_delta latest_completed_workstreams "
        "latest_incomplete_workstreams historical_snapshot all_time_totals",
        "Execution ledger",
    )
    require(
        ledger["scope"] == "TEN_IDENTIFIED_OWNER_INVOCATIONS_V340_THROUGH_V349"
        and ledger["deduplication"] == "ONE_RECORD_PER_AUTHENTICATED_INVOCATION",
        "Ledger scope or deduplication changed",
    )
    require(type(ledger["records"]) is list and len(ledger["records"]) == 10, "Ledger population")
    labels, identities = set(), set()
    actual = dict.fromkeys(("SUCCESS", "PARTIAL", "FAILED", "STOPPED"), 0)
    for row in ledger["records"]:
        fields(row, "execution invocation_digest status evidence_level evidence_sha256", "Run")
        require(row["execution"] not in labels, "Duplicate execution label")
        require(row["invocation_digest"] not in identities, "Duplicate owner invocation")
        labels.add(row["execution"])
        identities.add(row["invocation_digest"])
        require(row["status"] in actual, "Unknown terminal owner status")
        actual[row["status"]] += 1
        for key in ("invocation_digest", "evidence_sha256"):
            require(re.fullmatch(r"[a-f0-9]{64}", row[key]) is not None, "Run evidence hash")
        require(
            row["evidence_level"] in {"VERIFIED_NATIVE_SUMMARY", "CARRIED_OWNER_AUDIT"},
            "Historical evidence tier",
        )
    require(labels == {f"v{i}" for i in range(340, 350)}, "Recent execution scope")
    fields(ledger["counts"], "SUCCESS PARTIAL FAILED STOPPED", "Run counts")
    for key, value in ledger["counts"].items():
        count(value, key)
    require(ledger["counts"] == actual, "Whole-run counts disagree with unique invocations")
    fields(ledger["latest_delta"], "SUCCESS PARTIAL FAILED STOPPED", "Latest run delta")
    for key, value in ledger["latest_delta"].items():
        count(value, key)
    require(
        ledger["latest_delta"] == {"SUCCESS": 0, "PARTIAL": 1, "FAILED": 0, "STOPPED": 0},
        "Latest partial run counted as success or multiple invocations",
    )
    latest = next(row for row in ledger["records"] if row["execution"] == d["execution"])
    require(latest["status"] == d["status"], "Ledger latest status disagrees")
    require(
        ledger["latest_completed_workstreams"] == ["lineage", "research", "science"]
        and ledger["latest_incomplete_workstreams"] == ["odds"],
        "Workstream and whole-run outcomes confused",
    )
    require(ledger["all_time_totals"] is None, "Unknown complete history cannot become totals")
    historical = ledger["historical_snapshot"]
    fields(
        historical,
        "execution as_of_date summary_sha256 counters reported_not_reconstructed "
        "categories_overlap intermediate_history_incomplete",
        "Historical snapshot",
    )
    require(
        historical["execution"] == "v48" and historical["as_of_date"] == "2026-10-03",
        "Historical snapshot scope",
    )
    require(re.fullmatch(r"[a-f0-9]{64}", historical["summary_sha256"]), "Snapshot evidence hash")
    require(
        historical["reported_not_reconstructed"] is True
        and historical["categories_overlap"] is True
        and historical["intermediate_history_incomplete"] is True,
        "Historical aggregate counts misrepresented as reconstructed totals",
    )
    fields(
        historical["counters"],
        "successful_intended engineering_failures source_blocked valid_negative_experiments "
        "substantive_successes submission_failures",
        "Historical counters",
    )
    for key, value in historical["counters"].items():
        count(value, key)


def comparison_values(d: dict) -> dict:
    e, systems = d["execution_accounting"], d["systems"]
    return {
        "end_to_end_seconds": e["start_to_return_status_seconds"],
        "odds_seconds": systems["odds_seconds"],
        "s3_get_responses": systems["s3_get_responses"],
        "s3_http_attempts_including_retries": systems["s3_http_attempts_including_retries"],
        "download_bytes": systems["download_bytes"],
        "return_bytes": e["return_bytes"],
    }


def comparison_rows(d: dict) -> list[dict]:
    """Expose one arithmetic source for notebook and HTML review tables."""
    validate_replay(d)
    labels = {
        "end_to_end_seconds": ("Start through verified return", "seconds"),
        "odds_seconds": ("Owned market reconciliation", "seconds"),
        "s3_get_responses": ("Odds GET responses", "responses"),
        "s3_http_attempts_including_retries": ("Odds HTTP attempts including retries", "attempts"),
        "download_bytes": ("Odds downloaded bodies", "bytes"),
        "return_bytes": ("Complete uploaded review set", "bytes"),
    }
    return [
        {
            "measure": labels[k][0],
            "unit": labels[k][1],
            "before": d["comparison"]["baseline"][k],
            "after": v,
            "reduction_percent": d["comparison"]["reduction_percent"][k],
        }
        for k, v in comparison_values(d).items()
    ]


def load_replay(path: Path = REPLAY) -> dict:
    return validate_replay(json.loads(path.read_text()))


def render_replay_panel(d: dict) -> str:
    validate_replay(d)
    e, c = d["execution_accounting"], d["cohort"]
    cards = "".join(
        "<tr><th scope='row'>"
        + html.escape(row["arm"])
        + "</th>"
        + f"<td>{row['development_brier']:.7f}</td><td>{row['later_brier']:.7f}</td></tr>"
        for row in d["scorecards"]
    )
    gaps = "".join(
        f"<tr><th scope='row'>{html.escape(row['family'])}</th>"
        f"<td>{row['have']:,} / {row['required']:,}</td><td>{row['missing']:,}</td>"
        f"<td>{html.escape(row['unit'].replace('_', ' '))}</td></tr>"
        for row in d["coverage"]["residuals"]
    )

    def measured(value, unit):
        return f"{value:,.2f}" if unit == "seconds" else f"{value:,}"

    changes = "".join(
        f"<tr><th scope='row'>{html.escape(row['measure'])}</th>"
        f"<td>{measured(row['before'], row['unit'])}</td>"
        f"<td>{measured(row['after'], row['unit'])}</td>"
        f"<td>{row['reduction_percent']:.2f}%</td><td>{row['unit']}</td></tr>"
        for row in comparison_rows(d)
    )
    storage = d["storage"]
    transition, ledger = d["source_transition"], d["execution_ledger"]
    outcomes = "".join(
        f"<tr><th scope='row'>{row['execution']}</th><td>{row['status']}</td>"
        f"<td>{row['evidence_level'].replace('_', ' ').lower()}</td></tr>"
        for row in ledger["records"]
    )
    return f"""<section id="owner-replay" class="replay-panel" aria-labelledby="replay-title">
<div class="eyebrow">Private run aggregates · reviewed {html.escape(d["reviewed_on"])}</div>
<h2 id="replay-title">Completed work should survive the next run.</h2>
<p><strong>{html.escape(d["execution"])}: {html.escape(d["status"])}.</strong>
Research and science replay completed. Owned market-source reconciliation remains open.
The public checks below validate aggregate consistency; private bodies stay private.</p>
<div class="grid"><article><span>Verified fit reuse</span>
<strong>{e["research_fits_reused"] + e["science_fits_reused"]}</strong>
<span>{e["new_model_fits"]} new fits; {e["new_submissions"]} new submissions.</span></article>
<article><span>Matched research games</span><strong>{c["total_games"]}</strong>
<span>{c["arms"]} arms; {c["prediction_rows"]:,} probability rows.</span></article>
<article><span>Free disk after packaging</span>
<strong>{e["final_free_disk_bytes"] / 1e9:.2f} GB</strong>
<span>Historical run measurement; current free space is not established.</span></article></div>
<h3>Measured progress with remaining bottlenecks.</h3>
<div class="replay-table" tabindex="0" role="region" aria-label="Performance comparison">
<table><caption>Sequential owner runs with the same four CPUs,
eight source workers and 302 reused fitted operations. Source reinspection work differed.
Negative reductions mean an increase. Values keep their stated units.
Scroll horizontally to see all columns on narrow screens.</caption>
<thead><tr><th>Measure</th><th>{d["comparison"]["baseline"]["execution"]}</th>
<th>{d["execution"]}</th><th>Reduction</th><th>Unit</th></tr></thead><tbody>{changes}</tbody></table></div>
<p>Observed savings include one-time cleanup. Provider latency and background load were
not controlled. Odds request counts exclude historical-delivery archival transfers.
This is not proof of the fastest configuration.</p>
<p><strong>{storage["total_allocated_bytes_released"] / 1e9:.3f} GB of allocated disk
released.</strong>
{storage["archived_deliveries"]} old delivery files were released after full body and
restoration-manifest readback. Removing {storage["cache_files_removed"]} reproducible cache
files released {storage["cache_allocated_bytes_released"]:,} allocated bytes;
{storage["unmanifested_cache_extras_preserved"]} unmanifested additions were preserved.
{storage["consolidated_history_files"]} files from
{storage["consolidated_history_roots"]} history folders moved without copying;
those moves claim zero released bytes.
Net free-space change is a separate measurement from verified released blocks.</p>
<h3>A repaired reader is not a completed source inventory.</h3>
<p>{transition["decoder_change_reinspections"]:,} prior negative objects were reinspected.
The {transition["prior_hash_mismatch_objects"]:,} former hash-failure keys are absent from
the new negative ledger; {transition["remaining_negative_objects"]} other deterministic
decode failures remain. The complete positive catalog is withheld, so no per-object semantic
resolution claim is made. Broader unknown owned containers remain
{d["market"]["unknown_owned_containers"]:,}; market training admissions remain zero.</p>
<h3>Count the incomplete run as incomplete.</h3>
<p>V349 adds one PARTIAL owner outcome and zero overall successes.
Three completed workstreams do not become three successful owner invocations.
The ten identified V340–V349 runs contain {ledger["counts"]["SUCCESS"]} SUCCESS,
{ledger["counts"]["PARTIAL"]} PARTIAL, {ledger["counts"]["FAILED"]} FAILED and
{ledger["counts"]["STOPPED"]} STOPPED statuses. This is a scoped history, not all-time totals.</p>
<details><summary>Inspect the deduplicated recent run ledger</summary>
<div class="replay-table" tabindex="0" role="region" aria-label="Recent owner execution ledger">
<table><caption>One record per authenticated invocation; technical FAILED remains distinct
from incomplete PARTIAL and resource/operational STOPPED outcomes.</caption>
<thead><tr><th>Execution</th><th>Recorded status</th><th>Evidence tier</th></tr></thead>
<tbody>{outcomes}</tbody></table></div>
<p>The older V48 snapshot reports 74 successful intended executions, 36 engineering failures,
16 source-blocked outcomes, 46 valid negative experiments, 23 substantive successes and one
submission failure. These categories overlap. Missing intermediate history prevents an
exact updated all-time total; the historical aggregate is not relabeled a reconstructed ledger.</p>
</details>
<h3>A negative result is a model-selection result.</h3>
<p>The accepted control remains selected. Every challenger worsens the declared development
Brier. The later window was already examined; it cannot support a fresh-holdout claim.</p>
<div class="replay-table" tabindex="0" role="region" aria-label="Matched research scorecards">
<table><caption>Lower Brier is better.
Every arm uses the same physical-game population.</caption>
<thead><tr><th>Public arm label</th><th>Development · {c["development_games"]} games</th>
<th>Exposed later · {c["later_games"]} games</th></tr></thead><tbody>{cards}</tbody></table></div>
<p>Challenger labels omit private recipes. Aggregate scores do not reproduce private training.
No paired uncertainty can be recomputed publicly without per-game errors, so this table makes
no significance or prospective-superiority claim.</p>
<details><summary>Inspect remaining data gaps and runtime accounting</summary>
<p>The defined 2013–2025 study has its required detailed inputs. Broader source coverage remains
incomplete. The following carried counts are not a fresh raw-table census.</p>
<div class="replay-table" tabindex="0" role="region" aria-label="Remaining coverage gaps">
<table><thead><tr><th>Evidence family</th><th>Have / required</th>
<th>Missing</th><th>Unit</th></tr></thead><tbody>{gaps}</tbody></table></div>
<p>Market inventory: {d["market"]["selection_records"]:,} selection records;
{d["market"]["training_admissions"]} model admissions. Quote selections are not distinct games.
{d["market"]["unknown_owned_containers"]:,} owned containers remain unresolved.</p>
<p>Core work: {e["coordinator_seconds"]:.2f} seconds; recorded start through return status:
{e["start_to_return_status_seconds"]:.2f} seconds. Mean CPU use:
{e["mean_cpu_cores_used"]:.3f} of {e["effective_cpus"]} effective cores.
This is an observation, not proof of the fastest configuration.</p>
<p>The compact return contains {e["return_bytes"] / 1e6:.2f} MB of current review evidence.
Bulk market parts and the active database remain on the owner system and are explicitly
listed as omissions. Two current negative parse checkpoints remain;
zero negative-cache hits occurred in this decoder-change pass. Legacy inventory took
{d["systems"]["phase_seconds"]["legacy_request_inventory"]:.2f} seconds and baseline price
restoration took {d["systems"]["phase_seconds"]["baseline_price_restoration"]:.2f} seconds.
Uninterpreted sources remain unresolved.
Historical folders still require custody-aware consolidation.</p></details></section>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.parse_args()
    d = load_replay()
    print(
        json.dumps(
            {"status": "PASS", "execution": d["execution"], "scope": d["provenance"]["check_scope"]}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
