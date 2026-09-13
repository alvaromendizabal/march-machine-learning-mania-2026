"""Matched feature-capacity sensitivity, with forward-only selection and verified reuse.

The candidate matrix and fixed estimators are inherited from notebook 02. Cloning
its estimator template discards all fitted state. Only the number of retained
features changes. This study does not select a new final forecasting recipe.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from filelock import FileLock
from sklearn.base import clone
from threadpoolctl import threadpool_limits

from march_mania.advanced_features import candidate_blocks
from march_mania.feature_selection import ScreenedPredictor, TrainingScreen, screening_audit
from march_mania.modeling import validate_matrix
from march_mania.publication.artifacts import safe_path
from march_mania.publication.workflow import (
    evidence,
    require_current_features,
    require_recorded_source,
)
from march_mania.research import symmetric_probability
from march_mania.research_report import paired_season_intervals, probability_metrics
from march_mania.runtime import (
    EventLog,
    TaskStore,
    atomic_json,
    digest,
    fingerprint,
    runtime_identity,
)

ROUTES = {
    "M_rankings": ("M", "full"),
    "M_common": ("M", "expanded_non_massey"),
    "W_common": ("W", "full"),
}
KEYS = ["Gender", "Season", "DayNum", "ID", "y"]


def validate_config(config: dict[str, Any]) -> None:
    years, caps = config["validation_seasons"], config["capacities"]
    if (
        config["protocol"] != "retrospective-feature-capacity"
        or not years
        or years != sorted(set(years))
        or 2020 in years
        or max(years) >= 2022
        or config["first_training_season"] >= min(years) - 1
        or config["minimum_inner_seasons"] < 2
    ):
        raise ValueError("Capacity study requires earlier development seasons and inner history")
    if (
        not caps
        or caps != sorted(set(caps))
        or any(type(c) is not int or c < 1 for c in caps)
        or config["reference_capacity"] != 128
        or 128 not in caps
        or config["models"] != ["logistic", "hist"]
        or config["threads"] < 1
        or config["heartbeat_seconds"] <= 0
    ):
        raise ValueError("Invalid capacity or fixed-estimator contract")


def verified_reference(feature_run: Path, name: str, feature_key: str) -> Path:
    folder = safe_path(feature_run, name)
    record = json.loads((folder / "checkpoint.json").read_text())
    if record["fingerprint"] != feature_key or not record.get("outputs"):
        raise ValueError("Reference fit has the wrong feature lineage")
    for filename, expected in record["outputs"].items():
        if digest(safe_path(folder, filename)) != expected:
            raise ValueError("Reference fit checkpoint is corrupt")
    return folder


def fit_capacity(
    train: pd.DataFrame, valid: pd.DataFrame, columns: list[str], template: Any, capacity: int
) -> tuple[ScreenedPredictor, list[str], np.ndarray]:
    if (
        train.empty
        or valid.empty
        or train.Season.max() >= valid.Season.min()
        or train.y.nunique() != 2
        or valid.Season.nunique() != 1
    ):
        raise ValueError("Invalid chronological fold")
    if not columns or not set(columns).issubset(candidate_blocks()["full"]):
        raise ValueError("Unknown feature or target in capacity matrix")
    fitted = [c for c in columns if train[c].notna().any() and train[c].fillna(0).ne(0).any()]
    x, y = train[fitted].to_numpy(float), train.y.to_numpy(int)
    x, y = np.concatenate([x, -x]), np.concatenate([y, 1 - y])
    screen = TrainingScreen(max_features=capacity).fit(x, y)
    estimator = clone(template).fit(screen.transform(x), y)
    model = ScreenedPredictor(screen, estimator)
    return model, fitted, symmetric_probability(model, valid[fitted].to_numpy(float))


def select_capacity(history: pd.DataFrame, outer_season: int, minimum: int = 2) -> int:
    """Use only earlier OOF losses; deterministic ties favor the smaller representation."""
    prior = history.loc[history.Season < outer_season].copy()
    if prior.Season.nunique() < minimum:
        raise ValueError("Insufficient earlier OOF seasons")
    keys = ["Season", "ID"]
    groups = [
        part.sort_values(keys).reset_index(drop=True) for _, part in prior.groupby("capacity")
    ]
    if not groups or any(g.duplicated(keys).any() for g in groups):
        raise ValueError("Duplicate or missing capacity forecasts")
    if any(not g[keys + ["y"]].equals(groups[0][keys + ["y"]]) for g in groups[1:]):
        raise ValueError("Capacity candidates must score identical earlier games")
    if not np.isfinite(prior.p).all() or not prior.p.between(0, 1).all():
        raise ValueError("Invalid capacity probabilities")
    prior["loss"] = (prior.y - prior.p) ** 2
    scores = prior.groupby(["capacity", "Season"]).loss.mean().groupby("capacity").mean()
    return int(scores.reset_index().sort_values(["loss", "capacity"]).iloc[0].capacity)


def summarize(predictions: pd.DataFrame, config: dict[str, Any], destination: Path) -> None:
    fixed = predictions.loc[predictions.Season.isin(config["validation_seasons"])].copy()
    selected, decisions = [], []
    for (route, model), group in predictions.groupby(["route", "model"]):
        for year in config["validation_seasons"]:
            cap = select_capacity(group, year, config["minimum_inner_seasons"])
            selected.append(
                group.loc[(group.Season == year) & (group.capacity == cap)].assign(block="nested")
            )
            prior = group.loc[group.Season < year]
            decisions.append(
                {
                    "route": route,
                    "model": model,
                    "Season": year,
                    "capacity": cap,
                    "history_last_season": int(prior.Season.max()),
                    "history_seasons": int(prior.Season.nunique()),
                }
            )
    fixed["block"] = fixed.capacity.map(lambda c: f"cap_{c}")
    evaluation = pd.concat([fixed, *selected], ignore_index=True)
    metrics, intervals = [], []
    for (route, model, block), group in evaluation.groupby(["route", "model", "block"]):
        loss = group.assign(loss=(group.y - group.p) ** 2).groupby("Season").loss.mean()
        metrics.append(
            {
                "route": route,
                "model": model,
                "block": block,
                "games": len(group),
                "macro_season_brier": float(loss.mean()),
                **probability_metrics(group.y.to_numpy(), group.p.to_numpy()),
            }
        )
    for route, group in evaluation.groupby("route"):
        contrasts = [(f"cap_{c}", "cap_128") for c in config["capacities"] if c != 128]
        frame = paired_season_intervals(group, config["seed"], contrasts + [("nested", "cap_128")])
        intervals.append(frame.assign(route=route))
    pd.DataFrame(metrics).to_csv(destination / "leaderboard.csv", index=False)
    pd.concat(intervals, ignore_index=True).to_csv(destination / "intervals.csv", index=False)
    pd.DataFrame(decisions).to_csv(destination / "selection.csv", index=False)
    evaluation.to_csv(destination / "evaluation.csv", index=False)


def run(root: Path) -> Path:
    config = json.loads((root / "configs/feature_capacity.json").read_text())
    validate_config(config)
    feature_run = require_current_features(root)
    _, feature_record = evidence(root, "feature_store")
    require_recorded_source(root, "feature_store", feature_record)
    feature_key = feature_record["summary"]["fingerprint"]
    if json.loads((feature_run / "summary.json").read_text())["fingerprint"] != feature_key:
        raise ValueError("Capacity and published feature lineage differ")
    # Notebook 03 independently recorded the exact matrix bytes used for training.
    _, model_record = evidence(root, "model_comparison")
    if (
        model_record["manifest"]["inputs"]["feature_fingerprint"] != feature_key
        or digest(feature_run / "features.parquet")
        != model_record["manifest"]["inputs"]["data"]["features.parquet"]
    ):
        raise ValueError("Changed feature matrix or model lineage")
    inputs = {
        "feature_fingerprint": feature_key,
        "config": config,
        "data": {"features.parquet": digest(feature_run / "features.parquet")},
        "source": {
            **model_record["manifest"]["inputs"]["source"],
            **feature_record["manifest"]["inputs"]["source"],
            **{
                p: digest(root / p)
                for p in [
                    "src/march_mania/publication/capacity.py",
                    "src/march_mania/publication/workflow.py",
                ]
            },
        },
        "environment": {k: v for k, v in runtime_identity().items() if k != "platform"},
    }
    key = fingerprint(inputs)
    output = root / "outputs/feature_capacity" / key
    output.mkdir(parents=True, exist_ok=True)
    with FileLock(str(output / ".run.lock"), timeout=0):
        _run(feature_run, output, key, inputs)
    atomic_json(output.parent / "latest.json", {"fingerprint": key, "directory": key})
    publish(root, output)
    return output


def _run(feature_run: Path, output: Path, key: str, inputs: dict[str, Any]) -> None:
    config, feature_key = inputs["config"], inputs["feature_fingerprint"]
    log = EventLog(output / "events.jsonl")
    log.emit("run_started", fingerprint=key)
    atomic_json(output / "manifest.json", {"fingerprint": key, "inputs": inputs})
    store = TaskStore(output, key, log, config["heartbeat_seconds"])
    matrix = pd.read_parquet(feature_run / "features.parquet")
    # Filter before any data-dependent operation. Benchmark/2026 labels never enter this study.
    matrix = matrix.loc[
        matrix.Season.between(config["first_training_season"], max(config["validation_seasons"]))
    ].copy()
    validate_matrix(matrix)
    years = sorted(int(y) for y in matrix.Season.unique() if y > config["first_training_season"])
    frames, audits = [], []
    inherited = 0
    for route, (gender, block) in ROUTES.items():
        columns = candidate_blocks(gender == "M")[block]
        for model_name in config["models"]:
            reference_name = (
                f"fold_{gender.lower()}_{min(config['validation_seasons'])}_{block}_{model_name}"
            )
            reference = verified_reference(feature_run, reference_name, feature_key)
            template = joblib.load(reference / "model.joblib")["estimator"].model
            for year in years:
                train = matrix.loc[(matrix.Gender == gender) & (matrix.Season < year)]
                valid = matrix.loc[(matrix.Gender == gender) & (matrix.Season == year)]
                for cap in config["capacities"]:
                    old_name = f"fold_{gender.lower()}_{year}_{block}_{model_name}"
                    reuse = cap == 128 and (feature_run / old_name / "checkpoint.json").exists()

                    def fit(
                        target: Path,
                        train: pd.DataFrame = train,
                        valid: pd.DataFrame = valid,
                        columns: list[str] = columns,
                        template: Any = template,
                        cap: int = cap,
                        reuse: bool = reuse,
                        old_name: str = old_name,
                    ) -> list[Path]:
                        if reuse:
                            old = verified_reference(feature_run, old_name, feature_key)
                            record = json.loads((old / "fold.json").read_text())
                            if (
                                record["train_seasons"] != sorted(train.Season.unique().tolist())
                                or record["requested_features"] != columns
                            ):
                                raise ValueError("Reference fit population or columns differ")
                            saved = pd.read_parquet(old / "predictions.parquet")
                            if not saved[KEYS].equals(valid[KEYS].reset_index(drop=True)):
                                raise ValueError("Reference forecast games differ")
                            for name in [
                                "model.joblib",
                                "predictions.parquet",
                                "screening.csv",
                                "fold.json",
                            ]:
                                shutil.copy2(old / name, target / name)
                            atomic_json(
                                target / "origin.json",
                                {
                                    "kind": "verified_reference",
                                    "task": old_name,
                                    "feature_fingerprint": feature_key,
                                },
                            )
                        else:
                            with threadpool_limits(limits=config["threads"]):
                                estimator, fitted, p = fit_capacity(
                                    train, valid, columns, template, cap
                                )
                            valid[KEYS].assign(p=p).to_parquet(
                                target / "predictions.parquet", index=False
                            )
                            joblib.dump(
                                {"estimator": estimator, "features": fitted},
                                target / "model.joblib",
                            )
                            screening_audit(estimator, fitted).to_csv(
                                target / "screening.csv", index=False
                            )
                            atomic_json(
                                target / "fold.json",
                                {
                                    "train_seasons": sorted(train.Season.unique().tolist()),
                                    "validation_season": int(valid.Season.iloc[0]),
                                    "requested_features": columns,
                                    "model_input_features": fitted,
                                    "features": [fitted[i] for i in estimator.screen.indices_],
                                    "retained_count": len(estimator.screen.indices_),
                                    "capacity": cap,
                                },
                            )
                            atomic_json(target / "origin.json", {"kind": "new_fit"})
                        return [
                            target / name
                            for name in [
                                "model.joblib",
                                "predictions.parquet",
                                "screening.csv",
                                "fold.json",
                                "origin.json",
                            ]
                        ]

                    task = store.task(f"{route.lower()}_{model_name}_{year}_{cap}", fit)
                    frames.append(
                        pd.read_parquet(task / "predictions.parquet")[KEYS + ["p"]].assign(
                            route=route, model=model_name, capacity=cap
                        )
                    )
                    fold = json.loads((task / "fold.json").read_text())
                    inherited += int(
                        json.loads((task / "origin.json").read_text())["kind"]
                        == "verified_reference"
                    )
                    audits.append(
                        {
                            "route": route,
                            "model": model_name,
                            "Season": year,
                            "capacity": cap,
                            "candidate_count": len(columns),
                            "retained_count": fold["retained_count"],
                            "train_games": len(train),
                            "validation_games": len(valid),
                            "reference_reused": reuse,
                        }
                    )
    predictions = pd.concat(frames, ignore_index=True)
    predictions.to_csv(output / "predictions.csv", index=False)
    pd.DataFrame(audits).to_csv(output / "fit_audit.csv", index=False)
    summarize(predictions, config, output)
    atomic_json(
        output / "summary.json",
        {
            "status": "completed",
            "fingerprint": key,
            "feature_fingerprint": feature_key,
            "candidate_count": len(candidate_blocks()["full"]),
            "fit_tasks": len(audits),
            "inherited_reference_fits": inherited,
            "new_fits": len(audits) - inherited,
            "validation_seasons": config["validation_seasons"],
            "benchmark_labels_used": False,
            "final_recipe_changed": False,
        },
    )
    log.emit("run_completed", tasks=len(audits), inherited=inherited)


def publish(root: Path, output: Path) -> None:
    destination = root / "reports/feature_capacity"
    destination.mkdir(parents=True, exist_ok=True)
    filenames = [
        "leaderboard.csv",
        "intervals.csv",
        "selection.csv",
        "fit_audit.csv",
        "predictions.csv",
        "evaluation.csv",
    ]
    for name in filenames:
        shutil.copy2(output / name, destination / name)
    atomic_json(
        destination / "run.json",
        {
            "summary": json.loads((output / "summary.json").read_text()),
            "manifest": json.loads((output / "manifest.json").read_text()),
            "sha256": {name: digest(destination / name) for name in filenames},
        },
    )


def review(root: Path) -> tuple[Path, dict[str, Any]]:
    folder, record = evidence(root, "feature_capacity")
    _, features = evidence(root, "feature_store")
    inputs = record["manifest"]["inputs"]
    if inputs["feature_fingerprint"] != features["summary"]["fingerprint"]:
        raise ValueError("Stale feature-capacity lineage")
    if inputs["config"] != json.loads((root / "configs/feature_capacity.json").read_text()):
        raise ValueError("Stale feature-capacity configuration")
    for name, expected in inputs["source"].items():
        if digest(safe_path(root, name)) != expected:
            raise ValueError(f"Stale feature-capacity source: {name}")
    return folder, record


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(run(Path.cwd()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
