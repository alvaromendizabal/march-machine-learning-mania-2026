"""Reject misleading frontier summaries before a reviewer sees a chart."""

import copy
import json
import unittest

from evidence_history import snapshot_digest, strict_json
from qualification_frontier import (
    CURRENT,
    FRONTIER,
    load_frontier,
    render_frontier_panel,
    summarize_frontier,
    validate_frontier,
)


class FrontierTests(unittest.TestCase):
    def setUp(self):
        self.frontier = load_frontier()
        self.snapshot = strict_json(CURRENT.read_text())

    def rejected(self, mutate):
        changed = copy.deepcopy(self.frontier)
        mutate(changed)
        with self.assertRaises(ValueError):
            validate_frontier(changed, self.snapshot)

    def test_actual_current_partition(self):
        summary = summarize_frontier(self.frontier, self.snapshot)
        self.assertEqual(
            summary["totals"],
            {
                "required": 583,
                "qualified": 102,
                "missing_home_only": 21,
                "missing_court_only": 0,
                "missing_both": 460,
            },
        )
        self.assertEqual(summary["unknown"], 481)
        self.assertEqual(summary["completed_editions"], 0)
        self.assertFalse(summary["full_study_readiness_inferred"])

    def test_qualified_overlap_is_rejected(self):
        self.rejected(lambda f: f["editions"][0].update(qualified=7))

    def test_missing_partition_member_is_rejected(self):
        self.rejected(lambda f: f["editions"][0].pop("missing_home_only"))

    def test_negative_count_is_rejected(self):
        self.rejected(lambda f: f["editions"][0].update(missing_home_only=-1))

    def test_boolean_cannot_be_a_count(self):
        self.rejected(lambda f: f["editions"][0].update(missing_court_only=False))

    def test_float_cannot_be_a_count(self):
        self.rejected(lambda f: f["editions"][0].update(missing_court_only=0.0))

    def test_required_population_cannot_shift_between_editions(self):
        def mutate(f):
            f["editions"][0]["required"] -= 1
            f["editions"][0]["missing_both"] -= 1
            f["editions"][1]["required"] += 1
            f["editions"][1]["missing_both"] += 1

        self.rejected(mutate)

    def test_unknown_cannot_be_presented_as_qualified(self):
        def mutate(f):
            f["editions"][0]["qualified"] += 1
            f["editions"][0]["missing_both"] -= 1

        self.rejected(mutate)

    def test_court_first_meaning_cannot_silently_change(self):
        def mutate(f):
            f["editions"][0]["missing_court_only"] += 1
            f["editions"][0]["missing_both"] -= 1

        self.rejected(mutate)

    def test_edition_cannot_be_removed(self):
        self.rejected(lambda f: f["editions"].pop())

    def test_duplicate_edition_is_rejected(self):
        self.rejected(lambda f: f["editions"][0].update(season=2017))

    def test_edition_order_is_explicit(self):
        self.rejected(lambda f: f["editions"].reverse())

    def test_parent_execution_is_bound(self):
        self.rejected(lambda f: f.update(execution="v325"))

    def test_parent_digest_is_bound(self):
        self.rejected(lambda f: f.update(snapshot_sha256="0" * 64))

    def test_equal_counts_do_not_substitute_for_the_exact_parent(self):
        changed = copy.deepcopy(self.snapshot)
        changed["execution_counters"]["elapsed_seconds"] += 1
        self.assertNotEqual(snapshot_digest(changed), self.frontier["snapshot_sha256"])
        with self.assertRaises(ValueError):
            validate_frontier(self.frontier, changed)

    def test_review_date_is_bound(self):
        self.rejected(lambda f: f.update(reviewed_on="2026-10-25"))

    def test_readiness_claim_cannot_be_added(self):
        self.rejected(lambda f: f.update(full_study_completed=True))

    def test_private_routes_cannot_be_added(self):
        self.rejected(lambda f: f["editions"][0].update(source_url="withheld"))

    def test_schema_boolean_is_rejected(self):
        self.rejected(lambda f: f.update(schema_version=True))

    def test_semantics_are_fixed(self):
        self.rejected(lambda f: f.update(classification="ALL_WITNESSES_ARE_ADMITTED"))

    def test_completed_editions_must_match_snapshot(self):
        changed = copy.deepcopy(self.snapshot)
        changed["venue"]["qualified_editions"] = 1
        frontier = copy.deepcopy(self.frontier)
        frontier["snapshot_sha256"] = snapshot_digest(changed)
        with self.assertRaises(ValueError):
            validate_frontier(frontier, changed)

    def test_duplicate_json_is_rejected(self):
        raw = FRONTIER.read_text().replace(
            '"schema_version": 1', '"schema_version": 1, "schema_version": 1'
        )
        with self.assertRaises(ValueError):
            strict_json(raw)

    def test_nonfinite_json_is_rejected(self):
        with self.assertRaises(ValueError):
            strict_json('{"unknown": NaN}')

    def test_script_data_cannot_escape_its_element(self):
        changed = copy.deepcopy(self.frontier)
        changed["scope"] = '</script><script>alert("fixture")</script>'
        panel = render_frontier_panel(summarize_frontier(changed, self.snapshot))
        self.assertNotIn(changed["scope"], panel)
        self.assertIn("&lt;/script&gt;", panel)
        self.assertIn("\\u003c/script>", panel)

    def test_rendering_retains_all_editions_and_denominators(self):
        panel = render_frontier_panel(summarize_frontier(self.frontier, self.snapshot))
        self.assertEqual(panel.count('class="frontier-edition"'), 9)
        self.assertEqual(panel.count('<th scope="row">'), 9)
        self.assertIn("481 remain unknown", panel)
        self.assertIn("standalone home witness", panel)
        self.assertIn('aria-live="polite"', panel)

    def test_validation_does_not_mutate_original_evidence(self):
        before = json.dumps(self.frontier, sort_keys=True)
        summarize_frontier(self.frontier, self.snapshot)
        self.assertEqual(before, json.dumps(self.frontier, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
