"""Publish a small allowlisted receipt from one authenticated private owner return.

Regenerate: python tools/summarize_execution.py --archive /path/to/owner-return.zip
Public check: python tools/summarize_execution.py --check
No archive members are extracted or executed. The private archive is not published.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import re
import stat
import zipfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "portfolio/latest_execution.json"
RELEASE = ROOT / "portfolio/release_evidence.json"
ARCHIVE_LIMIT = 16 * 1024 * 1024
TOTAL_LIMIT = 64 * 1024 * 1024
MEMBER_LIMIT = 32 * 1024 * 1024
MEMBER_COUNT = 19
MANIFEST = "return_manifest.json"
SUMMARY = "summary.json"
FEATURES = "rebuilt_official_team_season_feature_bank.json"
PAIRS = "reconstructed_v19_source_linked_pair_bank.json"
INJURY = "injury_23_status_weight_and_team_rebuild.json"
CLOSURE = "v19_10stage_closure_and_stop_decision.json"
BLOCKERS = "v19_stages_missing_original_sources_and_models.json"
BASELINE = "recovered_strongest_baseline.json"
SOFTWARE_TESTS = "unit_tests.json"
AGGREGATE_MEMBERS = (SUMMARY, FEATURES, PAIRS, INJURY, CLOSURE, BLOCKERS, BASELINE, SOFTWARE_TESTS)
FEATURE_DATA = "official_owned_trimmed_efficiency_2003_2026.csv.gz"
PAIR_DATA = "v170_2026_owned_pair_inputs.csv.gz"
BASELINE_DATA = "restored_v155_sha_verified.csv"
PINNED_PROVENANCE = {
    "source_zip_sha256": "80fed2dbee847c2ec3986e15981802e924e4e790efc33c6dee3f10fed40a8de7",
    "manifest_sha256": "a0bba9dedc793b689e166aeffead6e12101e4e77b22127bd561f9f5d046dc2c2",
    "aggregate_receipt_sha256": {
        "execution": "b7ca3b8023006005a3e4f5bde8b2fb72449e7f11188649da6b26d76e29f08b69",
        "official_feature_coverage": (
            "5589e257daabee749830f40c8d9d3ccd1a1669a88e55bbeade03c2bc023ce32d"
        ),
        "matchup_coverage": "763291268088698d26684daac6726ec673f33b0633034d4bc3b71d239b22bc17",
        "injury_rebuild": "224080e8088c93bc44de46117cdb25b64491fac4acaf9a6a7068cd603f9e4b17",
        "admission": "fb05cdcae213bc4c6ff65bb5cb6e2fdb088b351d6568dab282e935b704591c0f",
        "unresolved_dependencies": (
            "98bf32ec1dbe14509407c30b833bfa16bb2f7388975c445a22afaa50f07b2746"
        ),
        "baseline_restoration": "dd171d7766eb552e8d0cb6cabf02dbc4dffee4098536f1bdf9c21aa55feec926",
        "software_tests": "ca30df9463718d8a2965072e67b9cc86f9b60f00b6e570198154729514513471",
    },
    "verified_manifest_members": MEMBER_COUNT,
    "only_unmanifested_member": MANIFEST,
}
VERIFICATION = (
    "Every archive member was checked against the manifest. Feature-profile and "
    "matchup counts, unique identifiers, coverage flags, and restored-probability "
    "validity were independently computed from private CSV members in memory. "
    "Regular-season game totals remain producer-reported; original game records "
    "and private forecasting stages were not independently replayed. "
    "Restoring existing prediction bytes is not a new forecast or score receipt."
)
RECENCY = (
    "Latest owner return inspected for this publication, not a claim about the globally "
    "latest AWS artifact or current live execution state."
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("EXECUTION_SUMMARY: " + message)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def read_json(content: bytes) -> dict:
    value = json.loads(content, object_pairs_hook=unique_object)
    require(isinstance(value, dict), "expected a JSON object")
    return value


def safe_member(name: str) -> None:
    require(isinstance(name, str) and bool(name), "invalid archive member name")
    require("\\" not in name and "\x00" not in name and ":" not in name, "unsafe archive path")
    require(not PurePosixPath(name).is_absolute(), "unsafe archive path")
    require(all(part not in ("", ".", "..") for part in name.split("/")), "unsafe archive path")


def accepted_score(path: Path = RELEASE) -> str:
    accepted = read_json(path.read_bytes())["scored"]["accepted"]
    require(accepted["status"] == "COMPLETE", "accepted score is not confirmed")
    score = Decimal(str(accepted["score"]))
    require(score.is_finite() and 0 <= score <= 1, "invalid accepted Brier")
    return str(score)


def inspect_archive(path: Path, expected_sha256: str) -> tuple[dict[str, bytes], dict, dict]:
    """Validate every member while retaining only allowlisted aggregate JSON objects."""
    require(path.stat().st_size <= ARCHIVE_LIMIT, "archive size limit exceeded")
    archive_digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            archive_digest.update(block)
    require(archive_digest.hexdigest() == expected_sha256, "archive SHA-256 mismatch")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        require(len(members) <= 256, "archive member limit exceeded")
        names = []
        for info in members:
            safe_member(info.filename)
            require(info.orig_filename == info.filename, "unsafe original archive path")
            require(not info.is_dir(), "directory members are not allowed")
            kind = stat.S_IFMT(info.external_attr >> 16)
            require(kind in (0, stat.S_IFREG), "linked or special archive member")
            require(not info.flag_bits & 1, "encrypted archive member")
            require(info.file_size <= MEMBER_LIMIT, "member size limit exceeded")
            names.append(info.filename)
        require(len(set(name.casefold() for name in names)) == len(names), "duplicate ZIP member")
        require(sum(info.file_size for info in members) <= TOTAL_LIMIT, "total size limit exceeded")
        require(MANIFEST in names, "missing manifest")
        manifest_info = archive.getinfo(MANIFEST)
        require(manifest_info.file_size <= 1024 * 1024, "manifest size limit exceeded")
        manifest_raw = archive.read(manifest_info)
        manifest = read_json(manifest_raw)
        artifacts = manifest["files"]
        require(
            isinstance(artifacts, list) and len(artifacts) == MEMBER_COUNT,
            "manifest count mismatch",
        )
        receipts = {}
        for item in artifacts:
            require(isinstance(item, dict), "invalid manifest artifact")
            name = item["path"]
            safe_member(name)
            require(name not in receipts and name != MANIFEST, "duplicate manifest member")
            require(type(item["size"]) is int and item["size"] >= 0, "invalid declared size")
            require(
                isinstance(item["sha256"], str)
                and re.fullmatch(r"[a-f0-9]{64}", item["sha256"]) is not None,
                "invalid declared digest",
            )
            receipts[name] = item
        require(set(receipts) == set(names) - {MANIFEST}, "manifest coverage mismatch")
        kept = {}
        total_read = 0
        for name, receipt in receipts.items():
            info = archive.getinfo(name)
            require(info.file_size == receipt["size"], "manifest size mismatch")
            member_digest = hashlib.sha256()
            size = 0
            retained = bytearray()
            with archive.open(info) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    size += len(block)
                    total_read += len(block)
                    require(
                        size <= MEMBER_LIMIT and total_read <= TOTAL_LIMIT,
                        "decompression bound exceeded",
                    )
                    member_digest.update(block)
                    if name in AGGREGATE_MEMBERS:
                        require(size <= 1024 * 1024, "aggregate JSON size limit exceeded")
                        retained.extend(block)
            require(
                size == receipt["size"] and member_digest.hexdigest() == receipt["sha256"],
                "manifest hash or size mismatch",
            )
            if name in AGGREGATE_MEMBERS:
                kept[name] = bytes(retained)
        require(set(kept) == set(AGGREGATE_MEMBERS), "missing aggregate receipt")
        provenance = {
            "source_zip_sha256": expected_sha256,
            "manifest_sha256": digest(manifest_raw),
            "aggregate_receipt_sha256": {
                label: digest(kept[name])
                for label, name in zip(
                    PINNED_PROVENANCE["aggregate_receipt_sha256"], AGGREGATE_MEMBERS, strict=True
                )
            },
            "verified_manifest_members": len(receipts),
            "only_unmanifested_member": MANIFEST,
        }
        independent = verify_private_tables(archive)
    return kept, provenance, independent


def csv_rows(archive: zipfile.ZipFile, name: str, required: set[str]):
    """Stream bounded private rows; never extract files or return their values publicly."""
    total_chars = 0
    with archive.open(name) as raw:
        binary = gzip.GzipFile(fileobj=raw) if name.endswith(".gz") else raw
        with io.TextIOWrapper(binary, encoding="utf-8", newline="") as stream:
            rows = csv.DictReader(stream)
            headers = rows.fieldnames
            require(
                headers is not None
                and len(set(headers)) == len(headers)
                and required <= set(headers),
                "private CSV header mismatch",
            )
            require(len(headers) <= 64, "private CSV column limit exceeded")
            for count, row in enumerate(rows, start=1):
                require(count <= 150000, "private CSV row limit exceeded")
                require(
                    None not in row and all(value is not None for value in row.values()),
                    "private CSV row width mismatch",
                )
                total_chars += sum(len(value) + 1 for value in row.values())
                require(total_chars <= TOTAL_LIMIT, "private CSV decompression limit exceeded")
                yield row


def canonical_matchup(identifier: str) -> str:
    require(
        re.fullmatch(r"2026_[13][0-9]{3}_[13][0-9]{3}", identifier) is not None,
        "invalid matchup identifier",
    )
    _, first, second = identifier.split("_")
    require(first < second and first[0] == second[0], "invalid matchup team order")
    return "M" if first[0] == "1" else "W"


def verify_private_tables(archive: zipfile.ZipFile) -> dict:
    """Independently compute only aggregate integrity facts from authenticated CSV bytes."""
    require(
        {FEATURE_DATA, PAIR_DATA, BASELINE_DATA} <= set(archive.namelist()),
        "missing private verification table",
    )
    profiles = set()
    profile_counts = {"M": 0, "W": 0}
    for row in csv_rows(archive, FEATURE_DATA, {"Sex", "Season", "TeamID"}):
        require(row["Sex"] in profile_counts, "invalid feature category")
        require(re.fullmatch(r"[0-9]{4}", row["Season"]) is not None, "invalid feature season")
        require(re.fullmatch(r"[13][0-9]{3}", row["TeamID"]) is not None, "invalid feature team")
        identity = (row["Sex"], row["Season"], row["TeamID"])
        require(identity not in profiles, "duplicate feature profile")
        profiles.add(identity)
        profile_counts[row["Sex"]] += 1
    pair_ids = set()
    pair_counts = {"M": 0, "W": 0}
    coverage_count = 0
    for row in csv_rows(
        archive,
        PAIR_DATA,
        {"ID", "Sex", "OfficialFeaturesPresent", "GameEffDiff", "WinPctDiff"},
    ):
        sex = canonical_matchup(row["ID"])
        require(row["Sex"] == sex, "matchup category disagreement")
        require(row["ID"] not in pair_ids, "duplicate matchup identifier")
        require(row["OfficialFeaturesPresent"] == "1", "missing official matchup features")
        season, first, second = row["ID"].split("_")
        require(
            (sex, season, first) in profiles and (sex, season, second) in profiles,
            "matchup team missing official feature profile",
        )
        for key in ("GameEffDiff", "WinPctDiff"):
            try:
                value = float(row[key])
            except ValueError:
                raise ValueError("EXECUTION_SUMMARY: invalid official matchup feature") from None
            require(math.isfinite(value), "invalid official matchup feature")
        pair_ids.add(row["ID"])
        pair_counts[sex] += 1
        coverage_count += 1
    baseline_ids = set()
    valid_probabilities = 0
    for row in csv_rows(archive, BASELINE_DATA, {"ID", "Pred"}):
        canonical_matchup(row["ID"])
        require(row["ID"] not in baseline_ids, "duplicate baseline identifier")
        baseline_ids.add(row["ID"])
        try:
            probability = float(row["Pred"])
        except ValueError:
            raise ValueError("EXECUTION_SUMMARY: invalid baseline probability") from None
        require(
            math.isfinite(probability) and 0 <= probability <= 1, "invalid baseline probability"
        )
        valid_probabilities += 1
    require(pair_ids == baseline_ids, "matchup and baseline identifier disagreement")
    return {
        "feature_profile_rows": len(profiles),
        "unique_feature_profiles": len(profiles),
        "men_feature_profile_rows": profile_counts["M"],
        "women_feature_profile_rows": profile_counts["W"],
        "matchup_rows": len(pair_ids),
        "unique_matchup_ids": len(pair_ids),
        "men_matchup_rows": pair_counts["M"],
        "women_matchup_rows": pair_counts["W"],
        "matchups_with_official_features": coverage_count,
        "restored_forecast_rows": len(baseline_ids),
        "unique_restored_forecast_ids": len(baseline_ids),
        "finite_probabilities_in_unit_interval": valid_probabilities,
        "matchup_ids_equal_restored_forecast_ids": True,
        "method": "streamed_private_archive_csv_members_in_memory",
    }


def assert_int(value: object, expected: int, message: str) -> None:
    require(type(value) is int and value == expected, message)


def public_fields(score: str) -> dict:
    """The complete disclosure contract; private fields never pass through this object."""
    return {
        "schema": 2,
        "scope": "latest_inspected_owner_return",
        "recorded_ended_utc": "2026-10-14T00:34:11.305161Z",
        "version": "v170-owned-source-rebuild-20261013",
        "run_id": "20261014T003403546859Z-5ffbd983",
        "status": "SOURCE_REBUILD_COMPLETED_ADMISSION_BLOCKED",
        "producer_reported_status": "V170_COMPLETED_REBUILD_NO_QUALIFIED_SUBMISSION",
        "previously_published_accepted_brier": score,
        "new_score_receipt_present": False,
        "activity": {"restored_baselines": 1, "new_candidates": 0, "submissions": 0},
        "score_improvement_claim": False,
        "historical_gate_passed": False,
        "full_forecast_reconstruction_complete": False,
        "source_vintage": "retrospective_2026",
        "target_tournament_outcomes_loaded": False,
        "source_engineering": {
            "official_feature_coverage": {
                "men": {
                    "regular_season_games": 124529,
                    "team_seasons": 8346,
                    "earliest_season": 2003,
                    "latest_season": 2026,
                },
                "women": {
                    "regular_season_games": 87187,
                    "team_seasons": 5965,
                    "earliest_season": 2010,
                    "latest_season": 2026,
                },
            },
            "matchup_rows": 132133,
            "men_matchup_rows": 66430,
            "women_matchup_rows": 65703,
            "official_features_present_for_all_matchups": True,
            "injury_recomputed_in_this_execution": False,
            "full_original_source_qualification": False,
        },
        "independent_verification": {
            "feature_profile_rows": 14311,
            "unique_feature_profiles": 14311,
            "men_feature_profile_rows": 8346,
            "women_feature_profile_rows": 5965,
            "matchup_rows": 132133,
            "unique_matchup_ids": 132133,
            "men_matchup_rows": 66430,
            "women_matchup_rows": 65703,
            "matchups_with_official_features": 132133,
            "restored_forecast_rows": 132133,
            "unique_restored_forecast_ids": 132133,
            "finite_probabilities_in_unit_interval": 132133,
            "matchup_ids_equal_restored_forecast_ids": True,
            "method": "streamed_private_archive_csv_members_in_memory",
        },
        "unresolved_dependencies": [
            "Historical source versions and complete provider coverage",
            "Injury input schema compatibility and status reconstruction",
            "Private model checkpoints and ordered forecast reproduction",
            "Historical admission of a newly reconstructed candidate",
        ],
        "producer_software_tests": {"passed": 7, "failures": 0, "errors": 0},
        "verification_scope": VERIFICATION,
        "recency_scope": RECENCY,
    }


def summarize_archive(path: Path, expected_sha256: str, score: str) -> dict:
    kept, provenance, independent = inspect_archive(path, expected_sha256)
    execution, features, pairs, injury, closure, blockers, baseline, tests = (
        read_json(kept[name]) for name in AGGREGATE_MEMBERS
    )
    require(
        execution["status"] == "V170_COMPLETED_REBUILD_NO_QUALIFIED_SUBMISSION"
        and execution["failure"] is None,
        "unexpected producer execution outcome",
    )
    require(
        execution["schema"] == "v170_owned_v19_primary_source_closure_20261013",
        "unexpected producer schema",
    )
    for key in (
        "2026_outcomes_loaded",
        "kaggle_submission_attempted",
        "new_candidate",
        "qualifying_new_submission",
    ):
        require(execution[key] is False, "unexpected scientific promotion claim")
    require(execution["labelling"] == "2026_RETROSPECTIVE_ONLY", "unexpected source vintage")
    for key in (
        "full_forecast",
        "full_source_qualified",
        "historical_admission",
        "kaggle_submit_attempted",
    ):
        require(closure[key] is False, "unexpected scientific promotion claim")
    require(
        blockers["exact_legacy_parity"] == "NOT_ESTABLISHED"
        and blockers["full_10stage_candidate_qualified"] is False,
        "unexpected reconstruction completion claim",
    )
    assert_int(blockers["historical_2026_tournament_labels_used"], 0, "target outcome disagreement")
    require(injury["fully_recomputed"] is False, "unexpected injury rebuild completion")
    assert_int(injury["target_players"], 0, "injury rebuild count disagreement")
    require(
        pairs["no_2026_outcome_columns"] is True
        and pairs["no_borrowed_competitor_numerics"] is True,
        "matchup source policy disagreement",
    )
    result = public_fields(score)
    require(
        independent == result["independent_verification"],
        "independently computed table integrity disagrees with published counts",
    )
    result["independent_verification"] = independent
    for category, sex in (("men", "M"), ("women", "W")):
        actual = features["coverage"][sex]
        expected = result["source_engineering"]["official_feature_coverage"][category]
        for public_key, source_key in (
            ("regular_season_games", "regular_games"),
            ("team_seasons", "team_seasons"),
            ("earliest_season", "earliest_season"),
            ("latest_season", "latest_season"),
        ):
            assert_int(actual[source_key], expected[public_key], "official coverage disagreement")
        expected_pairs = result["source_engineering"][f"{category}_matchup_rows"]
        for key in (f"{sex}_pairs", f"{sex}_OfficialFeaturesPresent"):
            assert_int(
                pairs["sex_counts_and_coverage"][key],
                expected_pairs,
                "matchup coverage disagreement",
            )
        assert_int(baseline[category], expected_pairs, "baseline coverage disagreement")
    assert_int(pairs["rows"], 132133, "matchup row disagreement")
    assert_int(baseline["rows"], 132133, "baseline row disagreement")
    require(
        baseline["sha256"]
        == execution["base_v155_sha"]
        == "432be1110f99f867009671367abd40a27637b966e3ffe64bc9ef00d81d061d0d",
        "baseline restoration digest disagreement",
    )
    for key, expected in result["producer_software_tests"].items():
        assert_int(tests[key], expected, "producer software test disagreement")
    require(tests["software_only"] is True, "unexpected model validation claim")
    ended = execution["finished_utc"]
    require(isinstance(ended, str) and ended.endswith("Z"), "missing recorded UTC time")
    datetime.fromisoformat(ended.replace("Z", "+00:00"))
    require(ended == result["recorded_ended_utc"], "execution timestamp disagreement")
    require(execution["run_id"] == result["run_id"], "execution identity disagreement")
    # Older score references in producer summaries are not new Kaggle receipts.
    # Preserve only the separately authenticated public release score.
    result["provenance"] = provenance
    return result


def validate_snapshot(snapshot: dict, score: str) -> None:
    expected = public_fields(score)
    expected["provenance"] = PINNED_PROVENANCE
    # Serialized equality rejects bool/int substitutions and additional private keys.
    require(
        json.dumps(snapshot, sort_keys=True) == json.dumps(expected, sort_keys=True),
        "public snapshot fields or provenance disagree",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--archive", type=Path)
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    score = accepted_score()
    if args.check:
        validate_snapshot(read_json(args.output.read_bytes()), score)
    else:
        snapshot = summarize_archive(args.archive, PINNED_PROVENANCE["source_zip_sha256"], score)
        validate_snapshot(snapshot, score)
        args.output.write_text(
            json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "scope": "latest_inspected_owner_return",
                "private_predictions_replayed": False,
            }
        )
    )


if __name__ == "__main__":
    main()
