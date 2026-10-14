"""Offline regression checks for sanitized owner-return publication."""

from __future__ import annotations

import copy
import functools
import gzip
import importlib.util
import itertools
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


@functools.cache
def fixture_tables() -> dict[str, bytes]:
    feature_lines = ["Sex,Season,TeamID"]
    for sex, total, first_year, team_start, teams in (
        ("M", 8346, 2003, 1000, 365),
        ("W", 5965, 2010, 3000, 363),
    ):
        feature_lines.extend(f"{sex},2026,{team_start + i}" for i in range(teams))
        feature_lines.extend(
            f"{sex},{first_year + i // 365},{team_start + i % 365}" for i in range(total - teams)
        )
    pair_lines = ["ID,Sex,OfficialFeaturesPresent,GameEffDiff,WinPctDiff"]
    baseline_lines = ["ID,Pred"]
    for sex, teams in (("M", range(1000, 1365)), ("W", range(3000, 3363))):
        for first, second in itertools.combinations(teams, 2):
            identifier = f"2026_{first}_{second}"
            pair_lines.append(f"{identifier},{sex},1,0,0")
            baseline_lines.append(f"{identifier},0.5")
    return {
        summary.FEATURE_DATA: gzip.compress(("\n".join(feature_lines) + "\n").encode()),
        summary.PAIR_DATA: gzip.compress(("\n".join(pair_lines) + "\n").encode()),
        summary.BASELINE_DATA: ("\n".join(baseline_lines) + "\n").encode(),
    }


