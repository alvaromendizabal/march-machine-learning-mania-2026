"""Adversarial checks for public source-custody claims and publication scope."""

import copy
import unittest

from source_readiness import load_source_readiness, render_source_panel, validate_source_readiness


def paths(value, prefix=()):
    """Visit every nested object without trusting a handpicked privacy case."""
    yield prefix, value
    children = (
        value.items()
        if isinstance(value, dict)
        else enumerate(value)
        if isinstance(value, list)
        else []
    )
    for key, child in children:
        yield from paths(child, prefix + (key,))


class SourceReadinessTests(unittest.TestCase):
    def setUp(self):
        self.data = load_source_readiness()

    def reject(self, section, key, value):
        changed = copy.deepcopy(self.data)
        changed[section][key] = value
        with self.assertRaises(ValueError):
            validate_source_readiness(changed)

    def reject_path(self, path, value):
        changed = copy.deepcopy(self.data)
        target = changed
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        with self.assertRaises(ValueError):
            validate_source_readiness(changed)

    def test_exact_public_population(self):
        self.assertEqual(self.data["source_audit"]["complete_bodies_verified"], 67)
        self.assertEqual(self.data["source_audit"]["unresolved_requests"], 3573)

    def test_private_extra_field_fails_closed(self):
        self.reject("source_audit", "private_location", "must-not-pass")

    def test_no_automatic_debt_closure(self):
        self.reject("source_audit", "new_debt_closures", 67)

    def test_no_feature_admission(self):
        self.reject("source_audit", "historical_features_admitted", 1)

    def test_reuse_is_not_new_content(self):
        self.reject("source_audit", "distinct_interpretations_completed", 66)

    def test_schema_only_not_rows(self):
        self.reject("interpretation", "schema_recognition_is_row_interpretation", True)

    def test_archive_text_not_marked_semantically_complete(self):
        self.reject("source_audit", "zip_text_members_semantically_uninspected", 0)

    def test_retrieval_time_not_source_availability(self):
        self.reject("interpretation", "retrieval_time_is_historical_availability", True)

    def test_no_new_private_fit(self):
        self.reject("source_audit", "new_private_model_fits", 1)

    def test_bool_is_not_count(self):
        self.reject("source_audit", "interpretation_errors", True)

    def test_stale_census_not_fresh(self):
        self.reject("source_audit", "metadata_is_current_census", True)

    def test_snapshot_record_receipt_closure(self):
        self.reject("source_audit", "metadata_snapshot_receipts", 90885)

    def test_cost_unknown_not_free(self):
        self.reject("resources", "aws_cost", 0)

    def test_timings_are_nested(self):
        self.reject("resources", "total_seconds_from_live_log", 20)

    def test_later_disk_not_embedded_in_earlier_archive(self):
        self.reject("resources", "postwrite_observations_are_outside_sealed_return", False)

    def test_feature_population_is_not_scoring_population(self):
        self.reject("matched_replay", "games", 218)

    def test_no_exposed_holdout(self):
        self.reject("matched_replay", "untouched_holdout", True)

    def test_no_score_selected_promotion(self):
        self.reject("matched_replay", "accepted_control_changed", True)

    def test_no_private_prediction_rows(self):
        scores = copy.deepcopy(self.data["matched_replay"]["aggregate_scores"])
        scores[0]["predictions"] = [0.5]
        self.reject("matched_replay", "aggregate_scores", scores)

    def test_no_nonfinite_log_loss(self):
        scores = copy.deepcopy(self.data["matched_replay"]["aggregate_scores"])
        scores[0]["log_loss"] = float("nan")
        self.reject("matched_replay", "aggregate_scores", scores)

    def test_no_complete_provider_claim(self):
        self.reject("coverage", "all_provider_data_acquired", True)

    def test_no_invented_global_fit_count(self):
        self.reject("interpretation", "all_time_fit_total", 344)

    def test_public_panel_preserves_limits(self):
        page = render_source_panel(self.data)
        for phrase in ("PARTIAL", "0/5", "not a new Kaggle score", "private rows"):
            self.assertIn(phrase, page)
        self.assertNotIn("s3://", page)

    def test_history_and_followup_are_distinct(self):
        self.assertEqual(self.data["schema_version"], 2)
        self.assertEqual((self.data["execution"], self.data["status"]), ("V019", "PARTIAL"))
        followup = self.data["latest_followup"]
        self.assertEqual(followup["execution"], "V020")
        self.assertEqual(followup["parent_execution"], "V019")
        self.assertEqual(followup["complete_format_or_row_inspections"], 2)
        self.assertEqual(self.data["source_audit"]["payload_uninterpreted"], 1)
        self.assertEqual(self.data["source_audit"]["parquet_schema_only"], 1)

    def test_followup_does_not_relabel_parent_success(self):
        self.reject_path(("status",), "SUCCESS")

    def test_all_recursive_objects_reject_unknown_fields(self):
        for path, value in paths(self.data):
            if isinstance(value, dict):
                with self.subTest(path=path):
                    changed = copy.deepcopy(self.data)
                    target = changed
                    for key in path:
                        target = target[key]
                    target["private_location"] = "PRIVATE_SOURCE_LOCATOR_NOT_FOR_PUBLICATION"
                    with self.assertRaises(ValueError):
                        validate_source_readiness(changed)

    def test_all_recursive_objects_require_every_field(self):
        for path, value in paths(self.data):
            if isinstance(value, dict):
                for missing in value:
                    with self.subTest(path=path, missing=missing):
                        changed = copy.deepcopy(self.data)
                        target = changed
                        for key in path:
                            target = target[key]
                        del target[missing]
                        with self.assertRaises(ValueError):
                            validate_source_readiness(changed)

    def test_all_count_leaves_reject_bool_fraction_and_drift(self):
        for path, value in paths(self.data):
            if type(value) is int:
                for bad in (True, value + 0.5, value + 1):
                    with self.subTest(path=path, bad=bad):
                        self.reject_path(path, bad)

    def test_all_float_leaves_reject_nonfinite_and_drift(self):
        for path, value in paths(self.data):
            if type(value) is float:
                for bad in (float("nan"), float("inf"), -float("inf"), value + 0.01):
                    with self.subTest(path=path, bad=bad):
                        self.reject_path(path, bad)

    def test_all_boolean_boundaries_reject_inversion_and_integer(self):
        for path, value in paths(self.data):
            if type(value) is bool:
                for bad in (not value, int(value)):
                    with self.subTest(path=path, bad=bad):
                        self.reject_path(path, bad)

    def test_all_text_leaves_reject_unregistered_private_content(self):
        for path, value in paths(self.data):
            if isinstance(value, str):
                with self.subTest(path=path):
                    self.reject_path(path, "PRIVATE_SOURCE_LOCATOR_NOT_FOR_PUBLICATION")

    def test_csv_records_not_unique_games_or_physical_lines(self):
        self.reject_path(("latest_followup", "csv", "records"), 15982)
        self.reject_path(("latest_followup", "csv", "unique_physical_games_proven"), True)

    def test_real_columns_not_container_visitor_counts(self):
        self.assertEqual(self.data["latest_followup"]["csv"]["columns"], 96)
        self.assertEqual(self.data["latest_followup"]["parquet"]["columns"], 83)
        self.reject_path(("latest_followup", "csv", "columns"), 97)
        self.reject_path(("latest_followup", "parquet", "columns"), 84)

    def test_candidate_season_is_not_historical_training_population(self):
        self.reject_path(("latest_followup", "parquet", "season_candidates"), {"2025": 1629})

    def test_event_year_histograms_cannot_be_timezone_normalized_by_assumption(self):
        self.reject_path(
            ("latest_followup", "parquet", "event_years_as_stored", "game_date_time"),
            {"2026": 636, "2027": 993},
        )
        self.reject_path(
            ("latest_followup", "parquet", "event_year_basis"),
            "UTC_NORMALIZED_FEATURE_AVAILABILITY",
        )

    def test_null_urls_do_not_prove_provider_or_sport(self):
        self.assertEqual(self.data["latest_followup"]["parquet"]["game_json_url_null"], 1629)
        self.reject_path(("latest_followup", "parquet", "provider_host_candidates"), 1)
        self.reject_path(("latest_followup", "parquet", "sport_token_candidates"), 1)

    def test_boolean_presence_not_source_body_custody(self):
        self.reject_path(
            ("latest_followup", "parquet", "presence_is_not_underlying_body_custody"), False
        )
        self.reject_path(
            ("latest_followup", "parquet", "boolean_presence_fields"), ["verified_JSON_body"]
        )

    def test_complete_diagnostics_do_not_admit_features_or_close_debt(self):
        for key in ("new_debt_closures", "new_historical_features", "new_private_model_fits"):
            with self.subTest(key=key):
                self.reject_path(("latest_followup", key), 1)
        self.assertEqual(self.data["latest_followup"]["unresolved_objects"], 67)
        self.assertEqual(self.data["latest_followup"]["unresolved_requests"], 3573)

    def test_followup_resource_scope_is_exact_not_cumulative(self):
        self.reject_path(("latest_followup", "resources", "head_calls"), 71)
        self.reject_path(("latest_followup", "resources", "verified_stored_bytes"), 191679544)
        self.reject_path(
            ("latest_followup", "resources", "source_body_strategy"), "FOUR_PARALLEL_WORKERS"
        )

    def test_followup_timing_and_live_log_scope(self):
        self.reject_path(
            ("latest_followup", "resources", "source_audit_seconds"), 11.786151601999961
        )
        self.reject_path(
            ("latest_followup", "resources", "postwrite_observations_are_outside_sealed_return"),
            False,
        )
        self.reject_path(("latest_followup", "resources", "aws_cost"), "FREE")

    def test_followup_never_requests_another_source_retry(self):
        self.reject_path(("latest_followup", "next_action"), "REPEAT_COMPLETE_SOURCE_AUDIT")
        self.assertFalse(self.data["latest_followup"]["metadata_snapshot_reread"])

    def test_renderer_displays_latest_scope_and_preserved_history(self):
        page = render_source_panel(self.data)
        for phrase in (
            "V020 completed",
            "2 / 2 bounded source diagnostics",
            "2,283 records",
            "96 columns",
            "1,629 rows",
            "83 columns",
            "season values are 2027",
            "presence fields are booleans",
            "Preserved V019 history",
            "not relabel the earlier run",
            "zero-source-read",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, page)
        self.assertNotIn("The next private task targets only the failed payload", page)


if __name__ == "__main__":
    unittest.main()
