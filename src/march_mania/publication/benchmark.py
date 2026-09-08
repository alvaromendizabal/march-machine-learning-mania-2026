"""Evaluate frozen development recipes without fitting or exporting 2026 predictions."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from filelock import FileLock

from march_mania.publication import inference
from march_mania.publication.artifacts import restore_tasks
from march_mania.runtime import (
    EventLog,
    Mirror,
    TaskStore,
    atomic_json,
    digest,
    fingerprint,
    runtime_identity,
)


def execute(
    frame: pd.DataFrame,
    recipe: dict[str, Any],
    store: TaskStore,
    config: dict[str, Any],
) -> Path:
    """Refit the declared logistic anchors annually; never select using benchmark labels.

    The model families and calibration are the predeclared inference contract.
    Notebook 03 separately compares all model families on development seasons.
    """
    inference.validate_config(config)
    frame = frame.loc[frame.Season.between(2013, 2025) & frame.Season.ne(2020)].copy()
    inference.validate_games(frame, 2025)
    predictions, audits = [], []
    for gender in ("M", "W"):
        population = frame.loc[frame.Gender == gender]
        for season in config["benchmark_seasons"]:
            train = population.loc[population.Season < season]
            valid = population.loc[population.Season == season]
            if valid.empty or train.empty or int(train.Season.max()) != season - 1:
                raise ValueError("Missing retrospective training or evaluation season")
            for route in ("seeded", "seed_free"):
                fitted = inference.training_task(
                    store, train, valid, gender, route, season, recipe, config
                )
                saved = joblib.load(fitted / "model.joblib")  # Own verified checkpoint only.
                audits.append(json.loads((fitted / "audit.json").read_text()))

                def evaluate(
                    target: Path,
                    valid: pd.DataFrame = valid,
                    saved: dict = saved,
                    route: str = route,
                ) -> list[Path]:
                    rows = valid[["Gender", "Season", "DayNum", "ID", "y"]].copy()
                    rows["p"] = inference.forecast(
                        saved["model"], valid, saved["features"], config["threads"]
                    )
                    rows["route"] = route
                    rows.to_csv(target / "predictions.csv", index=False)
                    return [target / "predictions.csv"]

                scored = store.task(f"score_{gender.lower()}_{season}_{route}", evaluate)
                predictions.append(pd.read_csv(scored / "predictions.csv"))

    def publish(target: Path) -> list[Path]:
        rows = pd.concat(predictions, ignore_index=True)
        files = inference.make_report(rows, target)
        atomic_json(target / "fit_audits.json", audits)
        atomic_json(target / "recipe.json", recipe)
        atomic_json(
            target / "summary.json",
            {
                "status": "completed",
                "fingerprint": store.run_fingerprint,
                "model_fits": len(audits),
                "physical_games": len(rows.drop_duplicates(["Gender", "Season", "ID"])),
                "prediction_rows": len(rows),
                "benchmark_seasons": config["benchmark_seasons"],
                "benchmark_status": "2022-2025 previously consumed; retrospective only",
                "model_scope": "Predeclared gender-specific logistic anchors",
                "scored_population": "Includes play-ins; differs from Kaggle scored games",
                "future_labels_used": False,
                "submission_generated": False,
                "kaggle_submission_sent": False,
            },
        )
        return files + [
            target / name for name in ("fit_audits.json", "recipe.json", "summary.json")
        ]

    return store.task("publication", publish)


def run(
    root: Path,
    feature_run: Path,
    model_run: Path,
    config: dict[str, Any],
    s3: str | None = None,
) -> Path:
    """Bind evaluation to completed upstream runs, exact sources, and immutable tasks."""
    inference.validate_config(config)
    feature_summary = json.loads((feature_run / "summary.json").read_text())
    model_summary = json.loads((model_run / "summary.json").read_text())
    model_manifest = json.loads((model_run / "manifest.json").read_text())
    matrix = feature_run / "features.parquet"
    history = model_run / "candidate_predictions.parquet"
    if any(s["status"] != "completed" for s in (feature_summary, model_summary)):
        raise ValueError("Both upstream research runs must be completed")
    if model_manifest["inputs"]["feature_fingerprint"] != feature_summary[
        "fingerprint"
    ] or model_manifest["inputs"]["data"]["features.parquet"] != digest(matrix):
        raise ValueError("Benchmark model and feature lineage differ")
    sources = [
        *[str(p.relative_to(root)) for p in sorted((root / "src/march_mania").glob("*.py"))],
        "src/march_mania/publication/benchmark.py",
        "src/march_mania/publication/inference.py",
        "src/march_mania/publication/artifacts.py",
    ]
    inputs = {
        "config": config,
        "feature_fingerprint": feature_summary["fingerprint"],
        "model_fingerprint": model_summary["fingerprint"],
        "data": {"features.parquet": digest(matrix)},
        "development_predictions_sha256": digest(history),
        "source": {name: digest(root / name) for name in sources},
        "environment": {k: v for k, v in runtime_identity().items() if k != "platform"},
    }
    key = fingerprint(inputs)
    output = root / "outputs/benchmark" / key
    output.mkdir(parents=True, exist_ok=True)
    with FileLock(str(output / ".run.lock"), timeout=0):
        start = time.monotonic()
        log = EventLog(output / "events.jsonl")
        log.emit("run_started", fingerprint=key, protocol="retrospective-benchmark-only")
        mirror = Mirror(f"{s3.rstrip('/')}/{key}") if s3 else None
        if mirror:
            restore_tasks(mirror, output, key, log)
        store = TaskStore(output, key, log, config["heartbeat_seconds"], mirror)
        # Freeze the recipe before loading any benchmark outcomes.
        recipe = inference.freeze_recipe(pd.read_parquet(history), config)
        atomic_json(output / "manifest.json", {"fingerprint": key, "inputs": inputs})
        shutil.copy2(history, output / "development_predictions.parquet")
        try:
            public = execute(pd.read_parquet(matrix), recipe, store, config)
            if (
                digest(matrix) != inputs["data"]["features.parquet"]
                or digest(history) != inputs["development_predictions_sha256"]
            ):
                raise ValueError("Benchmark inputs changed during execution")
            if any(digest(root / p) != h for p, h in inputs["source"].items()):
                raise ValueError("Benchmark source changed during execution")
            for path in public.iterdir():
                if path.is_file() and path.name != "checkpoint.json":
                    shutil.copy2(path, output / path.name)
            summary = json.loads((output / "summary.json").read_text())
            summary["elapsed_seconds"] = round(time.monotonic() - start, 3)
            atomic_json(output / "summary.json", summary)
            if mirror:
                for path in output.iterdir():
                    if path.is_file() and not path.name.startswith("."):
                        mirror.upload(path, path.name)
            atomic_json(output.parent / "latest.json", {"fingerprint": key, "directory": key})
            log.emit("run_completed", **summary)
        except Exception as exc:
            log.emit("run_failed", error_type=type(exc).__name__, error=str(exc))
            raise
    return output