def fixture_members() -> dict[str, bytes]:
    public = summary.public_fields("0.1067095")
    baseline_sha = "432be1110f99f867009671367abd40a27637b966e3ffe64bc9ef00d81d061d0d"
    execution = {
        "status": "V170_COMPLETED_REBUILD_NO_QUALIFIED_SUBMISSION",
        "schema": "v170_owned_v19_primary_source_closure_20261013",
        "failure": None,
        "finished_utc": public["recorded_ended_utc"],
        "run_id": public["run_id"],
        "labelling": "2026_RETROSPECTIVE_ONLY",
        "base_v155_sha": baseline_sha,
        # An inherited producer assertion must not promote the published score.
        "best_own_scored_v155": 0.00001,
        "private_recipe": {"details": "PRIVATE_EXTRA_INPUT_SENTINEL"},
    }
    for key in (
        "2026_outcomes_loaded",
        "kaggle_submission_attempted",
        "new_candidate",
        "qualifying_new_submission",
    ):
        execution[key] = False
    coverage = {}
    for category, sex in (("men", "M"), ("women", "W")):
        expected = public["source_engineering"]["official_feature_coverage"][category]
        coverage[sex] = {
            "regular_games": expected["regular_season_games"],
            "team_seasons": expected["team_seasons"],
            "earliest_season": expected["earliest_season"],
            "latest_season": expected["latest_season"],
            "source_file": "/PRIVATE_EXTRA_INPUT_SENTINEL/source.csv",
        }
    objects = {
        summary.SUMMARY: execution,
        summary.FEATURES: {"coverage": coverage},
        summary.PAIRS: {
            "rows": 132133,
            "no_2026_outcome_columns": True,
            "no_borrowed_competitor_numerics": True,
            "sex_counts_and_coverage": {
                "M_pairs": 66430,
                "M_OfficialFeaturesPresent": 66430,
                "W_pairs": 65703,
                "W_OfficialFeaturesPresent": 65703,
            },
        },
        summary.INJURY: {"fully_recomputed": False, "target_players": 0},
        summary.CLOSURE: {
            "full_forecast": False,
            "full_source_qualified": False,
            "historical_admission": False,
            "kaggle_submit_attempted": False,
        },
        summary.BLOCKERS: {
            "exact_legacy_parity": "NOT_ESTABLISHED",
            "full_10stage_candidate_qualified": False,
            "historical_2026_tournament_labels_used": 0,
        },
        summary.BASELINE: {
            "men": 66430,
            "women": 65703,
            "rows": 132133,
            "sha256": baseline_sha,
        },
        summary.SOFTWARE_TESTS: {"passed": 7, "failures": 0, "errors": 0, "software_only": True},
    }
    for value in objects.values():
        value["private_extra"] = "PRIVATE_EXTRA_INPUT_SENTINEL"
    members = {name: encoded(value) for name, value in objects.items()}
    members.update(fixture_tables())
    members.update(
        {f"unpublished/member_{i}.txt": b"PRIVATE_EXTRA_INPUT_SENTINEL" for i in range(8)}
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
                "size": len(content),
                "sha256": summary.digest(content),
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
                        summary.MANIFEST,
                        encoded({"files": records}),
                    )
        return summary.digest(self.archive.read_bytes())

    def test_verified_aggregate_is_allowlisted_and_never_extracts_or_copies_extra_fields(self):
        sha = self.write_archive()
        with (
            patch.object(zipfile.ZipFile, "extract", side_effect=AssertionError("extraction")),
            patch.object(zipfile.ZipFile, "extractall", side_effect=AssertionError("extraction")),
        ):
            result = summary.summarize_archive(self.archive, sha, "0.1067095")
        self.assertEqual(result["status"], "SOURCE_REBUILD_COMPLETED_ADMISSION_BLOCKED")
        self.assertEqual(result["provenance"]["verified_manifest_members"], 19)
        self.assertEqual(result["source_engineering"]["matchup_rows"], 132133)
        self.assertFalse(result["source_engineering"]["full_original_source_qualification"])
        self.assertEqual(
            result["activity"], {"restored_baselines": 1, "new_candidates": 0, "submissions": 0}
        )
        self.assertFalse(result["new_score_receipt_present"])
        self.assertEqual(result["independent_verification"]["feature_profile_rows"], 14311)
        self.assertEqual(result["independent_verification"]["unique_matchup_ids"], 132133)
        self.assertEqual(
            result["independent_verification"]["finite_probabilities_in_unit_interval"], 132133
        )
        self.assertEqual(result["previously_published_accepted_brier"], "0.1067095")
        self.assertNotIn("0.00001", json.dumps(result))
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

    def test_scientific_promotion_and_cross_receipt_disagreement_are_rejected(self):
        mutations = (
            (summary.SUMMARY, "new_candidate", True, "scientific promotion"),
            (summary.SUMMARY, "2026_outcomes_loaded", True, "scientific promotion"),
            (summary.CLOSURE, "full_source_qualified", True, "scientific promotion"),
            (summary.CLOSURE, "historical_admission", True, "scientific promotion"),
            (summary.INJURY, "fully_recomputed", True, "injury rebuild"),
            (summary.BASELINE, "rows", 132132, "baseline row disagreement"),
            (summary.SOFTWARE_TESTS, "failures", True, "software test disagreement"),
        )
        for member, key, value, error in mutations:
            with self.subTest(member=member, key=key):
                entries = fixture_members()
                result = json.loads(entries[member])
                result[key] = value
                entries[member] = encoded(result)
                sha = self.write_archive(members=entries)
                with self.assertRaisesRegex(ValueError, error):
                    summary.summarize_archive(self.archive, sha, "0.1067095")

    def test_manifest_must_cover_every_archive_member(self):
        sha = self.write_archive()
        with zipfile.ZipFile(self.archive, "a") as archive:
            archive.writestr("unmanifested.txt", "PRIVATE_EXTRA_INPUT_SENTINEL")
        sha = summary.digest(self.archive.read_bytes())
        with self.assertRaisesRegex(ValueError, "manifest coverage mismatch"):
            summary.summarize_archive(self.archive, sha, "0.1067095")

    def test_private_table_corruption_rejected_even_with_matching_new_manifest(self):
        for value in ("nan", "inf", "-0.1", "1.1", "not-a-number"):
            with self.subTest(probability=value):
                entries = fixture_members()
                entries[summary.BASELINE_DATA] = entries[summary.BASELINE_DATA].replace(
                    b",0.5\n", f",{value}\n".encode(), 1
                )
                sha = self.write_archive(members=entries)
                with self.assertRaisesRegex(ValueError, "invalid baseline probability"):
                    summary.summarize_archive(self.archive, sha, "0.1067095")
        for member, error in (
            (summary.BASELINE_DATA, "duplicate baseline identifier"),
            (summary.PAIR_DATA, "duplicate matchup identifier"),
            (summary.FEATURE_DATA, "duplicate feature profile"),
        ):
            with self.subTest(member=member):
                entries = fixture_members()
                raw = (
                    gzip.decompress(entries[member]) if member.endswith(".gz") else entries[member]
                )
                raw += raw.splitlines(keepends=True)[1]
                entries[member] = gzip.compress(raw) if member.endswith(".gz") else raw
                sha = self.write_archive(members=entries)
                with self.assertRaisesRegex(ValueError, error):
                    summary.summarize_archive(self.archive, sha, "0.1067095")

    def test_claimed_coverage_and_counts_must_match_private_rows(self):
        entries = fixture_members()
        raw = gzip.decompress(entries[summary.PAIR_DATA])
        entries[summary.PAIR_DATA] = gzip.compress(raw.replace(b",M,1,0,0\n", b",M,0,0,0\n", 1))
        sha = self.write_archive(members=entries)
        with self.assertRaisesRegex(ValueError, "missing official matchup features"):
            summary.summarize_archive(self.archive, sha, "0.1067095")
        entries = fixture_members()
        raw = gzip.decompress(entries[summary.FEATURE_DATA])
        entries[summary.FEATURE_DATA] = gzip.compress(b"\n".join(raw.splitlines()[:-1]) + b"\n")
        sha = self.write_archive(members=entries)
        with self.assertRaisesRegex(ValueError, "independently computed table integrity"):
            summary.summarize_archive(self.archive, sha, "0.1067095")

    def test_matchup_sets_and_official_feature_values_are_checked(self):
        entries = fixture_members()
        entries[summary.BASELINE_DATA] = entries[summary.BASELINE_DATA].replace(
            b"2026_1000_1001", b"2026_1998_1999", 1
        )
        sha = self.write_archive(members=entries)
        with self.assertRaisesRegex(ValueError, "identifier disagreement"):
            summary.summarize_archive(self.archive, sha, "0.1067095")
        entries = fixture_members()
        raw = gzip.decompress(entries[summary.PAIR_DATA])
        entries[summary.PAIR_DATA] = gzip.compress(raw.replace(b",M,1,0,0\n", b",M,1,nan,0\n", 1))
        sha = self.write_archive(members=entries)
        with self.assertRaisesRegex(ValueError, "invalid official matchup feature"):
            summary.summarize_archive(self.archive, sha, "0.1067095")

    def test_committed_public_receipt_matches_pinned_evidence_and_rejects_extra_fields(self):
        actual = summary.read_json(summary.OUTPUT.read_bytes())
        score = summary.accepted_score()
        summary.validate_snapshot(actual, score)
        for mutation in ("extra", "activity", "hash", "score", "false_as_zero"):
            changed = copy.deepcopy(actual)
            if mutation == "extra":
                changed["private_extra"] = "PRIVATE_EXTRA_INPUT_SENTINEL"
            elif mutation == "activity":
                changed["activity"]["submissions"] = 1
            elif mutation == "hash":
                changed["provenance"]["aggregate_receipt_sha256"]["execution"] = "0" * 64
            elif mutation == "score":
                changed["previously_published_accepted_brier"] = "0.1"
            else:
                changed["score_improvement_claim"] = 0
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, "snapshot"):
                summary.validate_snapshot(changed, score)

    def test_duplicate_json_keys_cannot_override_evidence(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            summary.read_json(b'{"status":"SOURCE_PARTIAL","status":"SUCCESS"}')


if __name__ == "__main__":
    unittest.main()
