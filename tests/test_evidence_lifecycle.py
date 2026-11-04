"""Portable invented event-lifecycle contracts; no real CI or owner work is run."""

from __future__ import annotations

import copy
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import PurePosixPath
from unittest.mock import patch

from march_mania.publication.evidence_bundle import (
    NOTEBOOKS,
    VALIDATION,
    EvidenceBundleError,
    canonical,
    strict_json,
    verify_notebook_event_lifecycle,
)


def authored_trace() -> tuple[bytes, dict[str, list[int]]]:
    """Construct explicit synthetic cells and clocks, never edit a real log."""
    cells = {
        name: list(range(count))
        for name, count in zip(NOTEBOOKS, (4, 3, 12, 16, 18, 4), strict=True)
    }
    rows = []
    for cold in (True, False):
        rows.append({"event": "run_started", "notebooks": 6, "publish": True})
        for position, name in enumerate(NOTEBOOKS, start=1):
            task = PurePosixPath(name).stem
            if cold:
                rows.append({"event": "task_started", "task": task})
                for cell in cells[name]:
                    rows.append(
                        {
                            "event": "cell_started",
                            "notebook": name,
                            "cell": cell,
                            "position": position,
                        }
                    )
                    rows.append(
                        {"event": "cell_finished", "notebook": name, "cell": cell, "status": "ok"}
                    )
                rows.append({"event": "task_completed", "task": task})
            else:
                rows.append({"event": "task_reused", "task": task})
            rows.append(
                {"event": "notebook_completed", "notebook": name, "completed": position, "total": 6}
            )
        rows.append({"event": "run_completed", "notebooks": 6})
    start = datetime(2025, 1, 1, tzinfo=UTC)
    run_start, task_start = 0, 0
    for index, row in enumerate(rows):
        event = row["event"]
        if event == "run_started":
            run_start = index
        if event == "task_started":
            task_start = index
        row["timestamp"] = (start + timedelta(milliseconds=index * 10)).isoformat()
        row["elapsed_seconds"] = round((index - run_start) * 0.01, 3)
        if event == "cell_finished":
            row["cell_elapsed_seconds"] = 0.01
        if event == "task_completed":
            row["task_elapsed_seconds"] = round((index - task_start) * 0.01, 3)
    return b"".join(canonical(row) for row in rows), cells


