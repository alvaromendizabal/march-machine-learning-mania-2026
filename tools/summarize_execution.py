"""Publish a small allowlisted receipt from one authenticated private owner return.

Regenerate: python tools/summarize_execution.py --archive /path/to/owner-return.zip
Public check: python tools/summarize_execution.py --check
No archive members are extracted or executed. The private archive is not published.
"""

from __future__ import annotations

import argparse
import hashlib
import json
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
MEMBER_COUNT = 75
SUMMARY = "summary.json"
REPAIR = "market_repair/repair_receipt.json"
INJURY = "new_original_sources/provider_injury_sources/provider_acquisition_result.json"
PINNED_PROVENANCE = {
    "source_zip_sha256": "12c77d28998170dc7afd53b6d2d81706182a45da83f216244d855e6c4dafb99b",
    "manifest_sha256": "0cbff9a4af630c8dd71e7a97225ff28716e6c2f40b340a0c054bb6f1f8a55fac",
    "summary_sha256": "5d6392195f623e276ff3aea64a8a08797f136def2669acc122f6c0df36a8994a",
    "repair_receipt_sha256": "f004f423cb9447ad037c67671027e8d149fcd66cc5b22b6788514ae7fbec5de6",
    "injury_receipt_sha256": "ce49352b800546fb19bec234c25e9eed0fed62f835c0de3a1fc32b6ebb32c995",
    "verified_manifest_members": MEMBER_COUNT,
    "only_unmanifested_member": "manifest.json",
}
VERIFICATION = (
    "Derived from an inspected owner return. Archive integrity was verified; "
    "private predictions were not independently replayed."
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


def inspect_archive(path: Path, expected_sha256: str) -> tuple[dict[str, bytes], dict]:
    """Validate every member while retaining only three small aggregate JSON objects."""
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
        require("manifest.json" in names, "missing manifest")
        manifest_info = archive.getinfo("manifest.json")
        require(manifest_info.file_size <= 1024 * 1024, "manifest size limit exceeded")
        manifest_raw = archive.read(manifest_info)
        manifest = read_json(manifest_raw)
        artifacts = manifest["artifacts"]
        require(
            isinstance(artifacts, list) and len(artifacts) == MEMBER_COUNT,
            "manifest count mismatch",
        )
        receipts = {}
        for item in artifacts:
            require(isinstance(item, dict), "invalid manifest artifact")
            name = item["path"]
            safe_member(name)
            require(name not in receipts and name != "manifest.json", "duplicate manifest member")
            require(
                type(item["size_bytes"]) is int and item["size_bytes"] >= 0, "invalid declared size"
            )
            require(
                isinstance(item["sha256"], str)
                and re.fullmatch(r"[a-f0-9]{64}", item["sha256"]) is not None,
                "invalid declared digest",
            )
            require(item["required_for_return"] is True, "unrequired manifest member")
            receipts[name] = item
        require(set(receipts) == set(names) - {"manifest.json"}, "manifest coverage mismatch")
        required = manifest["required_members"]
        require(
            isinstance(required, list)
            and len(required) == MEMBER_COUNT
            and set(required) == set(receipts),
            "required member coverage mismatch",
        )
        kept = {}
        total_read = 0
        for name, receipt in receipts.items():
            info = archive.getinfo(name)
            require(info.file_size == receipt["size_bytes"], "manifest size mismatch")
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
                    if name in (SUMMARY, REPAIR, INJURY):
                        require(size <= 1024 * 1024, "aggregate JSON size limit exceeded")
                        retained.extend(block)
            require(
                size == receipt["size_bytes"] and member_digest.hexdigest() == receipt["sha256"],
                "manifest hash or size mismatch",
            )
            if name in (SUMMARY, REPAIR, INJURY):
                kept[name] = bytes(retained)
        require(set(kept) == {SUMMARY, REPAIR, INJURY}, "missing aggregate receipt")
        provenance = {
            "source_zip_sha256": expected_sha256,
            "manifest_sha256": digest(manifest_raw),
            "summary_sha256": digest(kept[SUMMARY]),
            "repair_receipt_sha256": digest(kept[REPAIR]),
            "injury_receipt_sha256": digest(kept[INJURY]),
            "verified_manifest_members": len(receipts),
            "only_unmanifested_member": "manifest.json",
        }
    return kept, provenance


def summarize_archive(path: Path, expected_sha256: str, score: str) -> dict:
    kept, provenance = inspect_archive(path, expected_sha256)
    summary, repair, injury = (read_json(kept[name]) for name in (SUMMARY, REPAIR, INJURY))
    require(summary["status"] == "SOURCE_PARTIAL", "unexpected execution outcome")
    require(
        repair["status"] == "PASS" and injury["status"] == "SOURCE_PARTIAL",
        "source component status mismatch",
    )
    require(
        Decimal(str(summary["current_best_confirmed_kaggle_brier"])) == Decimal(score),
        "accepted score disagreement",
    )
    for key in (
        "model_fits",
        "model_fits_completed",
        "model_inferences",
        "model_inferences_completed",
        "new_candidates",
        "submissions",
    ):
        require(
            type(summary[key]) is int and summary[key] == 0,
            "unexpected model or submission activity",
        )
    for key in (
        "score_improvement_claim",
        "historical_gate_passed",
        "all_gaps_closed",
        "candidate_written",
        "submission_attempted",
        "target_score_computed",
        "exact_v19_recreated",
    ):
        require(summary[key] is False, "unexpected scientific promotion claim")
    for key in ("model_fits", "model_inferences", "submissions"):
        require(type(repair[key]) is int and repair[key] == 0, "repair activity disagreement")
    require(
        summary["quote_rows_reparsed"] == summary["repaired_quote_rows"] == repair["rows"] == 2258,
        "repaired quote count disagreement",
    )
    require(
        repair["last_missing_retained"] == 1075 and repair["eligible_model_feature"] is False,
        "source admission disagreement",
    )
    require(
        injury["exact23_injury_values_reconstructed"] is False
        and injury["model_admitted_BPR"] == 0
        and injury["proven_legacy_BPR_parity"] == 0,
        "injury completion disagreement",
    )
    require(
        summary["components"]["market_repair"] == repair
        and summary["components"]["provider_sources"] == injury,
        "component receipt disagreement",
    )
    ended = summary["ended_utc"]
    require(isinstance(ended, str) and ended.endswith("Z"), "missing recorded UTC time")
    datetime.fromisoformat(ended.replace("Z", "+00:00"))
    require(
        re.fullmatch(r"v\d+-[a-z0-9-]+", summary["version"]) is not None, "invalid public version"
    )
    require(
        re.fullmatch(r"\d{8}T\d{12}Z-[a-f0-9]{8}", summary["run_id"]) is not None,
        "invalid public run identity",
    )
    # Construct a new object. Never copy producer dictionaries or private detail fields.
    return {
        "schema": 1,
        "scope": "latest_inspected_owner_return",
        "recorded_ended_utc": ended,
        "version": summary["version"],
        "run_id": summary["run_id"],
        "status": summary["status"],
        "best_confirmed_brier": score,
        "activity": {"model_fits": 0, "model_inferences": 0, "new_candidates": 0, "submissions": 0},
        "score_improvement_claim": False,
        "historical_gate_passed": False,
        "source_engineering": {
            "repaired_quote_rows": repair["rows"],
            "missing_last_quote_rows_retained": repair["last_missing_retained"],
            "eligible_model_feature": False,
            "original_injury_inputs_complete": False,
        },
        "provenance": provenance,
        "verification_scope": VERIFICATION,
        "recency_scope": RECENCY,
    }


def validate_snapshot(snapshot: dict, score: str) -> None:
    expected = {
        "schema": 1,
        "scope": "latest_inspected_owner_return",
        "recorded_ended_utc": "2026-10-10T01:32:58.968371Z",
        "version": "v128-owned-source-repair-20261010",
        "run_id": "20261010T013254065226Z-2d8e2bc2",
        "status": "SOURCE_PARTIAL",
        "best_confirmed_brier": score,
        "activity": {"model_fits": 0, "model_inferences": 0, "new_candidates": 0, "submissions": 0},
        "score_improvement_claim": False,
        "historical_gate_passed": False,
        "source_engineering": {
            "repaired_quote_rows": 2258,
            "missing_last_quote_rows_retained": 1075,
            "eligible_model_feature": False,
            "original_injury_inputs_complete": False,
        },
        "provenance": PINNED_PROVENANCE,
        "verification_scope": VERIFICATION,
        "recency_scope": RECENCY,
    }
    # Serialized equality also rejects bool/int substitutions and additional keys.
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
