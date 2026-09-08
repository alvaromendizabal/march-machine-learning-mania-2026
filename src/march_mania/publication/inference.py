"""Freeze development choices, evaluate consumed years, and generate real 2026 predictions.

No 2026 tournament label enters selection, calibration, fitting, or prediction.
The 2022-2025 comparison is retrospective and cannot establish an untouched holdout.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from filelock import FileLock
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from march_mania.feature_selection import ScreenedPredictor, TrainingScreen
from march_mania.modeling import candidates, columns_for, predict_candidate, select_candidate
from march_mania.publication.artifacts import download_input, restore_tasks
from march_mania.publication.submission import validate_submission
from march_mania.research_report import probability_metrics
from march_mania.runtime import EventLog, Mirror, TaskStore, atomic_json, digest, fingerprint


def validate_config(config: dict[str, Any]) -> None:
    if config["protocol"] != "retrospective-final-prediction":
        raise ValueError("Explicit retrospective protocol required")
    if config["prediction_season"] != 2026 or config["first_training_season"] != 2013:
        raise ValueError("This release implements the recorded 2013-2026 contract")
    if config["selection_seasons"] != [2016, 2017, 2018, 2019, 2021]:
        raise ValueError("Do not change development seasons after benchmark inspection")
    if config["benchmark_seasons"] != [2022, 2023, 2024, 2025]:
        raise ValueError("The consumed benchmark is 2022-2025")
    if config["families"] != {"M": "rank_logistic", "W": "logistic"}:
        raise ValueError("Model families must match the declared development winners")
    if config["calibration"] != "identity":
        raise ValueError("No new temperature tuning or probability clipping is permitted")
    for name in ("chunk_size", "threads", "heartbeat_seconds"):
        if isinstance(config[name], bool) or not isinstance(config[name], int) or config[name] <= 0:
            raise ValueError(f"{name} must be a positive integer")


def freeze_recipe(history: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    """Use only recorded candidate OOF forecasts from the declared development seasons."""
    validate_config(config)
    history = history.loc[history.Season.isin(config["selection_seasons"])].copy()
    result: dict[str, Any] = {
        "selection_seasons": config["selection_seasons"],
        "selection_metric": "mean season Brier",
        "calibration": "identity",
        "selection_status": "retrospective development; not a new holdout",
        "genders": {},
    }
    for gender, family in config["families"].items():
        population = history.loc[(history.Gender == gender) & (history.route == gender)]
        if sorted(population.Season.unique()) != config["selection_seasons"]:
            raise ValueError("Missing development prediction seasons")
        if population.duplicated(["Season", "ID", "candidate"]).any():
            raise ValueError("Duplicate candidate OOF games")
        if not np.isin(population.y, [0, 1]).all() or not np.isfinite(population.p).all():
            raise ValueError("Invalid candidate OOF labels or probabilities")
        if not population.p.between(0, 1).all():
            raise ValueError("Invalid candidate OOF probabilities")
        name = select_candidate(population, family, 2022)
        candidate = next(c for c in candidates(gender) if c.name == name)
        columns = columns_for(candidate)
        seed_free = [column for column in columns if "seed" not in column.lower()]
        if not seed_free or len(seed_free) == len(columns):
            raise ValueError("Expected explicit seeded and seed-free feature routes")
        result["genders"][gender] = {
            "candidate": asdict(candidate),
            "features": {"seeded": columns, "seed_free": seed_free},
            "seed_free_note": "Same regularization; remove every seed-dependent input",
        }
    return result


def validate_games(frame: pd.DataFrame, last_season: int) -> None:
    required = {"Gender", "Season", "DayNum", "ID", "y"}
    if frame.empty or not required.issubset(frame):
        raise ValueError("Missing labeled physical games")
    if not frame.Season.between(2013, last_season).all() or frame.Season.eq(2020).any():
        raise ValueError("Training/evaluation season crosses the declared boundary")
    if not frame.DayNum.gt(132).all() or not frame.Gender.isin(["M", "W"]).all():
        raise ValueError("Invalid tournament population")
    if frame.duplicated(["Gender", "Season", "ID"]).any() or not np.isin(frame.y, [0, 1]).all():
        raise ValueError("Duplicate games or invalid outcomes")
    parsed = frame.ID.str.extract(r"^(\d{4})_(\d{4})_(\d{4})$")
    if parsed.isna().any().any():
        raise ValueError("Malformed game identity")
    if not parsed[0].astype(int).eq(frame.Season).all() or not (parsed[1] < parsed[2]).all():
        raise ValueError("Game identities must match season and lower-TeamID orientation")


def validate_matchups(frame: pd.DataFrame, sample: pd.DataFrame) -> None:
    validate_submission(sample, sample)
    if "y" in frame or "Pred" in frame or frame.empty:
        raise ValueError("Inference matrix must be label-free")
    if not frame.Season.eq(2026).all() or frame.ID.tolist() != sample.ID.tolist():
        raise ValueError("Inference matrix must exactly match the 2026 template")
    if set(frame.Gender) != {"M", "W"}:
        raise ValueError("Both tournament populations are required")
    parsed = frame.ID.str.split("_", expand=True)
    for gender, digit in (("M", "1"), ("W", "3")):
        rows = frame.Gender.eq(gender)
        if not (
            parsed.loc[rows, 1].str.startswith(digit) & parsed.loc[rows, 2].str.startswith(digit)
        ).all():
            raise ValueError("Mixed or inconsistent tournament/team identities")


def fit_model(
    train: pd.DataFrame, valid: pd.DataFrame, columns: list[str], c: float, config: dict[str, Any]
) -> Any:
    validate_games(train, int(valid.Season.min()) - 1)
    if train.y.nunique() != 2 or not columns or len(set(columns)) != len(columns):
        raise ValueError("Both labels and unique explicit features are required")
    values = train[columns].to_numpy(dtype=float)
    if np.isinf(values).any():
        raise ValueError("Features must have finite training support")
    model = make_pipeline(
        SimpleImputer(strategy="median", keep_empty_features=True),
        StandardScaler(),
        LogisticRegression(C=c, max_iter=3000, random_state=config["seed"]),
    )
    with threadpool_limits(limits=config["threads"]):
        x, y = np.concatenate([values, -values]), np.concatenate([train.y, 1 - train.y])
        screen = TrainingScreen().fit(x, y)
        model.fit(screen.transform(x), y)
    return ScreenedPredictor(screen, model)


def forecast(model: Any, frame: pd.DataFrame, columns: list[str], threads: int) -> np.ndarray:
    values = frame[columns].to_numpy(dtype=float)
    if np.isinf(values).any():
        raise ValueError("Infinite inference features")
    with threadpool_limits(limits=threads):
        p = predict_candidate(model, values, threads)
        reverse = predict_candidate(model, -values, threads)
    if not np.allclose(p + reverse, 1, atol=1e-12, rtol=0):
        raise ValueError("Team-swap probability symmetry failed")
    return p


def training_task(
    store: TaskStore,
    train: pd.DataFrame,
    valid: pd.DataFrame,
    gender: str,
    route: str,
    season: int,
    recipe: dict[str, Any],
    config: dict[str, Any],
) -> Path:
    specification = recipe["genders"][gender]
    columns = specification["features"][route]

    def work(target: Path) -> list[Path]:
        model = fit_model(train, valid, columns, specification["candidate"]["parameter"], config)
        joblib.dump({"model": model, "features": columns}, target / "model.joblib")
        atomic_json(
            target / "audit.json",
            {
                "gender": gender,
                "route": route,
                "prediction_season": season,
                "training_seasons": sorted(int(s) for s in train.Season.unique()),
                "training_games": len(train),
                "features": columns,
                "retained_features": [columns[i] for i in model.screen.indices_],
                "candidate_count": len(columns),
                "retained_count": len(model.screen.indices_),
                "candidate": specification["candidate"],
                "calibration": "identity",
                "training_max_season": int(train.Season.max()),
            },
        )
        return [target / "model.joblib", target / "audit.json"]

    return store.task(f"fit_{gender.lower()}_{season}_{route}", work)


def make_report(benchmark: pd.DataFrame, destination: Path) -> list[Path]:
    rows = []
    for (gender, route, year), group in benchmark.groupby(["Gender", "route", "Season"]):
        rows.append(
            {
                "Gender": gender,
                "route": route,
                "Season": year,
                "games": len(group),
                **probability_metrics(group.y.to_numpy(), group.p.to_numpy()),
            }
        )
    by_season = pd.DataFrame(rows)
    by_season.to_csv(destination / "metrics_by_season.csv", index=False)
    overall = []
    curves = []
    for (gender, route), group in benchmark.groupby(["Gender", "route"]):
        selected = by_season.loc[(by_season.Gender == gender) & (by_season.route == route)]
        overall.append(
            {
                "Gender": gender,
                "route": route,
                "games": len(group),
                "mean_season_brier": float(selected.brier.mean()),
                **probability_metrics(group.y.to_numpy(), group.p.to_numpy()),
            }
        )
        bins = group.assign(bin=np.minimum((group.p * 10).astype(int), 9))
        curve = (
            bins.groupby("bin")
            .agg(predicted=("p", "mean"), observed=("y", "mean"), games=("y", "size"))
            .reset_index()
        )
        curve["Gender"], curve["route"] = gender, route
        curves.append(curve)
    pd.DataFrame(overall).to_csv(destination / "metrics.csv", index=False)
    pd.concat(curves).to_csv(destination / "reliability.csv", index=False)
    benchmark.to_csv(destination / "benchmark_predictions.csv", index=False)
    return [
        destination / name
        for name in [
            "metrics.csv",
            "metrics_by_season.csv",
            "reliability.csv",
            "benchmark_predictions.csv",
        ]
    ]


def execute(
    frame: pd.DataFrame,
    matchups: pd.DataFrame | Path,
    sample: pd.DataFrame,
    recipe: dict[str, Any],
    output: Path,
    store: TaskStore,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Persist each estimator and forecast chunk; repeat calls verify and reuse them."""
    validate_config(config)
    # Drop future outcomes before any training or benchmark operation.
    frame = frame.loc[frame.Season.between(2013, 2025) & frame.Season.ne(2020)].copy()
    validate_games(frame, 2025)
    source = matchups
    if isinstance(source, Path):
        matchups = pd.read_parquet(source, columns=["Gender", "Season", "ID", "diff_seed"])
    else:
        matchups = source
    validate_matchups(matchups, sample)
    benchmark = []
    chunk_files = []
    final_fit_audits = []
    for gender in ("M", "W"):
        population = frame.loc[frame.Gender == gender]
        for season in [*config["benchmark_seasons"], 2026]:
            train = population.loc[population.Season < season]
            valid = (
                population.loc[population.Season == season]
                if season < 2026
                else matchups.loc[matchups.Gender == gender]
            )
            if valid.empty or int(train.Season.max()) != season - 1:
                raise ValueError("Missing final-fit or benchmark season coverage")
            for route in ("seeded", "seed_free"):
                fitted = training_task(store, train, valid, gender, route, season, recipe, config)
                saved = joblib.load(fitted / "model.joblib")  # Own checksum-verified task only.
                if season < 2026:

                    def evaluate(
                        target: Path,
                        valid: pd.DataFrame = valid,
                        saved: dict = saved,
                        route: str = route,
                    ) -> list[Path]:
                        rows = valid[["Gender", "Season", "DayNum", "ID", "y"]].copy()
                        rows["p"] = forecast(
                            saved["model"], valid, saved["features"], config["threads"]
                        )
                        rows["route"] = route
                        rows.to_csv(target / "predictions.csv", index=False)
                        return [target / "predictions.csv"]

                    target = store.task(f"score_{gender.lower()}_{season}_{route}", evaluate)
                    benchmark.append(pd.read_csv(target / "predictions.csv"))
                    continue
                final_fit_audits.append(json.loads((fitted / "audit.json").read_text()))
                # Persisted screening is a training-only decision. Column projection
                # changes memory usage, not the estimator or its probabilities.
                if isinstance(saved["model"], ScreenedPredictor):
                    selected_columns = [
                        saved["features"][i] for i in saved["model"].screen.indices_
                    ]
                    saved = {"model": saved["model"].model, "features": selected_columns}
                if isinstance(source, Path):
                    projection = list(
                        dict.fromkeys(["Gender", "Season", "ID", "diff_seed", *saved["features"]])
                    )
                    valid = pd.read_parquet(
                        source, columns=projection, filters=[("Gender", "==", gender)]
                    )
                eligible = valid.diff_seed.notna() if route == "seeded" else valid.diff_seed.isna()
                inference = valid.loc[eligible]
                for start in range(0, len(inference), config["chunk_size"]):
                    chunk = inference.iloc[start : start + config["chunk_size"]]

                    def predict(
                        target: Path,
                        chunk: pd.DataFrame = chunk,
                        saved: dict = saved,
                        route: str = route,
                    ) -> list[Path]:
                        values = forecast(
                            saved["model"], chunk, saved["features"], config["threads"]
                        )
                        pd.DataFrame(
                            {"ID": chunk.ID, "Pred": values, "route": route, "Gender": chunk.Gender}
                        ).to_csv(target / "predictions.csv", index=False)
                        return [target / "predictions.csv"]

                    target = store.task(f"predict_{gender.lower()}_{route}_{start:06d}", predict)
                    chunk_files.append(target / "predictions.csv")
                    store.log.emit(
                        "prediction_progress",
                        gender=gender,
                        route=route,
                        completed=min(start + config["chunk_size"], len(inference)),
                        total=len(inference),
                    )

    def publish(target: Path) -> list[Path]:
        rows = pd.concat([pd.read_csv(path) for path in chunk_files], ignore_index=True)
        if rows.ID.duplicated().any() or set(rows.ID) != set(sample.ID):
            raise ValueError("Incomplete or duplicated prediction chunks")
        rows = rows.set_index("ID").loc[sample.ID].reset_index()
        submission = rows[["ID", "Pred"]]
        audit = validate_submission(submission, sample)
        submission.to_csv(target / "submission.csv", index=False, float_format="%.17g")
        validate_submission(pd.read_csv(target / "submission.csv"), sample)
        files = make_report(pd.concat(benchmark, ignore_index=True), target)
        counts = rows.groupby(["Gender", "route"]).size().reset_index(name="rows")
        counts.to_csv(target / "routes.csv", index=False)
        atomic_json(target / "recipe.json", recipe)
        atomic_json(target / "fit_audits.json", final_fit_audits)
        audit.update(
            status="completed",
            fingerprint=store.run_fingerprint,
            submission_sha256=digest(target / "submission.csv"),
            model_fits=20,
            final_model_fits=4,
            benchmark_model_fits=16,
            benchmark_status="2022-2025 previously consumed; retrospective only",
            scored_population=(
                "Local benchmark includes play-ins; not identical to Kaggle scored games"
            ),
            kaggle_submission_sent=False,
            future_labels_used=False,
            final_training_max_season=2025,
        )
        atomic_json(target / "summary.json", audit)
        return files + [
            target / name
            for name in [
                "submission.csv",
                "routes.csv",
                "recipe.json",
                "fit_audits.json",
                "summary.json",
            ]
        ]

    published = store.task("publication", publish)
    return json.loads((published / "summary.json").read_text())