class NotebookLifecycleTests(unittest.TestCase):
    def setUp(self):
        raw, self.cells = authored_trace()
        self.payloads = {VALIDATION + "notebooks.jsonl": raw}

    def event_rows(self):
        return [
            strict_json(line) for line in self.payloads[VALIDATION + "notebooks.jsonl"].splitlines()
        ]

    def event_cell_map(self):
        return copy.deepcopy(self.cells)

    def audit_events(self, rows, cells=None):
        return verify_notebook_event_lifecycle(
            b"".join(canonical(row) for row in rows),
            self.event_cell_map() if cells is None else cells,
        )

    def heartbeat(self, rows, index, *, task=None):
        anchor = rows[index]
        return {
            "event": "heartbeat",
            "task": task or PurePosixPath(NOTEBOOKS[0]).stem,
            "timestamp": anchor["timestamp"],
            "elapsed_seconds": anchor["elapsed_seconds"],
            "task_elapsed_seconds": 0.01,
        }

    def test_lifecycle_rejects_every_adjacent_critical_event_swap(self):
        rows = self.event_rows()
        for index in range(len(rows) - 1):
            changed = copy.deepcopy(rows)
            changed[index], changed[index + 1] = changed[index + 1], changed[index]
            with self.subTest(index=index), self.assertRaises(EvidenceBundleError):
                self.audit_events(changed)

    def test_lifecycle_requires_every_event_once(self):
        rows = self.event_rows()
        for index in range(len(rows)):
            removed = rows[:index] + rows[index + 1 :]
            repeated = rows[:index] + [rows[index]] + rows[index:]
            for mutation, changed in (("removed", removed), ("repeated", repeated)):
                with (
                    self.subTest(index=index, mutation=mutation),
                    self.assertRaises(EvidenceBundleError),
                ):
                    self.audit_events(changed)

    def test_lifecycle_cell_finish_requires_matching_active_notebook(self):
        rows = self.event_rows()
        rows[3]["notebook"] = NOTEBOOKS[1]
        with self.assertRaisesRegex(EvidenceBundleError, "ordered lifecycle"):
            self.audit_events(rows)

    def test_lifecycle_task_requires_matching_notebook_stem(self):
        rows = self.event_rows()
        rows[1]["task"] = PurePosixPath(NOTEBOOKS[1]).stem
        with self.assertRaisesRegex(EvidenceBundleError, "ordered lifecycle"):
            self.audit_events(rows)

    def test_lifecycle_rejects_cells_in_warm_run(self):
        rows = self.event_rows()
        index = next(index for index, row in enumerate(rows) if row["event"] == "task_reused")
        rows[index] = {**rows[2], "timestamp": rows[index]["timestamp"]}
        with self.assertRaisesRegex(EvidenceBundleError, "ordered lifecycle"):
            self.audit_events(rows)

    def test_lifecycle_rejects_unknown_events(self):
        rows = self.event_rows()
        rows[2]["event"] = "invented_success"
        with self.assertRaisesRegex(EvidenceBundleError, "ordered lifecycle"):
            self.audit_events(rows)

    def test_lifecycle_progress_is_not_an_unchecked_decorative_message(self):
        for field, bad in (("completed", 6), ("total", 5), ("notebook", NOTEBOOKS[1])):
            rows = self.event_rows()
            row = next(row for row in rows if row["event"] == "notebook_completed")
            row[field] = bad
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(EvidenceBundleError, "ordered lifecycle"),
            ):
                self.audit_events(rows)

    def test_lifecycle_event_integer_fields_reject_booleans(self):
        for event, field in (
            ("run_started", "notebooks"),
            ("cell_started", "cell"),
            ("cell_started", "position"),
            ("notebook_completed", "completed"),
            ("notebook_completed", "total"),
        ):
            rows = self.event_rows()
            next(row for row in rows if row["event"] == event)[field] = True
            with (
                self.subTest(event=event, field=field),
                self.assertRaisesRegex(EvidenceBundleError, "ordered lifecycle"),
            ):
                self.audit_events(rows)

    def test_lifecycle_native_cell_indices_may_have_markdown_gaps(self):
        rows = self.event_rows()
        for row in rows:
            if row["event"] in ("cell_started", "cell_finished"):
                row["cell"] = row["cell"] * 2 + 1
        cells = {
            name: [cell * 2 + 1 for cell in indices]
            for name, indices in self.event_cell_map().items()
        }
        self.assertEqual(self.audit_events(rows, cells)["cold_code_cells"], 57)

    def test_lifecycle_cell_map_requires_exact_notebook_population(self):
        for replacement in ({}, {"unregistered.ipynb": [0]}):
            with (
                self.subTest(replacement=replacement),
                self.assertRaisesRegex(EvidenceBundleError, "six canonical notebooks"),
            ):
                self.audit_events(self.event_rows(), replacement)

    def test_lifecycle_cell_map_rejects_invalid_or_duplicated_indices(self):
        for bad in ([True], [0, 0], [1, 0], [-1], [10_000], [], (0, 1)):
            cells = self.event_cell_map()
            cells[NOTEBOOKS[0]] = bad
            with (
                self.subTest(bad=bad),
                self.assertRaisesRegex(EvidenceBundleError, "ordered unique native integer"),
            ):
                self.audit_events(self.event_rows(), cells)

    def test_lifecycle_requires_valid_explicit_utc_timestamps(self):
        for bad in (
            "2025-01-01",
            "2025-01-01T00:00:00",
            "2025-01-01T00:00:00+01:00",
            "2025-02-31T00:00:00Z",
            "2025-01-01 00:00:00+00:00",
            None,
        ):
            rows = self.event_rows()
            rows[2]["timestamp"] = bad
            with (
                self.subTest(bad=bad),
                self.assertRaisesRegex(EvidenceBundleError, "UTC timestamp"),
            ):
                self.audit_events(rows)

    def test_lifecycle_accepts_explicit_z_utc_spelling(self):
        rows = self.event_rows()
        for row in rows:
            row["timestamp"] = row["timestamp"].replace("+00:00", "Z")
        self.assertEqual(self.audit_events(rows)["status"], "PASS")

    def test_lifecycle_critical_wall_clock_regression_is_not_hidden(self):
        rows = self.event_rows()
        rows[3]["timestamp"] = rows[1]["timestamp"]
        with self.assertRaisesRegex(EvidenceBundleError, "nondecreasing recorded UTC"):
            self.audit_events(rows)

    def test_lifecycle_elapsed_regression_within_run_is_rejected(self):
        rows = self.event_rows()
        rows[3]["elapsed_seconds"] = rows[1]["elapsed_seconds"]
        with self.assertRaisesRegex(EvidenceBundleError, "nondecreasing per-run elapsed"):
            self.audit_events(rows)

    def test_lifecycle_same_clock_instant_is_not_a_duplicate_identity(self):
        rows = self.event_rows()
        rows[3]["timestamp"] = rows[2]["timestamp"]
        report = self.audit_events(rows)
        self.assertEqual(report["critical_utc_clock_ties"], 1)
        self.assertEqual(report["cold_code_cells"], 57)

    def test_lifecycle_rounded_elapsed_ties_are_permitted(self):
        rows = self.event_rows()
        rows[3]["elapsed_seconds"] = rows[2]["elapsed_seconds"]
        self.assertEqual(self.audit_events(rows)["critical_elapsed_clock_ties"], 1)

    def test_lifecycle_elapsed_clock_resets_only_at_new_run(self):
        report = self.audit_events(self.event_rows())
        self.assertEqual([run["start_elapsed_seconds"] for run in report["runs"]], [0, 0])
        self.assertGreater(report["runs"][0]["end_elapsed_seconds"], 0)

    def test_lifecycle_elapsed_clock_rejects_bool_negative_and_nonfinite(self):
        for bad in (True, -1, "0.02", None):
            rows = self.event_rows()
            rows[2]["elapsed_seconds"] = bad
            with (
                self.subTest(bad=bad),
                self.assertRaisesRegex(EvidenceBundleError, "elapsed seconds"),
            ):
                self.audit_events(rows)
        raw = self.payloads[VALIDATION + "notebooks.jsonl"].replace(
            b'"elapsed_seconds":0.02', b'"elapsed_seconds":1e999'
        )
        with self.assertRaisesRegex(EvidenceBundleError, "finite JSON"):
            verify_notebook_event_lifecycle(raw, self.event_cell_map())

    def test_lifecycle_missing_clock_is_not_imputed(self):
        for field in ("timestamp", "elapsed_seconds"):
            rows = self.event_rows()
            del rows[2][field]
            with self.subTest(field=field), self.assertRaises(EvidenceBundleError):
                self.audit_events(rows)

    def test_lifecycle_recorded_durations_reject_bool_negative_and_text(self):
        for field in ("cell_elapsed_seconds", "task_elapsed_seconds"):
            for bad in (True, -0.01, "0.01"):
                rows = self.event_rows()
                next(row for row in rows if field in row)[field] = bad
                with (
                    self.subTest(field=field, bad=bad),
                    self.assertRaisesRegex(EvidenceBundleError, "nonnegative duration"),
                ):
                    self.audit_events(rows)

    def test_lifecycle_allows_active_task_heartbeat_without_new_execution_credit(self):
        rows = self.event_rows()
        rows.insert(3, self.heartbeat(rows, 2))
        report = self.audit_events(rows)
        self.assertEqual((report["events"], report["heartbeat_events"]), (149, 1))
        self.assertEqual(report["critical_lifecycle_events"], 148)
        self.assertEqual(report["cold_code_cells"], 57)

    def test_lifecycle_allows_thread_shutdown_heartbeat_but_bounds_its_capture(self):
        rows = self.event_rows()
        index = next(index for index, row in enumerate(rows) if row["event"] == "task_completed")
        rows.insert(index + 1, self.heartbeat(rows, index - 1))
        report = self.audit_events(rows)
        self.assertEqual(report["heartbeats_with_cross_thread_capture_order"], 1)
        self.assertEqual(report["closed_ordered_runs"], 2)

    def test_lifecycle_heartbeat_requires_active_matching_cold_task(self):
        rows = self.event_rows()
        for index, task in ((1, None), (3, "wrong_task"), (len(rows) - 2, None)):
            changed = copy.deepcopy(rows)
            changed.insert(index, self.heartbeat(rows, 2, task=task))
            with (
                self.subTest(index=index),
                self.assertRaisesRegex(EvidenceBundleError, "active cold task"),
            ):
                self.audit_events(changed)

    def test_lifecycle_heartbeat_timestamps_must_be_inside_task_lifetime(self):
        rows = self.event_rows()
        for anchor in (0, len(rows) - 1):
            changed = copy.deepcopy(rows)
            changed.insert(3, self.heartbeat(rows, anchor))
            with (
                self.subTest(anchor=anchor),
                self.assertRaisesRegex(EvidenceBundleError, "clock is within its cold task"),
            ):
                self.audit_events(changed)

    def test_lifecycle_heartbeat_duration_cannot_be_omitted(self):
        rows = self.event_rows()
        heartbeat = self.heartbeat(rows, 2)
        del heartbeat["task_elapsed_seconds"]
        rows.insert(3, heartbeat)
        with self.assertRaisesRegex(EvidenceBundleError, "heartbeat duration"):
            self.audit_events(rows)

    def test_lifecycle_does_not_open_files_or_execute_notebooks(self):
        raw, cells = self.payloads[VALIDATION + "notebooks.jsonl"], self.event_cell_map()
        with patch("builtins.open", side_effect=AssertionError("No filesystem access")):
            report = verify_notebook_event_lifecycle(raw, cells)
        self.assertEqual(report["notebooks_executed_by_audit"], 0)
        self.assertEqual(report["model_fits_by_audit"], 0)

    def test_lifecycle_rejects_blank_or_nonobject_events(self):
        for raw in (b"", b"\n", b"[]\n", b"null\n"):
            with self.subTest(raw=raw), self.assertRaises(EvidenceBundleError):
                verify_notebook_event_lifecycle(raw, self.event_cell_map())


if __name__ == "__main__":
    unittest.main()
