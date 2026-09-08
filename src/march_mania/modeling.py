"""Nested temporal model selection on the verified pre-tournament feature store.

One physical game per row; mirrored pairs are created only inside a training fold.
Every candidate fit is checkpointed once and reused by later outer folds.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from filelock import FileLock
from scipy.optimize import minimize, minimize_scalar
from scipy.special import expit, logit
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits
from xgboost import XGBClassifier

from march_mania.advanced_features import candidate_blocks
from march_mania.feature_selection import ScreenedPredictor, TrainingScreen, screening_audit
from march_mania.publication.artifacts import restore_tasks
from march_mania.research import finalize_run, symmetric_probability
from march_mania.runtime import (
    EventLog,
    Mirror,
    TaskStore,
    atomic_json,
    digest,
    fingerprint,
    runtime_identity,
)

KEYS = ["Gender", "Season", "DayNum", "ID", "y"]


@dataclass(frozen=True)
class Candidate:
    name: str
    family: str
    block: str
    parameter: float


def candidates(route: str) -> list[Candidate]:
    """Bounded search, declared before outcomes are read; common features for pooling."""
    result = [Candidate("seed", "seed", "seed", 0.1)]
    for block in ("strength", "dynamic", "four_factors", "ball_control", "full"):
        for index, penalty in enumerate((0.03, 0.3)):
            result.append(Candidate(f"logistic_{block}_{index}", "logistic", block, penalty))
    for family in ("hist", "xgboost", "lightgbm"):
        for block in ("strength", "full"):
            for depth in (2, 3):
                result.append(Candidate(f"{family}_{block}_{depth}", family, block, depth))
    if route == "M":
        for index, penalty in enumerate((0.03, 0.3)):
            result.append(Candidate(f"rank_logistic_{index}", "rank_logistic", "rankings", penalty))
            result.append(
                Candidate(f"rank_logistic_full_{index}", "rank_logistic", "full", penalty)
            )
        # An explicit men-only ranking experiment; pooled/common baselines stay unchanged.
        for family in ("rank_xgboost", "rank_lightgbm"):
            for block in ("rankings", "full"):
                for depth in (2, 3):
                    result.append(Candidate(f"{family}_{block}_{depth}", family, block, depth))
    return result


def columns_for(candidate: Candidate) -> list[str]:
    # The common-feature comparison excludes all 23 Massey-derived variables for both sexes.
    return candidate_blocks(include_rankings=candidate.family.startswith("rank_"))[candidate.block]


def validate_config(config: dict[str, Any]) -> None:
    years = config["validation_seasons"]
    if not years or years != sorted(set(years)) or any(y >= 2022 or y == 2020 for y in years):
        raise ValueError("Use unique chronological development seasons before 2022, excluding 2020")
    if config["protocol"] != "retrospective-nested-model-comparison":
        raise ValueError("Evidence must be labeled retrospective")
    if config["minimum_inner_seasons"] < 2 or config["first_training_season"] >= min(years) - 1:
        raise ValueError("At least two earlier inner seasons are required")
    if config["threads"] < 1 or config["heartbeat_seconds"] <= 0:
        raise ValueError("Threads and heartbeat must be positive")
    bounds = config["calibration_temperature_bounds"]
    if len(bounds) != 2 or not 0 < bounds[0] < 1 < bounds[1]:
        raise ValueError("Temperature bounds must straddle one and be positive")
    if config["ensemble_l2"] <= 0 or config["permutation_repeats"] < 1:
        raise ValueError("Ensemble regularization and permutation repeats must be positive")


def validate_matrix(frame: pd.DataFrame) -> None:
    if frame.empty or not set(KEYS + ["Team1ID", "Team2ID"]).issubset(frame):
        raise ValueError("Missing physical-game keys")
    if frame[KEYS].isna().any().any() or frame.duplicated(["Gender", "Season", "ID"]).any():
        raise ValueError("Missing keys or duplicate physical games")
    if not frame.Gender.isin(["M", "W"]).all() or not frame.y.isin([0, 1]).all():
        raise ValueError("Invalid gender or binary target")
    if (frame.Season >= 2022).any() or (frame.Season == 2020).any() or (frame.DayNum <= 132).any():
        raise ValueError("Only post-cutoff development tournament labels are allowed")
    expected = (
        frame.Season.astype(str) + "_" + frame.Team1ID.astype(str) + "_" + frame.Team2ID.astype(str)
    )
    if not expected.equals(frame.ID) or not (frame.Team1ID < frame.Team2ID).all():
        raise ValueError("Expected canonical lower-TeamID-first games")
    values = frame[candidate_blocks()["full"]].to_numpy(dtype=float)
    if np.isinf(values).any():
        raise ValueError("Infinite feature values")


def fit_candidate(
    train: pd.DataFrame, valid: pd.DataFrame, candidate: Candidate, seed: int, threads: int
) -> tuple[Any, np.ndarray]:
    if train.empty or valid.empty or train.Season.max() >= valid.Season.min():
        raise ValueError("Temporal overlap or empty fold")
    if train.y.nunique() != 2:
        raise ValueError("Training requires both classes")
    columns = columns_for(candidate)
    x = train[columns].to_numpy(dtype=float)
    y = train.y.to_numpy(dtype=int)
    x, y = np.concatenate([x, -x]), np.concatenate([y, 1 - y])
    screen = TrainingScreen().fit(x, y)
    x = screen.transform(x)
    family = candidate.family.removeprefix("rank_")
    if family in {"seed", "logistic"}:
        model: Any = make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            StandardScaler(),
            LogisticRegression(C=candidate.parameter, max_iter=3000, random_state=seed),
        )
    elif family == "hist":
        model = HistGradientBoostingClassifier(
            max_iter=120,
            learning_rate=0.04,
            max_leaf_nodes=2 ** int(candidate.parameter),
            min_samples_leaf=25,
            l2_regularization=10,
            early_stopping=False,
            random_state=seed,
        )
    elif family == "xgboost":
        model = XGBClassifier(
            n_estimators=120,
            learning_rate=0.04,
            max_depth=int(candidate.parameter),
            min_child_weight=10,
            reg_lambda=10,
            tree_method="hist",
            device="cpu",
            n_jobs=threads,
            random_state=seed,
            eval_metric="logloss",
        )
    elif family == "lightgbm":
        # Native API avoids sklearn feature-name adaptation; fatal errors still raise.
        model = lgb.train(
            {
                "objective": "binary",
                "learning_rate": 0.04,
                "num_leaves": 2 ** int(candidate.parameter),
                "min_data_in_leaf": 25,
                "lambda_l2": 10,
                "num_threads": threads,
                "deterministic": True,
                "force_col_wise": True,
                "verbosity": -1,
                "seed": seed,
            },
            lgb.Dataset(x, label=y, feature_name=[columns[i] for i in screen.indices_]),
            num_boost_round=120,
        )
        model = ScreenedPredictor(screen, model)
        return model, predict_candidate(model, valid[columns].to_numpy(dtype=float), threads)
    else:
        raise ValueError(f"Unknown model family: {candidate.family}")
    model.fit(x, y)
    model = ScreenedPredictor(screen, model)
    return model, predict_candidate(model, valid[columns].to_numpy(dtype=float), threads)


def predict_candidate(model: Any, values: np.ndarray, threads: int = 2) -> np.ndarray:
    if isinstance(model, lgb.Booster):
        p = (
            np.asarray(model.predict(values, num_threads=threads), dtype=float)
            + 1
            - np.asarray(model.predict(-values, num_threads=threads), dtype=float)
        ) / 2
    else:
        p = symmetric_probability(model, values)
    result = np.asarray(p, dtype=float)
    if not np.isfinite(result).all() or ((result < 0) | (result > 1)).any():
        raise ValueError("Invalid model probabilities")
    return result


def season_weights(seasons: np.ndarray) -> np.ndarray:
    _, inverse, counts = np.unique(seasons, return_inverse=True, return_counts=True)
    if not len(counts):
        raise ValueError("No seasons to score")
    return 1 / (len(counts) * counts[inverse])


def temperature_probability(p: np.ndarray, temperature: float) -> np.ndarray:
    if temperature <= 0 or not np.isfinite(temperature):
        raise ValueError("Temperature must be finite and positive")
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Invalid calibration probabilities")
    return expit(logit(np.clip(p, 1e-7, 1 - 1e-7)) / temperature)


def fit_temperature(frame: pd.DataFrame, bounds: list[float]) -> float:
    weights = season_weights(frame.Season.to_numpy())
    result = minimize_scalar(
        lambda value: float(
            np.dot(weights, (frame.y - temperature_probability(frame.p.to_numpy(), value)) ** 2)
        ),
        bounds=tuple(bounds),
        method="bounded",
        options={"xatol": 1e-7},
    )
    if not result.success:
        raise RuntimeError("Temperature optimization did not converge")
    return float(result.x)


def calibrate_from_history(
    history: pd.DataFrame, outer_season: int, bounds: list[float]
) -> tuple[float, dict[str, Any]]:
    """Compare identity/temperature prequentially, then fit only on earlier OOF rows."""
    if history.empty or history.Season.max() >= outer_season or history.Season.nunique() < 2:
        raise ValueError("Calibration requires at least two strictly earlier OOF seasons")
    records = []
    for year in sorted(history.Season.unique())[1:]:
        train, valid = history.loc[history.Season < year], history.loc[history.Season == year]
        temperature = fit_temperature(train, bounds)
        records.append(
            {
                "season": int(year),
                "fit_last_season": int(train.Season.max()),
                "identity_brier": float(np.mean((valid.y - valid.p) ** 2)),
                "temperature_brier": float(
                    np.mean(
                        (valid.y - temperature_probability(valid.p.to_numpy(), temperature)) ** 2
                    )
                ),
            }
        )
    scores = pd.DataFrame(records)
    use_temperature = scores.temperature_brier.mean() < scores.identity_brier.mean()
    selected = fit_temperature(history, bounds) if use_temperature else 1.0
    return selected, {
        "method": "temperature" if use_temperature else "identity",
        "temperature": selected,
        "crossfit": records,
        "history_seasons": sorted(int(s) for s in history.Season.unique()),
    }


def simplex_weights(
    probabilities: np.ndarray, y: np.ndarray, seasons: np.ndarray, penalty: float
) -> np.ndarray:
    if (
        probabilities.ndim != 2
        or len(probabilities) != len(y)
        or not np.isfinite(probabilities).all()
    ):
        raise ValueError("Invalid blend matrix")
    if ((probabilities < 0) | (probabilities > 1)).any() or not np.isin(y, [0, 1]).all():
        raise ValueError("Invalid blend probabilities or targets")
    count = probabilities.shape[1]
    if count < 1 or len(seasons) != len(y) or penalty <= 0:
        raise ValueError("Invalid blend dimensions or regularization")
    weights = season_weights(seasons)
    initial = np.full(count, 1 / count)
    result = minimize(
        lambda w: float(
            np.dot(weights, (y - probabilities @ w) ** 2) + penalty * np.sum((w - initial) ** 2)
        ),
        initial,
        method="SLSQP",
        bounds=[(0, 1)] * count,
        constraints={"type": "eq", "fun": lambda w: w.sum() - 1},
        options={"ftol": 1e-12, "maxiter": 300},
    )
    if not result.success:
        raise RuntimeError(f"Blend optimization failed: {result.message}")
    answer = np.maximum(result.x, 0)
    return answer / answer.sum()


def select_candidate(history: pd.DataFrame, family: str, outer_season: int) -> str:
    if history.empty or history.Season.max() >= outer_season:
        raise ValueError("Model selection must use strictly earlier OOF seasons")
    frame = history.loc[history.family == family].copy()
    if frame.empty:
        raise ValueError("No candidates for family")
    coverage = [frozenset(zip(g.Season, g.ID, strict=True)) for _, g in frame.groupby("candidate")]
    if len(set(coverage)) != 1:
        raise ValueError("Candidates must have identical physical-game coverage")
    scores = (
        frame.assign(loss=(frame.y - frame.p) ** 2).groupby(["candidate", "Season"]).loss.mean()
    )
    return str(scores.groupby("candidate").mean().sort_values(kind="stable").index[0])


def evaluate_context(
    forecasts: pd.DataFrame, gender: str, route: str, season: int, config: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    group = forecasts.loc[
        (forecasts.Gender == gender) & (forecasts.route == route) & (forecasts.Season <= season)
    ]
    prior, outer = group.loc[group.Season < season], group.loc[group.Season == season]
    if prior.Season.nunique() < config["minimum_inner_seasons"] or outer.empty:
        raise ValueError("Insufficient inner seasons or outer games")
    families = sorted(group.family.unique())
    results, decisions, inner_streams, outer_streams = [], {}, {}, {}
    for family in families:
        choice = select_candidate(prior, family, season)
        history = prior.loc[prior.candidate == choice].sort_values(["Season", "ID"])
        valid = outer.loc[outer.candidate == choice].sort_values(["Season", "ID"])
        temperature, calibration = calibrate_from_history(
            history, season, config["calibration_temperature_bounds"]
        )
        decisions[family] = {"candidate": choice, **calibration}
        inner_streams[family], outer_streams[family] = history, valid
        for suffix, probability in [
            ("raw", valid.p.to_numpy()),
            ("calibrated", temperature_probability(valid.p.to_numpy(), temperature)),
        ]:
            rows = valid[KEYS].copy()
            rows["p"], rows["model"], rows["block"] = probability, f"{family}_{suffix}", route
            results.append(rows)
    # Fit a regularized convex blend of raw inner OOF streams. Identity/temperature is
    # scored above separately; calibrated in-sample rows never masquerade as blend OOF.
    blend_families = [name for name in families if not name.startswith("rank_")]
    reference = inner_streams[blend_families[0]]
    reference_outer = outer_streams[blend_families[0]]
    for name in blend_families:
        if not reference[KEYS].equals(inner_streams[name][KEYS]) or not reference_outer[
            KEYS
        ].equals(outer_streams[name][KEYS]):
            # Index positions differ between candidate slices; compare physical keys below.
            if reference[KEYS].reset_index(drop=True).equals(
                inner_streams[name][KEYS].reset_index(drop=True)
            ) and reference_outer[KEYS].reset_index(drop=True).equals(
                outer_streams[name][KEYS].reset_index(drop=True)
            ):
                continue
            raise ValueError("Blend streams must match on every physical game and target")
    weights = simplex_weights(
        np.column_stack([inner_streams[n].p for n in blend_families]),
        reference.y.to_numpy(),
        reference.Season.to_numpy(),
        config["ensemble_l2"],
    )
    rows = reference_outer[KEYS].copy()
    rows["p"] = np.column_stack([outer_streams[n].p for n in blend_families]) @ weights
    rows["model"], rows["block"] = "blend", route
    results.append(rows)
    decisions["blend"] = {
        "weights": dict(zip(blend_families, weights.tolist(), strict=True)),
        "history_seasons": sorted(int(s) for s in reference.Season.unique()),
    }
    return pd.concat(results, ignore_index=True), decisions


def run_inputs(feature_run: Path, config: dict[str, Any]) -> dict[str, Any]:
    """Fingerprint actual matrix bytes, declared candidates, configuration and implementation."""
    validate_config(config)
    upstream = json.loads((feature_run / "summary.json").read_text())
    if upstream.get("status") != "completed":
        raise ValueError("Feature store must be completed")
    feature_path = feature_run / "features.parquet"
    root = Path(__file__).resolve().parents[2]
    source = [
        *Path(__file__).parent.glob("*.py"),
        root / "src/march_mania/publication/artifacts.py",
        root / "pyproject.toml",
        root / "uv.lock",
    ]
    # Record the actual installed distribution; portable audits can use the full
    # XGBoost package, while the production lock deliberately installs xgboost-cpu.
    try:
        backend, backend_version = "xgboost-cpu", version("xgboost-cpu")
    except PackageNotFoundError:
        backend, backend_version = "xgboost", version("xgboost")
    identity = {
        **runtime_identity(),
        backend: backend_version,
        "lightgbm": version("lightgbm"),
    }
    return {
        "config": config,
        "data": {"features.parquet": digest(feature_path)},
        "feature_fingerprint": upstream["fingerprint"],
        "source": {str(p.relative_to(root)): digest(p) for p in source},
        "environment": {k: v for k, v in identity.items() if k != "platform"},
        "candidates": {
            route: [asdict(c) for c in candidates(route)] for route in ["M", "W", "pooled_common"]
        },
    }


def run(
    feature_run: Path, run_root: Path, config: dict[str, Any], mirror_uri: str | None = None
) -> dict[str, Any]:
    validate_config(config)
    upstream = json.loads((feature_run / "summary.json").read_text())
    if upstream.get("status") != "completed":
        raise ValueError("Feature store must be completed")
    feature_path = feature_run / "features.parquet"
    frame = pd.read_parquet(
        feature_path,
        filters=[
            ("Season", ">=", config["first_training_season"]),
            ("Season", "<=", max(config["validation_seasons"])),
        ],
    )
    validate_matrix(frame)
    inputs = run_inputs(feature_run, config)
    run_hash = fingerprint(inputs)
    output = run_root / run_hash
    output.mkdir(parents=True, exist_ok=True)
    with FileLock(str(output / ".run.lock"), timeout=0):
        log = EventLog(output / "events.jsonl")
        log.emit("run_started", fingerprint=run_hash, physical_games=len(frame))
        atomic_json(output / "manifest.json", {"fingerprint": run_hash, "inputs": inputs})
        mirror = Mirror(mirror_uri.rstrip("/") + "/" + run_hash) if mirror_uri else None
        if mirror:
            restore_tasks(mirror, output, run_hash, log)
        store = TaskStore(output, run_hash, log, config["heartbeat_seconds"], mirror)
        try:
            summary = _run(frame, output, store, config)
            if digest(feature_path) != inputs["data"]["features.parquet"]:
                raise ValueError("Feature matrix changed during model fitting")
            summary.update(
                fingerprint=run_hash,
                feature_fingerprint=upstream["fingerprint"],
                feature_count=upstream.get("feature_count"),
                evidence_status=config["protocol"],
                remote_run_uri=mirror_uri.rstrip("/") + "/" + run_hash if mirror_uri else None,
            )
            finalize_run(output, summary, mirror, log)
            atomic_json(run_root / "latest.json", {"directory": run_hash, "fingerprint": run_hash})
            return summary
        except BaseException as error:
            atomic_json(
                output / "summary.json",
                {
                    "status": "failed",
                    "fingerprint": run_hash,
                    "error_type": type(error).__name__,
                    "error": str(error),
                },
            )
            log.emit("run_failed", error_type=type(error).__name__, error=str(error))
            raise


def _run(
    frame: pd.DataFrame, output: Path, store: TaskStore, config: dict[str, Any]
) -> dict[str, Any]:
    from march_mania.model_report import write_model_report

    years = sorted(int(s) for s in frame.Season.unique())[1:]
    routes = ["M", "W", "pooled_common"]
    total = len(years) * sum(len(candidates(route)) for route in routes)
    forecasts, completed = [], 0
    for route in routes:
        population = frame if route == "pooled_common" else frame.loc[frame.Gender == route]
        for season in years:
            train, valid = (
                population.loc[population.Season < season],
                population.loc[population.Season == season],
            )
            for candidate in candidates(route):

                def fit(
                    target: Path,
                    train: pd.DataFrame = train,
                    valid: pd.DataFrame = valid,
                    candidate: Candidate = candidate,
                    route: str = route,
                ) -> list[Path]:
                    with threadpool_limits(limits=config["threads"]):
                        model, p = fit_candidate(
                            train, valid, candidate, config["seed"], config["threads"]
                        )
                        reverse = predict_candidate(
                            model,
                            -valid[columns_for(candidate)].to_numpy(dtype=float),
                            config["threads"],
                        )
                    if not np.allclose(p + reverse, 1, atol=1e-7, rtol=0):
                        raise ValueError("Team-swap complement audit failed")
                    rows = valid[KEYS].copy()
                    rows["p"], rows["candidate"], rows["family"], rows["route"] = (
                        p,
                        candidate.name,
                        candidate.family,
                        route,
                    )
                    rows.to_parquet(target / "predictions.parquet", index=False)
                    joblib.dump(
                        {"model": model, "features": columns_for(candidate)},
                        target / "model.joblib",
                    )
                    audit = screening_audit(model, columns_for(candidate))
                    audit.to_csv(target / "screening.csv", index=False)
                    atomic_json(
                        target / "fold.json",
                        {
                            "train_seasons": sorted(int(s) for s in train.Season.unique()),
                            "validation_season": int(valid.Season.min()),
                            "train_games": len(train),
                            "validation_games": len(valid),
                            "features": columns_for(candidate),
                            "selected_features": [
                                columns_for(candidate)[i] for i in model.screen.indices_
                            ],
                            "candidate_count": len(columns_for(candidate)),
                            "retained_count": len(model.screen.indices_),
                            "candidate": asdict(candidate),
                            "max_complement_error": float(np.max(np.abs(p + reverse - 1))),
                        },
                    )
                    return [
                        target / n
                        for n in [
                            "predictions.parquet",
                            "model.joblib",
                            "fold.json",
                            "screening.csv",
                        ]
                    ]

                target = store.task(f"fit_{route.lower()}_{season}_{candidate.name}", fit)
                forecasts.append(pd.read_parquet(target / "predictions.parquet"))
                completed += 1
                store.log.emit(
                    "progress",
                    phase="candidate_fits",
                    completed=completed,
                    total=total,
                    percent=round(100 * completed / total, 1),
                )
    all_forecasts = pd.concat(forecasts, ignore_index=True)
    all_forecasts.to_parquet(output / "candidate_predictions.parquet", index=False)
    final, choices = [], []
    for route in routes:
        for gender in ["M", "W"] if route == "pooled_common" else [route]:
            for season in config["validation_seasons"]:

                def select(
                    target: Path, route: str = route, gender: str = gender, season: int = season
                ) -> list[Path]:
                    rows, decisions = evaluate_context(all_forecasts, gender, route, season, config)
                    rows.to_parquet(target / "predictions.parquet", index=False)
                    atomic_json(target / "decisions.json", decisions)
                    return [target / "predictions.parquet", target / "decisions.json"]

                target = store.task(f"select_{route.lower()}_{gender.lower()}_{season}", select)
                final.append(pd.read_parquet(target / "predictions.parquet"))
                choices.append(
                    {
                        "Gender": gender,
                        "route": route,
                        "Season": season,
                        "decisions": json.loads((target / "decisions.json").read_text()),
                    }
                )
    predictions = pd.concat(final, ignore_index=True)
    predictions.to_parquet(output / "predictions.parquet", index=False)
    atomic_json(output / "decisions.json", choices)
    interpretations = []
    for context in choices:
        if context["Season"] != max(config["validation_seasons"]):
            continue
        for family, decision in context["decisions"].items():
            if family in {"seed", "blend"}:
                continue

            def interpret(
                target: Path,
                context: dict = context,
                family: str = family,
                decision: dict = decision,
            ) -> list[Path]:
                season, route, gender = context["Season"], context["route"], context["Gender"]
                saved = joblib.load(
                    output
                    / f"fit_{route.lower()}_{season}_{decision['candidate']}"
                    / "model.joblib"
                )
                valid = frame.loc[(frame.Season == season) & (frame.Gender == gender)]
                values = valid[saved["features"]].to_numpy(dtype=float)
                rng = np.random.default_rng(config["seed"])
                records = []
                with threadpool_limits(limits=config["threads"]):
                    baseline = np.mean(
                        (
                            valid.y.to_numpy()
                            - predict_candidate(saved["model"], values, config["threads"])
                        )
                        ** 2
                    )
                    for index, name in enumerate(saved["features"]):
                        if index not in saved["model"].screen.indices_:
                            continue  # Unselected columns cannot affect this fitted model.
                        deltas = []
                        for _ in range(config["permutation_repeats"]):
                            altered = values.copy()
                            altered[:, index] = rng.permutation(altered[:, index])
                            probability = predict_candidate(
                                saved["model"], altered, config["threads"]
                            )
                            deltas.append(
                                float(np.mean((valid.y.to_numpy() - probability) ** 2) - baseline)
                            )
                        records.append(
                            {
                                "Gender": gender,
                                "route": route,
                                "Season": season,
                                "family": family,
                                "feature": name,
                                "brier_increase": float(np.mean(deltas)),
                                "permutation_sd": float(np.std(deltas)),
                                "repeats": config["permutation_repeats"],
                            }
                        )
                pd.DataFrame(records).to_csv(target / "permutation.csv", index=False)
                return [target / "permutation.csv"]

            name = f"interpret_{context['route'].lower()}_{context['Gender'].lower()}_{family}"
            target = store.task(name, interpret)
            interpretations.append(pd.read_csv(target / "permutation.csv"))
    if interpretations:
        pd.concat(interpretations, ignore_index=True).to_csv(
            output / "permutation.csv", index=False
        )

    def report(target: Path) -> list[Path]:
        write_model_report(predictions, choices, target, config["seed"])
        return [
            p
            for p in target.iterdir()
            if p.is_file() and not p.name.startswith(".") and p.name != "checkpoint.json"
        ]

    report_dir = store.task("report", report)
    for path in report_dir.iterdir():
        if path.is_file() and path.suffix in {".csv", ".html"}:
            (output / path.name).write_bytes(path.read_bytes())
    fit_seconds = sum(
        json.loads(p.read_text())["elapsed_seconds"] for p in output.glob("fit_*/checkpoint.json")
    )
    return {
        "status": "completed",
        "fit_tasks": completed,
        "selection_tasks": len(choices),
        "physical_validation_games": len(predictions[KEYS].drop_duplicates()),
        "prediction_rows": len(predictions),
        "training_seconds": round(fit_seconds, 3),
        "validation_seasons": config["validation_seasons"],
        "model_families": sorted(all_forecasts.family.unique()),
        "protocol_note": (
            "Outer season excluded from all model/calibration/blend decisions; development "
            "years previously explored; 2022-2025 benchmark already consumed in prior work."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feature-run",
        type=Path,
        help="Completed feature-store directory; defaults to its latest pointer",
    )
    parser.add_argument("--run-root", type=Path, default=Path("outputs/model_comparison"))
    parser.add_argument("--config", type=Path, default=Path("configs/model_comparison.json"))
    parser.add_argument("--s3", help="Private S3 prefix for per-task replication")
    args = parser.parse_args()
    feature_run = args.feature_run
    if feature_run is None:
        base = Path("outputs/feature_store")
        pointer = json.loads((base / "latest.json").read_text())
        feature_run = base / pointer["directory"]
        if not feature_run.resolve().is_relative_to(base.resolve()):
            raise ValueError("Invalid feature-store pointer")
    started = time.monotonic()
    run(feature_run, args.run_root, json.loads(args.config.read_text()), args.s3)
    print(
        json.dumps(
            {
                "event": "model_comparison_completed",
                "total_seconds": round(time.monotonic() - started, 3),
            }
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
