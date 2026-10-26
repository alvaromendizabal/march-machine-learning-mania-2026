"""Behavioral failure and actual computation checks for the synthetic example."""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import reliability_demo as demo


class ReliabilityTests(unittest.TestCase):
    def test_lifecycle_and_corruption(self):
        result = demo.demonstrate()
        self.assertTrue(result["cold_and_resumed_results_identical"])
        self.assertTrue(result["corruption_rejected"])

    def test_actual_qualification_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(demo, "qualify", wraps=demo.qualify) as qualify:
                demo.run(root / "cold")
                self.assertEqual(qualify.call_count, 4)
                qualify.reset_mock()
                demo.run(root / "resumed", stop_after=1)
                self.assertEqual(qualify.call_count, 1)
                qualify.reset_mock()
                demo.run(root / "resumed")
                self.assertEqual(qualify.call_count, 3)
                qualify.reset_mock()
                demo.run(root / "resumed")
                self.assertEqual(qualify.call_count, 0)

    def test_unknown_timing_is_preserved(self):
        self.assertEqual(
            demo.qualify(demo.OBSERVATIONS[2], demo.CUTOFF)["status"], "UNKNOWN_TIMING"
        )

    def test_late_observation_is_not_eligible(self):
        self.assertEqual(demo.qualify(demo.OBSERVATIONS[1], demo.CUTOFF)["status"], "LATE_SOURCE")

    def test_boundary_is_inclusive(self):
        row = dict(demo.OBSERVATIONS[0], available_at=demo.CUTOFF)
        self.assertEqual(demo.qualify(row, demo.CUTOFF)["status"], "ELIGIBLE")

    def test_changed_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            demo.run(Path(directory))
            changed = copy.deepcopy(list(demo.OBSERVATIONS))
            changed[0]["value"] += 1
            with self.assertRaises(demo.IntegrityError):
                demo.run(Path(directory), observations=changed)

    def test_duplicate_identity_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                demo.run(Path(directory), observations=(demo.OBSERVATIONS[0],) * 2)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_generator_is_not_consumed_by_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            result = demo.run(Path(directory), observations=(r for r in demo.OBSERVATIONS))
            self.assertEqual(result["computed_this_invocation"], 4)

    def test_real_input_is_rejected(self):
        with self.assertRaises(ValueError):
            demo.qualify(dict(demo.OBSERVATIONS[0], scope="REAL"), demo.CUTOFF)

    def test_timezone_is_required(self):
        with self.assertRaises(ValueError):
            demo.qualify(dict(demo.OBSERVATIONS[0], available_at="2025-02-28"), demo.CUTOFF)

    def test_active_lock_is_not_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / "run.lock"
            lock.write_text("active")
            with self.assertRaises(demo.IntegrityError):
                demo.run(Path(directory))
            self.assertEqual(lock.read_text(), "active")

    def test_dangling_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "synthetic_alpha.json").symlink_to("missing")
            with self.assertRaises(demo.IntegrityError):
                demo.run(Path(directory))


if __name__ == "__main__":
    unittest.main()
