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
        self.assertEqual(self.replay["storage"]["cache_allocated_bytes_released"], 0)
        self.reject("storage", "cache_allocated_bytes_released", 1)

    def test_written_negative_cache_is_not_a_cache_hit_or_source_resolution(self):
        self.assertEqual(self.replay["systems"]["negative_cache_hits"], 0)
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
        self.assertTrue(all(r["before"] > r["after"] for r in rows))
        self.assertTrue(
            all(set(r) == {"measure", "unit", "before", "after", "reduction_percent"} for r in rows)
        )


if __name__ == "__main__":
    unittest.main()
