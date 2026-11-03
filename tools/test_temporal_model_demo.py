"""Temporal, numerical, identity and disclosure contracts for the learned public demo."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import math
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "temporal_model_demo", Path(__file__).with_name("temporal_model_demo.py")
)
assert SPEC is not None and SPEC.loader is not None
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


class TemporalModelDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = demo.make_fixture()
        cls.features, cls.feature_audit = demo.build_features(
            cls.fixture["games"], cls.fixture["observations"], cls.fixture["cutoffs_utc"]
        )
        cls.labels = {row["id"]: row for row in cls.fixture["labels"]}
        cls.training = [row for row in cls.features if row["season"] < 2024]
        cls.evaluation = [row for row in cls.features if row["season"] == 2024]
        cls.model = demo.fit_model(
            cls.training,
            [cls.labels[row["id"]] for row in cls.training],
            forecast_at_utc=cls.fixture["cutoffs_utc"]["2024"],
        )
        cls.predictions = demo.predict(cls.model, cls.evaluation)

    def test_authored_fixture_is_deterministic_and_explicitly_synthetic(self):
        self.assertEqual(self.fixture, demo.make_fixture())
        self.assertNotEqual(self.fixture, demo.make_fixture(demo.SEED + 1))
        self.assertEqual(len(self.fixture["games"]), 396)
        self.assertEqual(self.fixture["evidence_scope"], "SYNTHETIC_ONLY")
        self.assertTrue(all(row["id"].startswith("synthetic_") for row in self.fixture["games"]))

    def test_three_real_numerical_fits_are_not_owner_research(self):
        result = demo.run_demo()
        self.assertEqual(result["synthetic_model_fits"], 3)
        self.assertEqual(result["owner_research_fits"], 0)
        self.assertEqual(result["pooled_game_weighted"]["physical_games"], 198)
        self.assertEqual(result["network_requests"], 0)
        self.assertEqual(result["private_artifacts_read"], 0)
        self.assertEqual(
            [fold["evaluation_season"] for fold in result["folds"]], [2024, 2025, 2026]
        )
        self.assertEqual(
            [fold["physical_training_games"] for fold in result["folds"]], [198, 264, 330]
        )

    def test_gradient_optimization_changes_weights_and_reduces_training_objective(self):
        self.assertTrue(any(abs(value) > 1e-6 for value in self.model["coefficients"]))
        optimizer = self.model["optimizer"]
        self.assertEqual(optimizer["iterations_completed"], 250)
        self.assertLess(
            optimizer["training_objective_final"], optimizer["training_objective_initial"]
        )
        self.assertFalse(optimizer["early_stopping_or_evaluation_tuning"])

    def test_scaler_uses_only_training_rows_and_normalizes_mirror_weight(self):
        scaler = self.model["scaler"]
        self.assertEqual(scaler["mean"], [0.0, 0.0, 0.0])
        self.assertEqual(scaler["physical_training_games"], 198)
        self.assertEqual(scaler["augmented_training_rows"], 396)
        self.assertEqual(scaler["weight_per_augmented_row"], 0.5)
        self.assertEqual(scaler["effective_training_game_weight"], 198)
        for index, actual in enumerate(scaler["scale"]):
            expected = math.sqrt(
                math.fsum(row["features"][index] ** 2 for row in self.training) / len(self.training)
            )
            self.assertEqual(actual, expected)

    def test_current_evaluation_features_do_not_change_the_training_transform(self):
        altered = copy.deepcopy(self.evaluation)
        for row in altered:
            row["features"] = [5000.0, -5000.0, 5000.0]
        before = copy.deepcopy(self.model)
        demo.predict(self.model, altered)
        self.assertEqual(self.model, before)

    def test_changing_current_labels_does_not_change_current_fold_predictions(self):
        fixture = copy.deepcopy(self.fixture)
        for label in fixture["labels"]:
            if label["id"].startswith("synthetic_2024_"):
                label["outcome_a"] = 1 - label["outcome_a"]
        changed_labels = {row["id"]: row for row in fixture["labels"]}
        model = demo.fit_model(
            self.training,
            [changed_labels[row["id"]] for row in self.training],
            forecast_at_utc=fixture["cutoffs_utc"]["2024"],
        )
        self.assertEqual(model, self.model)
        self.assertEqual(demo.predict(model, self.evaluation), self.predictions)

    def test_post_cutoff_observations_are_excluded_even_when_influential(self):
        fixture = copy.deepcopy(self.fixture)
        for observation in fixture["observations"]:
            if observation["published_at_utc"][8:10] == "18":
                observation.update(rating=2500, form=-3, rest_days=14)
        features, audit = demo.build_features(
            fixture["games"], fixture["observations"], fixture["cutoffs_utc"]
        )
        self.assertEqual(features, self.features)
        self.assertEqual(audit["excluded_post_cutoff_observations"], 72)
        self.assertEqual(audit["selected_team_season_observations"], 72)

    def test_cutoff_instant_is_eligible_but_one_hour_game_gap_is_required(self):
        fixture = copy.deepcopy(self.fixture)
        fixture["observations"][1]["published_at_utc"] = fixture["cutoffs_utc"]["2021"]
        demo.build_features(fixture["games"], fixture["observations"], fixture["cutoffs_utc"])
        fixture["games"][0]["started_at_utc"] = "2021-03-17T00:59:59Z"
        with self.assertRaisesRegex(ValueError, "precede game by 1h"):
            demo.build_features(fixture["games"], fixture["observations"], fixture["cutoffs_utc"])

    def test_clock_comparison_uses_instant_not_lexical_timestamp_order(self):
        fixture = copy.deepcopy(self.fixture)
        for observation in fixture["observations"]:
            if observation["published_at_utc"] == "2021-03-16T12:00:00Z":
                if observation["team"] == fixture["games"][0]["team_b"]:
                    observation["published_at_utc"] = "2021-03-16T12:00:00.900Z"
        features, _ = demo.build_features(
            fixture["games"], fixture["observations"], fixture["cutoffs_utc"]
        )
        self.assertEqual(features[0]["feature_available_at_utc"], "2021-03-16T12:00:00.900Z")

    def test_missing_pre_cutoff_features_fail_closed(self):
        fixture = copy.deepcopy(self.fixture)
        fixture["observations"] = [
            row
            for row in fixture["observations"]
            if not (
                row["season"] == 2021
                and row["team"] == "FICTIONAL_01"
                and row["published_at_utc"][8:10] != "18"
            )
        ]
        with self.assertRaisesRegex(ValueError, "Missing eligible pre-cutoff"):
            demo.build_features(fixture["games"], fixture["observations"], fixture["cutoffs_utc"])

    def test_training_target_season_overlap_is_rejected(self):
        rows = self.training + self.evaluation[:1]
        with self.assertRaisesRegex(ValueError, "Training season must precede"):
            demo.fit_model(
                rows,
                [self.labels[row["id"]] for row in rows],
                forecast_at_utc=self.fixture["cutoffs_utc"]["2024"],
            )

    def test_training_label_availability_at_or_after_fit_is_rejected(self):
        labels = copy.deepcopy([self.labels[row["id"]] for row in self.training])
        labels[0]["available_at_utc"] = "2024-03-16T23:00:00Z"
        with self.assertRaisesRegex(ValueError, "Training label unavailable"):
            demo.fit_model(
                self.training, labels, forecast_at_utc=self.fixture["cutoffs_utc"]["2024"]
            )

    def test_model_fit_after_forecast_is_rejected(self):
        model = copy.deepcopy(self.model)
        model["fit_completed_at_utc"] = self.fixture["cutoffs_utc"]["2024"]
        with self.assertRaisesRegex(ValueError, "not fitted before forecast"):
            demo.predict(model, self.evaluation)

    def test_inference_cannot_receive_labels_or_post_cutoff_features(self):
        for change in ("label", "clock"):
            rows = copy.deepcopy(self.evaluation)
            if change == "label":
                rows[0]["outcome_a"] = 1
            else:
                rows[0]["feature_available_at_utc"] = "2024-03-17T00:00:01Z"
            with self.subTest(change=change), self.assertRaises(ValueError):
                demo.predict(self.model, rows)

    def test_training_ids_and_seasons_cannot_be_predicted_as_out_of_sample(self):
        with self.assertRaisesRegex(ValueError, "overlap"):
            demo.predict(self.model, self.training)
        model = copy.deepcopy(self.model)
        model["physical_training_ids"].append(self.evaluation[0]["id"])
        with self.assertRaisesRegex(ValueError, "Training ID in evaluation"):
            demo.predict(model, self.evaluation)

    def test_duplicate_ids_and_mirrored_physical_game_aliases_are_rejected(self):
        for swapped in (False, True):
            games = copy.deepcopy(self.fixture["games"])
            duplicate = copy.deepcopy(games[0])
            if swapped:
                duplicate["id"] += "_alias"
                duplicate["team_a"], duplicate["team_b"] = duplicate["team_b"], duplicate["team_a"]
                duplicate["started_at_utc"] = duplicate["started_at_utc"].replace("00Z", "00.000Z")
            games.append(duplicate)
            with self.subTest(swapped=swapped), self.assertRaisesRegex(ValueError, "Duplicate"):
                demo.validate_games(games, self.fixture["cutoffs_utc"])

    def test_duplicate_source_snapshots_are_rejected_including_conflicts(self):
        for different_value in (False, True):
            observations = copy.deepcopy(self.fixture["observations"])
            duplicate = copy.deepcopy(observations[0])
            if different_value:
                duplicate["rating"] += 10
            observations.append(duplicate)
            with (
                self.subTest(conflict=different_value),
                self.assertRaisesRegex(ValueError, "snapshot"),
            ):
                demo.build_features(
                    self.fixture["games"], observations, self.fixture["cutoffs_utc"]
                )

    def test_swapping_teams_complements_predictions_and_retains_scores(self):
        swapped = copy.deepcopy(self.evaluation)
        labels = copy.deepcopy([self.labels[row["id"]] for row in swapped])
        for row in swapped:
            row["team_a"], row["team_b"] = row["team_b"], row["team_a"]
            row["features"] = [-value for value in row["features"]]
        for label in labels:
            label["outcome_a"] = 1 - label["outcome_a"]
        after = demo.predict(self.model, swapped)
        for a, b in zip(self.predictions, after, strict=True):
            self.assertAlmostEqual(a["pred"] + b["pred"], 1, places=14)
        before_score = demo.score(
            self.predictions,
            [self.labels[r["id"]] for r in self.evaluation],
            self.fixture["cutoffs_utc"],
        )
        after_score = demo.score(after, labels, self.fixture["cutoffs_utc"])
        for metric in ("brier", "log_loss", "roc_auc", "accuracy_ties_half_credit"):
            self.assertAlmostEqual(
                before_score["pooled_game_weighted"][metric],
                after_score["pooled_game_weighted"][metric],
                places=14,
            )

    def test_swapping_training_orientation_leaves_the_actual_fit_unchanged(self):
        training = copy.deepcopy(self.training)
        labels = copy.deepcopy([self.labels[row["id"]] for row in training])
        for row in training:
            row["team_a"], row["team_b"] = row["team_b"], row["team_a"]
            row["features"] = [-value for value in row["features"]]
        for label in labels:
            label["outcome_a"] = 1 - label["outcome_a"]
        model = demo.fit_model(
            training, labels, forecast_at_utc=self.fixture["cutoffs_utc"]["2024"]
        )
        self.assertEqual(model["scaler"], self.model["scaler"])
        for a, b in zip(model["coefficients"], self.model["coefficients"], strict=True):
            self.assertAlmostEqual(a, b, places=14)

    def test_invalid_nonfinite_and_boolean_features_fail(self):
        for value in (float("nan"), float("inf"), -float("inf"), True, "2.0"):
            rows = copy.deepcopy(self.evaluation)
            rows[0]["features"][0] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Nonfinite"):
                demo.predict(self.model, rows)

    def test_invalid_excluded_observations_are_not_silently_ignored(self):
        observations = copy.deepcopy(self.fixture["observations"])
        observations[2]["rating"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Nonfinite"):
            demo.build_features(self.fixture["games"], observations, self.fixture["cutoffs_utc"])

    def test_model_shape_scaling_and_finite_coefficients_are_enforced(self):
        for defect in ("weights", "scale", "mean", "intercept", "scope"):
            model = copy.deepcopy(self.model)
            if defect == "weights":
                model["coefficients"][0] = float("nan")
            elif defect == "scale":
                model["scaler"]["scale"][0] = 0
            elif defect == "mean":
                model["scaler"]["mean"][0] = 1
            elif defect == "intercept":
                model["intercept"] = 1
            else:
                model["evidence_scope"] = "REAL"
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                demo.predict(model, self.evaluation)

    def test_zero_variance_features_have_finite_neutral_predictions(self):
        rows = copy.deepcopy(self.training[:8])
        for row in rows:
            row["features"] = [0.0, 0.0, 0.0]
        model = demo.fit_model(
            rows,
            [self.labels[row["id"]] for row in rows],
            forecast_at_utc=self.fixture["cutoffs_utc"]["2024"],
        )
        self.assertEqual(model["scaler"]["scale"], [1.0, 1.0, 1.0])
        self.assertEqual(model["coefficients"], [0.0, 0.0, 0.0])
        self.assertTrue(all(row["pred"] == 0.5 for row in demo.predict(model, self.evaluation)))

    def test_labels_require_exact_ID_closure_binary_values_and_availability(self):
        for defect in ("missing", "extra", "duplicate", "bool", "float", "before_game"):
            labels = copy.deepcopy([self.labels[row["id"]] for row in self.evaluation])
            if defect == "missing":
                labels.pop()
            elif defect == "extra":
                labels[0]["id"] = "synthetic_unregistered"
            elif defect == "duplicate":
                labels.append(labels[0])
            elif defect == "before_game":
                labels[0]["available_at_utc"] = self.evaluation[0]["started_at_utc"]
            else:
                labels[0]["outcome_a"] = True if defect == "bool" else 0.5
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                demo.score(self.predictions, labels, self.fixture["cutoffs_utc"])

    def test_invalid_probabilities_are_rejected_and_endpoints_are_finite(self):
        labels = [self.labels[row["id"]] for row in self.evaluation]
        for value in (float("nan"), float("inf"), True, "0.5", -0.001, 1.001):
            forecasts = copy.deepcopy(self.predictions)
            forecasts[0]["pred"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                demo.score(forecasts, labels, self.fixture["cutoffs_utc"])
        forecasts = [{**row, "pred": index % 2} for index, row in enumerate(self.predictions)]
        result = demo.score(forecasts, labels, self.fixture["cutoffs_utc"])
        self.assertTrue(math.isfinite(result["pooled_game_weighted"]["log_loss"]))
        self.assertEqual(result["log_loss_probability_clip"], 1e-15)

    def test_reference_metrics_ties_and_bin_counts(self):
        forecasts = [{**row, "pred": 0.5} for row in self.predictions]
        result = demo.score(
            forecasts,
            [self.labels[row["id"]] for row in self.evaluation],
            self.fixture["cutoffs_utc"],
        )
        score = result["pooled_game_weighted"]
        self.assertEqual(score["brier"], 0.25)
        self.assertAlmostEqual(score["log_loss"], math.log(2))
        self.assertEqual(score["roc_auc"], 0.5)
        self.assertEqual(score["accuracy_ties_half_credit"], 0.5)
        self.assertEqual(result["reliability"]["bins"][2]["count"], 66)
        self.assertIsNone(result["reliability"]["bins"][0]["mean_prediction"])

    def test_game_weighted_and_equal_season_metrics_are_not_conflated(self):
        rows = [
            *copy.deepcopy(self.predictions[:2]),
            {
                **copy.deepcopy(self.predictions[2]),
                "id": "synthetic_2025_extra",
                "season": 2025,
                "started_at_utc": "2025-03-18T17:00:00Z",
            },
        ]
        labels = []
        for index, row in enumerate(rows):
            row["pred"] = int(index == 2)
            labels.append(
                {
                    "scope": demo.SCOPE,
                    "id": row["id"],
                    "outcome_a": 0,
                    "available_at_utc": row["started_at_utc"].replace("17:", "20:"),
                }
            )
        result = demo.score(rows, labels, self.fixture["cutoffs_utc"])
        self.assertAlmostEqual(result["pooled_game_weighted"]["brier"], 1 / 3)
        self.assertEqual(result["unweighted_mean_season_brier"], 0.5)
        self.assertIsNone(result["pooled_game_weighted"]["roc_auc"])

    def test_bad_times_scope_schema_seed_and_self_match_are_rejected(self):
        for defect in ("timezone", "year", "scope", "self_match", "schema", "seed"):
            fixture = copy.deepcopy(self.fixture)
            if defect == "timezone":
                fixture["observations"][0]["published_at_utc"] = "2021-03-14T12:00:00"
            elif defect == "year":
                fixture["games"][0]["started_at_utc"] = "2022-03-18T17:00:00Z"
            elif defect == "scope":
                fixture["evidence_scope"] = "REAL"
            elif defect == "self_match":
                fixture["games"][0]["team_b"] = fixture["games"][0]["team_a"]
            elif defect == "schema":
                fixture["schema_version"] = True
            else:
                fixture["seed"] = True
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                demo.reproduce(fixture)

    def test_manifest_and_forecast_freeze_pins_cover_exact_artifacts(self):
        files = demo.reproduce(self.fixture)
        self.assertEqual(files, demo.reproduce(self.fixture))
        manifest = json.loads(files["manifest.json"])
        self.assertEqual(set(manifest["payloads"]) | {"manifest.json"}, set(files))
        for name, expected in manifest["payloads"].items():
            self.assertEqual(demo.pin(files[name]), expected)
        evaluation = json.loads(files["evaluation.json"])
        self.assertEqual(
            evaluation["forecast_pin_before_scoring"], demo.pin(files["predictions.json"])
        )
        self.assertEqual(
            evaluation["protocol_pin_before_fitting"], demo.pin(demo.canonical(demo.PROTOCOL))
        )
        self.assertEqual(manifest["generator_pin"], demo.pin(Path(demo.__file__).read_bytes()))

    def test_static_fallback_is_valid_accessible_SVG(self):
        svg = demo.calibration_svg(demo.run_demo())
        root = ET.fromstring(svg)
        self.assertEqual(root.attrib["role"], "img")
        self.assertEqual(root.attrib["aria-labelledby"], "title desc")
        self.assertIn(b"SYNTHETIC ONLY", svg)
        self.assertIn(b"not a calibration guarantee", svg)
        self.assertNotIn(b"<script", svg)

    def test_cli_byte_check_is_read_only_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            arguments = ["--out-dir", directory]
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(demo.main(arguments), 0)
                self.assertEqual(demo.main([*arguments, "--check"]), 0)
                path = Path(directory) / "predictions.json"
                path.write_bytes(path.read_bytes() + b" ")
                before = {p.name: p.read_bytes() for p in Path(directory).iterdir()}
                self.assertEqual(demo.main([*arguments, "--check"]), 1)
                self.assertEqual(
                    before, {p.name: p.read_bytes() for p in Path(directory).iterdir()}
                )

    def test_invalid_seed_fails_before_any_output_is_created(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "not_created"
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(demo.main(["--out-dir", str(destination), "--seed", "-1"]), 1)
            self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
