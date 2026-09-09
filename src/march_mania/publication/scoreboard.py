"""Preserve observed scores and exact submission bytes across completed batches."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from march_mania.publication import refinement
from march_mania.publication.artifacts import verified_write
from march_mania.publication.submission import validate_submission
from march_mania.runtime import EventLog, TaskStore, atomic_json, digest, fingerprint

REPORT = "reports/submission_scores"


def scores(root: Path) -> pd.DataFrame:
    """Join each observation to the exact generated CSV; reject missing or stale rows."""
    original = refinement.score_table(root)
    original["batch"] = "original_50"
    provenance = json.loads((root / REPORT / "provenance.json").read_text())
    path = root / REPORT / "refinement_scores.csv"
    if digest(path) != provenance["scores_sha256"]:
        raise ValueError("Refinement score provenance mismatch")
    observed = pd.read_csv(path)
    manifest = pd.read_csv(root / refinement.REPORT / "submission_manifest.csv")
    if (
        len(observed) != 8
        or observed.isna().any().any()
        or observed.candidate_id.duplicated().any()
        or manifest.candidate_id.duplicated().any()
        or set(observed.candidate_id) != set(manifest.candidate_id)
        or not observed.source_image.eq(provenance["source_image"]).all()
        or not observed.private_brier.equals(observed.public_brier)
        or not np.isfinite(observed[["private_brier", "public_brier"]]).all().all()
        or not observed.private_brier.between(0, 1).all()
    ):
        raise ValueError("Expected all eight complete refinement observations")
    current = observed.merge(manifest, on="candidate_id", validate="one_to_one")
    current["filename"] = current.candidate_id + ".csv"
    current["status"] = provenance["status"]
    current["recorded_at_utc"] = provenance["recorded_at_utc"]
    current["batch"] = "refinement_8"
    columns = [
        "candidate_id",
        "filename",
        "batch",
        "private_brier",
        "public_brier",
        "rows",
        "bytes",
        "sha256",
        "status",
        "recorded_at_utc",
        "source_image",
    ]
    result = pd.concat([original[columns], current[columns]], ignore_index=True)
    if (
        len(result) != 58
        or result.candidate_id.duplicated().any()
        or result.sha256.duplicated().any()
        or not result.rows.eq(132133).all()
    ):
        raise ValueError("The completed collection must contain 58 distinct submissions")
    return result.sort_values(["private_brier", "candidate_id"]).reset_index(drop=True)


def review(root: Path, *, write: bool = False) -> dict[str, Any]:
    frame = scores(root)
    original_best = frame.loc[frame.batch.eq("original_50"), "private_brier"].min()
    legacy = root / "reports/submission_portfolio/kaggle_scores.csv"
    paths = [
        "src/march_mania/publication/scoreboard.py",
        REPORT + "/refinement_scores.csv",
        REPORT + "/provenance.json",
        "reports/prediction_production/kaggle_scores.csv",
        "reports/prediction_production/submission_manifest.csv",
        "reports/prediction_refinement/submission_manifest.csv",
        "reports/submission_portfolio/kaggle_scores.csv",
    ]
    payload = frame.to_csv(index=False, float_format="%.7f", lineterminator="\n").encode()
    summary = {
        "status": "verified",
        "current_submission_files": len(frame),
        "best_candidate": str(frame.iloc[0].candidate_id),
        "best_brier": float(frame.iloc[0].private_brier),
        "previous_best_brier": float(original_best),
        "absolute_improvement": float(original_best - frame.iloc[0].private_brier),
        "legacy_score_rows_preserved": len(pd.read_csv(legacy)),
        "legacy_predictions_in_current_collection": False,
        "scores_sha256": hashlib.sha256(payload).hexdigest(),
        "inputs": {name: digest(root / name) for name in paths},
        "scope": "Observed late 2026 scores; subsequent research is retrospective.",
    }
    for name, contents in {
        "kaggle_scores.csv": payload,
        "summary.json": (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(),
    }.items():
        path = root / REPORT / name
        if write:
            verified_write(path, contents, hashlib.sha256(contents).hexdigest())
        elif not path.is_file() or path.read_bytes() != contents:
            raise ValueError(f"Stale submission score report: {name}")
    return summary


def package(root: Path, original: Path, adjusted: Path) -> dict[str, Any]:
    """Package the original 58 CSVs, never rounded or regenerated predictions."""
    summary = review(root)
    table = scores(root)
    original_receipt = json.loads(
        (root / "reports/prediction_production/delivery.json").read_text()
    )["archive"]
    adjusted_receipt = json.loads((root / refinement.REPORT / "generation.json").read_text())
    archives = {"original_50": original, "refinement_8": adjusted}
    expected = {
        "original_50": original_receipt["sha256"],
        "refinement_8": adjusted_receipt["sha256"],
    }
    if any(digest(path) != expected[name] for name, path in archives.items()):
        raise ValueError("Submission input ZIP changed")
    inputs = {
        "score_inputs": summary["inputs"],
        "archives": expected,
        "readme": digest(root / REPORT / "README.md"),
    }
    key = fingerprint(inputs)
    run = root / "outputs/submission_collection" / key
    log = EventLog(run / "events.jsonl")
    store = TaskStore(run, key, log, heartbeat_seconds=15)

    def work(target: Path) -> list[Path]:
        bundle = target / "submission_collection.zip"
        baseline = None
        count = 0
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as destination:
            for batch, archive in archives.items():
                with zipfile.ZipFile(archive) as source:
                    if len(source.namelist()) != len(set(source.namelist())):
                        raise ValueError("Duplicate ZIP member")
                    for row in table.loc[table.batch.eq(batch)].itertuples(index=False):
                        data = source.read(str(row.filename))
                        if hashlib.sha256(data).hexdigest() != row.sha256 or len(data) != row.bytes:
                            raise ValueError("Submission bytes differ from their manifest")
                        frame = pd.read_csv(io.BytesIO(data), float_precision="round_trip")
                        baseline = frame if baseline is None else baseline
                        validate_submission(frame, baseline)
                        if len(frame) != row.rows:
                            raise ValueError("Submission row count changed")
                        member = zipfile.ZipInfo(str(row.filename), date_time=(2026, 9, 9, 0, 0, 0))
                        member.compress_type = zipfile.ZIP_DEFLATED
                        destination.writestr(member, data)
                        count += 1
                        log.emit(
                            "submission_preserved",
                            candidate=row.candidate_id,
                            completed=count,
                            total=58,
                        )
            extras = {
                "kaggle_scores.csv": root / REPORT / "kaggle_scores.csv",
                "README.md": root / REPORT / "README.md",
                "provenance.json": root / REPORT / "provenance.json",
                "original_score_provenance.json": root / refinement.SCORES.replace(".csv", ".json"),
                "legacy_kaggle_scores.csv": root / "reports/submission_portfolio/kaggle_scores.csv",
                "original_recipe.json": root / "reports/prediction_production/recipe.json",
                "refinement_recipe.json": root / refinement.CONFIG,
            }
            for name, path in extras.items():
                member = zipfile.ZipInfo(name, date_time=(2026, 9, 9, 0, 0, 0))
                member.compress_type = zipfile.ZIP_DEFLATED
                destination.writestr(member, path.read_bytes())
        with zipfile.ZipFile(bundle) as verify:
            for row in table.itertuples(index=False):
                if hashlib.sha256(verify.read(str(row.filename))).hexdigest() != row.sha256:
                    raise ValueError("Packaged submission checksum mismatch")
        return [bundle]

    bundle = store.task("package", work) / "submission_collection.zip"
    output = root / "submissions/submission_collection.zip"
    verified_write(output, bundle.read_bytes(), digest(bundle))
    receipt = {
        "status": "verified",
        "fingerprint": key,
        "files": 58,
        "rows_per_file": 132133,
        "new_model_fits": 0,
        "prediction_bytes_unchanged": True,
        "sha256": digest(bundle),
        "bytes": bundle.stat().st_size,
        "inputs": inputs,
    }
    atomic_json(root / REPORT / "collection.json", receipt)
    log.emit("collection_completed", files=58, new_model_fits=0)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--package", action="store_true")
    parser.add_argument("--original-archive", type=Path)
    parser.add_argument("--refinement-archive", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if args.package:
        package(
            root,
            args.original_archive or root / "submissions/prediction_portfolio.zip",
            args.refinement_archive or root / "submissions/prediction_refinement.zip",
        )
    else:
        review(root, write=args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
