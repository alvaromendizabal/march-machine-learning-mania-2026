"""Run matched, expanding-window feature ablations with durable task checkpoints."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from filelock import FileLock
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from march_mania.advanced_features import candidate_blocks
from march_mania.feature_selection import ScreenedPredictor, TrainingScreen
from march_mania.features import feature_blocks, matchups, read_official, snapshot
from march_mania.research_report import write_report
from march_mania.runtime import (
    EventLog,
    Mirror,
    TaskStore,
    atomic_json,
    digest,
    fingerprint,
    runtime_identity,
)


def validate_config(config: dict[str, Any]) -> None:
    seasons = config["validation_seasons"]
    if not seasons or seasons != sorted(set(seasons)) or 2020 in seasons:
        raise ValueError("Validation seasons must be sorted, unique, nonempty, and exclude 2020")
    if config["first_training_season"] >= min(seasons):
        raise ValueError("Training must start before validation")
    if any(s >= 2022 for s in seasons):
        raise ValueError("This development protocol excludes previously locked 2022-2026 seasons")
    if config["feature_cutoff_day"] != 132:
        raise ValueError("This protocol requires the pre-tournament DayNum 132 cutoff")
    if config["ridge_alpha"] <= 0 or config["recent_half_life_days"] <= 0:
        raise ValueError("Rating regularization and half life must be positive")
    if config["minimum_prior_seasons"] < 2 or config["threads"] < 1:
        raise ValueError("At least two prior seasons and one thread are required")
    if config["heartbeat_seconds"] <= 0:
        raise ValueError("Heartbeat interval must be positive")
    if not isinstance(config["include_play_in"], bool):
        raise ValueError("include_play_in must be a boolean")
    if config["protocol"] != "retrospective-feature-research":
        raise ValueError("The evidence status must remain retrospective-feature-research")


def fit_fold(
    train: pd.DataFrame, valid: pd.DataFrame, columns: list[str], model_name: str, seed: int
) -> tuple[Any, np.ndarray]:
    if train.empty or valid.empty or train.Season.max() >= valid.Season.min():
        raise ValueError("Empty fold or temporal train/validation overlap")
    if train.y.nunique() != 2:
        raise ValueError("Training labels must contain both classes")
    if not columns or not set(columns).issubset(candidate_blocks()["full"]):
        raise ValueError("Unknown feature or label in model matrix")
    x = train[columns].to_numpy(dtype=float)
    y = train.y.to_numpy(dtype=int)
    # Each physical game is mirrored inside its training fold, never before splitting.
    x, y = np.concatenate([x, -x]), np.concatenate([y, 1 - y])
    if model_name == "logistic":
        estimator = make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            StandardScaler(),
            LogisticRegression(C=0.1, max_iter=2000, random_state=seed),
        )
    elif model_name == "hist":
        estimator = make_pipeline(
            HistGradientBoostingClassifier(
                max_iter=100,
                max_leaf_nodes=7,
                min_samples_leaf=25,
                l2_regularization=10,
                learning_rate=0.05,
                early_stopping=False,
                random_state=seed,
            )
        )
    else:
        raise ValueError(f"Unknown model: {model_name}")
    screen = TrainingScreen().fit(x, y)
    estimator.fit(screen.transform(x), y)
    estimator = ScreenedPredictor(screen, estimator)
    values = valid[columns].to_numpy(dtype=float)
    p = symmetric_probability(estimator, values)
    return estimator, p


def symmetric_probability(estimator: Any, values: np.ndarray) -> np.ndarray:
    p = (estimator.predict_proba(values)[:, 1] + 1 - estimator.predict_proba(-values)[:, 1]) / 2
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Invalid model probabilities")
    return p


def run(
    raw: Path, output: Path, config: dict[str, Any], mirror_uri: str | None = None
) -> dict[str, Any]:
    validate_config(config)
    output.mkdir(parents=True, exist_ok=True)
    # Prevent simultaneous writers to the manifest, logs, and all task checkpoints.
    with FileLock(str(output / ".run.lock"), timeout=0):
        return _run(raw, output, config, mirror_uri)


def _run(raw: Path, output: Path, config: dict[str, Any], mirror_uri: str | None) -> dict[str, Any]:
    log = EventLog(output / "events.jsonl")
    log.emit("run_started", protocol=config["protocol"])
    data, paths = read_official(raw)
    root = Path(__file__).resolve().parents[2]
    sources = list(Path(__file__).parent.glob("*.py")) + [root / "uv.lock", root / "pyproject.toml"]
    identity = runtime_identity()
    inputs = {
        "config": config,
        "data": {p.name: digest(p) for p in paths},
        "source": {str(p.relative_to(root)): digest(p) for p in sources},
        "environment": {k: v for k, v in identity.items() if k != "platform"},
    }
    run_hash = fingerprint(inputs)
    manifest = output / "manifest.json"
    if manifest.exists() and json.loads(manifest.read_text())["fingerprint"] != run_hash:
        raise ValueError(
            "Inputs/configuration/code/environment changed. Choose a new run directory."
        )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    ).stdout.strip()
    record = {
        "fingerprint": run_hash,
        "inputs": inputs,
        "git_commit": commit,
        "platform": identity["platform"],
        "evidence_status": config["protocol"],
    }
    atomic_json(manifest, record)
    # Add the content fingerprint to avoid accidentally mixing runs in S3.
    mirror = Mirror(mirror_uri.rstrip("/") + "/" + run_hash) if mirror_uri else None
    store = TaskStore(output, run_hash, log, config["heartbeat_seconds"], mirror)
    if mirror:
        mirror.upload(manifest, "manifest.json")
        for path in paths:
            mirror.upload(path, "raw/" + path.name)
        log.emit("raw_data_uploaded", files=len(paths), run_fingerprint=run_hash)
    frames = []
    coverage = []
    for gender in ("M", "W"):
        tables = data[gender]
        compact = tables["RegularSeasonCompactResults"]
        years = sorted(
            int(s)
            for s in compact.Season.unique()
            if config["first_training_season"] <= s <= max(config["validation_seasons"])
        )
        team_frames = []
        for season in years:
            if season == 2020:
                continue

            def build(
                target: Path,
                season: int = season,
                gender: str = gender,
                tables: dict[str, pd.DataFrame] = tables,
            ) -> list[Path]:
                with threadpool_limits(limits=config["threads"]):
                    result = snapshot(
                        tables["RegularSeasonCompactResults"],
                        tables["RegularSeasonDetailedResults"],
                        tables["NCAATourneySeeds"],
                        gender,
                        season,
                        config["feature_cutoff_day"],
                        config["ridge_alpha"],
                        config["recent_half_life_days"],
                    )
                path = target / "teams.parquet"
                result.to_parquet(path, index=False)
                return [path]

            target = store.task(f"snapshot_{gender.lower()}_{season}", build)
            team_frames.append(pd.read_parquet(target / "teams.parquet"))
        if not team_frames:
            raise ValueError(f"No usable seasons for {gender}")
        teams = pd.concat(team_frames, ignore_index=True)
        labels = tables["NCAATourneyCompactResults"]
        labels = labels.loc[labels.Season.isin(years) & (labels.Season != 2020)]
        if (labels.DayNum <= config["feature_cutoff_day"]).any():
            raise ValueError("NCAA labels overlap the feature cutoff")
        frame = matchups(teams, labels, gender, config["include_play_in"])
        frames.append(frame)
        coverage.append(
            teams.groupby(["Gender", "Season"])
            .agg(teams=("TeamID", "size"), mean_detailed_coverage=("detailed_coverage", "mean"))
            .reset_index()
        )
    matrix = pd.concat(frames, ignore_index=True)
    matrix.to_parquet(output / "features.parquet", index=False)
    pd.concat(coverage).to_csv(output / "coverage.csv", index=False)
    predictions = []
    total = 2 * len(config["validation_seasons"]) * len(feature_blocks()) * 2
    completed = 0
    for gender in ("M", "W"):
        for season in config["validation_seasons"]:
            train = matrix.loc[(matrix.Gender == gender) & (matrix.Season < season)]
            valid = matrix.loc[(matrix.Gender == gender) & (matrix.Season == season)]
            if train.Season.nunique() < config["minimum_prior_seasons"] or valid.empty:
                raise ValueError(f"Insufficient history/validation data for {gender} {season}")
            for block, columns in feature_blocks().items():
                for model_name in ("logistic", "hist"):
                    task_name = f"fold_{gender.lower()}_{season}_{block}_{model_name}"

                    def evaluate(
                        target: Path,
                        train: pd.DataFrame = train,
                        valid: pd.DataFrame = valid,
                        columns: list[str] = columns,
                        model_name: str = model_name,
                        block: str = block,
                    ) -> list[Path]:
                        with threadpool_limits(limits=config["threads"]):
                            estimator, probability = fit_fold(
                                train, valid, columns, model_name, config["seed"]
                            )
                        result = valid[["Gender", "Season", "DayNum", "ID", "y"]].copy()
                        result["p"], result["block"], result["model"] = (
                            probability,
                            block,
                            model_name,
                        )
                        result.to_parquet(target / "predictions.parquet", index=False)
                        joblib.dump(
                            {"estimator": estimator, "features": columns}, target / "model.joblib"
                        )
                        atomic_json(
                            target / "fold.json",
                            {
                                "train_seasons": sorted(int(s) for s in train.Season.unique()),
                                "validation_seasons": sorted(int(s) for s in valid.Season.unique()),
                                "train_physical_games": len(train),
                                "validation_games": len(valid),
                                "features": columns,
                                "seed": config["seed"],
                            },
                        )
                        return [
                            target / name
                            for name in ["predictions.parquet", "model.joblib", "fold.json"]
                        ]

                    target = store.task(task_name, evaluate)
                    predictions.append(pd.read_parquet(target / "predictions.parquet"))
                    completed += 1
                    log.emit(
                        "progress",
                        completed=completed,
                        total=total,
                        percent=round(100 * completed / total, 1),
                    )
    all_predictions = pd.concat(predictions, ignore_index=True)
    all_predictions.to_parquet(output / "predictions.parquet", index=False)
    write_report(all_predictions, output, config["seed"])
    summary = {
        "status": "completed",
        "fold_tasks": completed,
        "fingerprint": run_hash,
        "evidence_status": config["protocol"],
        "elapsed_seconds": round(time.monotonic() - log.started, 3),
        "remote_run_uri": mirror_uri.rstrip("/") + "/" + run_hash if mirror_uri else None,
    }
    return finalize_run(output, summary, mirror, log)


def finalize_run(
    output: Path, summary: dict[str, Any], mirror: Mirror | None, log: EventLog
) -> dict[str, Any]:
    summary["elapsed_seconds"] = round(time.monotonic() - log.started, 3)
    log.emit("artifacts_ready", elapsed_seconds=summary["elapsed_seconds"])
    summary["status"] = "uploading" if mirror else "completed"
    atomic_json(output / "summary.json", summary)
    if mirror:
        try:
            for path in output.iterdir():
                if path.is_file() and not path.name.startswith(".") and path.name != "summary.json":
                    mirror.upload(path, path.name)
            summary["status"] = "completed"
            summary["elapsed_seconds"] = round(time.monotonic() - log.started, 3)
            atomic_json(output / "summary.json", summary)
            # The remote completion record is published after every run-level artifact.
            mirror.upload(output / "summary.json", "summary.json")
        except Exception:
            summary["status"] = "upload_failed"
            atomic_json(output / "summary.json", summary)
            log.emit("run_upload_failed")
            raise
    log.emit("run_completed", **summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw", type=Path, default=Path("data/raw/march-machine-learning-mania-2026")
    )
    parser.add_argument("--output", type=Path, default=Path("outputs/research"))
    parser.add_argument("--config", type=Path, default=Path("configs/research.json"))
    parser.add_argument("--s3", help="S3 run prefix; content fingerprint is appended automatically")
    parser.add_argument("--restore", help="Exact remote_run_uri to restore into an empty --output")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    try:
        if args.restore:
            Mirror(args.restore).restore(args.output)
            print(json.dumps({"status": "restored", "path": str(args.output)}), flush=True)
            return 0
        config = json.loads(args.config.read_text())
        validate_config(config)
        if args.preflight:
            _, paths = read_official(args.raw)
            print(
                json.dumps(
                    {
                        "status": "ready",
                        "files": {p.name: digest(p) for p in paths},
                        "environment": runtime_identity(),
                    }
                ),
                flush=True,
            )
        else:
            run(args.raw, args.output, config, args.s3)
        return 0
    except Exception as error:
        print(
            json.dumps({"status": "failed", "type": type(error).__name__, "error": str(error)}),
            file=sys.stderr,
            flush=True,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
