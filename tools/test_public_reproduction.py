"""Meaningful input, temporal, scoring and artifact checks for the public lab."""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import json
import math
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "public_reproduction", Path(__file__).with_name("reproduce_public.py")
)
assert SPEC is not None and SPEC.loader is not None
lab = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lab)


class PublicReproductionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = lab.make_fixture()

    def forecasts(self):
        return lab.predict(
            self.fixture["games"], self.fixture["observations"], self.fixture["cutoffs_utc"]
        )[0]

    def score(self, forecasts, labels=None):
        return lab.evaluate(
            forecasts,
            self.fixture["labels"] if labels is None else labels,
            self.fixture["cutoffs_utc"],
        )

    def test_seed_and_outputs_are_deterministic(self):
        self.assertEqual(self.fixture, lab.make_fixture())
        self.assertNotEqual(self.fixture, lab.make_fixture(lab.SEED + 1))
        self.assertEqual(lab.reproduce(self.fixture), lab.reproduce(self.fixture))
        self.assertEqual(len(self.fixture["games"]), 88)

    def test_future_observations_are_excluded(self):
        before = self.forecasts()
        for row in self.fixture["observations"]:
            if row["observed_at_utc"][8:10] == "18":
                row["rating"] = 2500
        after, audit = lab.predict(
            self.fixture["games"], self.fixture["observations"], self.fixture["cutoffs_utc"]
        )
        self.assertEqual(before, after)
        self.assertEqual(audit["excluded_post_cutoff_observations"], 32)
        self.assertEqual(audit["selected_team_season_observations"], 32)
        self.assertTrue(
            all(row["observed_at_utc"][8:10] == "16" for row in audit["selected_observations"])
        )

    def test_missing_pre_cutoff_rating_is_rejected(self):
        self.fixture["observations"] = [
            row
            for row in self.fixture["observations"]
            if not (
                row["season"] == 2023
                and row["team"] == "FICTIONAL_01"
                and row["observed_at_utc"][8:10] != "18"
            )
        ]
        with self.assertRaisesRegex(ValueError, "Missing eligible pre-cutoff"):
            self.forecasts()

    def test_exact_cutoff_is_eligible_and_future_game_is_required(self):
        row = self.fixture["observations"][1]
        row["observed_at_utc"] = self.fixture["cutoffs_utc"][str(row["season"])]
        self.forecasts()
        self.fixture["games"][0]["started_at_utc"] = self.fixture["cutoffs_utc"]["2023"]
        with self.assertRaisesRegex(ValueError, "strictly after forecast cutoff"):
            self.forecasts()

    def test_labels_cannot_change_prediction(self):
        before = self.forecasts()
        for row in self.fixture["labels"]:
            row["outcome_a"] = 1 - row["outcome_a"]
        self.assertEqual(before, self.forecasts())
        self.fixture["games"][0]["outcome_a"] = 1
        with self.assertRaisesRegex(ValueError, "Invalid game fields"):
            self.forecasts()

    def test_duplicate_game_ids_and_swapped_physical_games_are_rejected(self):
        for swapped in (False, True):
            with self.subTest(swapped=swapped):
                fixture = lab.make_fixture()
                duplicate = copy.deepcopy(fixture["games"][0])
                if swapped:
                    duplicate["game_id"] += "-alias"
                    a, b = duplicate["team_a"], duplicate["team_b"]
                    duplicate["team_a"], duplicate["team_b"] = b, a
                    duplicate["started_at_utc"] = duplicate["started_at_utc"].replace(
                        "00Z", "00.000Z"
                    )
                fixture["games"].append(duplicate)
                with self.assertRaisesRegex(ValueError, "Duplicate (physical game|game ID)"):
                    lab.reproduce(fixture)

    def test_swapping_teams_complements_predictions_and_preserves_proper_scores(self):
        before = self.forecasts()
        scores = self.score(before)
        for game in self.fixture["games"]:
            game["team_a"], game["team_b"] = game["team_b"], game["team_a"]
        for label in self.fixture["labels"]:
            label["outcome_a"] = 1 - label["outcome_a"]
        after = self.forecasts()
        for a, b in zip(before, after, strict=True):
            self.assertAlmostEqual(a["probability_a"] + b["probability_a"], 1, places=14)
        new_scores = self.score(after)
        for metric in ("brier", "log_loss", "roc_auc"):
            self.assertAlmostEqual(
                scores["pooled_game_weighted"][metric],
                new_scores["pooled_game_weighted"][metric],
                places=14,
            )

    def test_nonfinite_out_of_range_and_boolean_probabilities_are_rejected(self):
        for value in (float("nan"), float("inf"), -0.001, 1.001, True, "0.5"):
            with self.subTest(probability=value):
                rows = self.forecasts()
                rows[0]["probability_a"] = value
                with self.assertRaisesRegex(ValueError, "Probability must be finite"):
                    self.score(rows)

    def test_probability_endpoints_have_documented_finite_log_loss(self):
        rows = self.forecasts()
        for index, row in enumerate(rows):
            row["probability_a"] = index % 2
        scores = self.score(rows)
        self.assertTrue(math.isfinite(scores["pooled_game_weighted"]["log_loss"]))
        self.assertEqual(scores["log_loss_probability_clip"], 1e-15)
        self.assertEqual(sum(b["count"] for b in scores["reliability"]["bins"]), len(rows))

    def test_label_coverage_uniqueness_and_binary_type_are_required(self):
        for mutation in ("missing", "extra", "duplicate", "boolean", "fractional"):
            with self.subTest(mutation=mutation):
                labels = copy.deepcopy(self.fixture["labels"])
                if mutation == "missing":
                    labels.pop()
                elif mutation == "extra":
                    labels.append({"game_id": "unknown", "outcome_a": 1})
                elif mutation == "duplicate":
                    labels.append(labels[0])
                else:
                    labels[0]["outcome_a"] = True if mutation == "boolean" else 0.5
                with self.assertRaises(ValueError):
                    self.score(self.forecasts(), labels)

    def test_weighted_brier_differs_from_mean_season_brier(self):
        all_rows = self.forecasts()
        rows = [*all_rows[:2], next(row for row in all_rows if row["season"] == 2024)]
        for index, row in enumerate(rows):
            row["probability_a"] = int(index == 2)
        labels = [{"game_id": row["game_id"], "outcome_a": 0} for row in rows]
        result = self.score(rows, labels)
        self.assertAlmostEqual(result["pooled_game_weighted"]["brier"], 1 / 3)
        self.assertEqual(result["unweighted_mean_season_brier"], 0.5)
        self.assertIsNone(result["pooled_game_weighted"]["roc_auc"])

    def test_reference_metrics_and_auc_ties_are_correct(self):
        rows = self.forecasts()
        for row in rows:
            row["probability_a"] = 0.5
        result = self.score(rows)
        self.assertEqual(result["pooled_game_weighted"]["brier"], 0.25)
        self.assertAlmostEqual(result["pooled_game_weighted"]["log_loss"], math.log(2))
        self.assertEqual(result["pooled_game_weighted"]["roc_auc"], 0.5)
        self.assertEqual(result["reliability"]["bins"][2]["count"], len(rows))
        self.assertIsNone(result["reliability"]["bins"][0]["mean_prediction"])

    def test_source_conflicts_bad_ratings_and_timezones_are_rejected(self):
        for mutation in ("duplicate", "rating", "timezone", "year", "self_match"):
            with self.subTest(mutation=mutation):
                fixture = lab.make_fixture()
                row = fixture["observations"][0]
                if mutation == "duplicate":
                    fixture["observations"].append(row)
                elif mutation == "rating":
                    row["rating"] = float("nan")
                elif mutation == "timezone":
                    row["observed_at_utc"] = "2023-03-14T12:00:00"
                elif mutation == "year":
                    row["observed_at_utc"] = "2024-03-14T12:00:00Z"
                else:
                    fixture["games"][0]["team_a"] = fixture["games"][0]["team_b"]
                with self.assertRaises(ValueError):
                    lab.reproduce(fixture)

    def test_schema_and_explicit_synthetic_scope_are_required(self):
        for field, value in (
            ("evidence_scope", "REAL"),
            ("schema_version", 2),
            ("seed", True),
            ("unreviewed_source", "secret"),
        ):
            with self.subTest(field=field):
                fixture = lab.make_fixture()
                fixture[field] = value
                with self.assertRaises(ValueError):
                    lab.reproduce(fixture)

    def test_provenance_hashes_cover_inputs_and_outputs(self):
        files = lab.reproduce(self.fixture)
        provenance = json.loads(files["provenance.json"])
        self.assertEqual(provenance["evidence_scope"], lab.SCOPE)
        for name, artifact in provenance["artifacts"].items():
            self.assertEqual(lab.digest(files[name]), artifact["sha256"])
            self.assertEqual(len(files[name]), artifact["bytes"])
        self.assertEqual(
            provenance["generator_sha256"], lab.digest(Path(lab.__file__).read_bytes())
        )

    def test_cli_round_trip_check_rejects_tampering_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            args = ["--output-dir", directory]
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(lab.main(args), 0)
                self.assertEqual(lab.main([*args, "--check"]), 0)
                path = Path(directory) / "predictions.json"
                path.write_bytes(path.read_bytes() + b" ")
                original = {p.name: p.read_bytes() for p in Path(directory).iterdir()}
                self.assertEqual(lab.main([*args, "--check"]), 1)
                self.assertEqual(
                    original, {p.name: p.read_bytes() for p in Path(directory).iterdir()}
                )
                path.unlink()
                self.assertEqual(lab.main([*args, "--check"]), 1)
                self.assertFalse(path.exists())

    def test_invalid_fixture_cli_fails_before_artifact_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "bad.json"
            self.fixture["labels"].pop()
            fixture.write_bytes(lab.canonical(self.fixture))
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                code = lab.main(["--fixture", str(fixture), "--output-dir", str(root / "output")])
            self.assertEqual(code, 1)
            self.assertFalse((root / "output").exists())

    def test_ambiguous_and_nonfinite_json_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            for raw in ('{"a":1,"a":2}', '{"value":NaN}', '{"value":Infinity}'):
                with self.subTest(raw=raw):
                    path.write_text(raw)
                    with self.assertRaises(ValueError):
                        lab.read_fixture(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
