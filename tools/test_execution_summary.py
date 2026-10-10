"""Offline regression checks for sanitized owner-return publication."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).with_name("summarize_execution.py")
SPEC = importlib.util.spec_from_file_location("execution_summary", SOURCE)
assert SPEC is not None and SPEC.loader is not None
summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(summary)


def encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True).encode()


def fixture_members() -> dict[str, bytes]:
    repair = {
        "status": "PASS",
        "rows": 2258,
        "last_missing_retained": 1075,
        "eligible_model_feature": False,
        "model_fits": 0,
        "model_inferences": 0,
        "submissions": 0,
        "private_field": "PRIVATE_EXTRA_INPUT_SENTINEL",
    }
    injury = {
        "status": "SOURCE_PARTIAL",
        "exact23_injury_values_reconstructed": False,
        "model_admitted_BPR": 0,
        "proven_legacy_BPR_parity": 0,
        "private_field": "PRIVATE_EXTRA_INPUT_SENTINEL",
    }
    result = {
        "status": "SOURCE_PARTIAL",
        "current_best_confirmed_kaggle_brier": 0.1067095,
        "ended_utc": "2026-10-10T01:32:58.968371Z",
        "version": "v128-owned-source-repair-20261010",
        "run_id": "20261010T013254065226Z-2d8e2bc2",
        "quote_rows_reparsed": 2258,
        "repaired_quote_rows": 2258,
        "components": {"market_repair": repair, "provider_sources": injury},
        "private_recipe": {"details": "PRIVATE_EXTRA_INPUT_SENTINEL"},
    }
    for key in (
        "model_fits",
        "model_fits_completed",
        "model_inferences",
        "model_inferences_completed",
        "new_candidates",
        "submissions",
    ):
        result[key] = 0
    for key in (
        "score_improvement_claim",
        "historical_gate_passed",
        "all_gaps_closed",
        "candidate_written",
        "submission_attempted",
        "target_score_computed",
        "exact_v19_recreated",
    ):
        result[key] = False
    members = {
        summary.SUMMARY: encoded(result),
        summary.REPAIR: encoded(repair),
        summary.INJURY: encoded(injury),
    }
    members.update(
        {f"unpublished/member_{i}.txt": b"PRIVATE_EXTRA_INPUT_SENTINEL" for i in range(72)}
    )
    return members


class ExecutionSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.archive = Path(self.directory.name) / "owner-return.zip"

    def write_archive(
        self, *, members=None, manifest=True, wrong_digest=False, duplicate=False
    ) -> str:
        entries = fixture_members() if members is None else members
        records = [
            {
                "path": name,
                "size_bytes": len(content),
                "sha256": summary.digest(content),
                "required_for_return": True,
            }
            for name, content in entries.items()
        ]
        if wrong_digest:
            records[0]["sha256"] = "0" * 64
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name, content in entries.items():
                    archive.writestr(name, content)
                if duplicate:
                    archive.writestr(summary.SUMMARY, entries[summary.SUMMARY])
                if manifest:
                    archive.writestr(
                        "manifest.json",
                        encoded({"artifacts": records, "required_members": list(entries)}),
                    )
        return summary.digest(self.archive.read_bytes())

    def test_verified_aggregate_is_allowlisted_and_never_extracts_or_copies_extra_fields(self):
        sha = self.write_archive()
        with (
            patch.object(zipfile.ZipFile, "extract", side_effect=AssertionError("extraction")),
            patch.object(zipfile.ZipFile, "extractall", side_effect=AssertionError("extraction")),
        ):
            result = summary.summarize_archive(self.archive, sha, "0.1067095")
        self.assertEqual(result["status"], "SOURCE_PARTIAL")
        self.assertEqual(result["provenance"]["verified_manifest_members"], 75)
        self.assertEqual(result["source_engineering"]["repaired_quote_rows"], 2258)
        self.assertFalse(result["source_engineering"]["eligible_model_feature"])
        self.assertEqual(set(result["activity"].values()), {0})
        self.assertNotIn("PRIVATE_EXTRA_INPUT_SENTINEL", json.dumps(result))
        self.assertNotIn("private_recipe", json.dumps(result))
        self.assertNotIn(str(self.directory.name), json.dumps(result))
        self.assertEqual(list(Path(self.directory.name).iterdir()), [self.archive])

    def test_archive_hash_tampering_is_rejected_before_zip_read(self):
        sha = self.write_archive()
        with self.archive.open("ab") as stream:
            stream.write(b"altered")
        with self.assertRaisesRegex(ValueError, "archive SHA-256 mismatch"):
            summary.summarize_archive(self.archive, sha, "0.1067095")

    def test_manifest_and_member_hash_are_required(self):
        sha = self.write_archive(manifest=False)
        with self.assertRaisesRegex(ValueError, "missing manifest"):
            summary.summarize_archive(self.archive, sha, "0.1067095")
        sha = self.write_archive(wrong_digest=True)
        with self.assertRaisesRegex(ValueError, "manifest hash or size mismatch"):
            summary.summarize_archive(self.archive, sha, "0.1067095")

    def test_traversal_absolute_backslash_and_duplicate_members_are_rejected(self):
        for bad_path in ("../outside", "/absolute", "a/../outside", "a\\outside", "C:outside"):
            with self.subTest(path=bad_path):
                entries = fixture_members()
                entries[bad_path] = entries.pop("unpublished/member_0.txt")
                sha = self.write_archive(members=entries)
                with self.assertRaisesRegex(ValueError, "unsafe archive path"):
                    summary.summarize_archive(self.archive, sha, "0.1067095")
        sha = self.write_archive(duplicate=True)
        with self.assertRaisesRegex(ValueError, "duplicate ZIP member"):
            summary.summarize_archive(self.archive, sha, "0.1067095")

    def test_archive_member_and_total_size_admission_are_bounded(self):
        sha = self.write_archive()
        for constant in ("ARCHIVE_LIMIT", "MEMBER_LIMIT", "TOTAL_LIMIT"):
            with self.subTest(limit=constant), patch.object(summary, constant, 1):
                with self.assertRaisesRegex(ValueError, "size limit exceeded"):
                    summary.summarize_archive(self.archive, sha, "0.1067095")

    def test_scientific_promotion_and_disagreement_with_accepted_score_are_rejected(self):
        entries = fixture_members()
        result = json.loads(entries[summary.SUMMARY])
        result["score_improvement_claim"] = True
        entries[summary.SUMMARY] = encoded(result)
        sha = self.write_archive(members=entries)
        with self.assertRaisesRegex(ValueError, "scientific promotion"):
            summary.summarize_archive(self.archive, sha, "0.1067095")
        sha = self.write_archive()
        with self.assertRaisesRegex(ValueError, "accepted score disagreement"):
            summary.summarize_archive(self.archive, sha, "0.1000000")

    def test_committed_public_receipt_matches_pinned_evidence_and_rejects_extra_fields(self):
        actual = summary.read_json(summary.OUTPUT.read_bytes())
        score = summary.accepted_score()
        summary.validate_snapshot(actual, score)
        for mutation in ("extra", "activity", "hash", "score", "false_as_zero"):
            changed = copy.deepcopy(actual)
            if mutation == "extra":
                changed["private_extra"] = "PRIVATE_EXTRA_INPUT_SENTINEL"
            elif mutation == "activity":
                changed["activity"]["model_fits"] = 1
            elif mutation == "hash":
                changed["provenance"]["summary_sha256"] = "0" * 64
            elif mutation == "score":
                changed["best_confirmed_brier"] = "0.1"
            else:
                changed["score_improvement_claim"] = 0
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, "snapshot"):
                summary.validate_snapshot(changed, score)

    def test_duplicate_json_keys_cannot_override_evidence(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            summary.read_json(b'{"status":"SOURCE_PARTIAL","status":"SUCCESS"}')


if __name__ == "__main__":
    unittest.main()
