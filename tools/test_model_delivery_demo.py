"""Adversarial contracts for data-only, labels-free public model delivery."""

from __future__ import annotations

import copy
import importlib.util
import json
import socket
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from march_mania import public_reference as serving  # noqa: E402

SPEC = importlib.util.spec_from_file_location(
    "model_delivery_demo", ROOT / "tools/model_delivery_demo.py"
)
assert SPEC is not None and SPEC.loader is not None
delivery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delivery)


class ModelDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files, cls.receipt = delivery.build_demo_files()
        cls.model_raw = cls.files["folds/2026/model.json"]
        cls.model_sha = serving.pin(cls.model_raw)["sha256"]
        cls.request_raw = cls.files["folds/2026/request.json"]
        cls.model = json.loads(cls.model_raw)
        cls.request = json.loads(cls.request_raw)

    def reject_model(self, value):
        raw = json.dumps(value).encode()
        with self.assertRaises(ValueError):
            serving.load_model(raw, serving.pin(raw)["sha256"])

    def reject_request(self, value):
        raw = json.dumps(value).encode()
        with self.assertRaises(ValueError):
            serving.predict_bytes(self.model_raw, self.model_sha, raw)

    def changed_model(self):
        return copy.deepcopy(self.model)

    def changed_request(self):
        return copy.deepcopy(self.request)

    def test_three_frozen_models_match_all_198_predictions_without_fitting(self):
        self.assertEqual(self.receipt["model_count"], 3)
        self.assertEqual(self.receipt["predictions_checked"], 198)
        self.assertEqual(self.receipt["maximum_absolute_probability_difference"], 0.0)
        self.assertTrue(self.receipt["exact_prediction_parity"])
        self.assertEqual(self.receipt["new_model_fits"], 0)
        self.assertEqual(self.receipt["scope"], "SYNTHETIC_ONLY")
        self.assertEqual(len(self.files), 9)

    def test_loaded_model_is_deeply_immutable(self):
        model = serving.load_model(self.model_raw, self.model_sha)
        self.assertIsInstance(model.coefficients, tuple)
        self.assertIsInstance(model.scale, tuple)
        self.assertIsInstance(model.physical_training_ids, frozenset)
        with self.assertRaises(FrozenInstanceError):
            model.evaluation_season = 2027

    def test_response_is_byte_deterministic_and_pins_exact_request(self):
        actual = serving.predict_bytes(self.model_raw, self.model_sha, self.request_raw)
        self.assertEqual(actual, self.files["folds/2026/response.json"])
        self.assertEqual(
            actual, serving.predict_bytes(self.model_raw, self.model_sha, self.request_raw)
        )
        value = json.loads(actual)
        self.assertEqual(value["request_sha256"], serving.pin(self.request_raw)["sha256"])
        self.assertEqual(value["model_sha256"], self.model_sha)
        self.assertEqual(value["physical_games"], 66)

    def test_expected_hash_is_external_and_required(self):
        for wrong in ("0" * 64, "", None, True, "Z" * 64, self.model_sha.upper()):
            with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                serving.load_model(self.model_raw, wrong)

    def test_tampered_model_rejected_even_when_still_valid_json(self):
        model = self.changed_model()
        model["model"]["coefficients"][0] += 0.001
        with self.assertRaises(ValueError):
            serving.load_model(serving.canonical(model), self.model_sha)

    def test_duplicate_keys_rejected_at_every_json_level(self):
        for raw in (b'{"schema":1,"schema":1}', b'{"model":{"a":1,"a":1}}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                serving.decode_json(raw, 1024)

    def test_complete_utf8_json_required(self):
        for raw in (b"\xff", b"{}{}", b'{"x":', b"", b"{not json}"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                serving.decode_json(raw, 1024)

    def test_model_and_request_roots_must_be_closed_objects(self):
        for value in ([], None, 7, "text"):
            with self.subTest(value=value):
                self.reject_model(value)
                self.reject_request(value)

    def test_nonfinite_constants_are_rejected(self):
        for raw in (b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                serving.decode_json(raw, 1024)

    def test_model_byte_bound(self):
        raw = b" " * (serving.MAX_MODEL_BYTES + 1)
        with self.assertRaises(ValueError):
            serving.load_model(raw, serving.pin(raw)["sha256"])

    def test_request_byte_bound(self):
        with self.assertRaises(ValueError):
            serving.predict_bytes(
                self.model_raw, self.model_sha, b" " * (serving.MAX_REQUEST_BYTES + 1)
            )

    def test_unknown_model_fields_rejected(self):
        for path in ((), ("model",), ("model", "scaler"), ("lineage",)):
            model = self.changed_model()
            target = model
            for part in path:
                target = target[part]
            target["private_extra"] = "not permitted"
            with self.subTest(path=path):
                self.reject_model(model)

    def test_wrong_model_version_or_scope_rejected(self):
        for field, value in (
            ("schema", 1),
            ("schema", "v2"),
            ("evidence_scope", "NCAA"),
            ("disclosure", "PRODUCTION"),
        ):
            model = self.changed_model()
            model[field] = value
            with self.subTest(field=field):
                self.reject_model(model)

    def test_unknown_model_family_rejected(self):
        model = self.changed_model()
        model["model"]["family"] = "PICKLED_ARBITRARY_ESTIMATOR"
        self.reject_model(model)

    def test_reordered_or_missing_feature_names_rejected(self):
        for names in (
            list(reversed(serving.FEATURE_NAMES)),
            ["rating_difference"],
            {name: 1 for name in serving.FEATURE_NAMES},
        ):
            model = self.changed_model()
            model["model"]["feature_names"] = names
            self.reject_model(model)

    def test_coefficient_shape_boolean_and_range(self):
        for coefficients in ([0, 0], [False, 0, 0], [float("nan"), 0, 0], [101, 0, 0], ["0", 0, 0]):
            model = self.changed_model()
            model["model"]["coefficients"] = coefficients
            self.reject_model(model)

    def test_zero_intercept_is_numeric_not_boolean(self):
        for intercept in (True, False, 0.01, "0", float("inf")):
            model = self.changed_model()
            model["model"]["intercept"] = intercept
            self.reject_model(model)

    def test_scaler_must_preserve_symmetry(self):
        for means in ([0, 0], [0.01, 0, 0], [False, 0, 0]):
            model = self.changed_model()
            model["model"]["scaler"]["mean"] = means
            self.reject_model(model)

    def test_scaler_requires_finite_positive_bounded_scales(self):
        for scales in (
            [1, 1],
            [0, 1, 1],
            [-1, 1, 1],
            [True, 1, 1],
            [1e-13, 1, 1],
            [float("inf"), 1, 1],
            [10_001, 1, 1],
        ):
            model = self.changed_model()
            model["model"]["scaler"]["scale"] = scales
            self.reject_model(model)

    def test_training_seasons_are_unique_earlier_integers(self):
        for years in ([], [True], [2021, 2021], [2022, 2021], [2021, 2026]):
            model = self.changed_model()
            model["lineage"]["training_seasons"] = years
            self.reject_model(model)

    def test_training_ids_and_denominator_must_match(self):
        for mutation in ("duplicate", "wrong_year", "wrong_count", "real_id"):
            model = self.changed_model()
            lineage = model["lineage"]
            if mutation == "duplicate":
                lineage["physical_training_ids"][1] = lineage["physical_training_ids"][0]
            elif mutation == "wrong_year":
                lineage["physical_training_ids"][0] = "synthetic_2026_r01_g01"
            elif mutation == "real_id":
                lineage["physical_training_ids"][0] = "private_game_1"
            else:
                lineage["physical_training_games"] = True
            self.reject_model(model)

    def test_training_clock_contract(self):
        for field, value in (
            ("fit_completed_at_utc", "2025-03-17T00:00:00Z"),
            ("fit_completed_at_utc", "2026-03-17T00:00:00"),
            ("latest_training_label_available_at_utc", "2026-03-17T00:00:00Z"),
            ("fit_clock_is_authored_not_wall_clock", 1),
        ):
            model = self.changed_model()
            model["lineage"][field] = value
            self.reject_model(model)

    def test_lineage_content_pins_have_strict_schema(self):
        for value in (
            {"bytes": True, "sha256": "a" * 64},
            {"bytes": 1, "sha256": "invalid"},
            {"bytes": 1, "sha256": "a" * 64, "extra": 1},
        ):
            model = self.changed_model()
            model["lineage"]["training_input_pin"] = value
            self.reject_model(model)

    def test_request_has_no_label_channel(self):
        for name in ("labels", "outcome_a", "ground_truth", "metadata"):
            request = self.changed_request()
            request[name] = [1]
            self.reject_request(request)

    def test_feature_rows_have_no_label_channel(self):
        request = self.changed_request()
        request["rows"][0]["outcome_a"] = 1
        self.reject_request(request)

    def test_request_version_and_scope_are_explicit(self):
        for key, value in (("schema", "v2"), ("evidence_scope", "REAL")):
            request = self.changed_request()
            request[key] = value
            self.reject_request(request)

    def test_request_row_count_is_bounded_nonempty(self):
        for rows in ([], {}, [self.request["rows"][0]] * (serving.MAX_BATCH_ROWS + 1)):
            request = self.changed_request()
            request["rows"] = rows
            self.reject_request(request)

    def test_feature_types_shapes_and_authored_ranges(self):
        for features in (
            [1, 2],
            [True, 0, 0],
            [0, float("nan"), 0],
            [2001, 0, 0],
            [0, 6.001, 0],
            [0, 0, 14.001],
            ["0", 0, 0],
        ):
            request = self.changed_request()
            request["rows"][0]["features"] = features
            self.reject_request(request)

    def test_future_feature_rejected(self):
        request = self.changed_request()
        request["rows"][0]["feature_available_at_utc"] = "2026-03-17T00:00:00.000001Z"
        self.reject_request(request)

    def test_feature_available_exactly_at_cutoff_is_allowed(self):
        request = self.changed_request()
        request["rows"][0]["feature_available_at_utc"] = "2026-03-17T00:00:00Z"
        response = serving.predict_bytes(self.model_raw, self.model_sha, serving.canonical(request))
        self.assertEqual(json.loads(response)["physical_games"], 66)

    def test_fit_must_strictly_precede_forecast(self):
        request = self.changed_request()
        request["rows"][0]["forecast_at_utc"] = self.model["lineage"]["fit_completed_at_utc"]
        self.reject_request(request)

    def test_one_hour_boundary_is_inclusive_not_less(self):
        request = self.changed_request()
        request["rows"] = request["rows"][:1]
        row = request["rows"][0]
        row["started_at_utc"] = "2026-03-17T01:00:00Z"
        serving.predict_bytes(self.model_raw, self.model_sha, serving.canonical(request))
        row["started_at_utc"] = "2026-03-17T00:59:59.999999Z"
        self.reject_request(request)

    def test_naive_non_utc_and_bad_calendar_clocks_rejected(self):
        for clock in (
            "2026-03-16T12:00:00",
            "2026-03-16T12:00:00+00:00",
            "2026-02-30T12:00:00Z",
            "2026-03-16 12:00:00Z",
        ):
            request = self.changed_request()
            request["rows"][0]["feature_available_at_utc"] = clock
            self.reject_request(request)

    def test_utc_instants_not_lexical_strings(self):
        request = self.changed_request()
        request["rows"][0]["feature_available_at_utc"] = "2026-03-17T00:00:00.000000Z"
        serving.predict_bytes(self.model_raw, self.model_sha, serving.canonical(request))

    def test_duplicate_ids_rejected(self):
        request = self.changed_request()
        request["rows"].append(copy.deepcopy(request["rows"][0]))
        self.reject_request(request)

    def test_swapped_physical_duplicate_with_new_id_rejected(self):
        request = self.changed_request()
        a, b = request["rows"][:2]
        b["team_a"], b["team_b"] = a["team_b"], a["team_a"]
        b["started_at_utc"] = a["started_at_utc"]
        self.reject_request(request)

    def test_other_season_and_nonsynthetic_ids_rejected(self):
        for field, value in (
            ("season", True),
            ("season", 2027),
            ("id", "private_game_1"),
            ("id", "synthetic_2025_r01_g01"),
            ("scope", "NCAA"),
        ):
            request = self.changed_request()
            request["rows"][0][field] = value
            self.reject_request(request)

    def test_team_domain_and_self_games_rejected(self):
        for team in ("Duke", "FICTIONAL_99", 1, self.request["rows"][0]["team_a"]):
            request = self.changed_request()
            request["rows"][0]["team_b"] = team
            self.reject_request(request)

    def test_team_swap_complements_probabilities(self):
        request = self.changed_request()
        request["rows"] = request["rows"][:1]
        original = json.loads(
            serving.predict_bytes(self.model_raw, self.model_sha, serving.canonical(request))
        )
        row = request["rows"][0]
        row["team_a"], row["team_b"] = row["team_b"], row["team_a"]
        row["features"] = [-value for value in row["features"]]
        reverse = json.loads(
            serving.predict_bytes(self.model_raw, self.model_sha, serving.canonical(request))
        )
        self.assertAlmostEqual(
            original["predictions"][0]["pred"] + reverse["predictions"][0]["pred"], 1.0, places=15
        )

    def test_zero_features_have_half_probability(self):
        request = self.changed_request()
        request["rows"] = request["rows"][:1]
        request["rows"][0]["features"] = [0, 0, 0]
        result = json.loads(
            serving.predict_bytes(self.model_raw, self.model_sha, serving.canonical(request))
        )
        self.assertEqual(result["predictions"][0]["pred"], 0.5)

    def test_inference_has_no_file_or_network_calls(self):
        blocked = mock.Mock(side_effect=AssertionError("Inference attempted external I/O"))
        with (
            mock.patch("builtins.open", blocked),
            mock.patch.object(Path, "open", blocked),
            mock.patch.object(socket, "socket", blocked),
        ):
            response = serving.predict_bytes(self.model_raw, self.model_sha, self.request_raw)
        self.assertEqual(response, self.files["folds/2026/response.json"])
        blocked.assert_not_called()

    def test_three_fresh_processes_need_no_trainer_fixture_or_site_packages(self):
        receipt = delivery.fresh_process_check(self.files)
        self.assertEqual(receipt["predictions_checked"], 198)
        self.assertEqual(receipt["isolated_processes"], 3)
        self.assertFalse(receipt["trainer_or_fixtures_present"])
        self.assertFalse(receipt["site_packages_enabled"])
        self.assertTrue(receipt["exact_response_bytes_match"])

    def test_written_demo_has_exact_payload_closure_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "new-demo"
            receipt = delivery.run_demo(output)
            self.assertEqual(receipt["status"], "PASS")
            manifest = json.loads((output / "manifest.json").read_bytes())
            actual = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
            self.assertEqual(actual, set(manifest["payloads"]) | {"manifest.json"})
            self.assertEqual(len(manifest["payloads"]), 10)
            for path, expected in manifest["payloads"].items():
                self.assertEqual(serving.pin((output / path).read_bytes()), expected)
            self.assertEqual(delivery.run_demo(output), receipt)
            model = output / "folds/2026/model.json"
            model.write_bytes(b"changed evidence")
            with self.assertRaises(ValueError):
                delivery.run_demo(output)
            self.assertEqual(model.read_bytes(), b"changed evidence")

    def test_existing_demo_rejects_extra_files_without_removing_them(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "new-demo"
            delivery.run_demo(output)
            extra = output / "unrelated.txt"
            extra.write_bytes(b"preserve unrelated work")
            with self.assertRaises(ValueError):
                delivery.run_demo(output)
            self.assertEqual(extra.read_bytes(), b"preserve unrelated work")

    def test_existing_demo_rejects_symlinks_without_following_them(self):
        with tempfile.TemporaryDirectory() as name:
            output = Path(name) / "new-demo"
            delivery.run_demo(output)
            extra = output / "alias.json"
            extra.symlink_to(output / "folds/2026/model.json")
            with self.assertRaises(ValueError):
                delivery.run_demo(output)
            self.assertTrue(extra.is_symlink())

    def test_predict_cli_fails_without_overwriting_existing_output(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            model, request, output = (
                root / x for x in ("model.json", "request.json", "output.json")
            )
            model.write_bytes(self.model_raw)
            request.write_bytes(self.request_raw)
            output.write_bytes(b"existing evidence")
            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    str(Path(delivery.__file__)),
                    "predict",
                    "--model",
                    str(model),
                    "--expected-sha256",
                    self.model_sha,
                    "--request",
                    str(request),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), b"existing evidence")
            self.assertNotIn(str(root), result.stderr)

    def test_input_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            source, link = root / "model.json", root / "alias.json"
            source.write_bytes(self.model_raw)
            link.symlink_to(source)
            with self.assertRaises(ValueError):
                delivery.read_bounded(link, serving.MAX_MODEL_BYTES)


if __name__ == "__main__":
    unittest.main()
