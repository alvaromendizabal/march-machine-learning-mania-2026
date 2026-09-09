"""Recompute every archived probability chunk from saved models, without fitting."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from march_mania.publication import production, production_inputs, production_release
from march_mania.runtime import EventLog, atomic_json, digest


def verify(root: Path, run: Path, inputs: Path, receipt: Path) -> dict:
    summary = production_release.check(root)
    before = production_release.verify_tasks(run, summary["fingerprint"])
    manifest = json.loads((run / "manifest.json").read_text())
    published = json.loads((root / production.REPORT / "run.json").read_text())
    if manifest != {"fingerprint": summary["fingerprint"], "inputs": published["inputs"]}:
        raise ValueError("Verification run differs from the published production lineage")
    if production_inputs.verify(root, inputs) != manifest["inputs"]["inputs"]:
        raise ValueError("Verification inputs differ from the fitted run")
    recipe = manifest["inputs"]["recipe"]
    config = manifest["inputs"]["config"]
    models = {
        (component, route): joblib.load(run / f"fit_{component}_{route}" / "model.joblib")
        for component in recipe["components"]
        for route in production.ROUTES
    }
    teams = pd.read_parquet(inputs / "feature_store/run/teams.parquet")
    teams = teams.loc[teams.Season == 2026]
    sample = pd.read_csv(inputs / "feature_store/raw/SampleSubmissionStage2.csv")
    pairs = production.sample_pairs(sample, teams)
    chunk_size = min(config["chunk_size"], 512)
    log = EventLog(receipt.with_suffix(".jsonl"))
    chunks = 0
    for start in range(0, len(sample), chunk_size):
        features = production.pair_features(teams, pairs.iloc[start : start + chunk_size])
        actual = production.predict_chunk(features, recipe, models, config["threads"])
        expected = pd.read_parquet(run / f"predict_{start:06d}" / "predictions.parquet")
        pd.testing.assert_frame_equal(actual, expected, check_exact=True)
        chunks += 1
        log.emit(
            "saved_models_verified",
            completed=min(start + chunk_size, len(sample)),
            total=len(sample),
            chunks=chunks,
        )
    if production_release.verify_tasks(run, summary["fingerprint"]) != before:
        raise ValueError("Final prediction files changed during independent verification")
    result = {
        "status": "verified",
        "fingerprint": summary["fingerprint"],
        "fitted_models_verified": summary["fitted_models"],
        "neutral_routes_verified": summary["neutral_routes"],
        "prediction_chunks_recomputed": chunks,
        "rows_verified": len(sample),
        "submission_files_unchanged": len(before),
        "new_fits": 0,
        "probability_comparison": "Exact equality, including all route and stream columns",
        "verification_source_sha256": digest(Path(__file__)),
    }
    atomic_json(receipt, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--inputs", type=Path, default=Path("outputs/production_inputs"))
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(verify(root, args.run, args.inputs, args.receipt), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
