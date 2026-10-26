"""Reject inconsistent or overstated public evidence before rendering."""

import copy
import re
import unittest
from pathlib import Path

from review_project import load_snapshot, validate_snapshot


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.current = load_snapshot()

    def reject(self, group, field, value):
        changed = copy.deepcopy(self.current)
        changed[group][field] = value
        with self.assertRaises(ValueError):
            validate_snapshot(changed)

    def test_current_partition(self):
        self.assertEqual(self.current["box_scores"]["recovered"], 133)
        self.assertEqual(self.current["box_scores"]["remaining"], 88)

    def test_browser_snapshot_does_not_drift(self):
        page = (Path(__file__).resolve().parents[1] / "public-demo/index.html").read_text()
        metrics = dict(
            re.findall(r'<strong data-evidence-metric="([a-z_]+)">([^<]+)</strong>', page)
        )
        b, v = self.current["box_scores"], self.current["venue"]
        self.assertEqual(
            metrics,
            {
                "recovered": f"{b['recovered']} / {b['original_missing']}",
                "completed_units": f"{v['completed_units']} / {v['planned_units']}",
                "women_rows_qualified": f"{v['women_rows_qualified']} / {v['women_rows_required']}",
            },
        )

    def test_box_denominator(self):
        self.reject("box_scores", "remaining", 87)

    def test_residual_partition(self):
        self.reject("box_scores", "quarantined", 11)

    def test_carried_men_are_not_new_women(self):
        self.reject("venue", "women_rows_qualified", 608)

    def test_downloads_do_not_mean_known_rows(self):
        self.reject("venue", "women_rows_unknown", 0)

    def test_no_new_fit_claim(self):
        self.reject("execution_counters", "new_model_fits", 7)

    def test_no_completed_study_claim(self):
        self.reject("interpretation", "full_model_study_completed", True)

    def test_private_rows_excluded(self):
        self.reject("box_scores", "private_rows", [{"sample": "not_allowed"}])

    def test_bool_is_not_a_count(self):
        self.reject("venue", "source_errors", True)


if __name__ == "__main__":
    unittest.main()
