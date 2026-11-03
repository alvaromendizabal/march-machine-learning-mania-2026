"""Adversarial checks for public source-custody claims and publication scope."""

import copy
import unittest

from source_readiness import load_source_readiness, render_source_panel, validate_source_readiness


class SourceReadinessTests(unittest.TestCase):
    def setUp(self):
        self.data = load_source_readiness()

    def reject(self, section, key, value):
        changed = copy.deepcopy(self.data)
        changed[section][key] = value
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


if __name__ == "__main__":
    unittest.main()
