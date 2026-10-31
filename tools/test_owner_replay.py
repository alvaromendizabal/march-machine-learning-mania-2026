"""Guard the scientific and storage claims made by public owner-run aggregates."""

import copy
import unittest

from owner_replay import comparison_rows, load_replay, render_replay_panel, validate_replay


class OwnerReplayTests(unittest.TestCase):
    def setUp(self):
        self.replay = load_replay()

    def reject(self, group, key, value):
        changed = copy.deepcopy(self.replay)
        changed[group][key] = value
        with self.assertRaises(ValueError):
            validate_replay(changed)

    def test_current_cohort_and_fits(self):
        self.assertEqual(self.replay["cohort"]["total_games"], 925)
        e = self.replay["execution_accounting"]
        self.assertEqual(e["research_fits_reused"] + e["science_fits_reused"], 302)

    def test_selection_uses_development_not_exposed_window(self):
        rows = self.replay["scorecards"]
        self.assertTrue(
            all(r["development_brier"] > rows[0]["development_brier"] for r in rows[1:])
        )
        self.assertTrue(all(r["later_brier"] < rows[0]["later_brier"] for r in rows[1:]))
        self.reject("decision", "selected_arm", "Challenger A")

    def test_no_fresh_holdout_after_replay(self):
        self.reject("cohort", "fresh_holdout", True)

    def test_no_cross_window_season_leakage(self):
        self.reject("cohort", "later_seasons", [2022, 2023, 2024, 2025])

    def test_probability_rows_are_not_game_denominator(self):
        self.reject("cohort", "total_games", 3700)

    def test_cohort_must_be_identical_for_each_arm(self):
        self.reject("cohort", "identical_arm_populations_verified", False)

    def test_bool_not_count(self):
        self.reject("execution_accounting", "new_model_fits", False)

    def test_nonfinite_metric_rejected(self):
        self.replay["scorecards"][1]["development_brier"] = float("nan")
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_development_decision_must_match_values(self):
        self.replay["scorecards"][1]["development_brier"] = 0.1
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_part_boundary_is_exclusive(self):
        self.replay["provenance"]["return_parts"][0]["bytes"] = 150_000_000
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_duplicate_part_and_identity_rejected(self):
        self.replay["provenance"]["return_parts"].append(
            self.replay["provenance"]["return_parts"][0]
        )
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_return_sum_and_bulk_partition(self):
        self.reject("execution_accounting", "return_bytes", 1000)
        self.reject("execution_accounting", "bulk_derived_bytes_in_return", 999_999_999)

    def test_logical_and_allocated_bytes_are_distinct(self):
        e = self.replay["execution_accounting"]
        self.assertNotEqual(
            e["old_return_source_bytes_preserved"], e["old_return_allocated_bytes_released"]
        )
        validate_replay(self.replay)

    def test_source_count_does_not_admit_market_features(self):
        self.reject("market", "training_admissions", 17_012_534)
        self.reject("market", "source_closure_complete", True)

    def test_incomplete_inventory_blocks_paid_eligibility(self):
        self.reject("market", "eligible_paid_requests", 1)
        self.reject("market", "unresolved_requests", 0)

    def test_carried_detail_does_not_complete_broader_inventory(self):
        self.reject("coverage", "broader_project_data_complete", True)
        self.reject("coverage", "future_2027_data_complete", True)

    def test_private_nested_fields_are_rejected(self):
        self.reject("execution_accounting", "private_path", "/home/owner/private")
        self.reject("provenance", "raw_source_data_public", True)

    def test_private_locator_in_free_text_rejected(self):
        self.replay["coverage"]["residuals"][0]["family"] = "s3://private/example"
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_html_escapes_untrusted_labels_and_preserves_scopes(self):
        self.replay["coverage"]["residuals"][0]["family"] = "<script>alert(1)</script>"
        rendered = render_replay_panel(self.replay)
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("Exposed later · 402 games", rendered)
        self.assertIn("not proof of the fastest configuration", rendered)

    def test_observed_comparison_cannot_claim_controlled_or_optimal(self):
        self.reject("systems", "fastest_possible_proven", True)
        self.reject("comparison", "provider_latency_and_background_load_controlled", True)
        self.reject("systems", "measurement", "CONTROLLED_BENCHMARK")

    def test_all_derived_reductions_use_prior_value_denominator(self):
        for key in self.replay["comparison"]["reduction_percent"]:
            with self.subTest(metric=key):
                changed = copy.deepcopy(self.replay)
                changed["comparison"]["reduction_percent"][key] += 0.1
                with self.assertRaises(ValueError):
                    validate_replay(changed)

    def test_changed_hardware_or_training_is_not_equal_work(self):
        for key, value in (("effective_cpus", 8), ("source_workers", 16), ("new_fits", 1)):
            with self.subTest(field=key):
                changed = copy.deepcopy(self.replay)
                changed["comparison"]["baseline"][key] = value
                with self.assertRaises(ValueError):
                    validate_replay(changed)

    def test_physically_released_blocks_are_not_net_disk_change(self):
        s = self.replay["storage"]
        self.assertNotEqual(s["total_allocated_bytes_released"], s["net_free_increase_bytes"])
        self.reject("storage", "total_allocated_bytes_released", s["net_free_increase_bytes"])
        self.reject("storage", "net_free_increase_bytes", s["total_allocated_bytes_released"])

    def test_readback_is_required_before_lossless_cleanup_claim(self):
        self.reject("storage", "verified_remote_body_and_manifest_readback", False)
        self.reject("storage", "unique_scientific_bytes_discarded", 1)
        self.reject("storage", "all_historical_work_folders_removed", True)

    def test_hardlink_alias_removal_does_not_count_as_new_physical_savings(self):
        self.assertGreater(self.replay["storage"]["cache_files_removed"], 0)
        self.assertEqual(self.replay["storage"]["cache_allocated_bytes_released"], 117_338_112)
        self.reject("storage", "cache_allocated_bytes_released", 1)
        self.assertEqual(self.replay["storage"]["unmanifested_cache_extras_preserved"], 0)

    def test_written_negative_cache_is_not_a_cache_hit_or_source_resolution(self):
        self.assertEqual(self.replay["systems"]["negative_cache_hits"], 2)
        self.assertEqual(self.replay["systems"]["negative_cache_entries_written"], 0)
        self.reject("systems", "negative_cache_hits", 7700)
        self.reject("systems", "adapter_unresolved_objects", 0)
        self.reject("market", "unknown_owned_containers", 0)

    def test_error_reasons_reconcile_without_claiming_complete_inventory(self):
        self.replay["systems"]["adapter_error_reasons"][
            "CONTENT_ADDRESSED_OBJECT_HASH_MISMATCH"
        ] -= 1
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_http_scope_and_retry_accounting_are_preserved(self):
        self.reject("systems", "s3_http_attempts_including_retries", 7700)
        self.reject("systems", "request_scope", "ALL_AWS_TRAFFIC")

    def test_phase_intervals_do_not_exceed_measured_worker(self):
        self.replay["systems"]["phase_seconds"]["legacy_request_inventory"] = 999
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_public_comparison_rows_include_units_and_no_raw_records(self):
        rows = comparison_rows(self.replay)
        self.assertEqual(len(rows), 6)
        self.assertEqual({r["unit"] for r in rows}, {"bytes", "seconds", "attempts", "responses"})
        self.assertTrue(any(r["before"] > r["after"] for r in rows))
        self.assertTrue(any(r["before"] < r["after"] for r in rows))
        self.assertTrue(
            all(set(r) == {"measure", "unit", "before", "after", "reduction_percent"} for r in rows)
        )

    def test_increased_work_is_a_negative_reduction_not_hidden_improvement(self):
        changes = self.replay["comparison"]["reduction_percent"]
        self.assertGreater(changes["odds_seconds"], 0)
        self.assertLess(changes["download_bytes"], 0)
        self.assertLess(changes["end_to_end_seconds"], 0)
        changes["end_to_end_seconds"] = abs(changes["end_to_end_seconds"])
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_decoder_repair_does_not_prove_semantic_source_resolution(self):
        self.assertEqual(self.replay["source_transition"]["remaining_negative_objects"], 2)
        self.assertEqual(self.replay["market"]["unknown_owned_containers"], 71)
        self.reject("source_transition", "all_former_failures_semantically_resolved", True)
        self.reject("source_transition", "complete_positive_catalog_public", True)

    def test_retry_population_includes_unchanged_non_hash_failures(self):
        self.assertEqual(self.replay["source_transition"]["prior_hash_mismatch_objects"], 7698)
        self.reject("source_transition", "decoder_change_reinspections", 7698)
        self.reject("source_transition", "unchanged_other_failure_keys_and_body_hashes", 0)

    def test_duplicate_invocation_is_not_a_new_owner_run(self):
        rows = self.replay["execution_ledger"]["records"]
        rows[1]["invocation_digest"] = rows[0]["invocation_digest"]
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_phase_success_does_not_increment_whole_run_success(self):
        ledger = self.replay["execution_ledger"]
        self.assertEqual(len(ledger["latest_completed_workstreams"]), 3)
        self.assertEqual(ledger["counts"], {"SUCCESS": 0, "PARTIAL": 8, "FAILED": 0, "STOPPED": 4})
        ledger["counts"]["SUCCESS"] = 3
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_latest_incomplete_run_is_counted_once(self):
        self.reject(
            "execution_ledger",
            "latest_delta",
            {"SUCCESS": 1, "PARTIAL": 1, "FAILED": 0, "STOPPED": 0},
        )

    def test_missing_history_cannot_become_an_all_time_total(self):
        self.reject("execution_ledger", "all_time_totals", {"SUCCESS": 74, "PARTIAL": 6})
        self.replay["execution_ledger"]["historical_snapshot"]["reported_not_reconstructed"] = False
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_historical_categories_must_keep_overlap_and_missing_history(self):
        for key in ("categories_overlap", "intermediate_history_incomplete"):
            with self.subTest(field=key):
                changed = copy.deepcopy(self.replay)
                changed["execution_ledger"]["historical_snapshot"][key] = False
                with self.assertRaises(ValueError):
                    validate_replay(changed)

    def test_current_quotes_cannot_become_historical_training_coverage(self):
        self.assertEqual(self.replay["source_recovery"]["new_current_selection_records"], 0)
        self.assertEqual(self.replay["source_recovery"]["cumulative_product_selection_rows"], 3482)
        self.reject("source_recovery", "new_historical_selection_records", 3482)
        self.reject("source_recovery", "current_rows_have_historical_snapshot", True)
        self.reject("source_recovery", "training_admissions", 3482)

    def test_zero_canonical_rows_do_not_prove_provider_payload_empty(self):
        source = self.replay["source_recovery"]
        self.assertEqual(source["event_bearing_zero_canonical_objects"], 7677)
        self.assertEqual(source["zero_event_objects"], 1)
        self.reject("source_recovery", "provider_empty_payloads_independently_verified", True)
        self.reject("source_recovery", "event_bearing_zero_canonical_objects", 0)

    def test_recovered_objects_are_not_quote_rows_or_general_counter(self):
        self.assertEqual(self.replay["source_recovery"]["product_ledger_objects"], 7707)
        self.reject("source_recovery", "reported_general_recovered_counter", 7707)
        self.reject("source_recovery", "product_ledger_objects", 3482)

    def test_source_recovery_must_match_actual_selection_and_unknown_deltas(self):
        self.reject("source_recovery", "new_selection_records", 3483)
        self.reject("source_recovery", "remaining_unknown_owned_containers", 7774)
        self.reject("source_recovery", "prior_selection_records", 0)

    def test_product_population_cannot_be_duplicated_with_matching_grand_total(self):
        rows = self.replay["source_recovery"]["products"]
        rows[1]["kind"] = rows[0]["kind"]
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_product_current_snapshot_cannot_override_aggregate_disclaimer(self):
        rows = self.replay["source_recovery"]["products"]
        next(r for r in rows if r["kind"] == "CURRENT_SPORT_ODDS")[
            "historical_snapshot_objects"
        ] = 1
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_product_counts_must_reconcile_to_complete_ledger(self):
        self.replay["source_recovery"]["products"][0]["objects"] += 1
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_presentation_links_are_not_physical_moves(self):
        self.assertEqual(self.replay["organization"]["physically_moved"], 472)
        self.reject("organization", "all_presentations_physically_centralized", True)
        self.reject("organization", "physically_moved", 2306)

    def test_census_scope_keeps_home_entries_distinct_from_project_roots(self):
        self.assertEqual(self.replay["organization"]["census_files"], 587969)
        self.assertEqual(self.replay["organization"]["census_root_entries"], 1583)
        self.reject("organization", "census_root_entries", 109)
        self.reject("organization", "census_timing", "AFTER_ALL_CLEANUP_AND_PACKAGING")

    def test_moves_cannot_claim_released_blocks_or_duplicate_full_workspace(self):
        self.reject("organization", "allocated_bytes_released_by_moves", 1)
        self.reject("organization", "data_trees_copied", 1)
        self.reject("organization", "new_full_version_workspaces", 1)

    def test_aggregate_census_is_not_a_complete_feature_or_duplicate_inventory(self):
        self.reject("organization", "full_file_hash_duplicate_inventory_complete", True)
        self.reject("organization", "feature_reproducibility_dependency_manifest_complete", True)

    def test_forced_probes_are_not_hidden_by_sampling_interval(self):
        systems = self.replay["systems"]
        self.assertEqual(systems["forced_resource_probes"], 196)
        self.reject("systems", "forced_resource_probes", systems["resource_probes"] + 1)
        self.reject("systems", "resource_sampling_interval_seconds", 0)

    def test_authenticated_warm_checkpoint_is_not_a_new_full_join(self):
        self.reject("systems", "warm_price_checkpoint_reuse_observed", False)
        self.reject("systems", "price_checkpoint_created", True)
        self.reject("systems", "warm_price_checkpoint_seconds", 31.31)

    def test_cumulative_product_rows_cannot_be_recounted_as_new(self):
        self.reject("source_recovery", "new_current_selection_records", 3482)
        self.reject("source_recovery", "cumulative_product_selection_rows", 0)

    def test_verified_blocker_bodies_do_not_prove_source_closure(self):
        self.reject("source_recovery", "new_blocker_closures", 71)
        self.reject("source_recovery", "verified_blocker_records", 70)

    def test_source_structure_status_counts_cover_every_verified_body(self):
        self.replay["source_recovery"]["diagnostic_status_counts"]["VERIFIED_JSON_STRUCTURE"] += 1
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_complete_metadata_is_not_a_final_post_action_census(self):
        self.reject("organization", "final_post_action_census_available", True)
        self.reject("organization", "current_diagnostic_files_verified", 7)

    def test_complete_census_keeps_file_directory_and_link_denominators(self):
        self.reject("organization", "metadata_records", 587969)
        self.reject("organization", "root_regular_files", 1583)

    def test_duplicate_upper_bound_is_not_released_space(self):
        self.reject("organization", "duplicate_candidate_bytes_released", 4972310528)

    def test_cumulative_notebook_moves_cannot_become_current_progress(self):
        self.reject("organization", "notebook_moves_newly_recorded", 472)
        self.reject("organization", "notebook_counts_are_cumulative", False)

    def test_feature_population_cannot_replace_matched_evaluation_games(self):
        self.reject("organization", "feature_evaluated_games", 1575)

    def test_root_migration_blockers_cannot_be_hidden(self):
        self.reject("organization", "root_migration_blockers", 0)
        self.reject("organization", "physical_historical_roots_moved", 271)

    def test_reused_products_cannot_be_claimed_as_new_acquisition(self):
        self.reject("systems", "product_originals_requeued", 7791)

    def test_historical_decoder_repair_cannot_be_recounted_as_current_work(self):
        self.assertEqual(self.replay["source_transition"]["execution"], "v349")
        self.reject("source_transition", "execution", "v350")

    def test_repository_storage_categories_do_not_exceed_actual_total(self):
        self.replay["organization"]["repository_major_categories"][0]["allocated_bytes"] = (
            self.replay["organization"]["repository_allocated_bytes"]
        )
        with self.assertRaises(ValueError):
            validate_replay(self.replay)

    def test_partial_source_recovery_cannot_disclose_bodies_or_claim_completion(self):
        self.reject("source_recovery", "original_raw_bodies_public", True)
        self.reject("source_recovery", "source_closure_complete", True)


if __name__ == "__main__":
    unittest.main()
