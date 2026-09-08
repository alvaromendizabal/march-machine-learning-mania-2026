"""Notebook-controlled research with explicit data lineage and no Kaggle upload."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from march_mania import feature_store, modeling
from march_mania.publication.artifacts import download_input, safe_path, verified_write
from march_mania.runtime import EventLog, Mirror, atomic_json, digest, fingerprint

S3_PREFIX = "s3://sagemaker-march-mania-560403859723-us-west-2/final-predictions/notebook-research"


def execution_mode() -> str:
    mode = os.environ.get("MARCH_NOTEBOOK_MODE", "review")
    if mode not in {"review", "train"}:
        raise ValueError("MARCH_NOTEBOOK_MODE must be review or train")
    return mode


def evidence(root: Path, name: str) -> tuple[Path, dict[str, Any]]:
    """Review committed evidence, not an arbitrary older local latest pointer."""
    folder = safe_path(root / "reports", name)
    record = json.loads((folder / "run.json").read_text())
    for filename, expected in record["sha256"].items():
        if digest(safe_path(folder, filename)) != expected:
            raise ValueError(f"Changed {name} evidence: {filename}")
    if record["summary"]["status"] != "completed":
        raise ValueError(f"Incomplete {name} evidence")
    return folder, record


def lineage(root: Path) -> pd.DataFrame:
    """Prove the feature-to-model dependency; separate old research from current models."""
    _, features = evidence(root, "feature_store")
    _, models = evidence(root, "model_comparison")
    feature_key = features["summary"]["fingerprint"]
    if models["manifest"]["inputs"]["feature_fingerprint"] != feature_key:
        raise ValueError("Model results are stale for notebook 02; run 02 and 03 in train mode")
    if models["summary"]["feature_count"] != features["summary"]["feature_count"]:
        raise ValueError("Feature schema mismatch")
    old = json.loads((root / "reports/research/run.json").read_text())
    return pd.DataFrame(
        [
            {
                "Stage": "02 feature matrix",
                "Run": feature_key,
                "Fits": features["summary"]["fold_tasks"],
                "Meaning": "Feature ablation fits; not the final model search",
            },
            {
                "Stage": "03 current model search",
                "Run": models["summary"]["fingerprint"],
                "Fits": models["summary"]["fit_tasks"],
                "Meaning": "Fits on the exact notebook 02 matrix",
            },
            {
                "Stage": "Earlier compact research",
                "Run": old["summary"]["fingerprint"],
                "Fits": old["summary"]["fold_tasks"],
                "Meaning": "Historical 120-fold study; not current retraining",
            },
        ]
    )


def current_directory(root: Path, name: str) -> Path:
    base = root / "outputs" / name
    pointer = json.loads((base / "latest.json").read_text())
    key = pointer["fingerprint"]
    if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
        raise ValueError("Invalid run fingerprint")
    if pointer["directory"] != key:
        raise ValueError("Run pointer does not match fingerprint")
    path = safe_path(base, key)
    summary = json.loads((path / "summary.json").read_text())
    if summary.get("status") != "completed" or summary.get("fingerprint") != key:
        raise ValueError("A completed current run is required")
    return path


def raw_directory(root: Path) -> Path:
    local = root / "data/kaggle/raw"
    return local if local.is_dir() else root / "outputs/inference_inputs/features/raw"


def same_feature_computation(recorded: dict[str, Any], current: dict[str, Any]) -> bool:
    """Packaging-only additions do not invalidate identical feature computation.

    Preserve the original run ID and source. All actual feature dependencies, code,
    data and configuration must match; changed values or features require a new run.
    """

    def relevant(value: dict[str, Any]) -> dict[str, Any]:
        return {
            **value,
            "source": {
                k: v for k, v in value["source"].items() if k not in {"pyproject.toml", "uv.lock"}
            },
        }

    return relevant(recorded) == relevant(current)


def require_current_features(root: Path) -> Path:
    path = current_directory(root, "feature_store")
    config = json.loads((root / "configs/feature_store.json").read_text())
    *_, inputs = feature_store.prepare_inputs(raw_directory(root), config)
    recorded = json.loads((path / "manifest.json").read_text())["inputs"]
    if not same_feature_computation(recorded, inputs):
        raise ValueError("Notebook 02 inputs/code changed; run notebook 02 in train mode first")
    return path


def publish_report(root: Path, name: str, run: Path, archive: dict[str, Any]) -> None:
    """Replace only the canonical compact evidence, with hashes computed from real outputs."""
    folder = root / "reports" / name
    folder.mkdir(parents=True, exist_ok=True)
    old = json.loads((folder / "run.json").read_text())
    filenames = set(old["sha256"]) - {"validation.json"}
    if name == "model_comparison":
        filenames.update(
            {"comparison.csv", "research_recovery.json"} & {p.name for p in run.iterdir()}
        )
    hashes = {}
    for filename in sorted(filenames):
        source = safe_path(run, filename)
        if not source.is_file():
            # A non-model validation record may describe the preceding CI, never this run.
            if filename in {"comparison.csv", "research_recovery.json"}:
                continue
            raise ValueError(f"Missing completed report output: {filename}")
        expected = digest(source)
        verified_write(folder / filename, source.read_bytes(), expected)
        hashes[filename] = expected
    record = {
        "summary": json.loads((run / "summary.json").read_text()),
        "manifest": json.loads((run / "manifest.json").read_text()),
        "sha256": hashes,
        "archive": archive,
        "execution_note": "Executed notebook pipeline; manifest records exact training provenance.",
    }
    atomic_json(folder / "run.json", record)


def feature_stage(root: Path) -> Path:
    """Use current local data when present; otherwise restore the explicitly recorded snapshot."""
    log = EventLog(root / "outputs/notebook_workflow/events.jsonl")
    _, record = evidence(root, "feature_store")
    raw = raw_directory(root)
    restored = None
    if not raw.is_dir():
        restored = download_input(
            record["archive"], root / "outputs/inference_inputs/features", log, complete_run=True
        )
        raw = restored.parent / "raw"
    config = json.loads((root / "configs/feature_store.json").read_text())
    *_, inputs = feature_store.prepare_inputs(raw, config)
    key = fingerprint(inputs)
    base = root / "outputs/feature_store"
    target = base / key
    if restored is not None and same_feature_computation(
        json.loads((restored / "manifest.json").read_text())["inputs"], inputs
    ):
        # Keep the original run ID; this is verified reuse, not a newly computed result.
        key = json.loads((restored / "summary.json").read_text())["fingerprint"]
        target = base / key
        # The whole archive and every member were verified before reuse, including estimators.
        for source in restored.rglob("*"):
            if source.is_file() and not source.name.startswith("."):
                destination = safe_path(target, str(source.relative_to(restored)))
                verified_write(destination, source.read_bytes(), digest(source))
        atomic_json(base / "latest.json", {"directory": key, "fingerprint": key})
        log.emit(
            "feature_stage_reused",
            fingerprint=key,
            reason="feature code/data/config/runtime match; original packaging provenance retained",
        )
        return target
    if not raw.is_dir():
        raise ValueError("Provide the official raw directory before training")
    summary = feature_store.run(
        raw, base, config, S3_PREFIX + "/features", managed=True, require_massey=True
    )
    target = base / summary["fingerprint"]
    archive = archive_run(root, "features", target, raw, log)
    publish_report(root, "feature_store", target, archive)
    log.emit("feature_stage_completed", fingerprint=target.name)
    return target


def archive_run(root: Path, name: str, run: Path, raw: Path, log: EventLog) -> dict[str, Any]:
    destination = root / "outputs/archives" / name / (run.name + ".zip")
    subprocess.run(
        [
            sys.executable,
            str(root / "scripts/archive.py"),
            "create",
            "--run",
            str(run),
            "--raw",
            str(raw),
            "--destination",
            str(destination),
        ],
        cwd=root,
        check=True,
    )
    mirror = Mirror(f"{S3_PREFIX}/{name}/{run.name}")
    mirror.upload(destination, "archive.zip")
    head = mirror.client.head_object(Bucket=mirror.bucket, Key=mirror.prefix + "/archive.zip")
    if head["ContentLength"] != destination.stat().st_size or head.get("Metadata", {}).get(
        "sha256"
    ) != digest(destination):
        raise ValueError("Archive upload metadata mismatch")
    log.emit("archive_preserved", bytes=destination.stat().st_size, sha256=digest(destination))
    return {
        "uri": f"s3://{mirror.bucket}/{mirror.prefix}/archive.zip",
        "sha256": digest(destination),
        "bytes": destination.stat().st_size,
        "version_id": head.get("VersionId"),
        "status": "uploaded",
    }


def matched_comparison(previous: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
    """Old and revised common streams must cover identical games; never compare unpaired means."""
    keys = ["Gender", "Season", "ID", "block", "model"]
    if previous.duplicated(keys).any() or current.duplicated(keys).any():
        raise ValueError("Duplicate comparison forecasts")
    joined = previous.merge(current, on=keys, suffixes=("_old", "_new"), validate="one_to_one")
    if len(joined) != len(previous) or not np.array_equal(joined.y_old, joined.y_new):
        raise ValueError("Previous and current evidence must match on every game and label")
    joined["old_loss"] = (joined.y_old - joined.p_old) ** 2
    joined["new_loss"] = (joined.y_new - joined.p_new) ** 2
    joined["absolute_probability_change"] = np.abs(joined.p_old - joined.p_new)
    return (
        joined.groupby(["Gender", "block", "model"])
        .agg(
            games=("ID", "size"),
            old_brier=("old_loss", "mean"),
            new_brier=("new_loss", "mean"),
            max_probability_change=("absolute_probability_change", "max"),
        )
        .reset_index()
    )


def model_stage(root: Path) -> Path:
    feature_run = require_current_features(root)
    folder, previous = evidence(root, "model_comparison")
    previous_predictions = pd.read_csv(folder / "predictions.csv")
    config = json.loads((root / "configs/model_comparison.json").read_text())
    summary = modeling.run(
        feature_run, root / "outputs/model_comparison", config, S3_PREFIX + "/models"
    )
    run = root / "outputs/model_comparison" / summary["fingerprint"]
    if previous["summary"]["fingerprint"] != summary["fingerprint"]:
        matched_comparison(previous_predictions, pd.read_csv(run / "predictions.csv")).to_csv(
            run / "comparison.csv", index=False
        )
    log = EventLog(root / "outputs/notebook_workflow/events.jsonl")
    archive = archive_run(root, "models", run, feature_run, log)
    publish_report(root, "model_comparison", run, archive)
    log.emit(
        "model_stage_completed",
        fingerprint=run.name,
        fit_tasks=summary["fit_tasks"],
        feature_fingerprint=summary["feature_fingerprint"],
    )
    return run


def verify_model_recovery(root: Path) -> dict[str, Any]:
    feature_run = require_current_features(root)
    current = current_directory(root, "model_comparison")
    base = root / "outputs/model_recovery"
    if base.exists():
        raise ValueError("Recovery verification requires a fresh destination")
    config = json.loads((root / "configs/model_comparison.json").read_text())
    summary = modeling.run(feature_run, base, config, S3_PREFIX + "/models")
    restored = base / summary["fingerprint"]
    events = [json.loads(row) for row in (restored / "events.jsonl").read_text().splitlines()]
    repeats = sum(row["event"] == "task_started" for row in events)
    if repeats or digest(current / "predictions.csv") != digest(restored / "predictions.csv"):
        raise ValueError("Recovery repeated work or changed forecasts")
    result = {
        "status": "passed",
        "fingerprint": current.name,
        "repeated_tasks": repeats,
        "restored_tasks": sum(row["event"] == "task_restored" for row in events),
        "reused_tasks": sum(row["event"] == "task_reused" for row in events),
        "identical_predictions": True,
    }
    atomic_json(current / "research_recovery.json", result)
    folder, record = evidence(root, "model_comparison")
    verified_write(
        folder / "research_recovery.json",
        (current / "research_recovery.json").read_bytes(),
        digest(current / "research_recovery.json"),
    )
    record["sha256"]["research_recovery.json"] = digest(folder / "research_recovery.json")
    atomic_json(folder / "run.json", record)
    mirror = Mirror(f"{S3_PREFIX}/models/{current.name}")
    mirror.upload(current / "research_recovery.json", "research_recovery.json")
    return result


def generate_submission(root: Path) -> Path:
    """Explicit notebook opt-in: generate and audit locally; never send anything to Kaggle."""
    from march_mania.publication.inference import run

    feature_run = require_current_features(root)
    model_run = current_directory(root, "model_comparison")
    model_config = json.loads((root / "configs/model_comparison.json").read_text())
    if fingerprint(modeling.run_inputs(feature_run, model_config)) != model_run.name:
        raise ValueError("Model inputs/code changed; run notebook 03 in train mode first")
    public = run(
        feature_run,
        model_run,
        raw_directory(root) / "SampleSubmissionStage2.csv",
        root,
        root / "outputs/final_predictions",
        json.loads((root / "configs/inference.json").read_text()),
        S3_PREFIX + "/submissions",
    )
    target = root / "submissions/submission.csv"
    verified_write(
        target, (public / "submission.csv").read_bytes(), digest(public / "submission.csv")
    )
    folder = root / "reports/final_predictions"
    names = [
        p.name
        for p in public.iterdir()
        if p.suffix in {".csv", ".json"} and p.name not in {"submission.csv", "checkpoint.json"}
    ]
    names.append("run.json")
    atomic_json(folder / "evidence.json", {"sha256": {n: digest(folder / n) for n in names}})
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-recovery", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if args.verify_recovery:
        print(json.dumps(verify_model_recovery(root), indent=2))
    else:
        print(lineage(root).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
