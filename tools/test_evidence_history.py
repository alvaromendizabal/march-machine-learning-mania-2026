"""Prevent false progress when publishing a sequence of owner-run aggregates."""

import copy
import unittest

from evidence_history import (
    load_history,
    render_history_panel,
    strict_json,
    summarize_history,
    validate_history,
)


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.history = load_history()

    def reject(self, edit):
        changed = copy.deepcopy(self.history)
        edit(changed)
        with self.assertRaises(ValueError):
            validate_history(changed)

    def test_current_observed_gains(self):
        change = summarize_history(self.history)["latest_change"]
        self.assertEqual((change["women_net_gain"], change["box_candidates_added"]), (21, 0))
        self.assertEqual((change["dated_court_net_gain"], change["home_pod_net_gain"]), (16, 7))

    def test_duplicate_execution_rejected(self):
        self.reject(lambda d: d["snapshots"][1].update(execution="v324"))

    def test_reordered_history_rejected(self):
        self.reject(lambda d: d["snapshots"].reverse())

    def test_reused_gains_cannot_be_added_again(self):
        self.reject(lambda d: d["transitions"][0].update(box_candidates_added=2))

    def test_changed_parent_rejected(self):
        self.reject(lambda d: d["transitions"][0].update(**{"from": "v323"}))

    def test_changed_population_rejected(self):
        def edit(d):
            v = d["snapshots"][1]["venue"]
            v["women_rows_required"] += 1
            v["women_rows_unknown"] += 1

        self.reject(edit)

    def test_undeclared_row_loss_rejected(self):
        def edit(d):
            v = d["snapshots"][1]["venue"]
            v["women_rows_qualified"] -= 1
            v["women_rows_unknown"] += 1

        self.reject(edit)

    def test_explicit_retraction_is_accounted_for(self):
        d = copy.deepcopy(self.history)
        d["snapshots"][1]["venue"].update(women_rows_qualified=26, women_rows_unknown=557)
        d["transitions"][0]["women_rows_removed"] = 1
        self.assertEqual(
            summarize_history(validate_history(d))["latest_change"]["women_net_gain"], 20
        )

    def test_cannot_retract_more_than_prior_population(self):
        self.reject(lambda d: d["transitions"][0].update(women_rows_removed=7, women_rows_added=28))

    def test_unverified_reparse_rejected(self):
        self.reject(lambda d: d["transitions"][0].update(prior_bodies_verified=61))

    def test_error_resolution_cannot_exceed_prior_errors(self):
        self.reject(lambda d: d["transitions"][0].update(prior_processing_errors_resolved=28))

    def test_success_cannot_hide_processing_errors(self):
        self.reject(lambda d: d["snapshots"][0].update(status="SUCCESS"))

    def test_partial_acquisition_cannot_be_called_complete(self):
        self.reject(lambda d: d["snapshots"][1]["venue"].update(completed_units=79))

    def test_bool_is_not_a_transition_count(self):
        self.reject(lambda d: d["transitions"][0].update(prior_bodies_verified=True))

    def test_private_fields_rejected(self):
        self.reject(lambda d: d["transitions"][0].update(raw_provider_rows=[]))

    def test_latest_observation_must_match_current(self):
        current = copy.deepcopy(self.history["snapshots"][-1])
        current["execution_counters"]["elapsed_seconds"] += 1
        with self.assertRaises(ValueError):
            validate_history(self.history, current)

    def test_changed_observation_changes_digest(self):
        before = summarize_history(self.history)["observations"][-1]["digest"]
        self.history["snapshots"][-1]["execution_counters"]["elapsed_seconds"] += 1
        after = summarize_history(self.history)["observations"][-1]["digest"]
        self.assertNotEqual(before, after)

    def test_duplicate_json_key_and_nonfinite_rejected(self):
        for raw in ('{"a":1,"a":2}', '{"value":NaN}', '{"value":Infinity}'):
            with self.assertRaises(ValueError):
                strict_json(raw)

    def test_success_requires_all_units_even_without_milestone(self):
        d = copy.deepcopy(self.history)
        d["snapshots"][1]["venue"]["completed_units"] -= 1
        d["snapshots"][1]["interpretation"]["acquisition_milestone_completed"] = False
        with self.assertRaises(ValueError):
            validate_history(d)

    def test_bool_schema_member_count_and_milestone_rejected(self):
        for group, field in (
            (None, "schema_version"),
            ("provenance", "manifest_members_verified"),
            ("interpretation", "acquisition_milestone_completed"),
        ):
            d = copy.deepcopy(self.history)
            target = d["snapshots"][1] if group is None else d["snapshots"][1][group]
            target[field] = 1 if field == "acquisition_milestone_completed" else True
            with self.assertRaises(ValueError):
                validate_history(d)

    def test_season_population_redistribution_rejected(self):
        d = copy.deepcopy(self.history)
        rows = d["snapshots"][1]["box_scores"]["by_season"]
        for field in ("original_missing", "remaining"):
            rows[0][field] += 1
            rows[1][field] -= 1
        with self.assertRaises(ValueError):
            validate_history(d)

    def test_team_season_population_change_rejected(self):
        d = copy.deepcopy(self.history)
        d["snapshots"][1]["team_seasons"]["total"] += 1
        d["snapshots"][1]["team_seasons"]["affected"] += 1
        with self.assertRaises(ValueError):
            validate_history(d)

    def test_rendered_transition_has_resolved_values(self):
        rendered = render_history_panel(summarize_history(self.history))
        for text in (
            "<strong>+21</strong>",
            "<strong>27</strong>",
            "<strong>62</strong>",
            "Numerical additions: 0.",
            "Dated courts: +16",
            "home-context facts: +7",
        ):
            self.assertIn(text, rendered)
        self.assertNotIn("{change[", rendered)

    def test_render_has_explicit_populations_and_accessible_controls(self):
        page = render_history_panel(summarize_history(self.history))
        for expected in (
            "27 / 583 qualified",
            "133/221",
            'aria-live="polite"',
            'for="history-metric"',
            "Historical admission of recovered boxes",
        ):
            self.assertIn(expected, page)
        self.assertNotIn("overall percent complete", page.lower())


if __name__ == "__main__":
    unittest.main()
