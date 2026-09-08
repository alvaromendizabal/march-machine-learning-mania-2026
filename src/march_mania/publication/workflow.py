"""Notebook-controlled research with explicit data lineage and no Kaggle upload."""

from __future__ import annotations

import argparse
import hashlib
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
from march_mania.publication.reporting import public_bytes
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
    require_recorded_source(root, "feature_store", features)
    require_recorded_source(root, "model_comparison", models)
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


def require_recorded_source(root: Path, name: str, record: dict[str, Any]) -> None:
    """Detect equally stale feature/model reports without requiring private raw data.

    Report readers verify computational sources and configuration. Training also
    verifies exact data and runtime through require_current_features/run_inputs.
    """
    from march_mania.advanced_features import candidate_blocks

    inputs = record["manifest"]["inputs"]
    changed = [
        path
        for path, expected in inputs["source"].items()
        if path not in {"pyproject.toml", "uv.lock"}
        and (not safe_path(root, path).is_file() or digest(safe_path(root, path)) != expected)
    ]
    config = json.loads((root / "configs" / (name + ".json")).read_text())
    if config != inputs["config"]:
        changed.append("configuration")
    if record["summary"]["feature_count"] != len(candidate_blocks()["full"]):
        changed.append("feature catalog")
    if changed:
        raise ValueError(
            f"Stale {name} results for current source: {', '.join(changed)}. "
            "Run 02 then 03 in train mode."
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
    filenames.update(
        {"screening_summary.csv", "selection_stability.csv", "source_coverage.csv"}
        & {p.name for p in run.iterdir()}
    )
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
        contents = public_bytes(
            source, feature_audit=name == "feature_store" and filename == "feature_usage.csv"
        )
        expected = hashlib.sha256(contents).hexdigest()
        verified_write(folder / filename, contents, expected)
        hashes[filename] = expected
    record = {
        "summary": json.loads((run / "summary.json").read_text()),
        "manifest": json.loads((run / "manifest.json").read_text()),
        "sha256": hashes,
        "archive": archive,
        "execution_note": "Executed notebook pipeline; manifest records exact training provenance.",
    }
    if name == "feature_store" and "feature_usage.csv" in hashes:
        record["public_report_scope"] = {
            "feature_usage.csv": {
                "view": "Retained full-block features only; all rejection counts remain public.",
                "complete_audit": "archive:run/feature_usage.csv",
                "complete_audit_sha256": digest(run / "feature_usage.csv"),
            }
        }
    atomic_json(folder / "run.json", record)


def restore_context_file(raw: Path, log: EventLog, name: str, expected: str, version: str) -> None:
    """Restore a recorded official context file without replacing an existing source."""
    target = safe_path(raw, name)
    if target.exists():
        return
    if not (raw / "MRegularSeasonCompactResults.csv").is_file():
        raise ValueError("Restore the complete official raw directory before context")
    mirror = Mirror(
        "s3://sagemaker-march-mania-560403859723-us-west-2/final-predictions/official-context"
    )
    key = (
        mirror.prefix + "/c9df24626b8953cde6386be98ce64e273fb2e96057af5b5234d9adc54c939e78/" + name
    )
    temporary = target.with_name("." + name + ".tmp")
    try:
        mirror.client.download_file(
            mirror.bucket,
            key,
            str(temporary),
            ExtraArgs={"VersionId": version},
        )
        if digest(temporary) != expected:
            raise ValueError("Official context checksum mismatch")
        temporary.replace(target)
        log.emit("official_context_verified", sha256=expected, source=key)
    finally:
        temporary.unlink(missing_ok=True)


def restore_official_context(raw: Path, log: EventLog) -> None:
    records = [
        (
            "MTeamCoaches.csv",
            "e0fe04e53ea35f4a120f0368164c2a7035d5a0b1ab427a078a27304bd16003bc",
            "zEiRmU_hLDhAalrC64w6DBQdxATntgqP",
        ),
        (
            "MTeamConferences.csv",
            "a798dcd8ac5ddfbcbe13fe6217054f05ccc8b952b0c662eb3f1973ae6be3f6bc",
            "MEPbP8ns7HUwWOIbNcycPcwrFsdBZ.J7",
        ),
        (
            "WTeamConferences.csv",
            "be4d13c60f1c567de7bdb927c8801cc62e4d3ff3297d05ca15276b7c219c1805",
            "n.b9bHT7_yhuZOTlyv1DPfljWyPTs1xl",
        ),
    ]
    for name, sha256, version in records:
        restore_context_file(raw, log, name, sha256, version)


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
    restore_official_context(raw, log)
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


def materialize_predictions(run: Path) -> Path:
    """Derive the public CSV from canonical Parquet; never substitute an old report."""
    source = run / "predictions.parquet"
    payload = pd.read_parquet(source).to_csv(index=False).encode("utf-8")
    target = run / "predictions.csv"
    verified_write(target, payload, hashlib.sha256(payload).hexdigest())
    return target


def model_stage(root: Path) -> Path:
    feature_run = require_current_features(root)
    folder, previous = evidence(root, "model_comparison")
    previous_predictions = pd.read_csv(folder / "predictions.csv")
    config = json.loads((root / "configs/model_comparison.json").read_text())
    expected = fingerprint(modeling.run_inputs(feature_run, config))
    target = root / "outputs/model_comparison" / expected
    if previous["summary"]["fingerprint"] == expected and not (target / "summary.json").exists():
        log = EventLog(root / "outputs/notebook_workflow/events.jsonl")
        restored = download_input(
            previous["archive"], root / "outputs/inference_inputs/models", log, complete_run=True
        )
        if json.loads((restored / "summary.json").read_text())["fingerprint"] != expected:
            raise ValueError("Archived model run does not match current inputs")
        for source in restored.rglob("*"):
            if source.is_file() and not source.name.startswith("."):
                destination = safe_path(target, str(source.relative_to(restored)))
                verified_write(destination, source.read_bytes(), digest(source))
        log.emit("model_archive_restored", fingerprint=expected)
    summary = modeling.run(
        feature_run, root / "outputs/model_comparison", config, S3_PREFIX + "/models"
    )
    run = root / "outputs/model_comparison" / summary["fingerprint"]
    materialize_predictions(run)
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
    materialize_predictions(restored)
    events = [json.loads(row) for row in (restored / "events.jsonl").read_text().splitlines()]
    repeats = sum(row["event"] == "task_started" for row in events)
    if (
        repeats
        or digest(current / "predictions.parquet") != digest(restored / "predictions.parquet")
        or digest(current / "predictions.csv") != digest(restored / "predictions.csv")
    ):
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


def benchmark_evidence(root: Path) -> tuple[Path, dict[str, Any]]:
    """Reject retrospective scores from a different feature/model research lineage."""
    folder, record = evidence(root, "benchmark")
    for name, key in (
        ("feature_store", "feature_fingerprint"),
        ("model_comparison", "model_fingerprint"),
    ):
        _, upstream = evidence(root, name)
        require_recorded_source(root, name, upstream)
        if record["manifest"]["inputs"][key] != upstream["summary"]["fingerprint"]:
            raise ValueError("Benchmark results are stale; execute notebook 04 in train mode")
    inputs = record["manifest"]["inputs"]
    if inputs["config"] != json.loads((root / "configs/inference.json").read_text()):
        raise ValueError("Benchmark configuration changed")
    if any(digest(safe_path(root, p)) != h for p, h in inputs["source"].items()):
        raise ValueError("Benchmark source changed")
    return folder, record


def benchmark_stage(root: Path) -> Path:
    from march_mania.publication.benchmark import run

    features = require_current_features(root)
    models = current_directory(root, "model_comparison")
    config = json.loads((root / "configs/model_comparison.json").read_text())
    if fingerprint(modeling.run_inputs(features, config)) != models.name:
        raise ValueError("Run notebook 03 on the current features before evaluating")
    result = run(
        root,
        features,
        models,
        json.loads((root / "configs/inference.json").read_text()),
        S3_PREFIX + "/benchmark",
    )
    log = EventLog(root / "outputs/notebook_workflow/events.jsonl")
    archive = archive_run(root, "benchmark", result, features, log)
    publish_benchmark(root, result, archive)
    return result


def publish_benchmark(root: Path, run: Path, archive: dict[str, Any]) -> None:
    folder = root / "reports/benchmark"
    hashes = {}
    for source in (run / "publication").iterdir():
        if source.is_file() and source.name not in {"checkpoint.json", "summary.json"}:
            expected = digest(source)
            verified_write(folder / source.name, source.read_bytes(), expected)
            hashes[source.name] = expected
    atomic_json(
        folder / "run.json",
        {
            "summary": json.loads((run / "summary.json").read_text()),
            "manifest": json.loads((run / "manifest.json").read_text()),
            "sha256": hashes,
            "archive": archive,
        },
    )


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