def run(
    feature_run: Path,
    model_run: Path,
    sample_path: Path,
    root: Path,
    run_root: Path,
    config: dict[str, Any],
    s3: str | None = None,
) -> Path:
    import platform
    from importlib.metadata import version

    validate_config(config)
    for completed in (feature_run, model_run):
        if json.loads((completed / "summary.json").read_text())["status"] != "completed":
            raise ValueError("Upstream runs must be completed")
    matrix_hash = json.loads((model_run / "manifest.json").read_text())["inputs"]["data"][
        "features.parquet"
    ]
    if digest(feature_run / "features.parquet") != matrix_hash:
        raise ValueError("Model selection and final fitting must share the same feature matrix")
    inputs_paths = {
        "features": feature_run / "features.parquet",
        "matchups": feature_run / "submission_features.parquet",
        "history": model_run / "candidate_predictions.parquet",
        "template": sample_path,
    }
    source_paths = list((root / "src/march_mania").glob("*.py"))
    source_paths += [
        Path(__file__),
        Path(__file__).with_name("artifacts.py"),
        Path(__file__).with_name("submission.py"),
        root / "pyproject.toml",
        root / "uv.lock",
    ]
    inputs = {
        "config": config,
        "data": {k: digest(v) for k, v in inputs_paths.items()},
        "source": {str(p.relative_to(root)): digest(p) for p in source_paths},
        "environment": {
            "python": platform.python_version(),
            **{
                p: version(p)
                for p in ["numpy", "pandas", "scipy", "scikit-learn", "pyarrow", "joblib"]
            },
        },
    }
    key = fingerprint(inputs)
    output = run_root / key
    output.mkdir(parents=True, exist_ok=True)
    with FileLock(str(output / ".lock"), timeout=0):
        log = EventLog(output / "events.jsonl")
        mirror = Mirror(f"{s3.rstrip('/')}/{key}") if s3 else None
        log.emit("run_started", fingerprint=key)
        if mirror:
            restore_tasks(mirror, output, key, log)
        store = TaskStore(output, key, log, config["heartbeat_seconds"], mirror)
        history = pd.read_parquet(inputs_paths["history"])
        recipe = freeze_recipe(history, config)
        # Freeze before opening benchmark labels; never overwrite a different recipe.
        manifest = {"fingerprint": key, "inputs": inputs, "recipe": recipe}
        atomic_json(output / "manifest.json", manifest)
        if mirror:
            mirror.upload(output / "manifest.json", "manifest.json")
        try:
            execute(
                pd.read_parquet(inputs_paths["features"]),
                inputs_paths["matchups"],
                pd.read_csv(sample_path),
                recipe,
                output,
                store,
                config,
            )
            if any(digest(path) != inputs["data"][name] for name, path in inputs_paths.items()):
                raise ValueError("An input changed during the run")
            public = output / "publication"
            evidence = root / "reports/final_predictions"
            evidence.mkdir(parents=True, exist_ok=True)
            for path in public.iterdir():
                if path.name not in {"submission.csv", "checkpoint.json", ".lock"}:
                    shutil.copy2(path, evidence / path.name)
            atomic_json(evidence / "run.json", manifest)
            with zipfile.ZipFile(output / "source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
                for path in source_paths:
                    archive.write(path, str(path.relative_to(root)))
                archive.writestr("configs/inference.json", json.dumps(config, indent=2))
            if mirror:
                mirror.upload(output / "source.zip", "source.zip")
            atomic_json(run_root / "latest.json", {"directory": key, "fingerprint": key})
            log.emit(
                "run_completed",
                fingerprint=key,
                submission_sha256=digest(public / "submission.csv"),
            )
            if mirror:
                mirror.upload(log.path, "events.jsonl")
            return public
        except BaseException as error:
            log.emit("run_failed", error_type=type(error).__name__, error=str(error))
            if mirror:
                mirror.upload(log.path, "events.jsonl")
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-inputs", action="store_true")
    parser.add_argument("--inputs", type=Path, default=Path("outputs/inference_inputs"))
    parser.add_argument("--run-root", type=Path, default=Path("outputs/final_predictions"))
    parser.add_argument("--config", type=Path, default=Path("configs/inference.json"))
    parser.add_argument("--s3")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    log = EventLog(args.inputs / "events.jsonl")
    if args.download_inputs:
        for name, report in [("features", "feature_store"), ("models", "model_comparison")]:
            record = json.loads((root / "reports" / report / "run.json").read_text())["archive"]
            download_input(record, args.inputs / name, log)
    output = run(
        args.inputs / "features/run",
        args.inputs / "models/run",
        args.inputs / "features/raw/SampleSubmissionStage2.csv",
        root,
        args.run_root,
        json.loads(args.config.read_text()),
        args.s3,
    )
    log.emit(
        "inference_completed", publication=str(output), total_seconds=time.monotonic() - log.started
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
