"""Freeze, fit and generate the current 50-file portfolio without future-label selection."""

from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from filelock import FileLock
from threadpoolctl import threadpool_limits

from march_mania import modeling
from march_mania.advanced_features import pair_features
from march_mania.feature_store import sample_pairs
from march_mania.publication import inference, portfolio, production_inputs, workflow
from march_mania.publication.artifacts import verified_write
from march_mania.publication.submission import validate_submission
from march_mania.runtime import (
    EventLog,
    TaskStore,
    atomic_json,
    digest,
    fingerprint,
    runtime_identity,
)

REPORT = "reports/prediction_production"
ROUTES = ("seeded", "seed_free")


def feature_columns(component: dict[str, Any], route: str) -> list[str]:
    if route not in ROUTES:
        raise ValueError("Unknown feature route")
    candidate = modeling.Candidate(**component["candidate"])
    columns = modeling.columns_for(candidate)
    if route == "seed_free":
        columns = [c for c in columns if "seed" not in c.lower()]
    return columns


def freeze(
    history: pd.DataFrame, config: dict[str, Any], model_config: dict[str, Any]
) -> dict[str, Any]:
    """Choose concrete parameters and blend weights from pre-2022 OOF evidence only."""
    portfolio.validate_config(config)
    modeling.validate_config(model_config)
    years = config["development_seasons"]
    history = history.loc[history.Season.isin(years)].copy()
    components: dict[str, Any] = {}
    streams, selections = [], []
    for gender, specifications in config["streams"].items():
        for spec in specifications:
            route, family = spec["route"], spec["family"]
            options = modeling.candidates(route)
            families = (
                sorted({c.family for c in options if not c.family.startswith("rank_")})
                if family == "blend"
                else [family]
            )
            selected: list[str] = []
            frames: list[pd.DataFrame] = []
            for current in families:
                population = history.loc[
                    (history.Gender == gender)
                    & (history.route == route)
                    & (history.family == current)
                ].copy()
                allowed = {c.name for c in options if c.family == current}
                if (
                    set(population.Season) != set(years)
                    or set(population.candidate) != allowed
                    or population.duplicated(["Season", "ID", "candidate"]).any()
                    or not np.isfinite(population.p).all()
                    or not population.p.between(0, 1).all()
                ):
                    raise ValueError("Incomplete or invalid development candidate population")
                inference.validate_games(population[modeling.KEYS].drop_duplicates(), 2021)
                games = population[modeling.KEYS].drop_duplicates().sort_values(["Season", "ID"])
                if any(
                    not group[modeling.KEYS]
                    .sort_values(["Season", "ID"])
                    .reset_index(drop=True)
                    .equals(games.reset_index(drop=True))
                    for _, group in population.groupby("candidate")
                ):
                    raise ValueError("Every candidate must cover the same development games")
                chosen = modeling.select_candidate(population, current, 2022)
                candidate = next(c for c in options if c.name == chosen)
                definition: dict[str, Any] = {"population": route, "candidate": asdict(candidate)}
                definition["feature_routes"] = {
                    r: {
                        "count": len(feature_columns(definition, r)),
                        "sha256": fingerprint(feature_columns(definition, r)),
                    }
                    for r in ROUTES
                }
                key = "c_" + fingerprint(definition)[:20]
                components[key] = definition
                selected.append(key)
                rows = (
                    population.loc[population.candidate == chosen]
                    .sort_values(["Season", "ID"])
                    .reset_index(drop=True)
                )
                if frames and not rows[modeling.KEYS].equals(frames[0][modeling.KEYS]):
                    raise ValueError("Ensemble components must share physical games and targets")
                frames.append(rows)
                selections.append(
                    {
                        "stream": spec["id"],
                        "family": current,
                        "component": key,
                        "candidate": chosen,
                        "development_mean_season_brier": float(
                            (rows.p - rows.y).pow(2).groupby(rows.Season).mean().mean()
                        ),
                    }
                )
            weights = (
                modeling.simplex_weights(
                    np.column_stack([f.p.to_numpy() for f in frames]),
                    frames[0].y.to_numpy(),
                    frames[0].Season.to_numpy(),
                    model_config["ensemble_l2"],
                )
                if family == "blend"
                else np.ones(1)
            )
            streams.append(
                {
                    **spec,
                    "Gender": gender,
                    "components": [
                        {"id": key, "weight": float(weight)}
                        for key, weight in zip(selected, weights, strict=True)
                    ],
                }
            )
    pairs = [
        {"id": m["id"] + "__" + w["id"], "M": m["id"], "W": w["id"]}
        for m in config["streams"]["M"]
        for w in config["streams"]["W"]
    ]
    return {
        "protocol": "retrospective-frozen-portfolio",
        "prediction_season": 2026,
        "selection_seasons": years,
        "selection_metric": "mean season Brier",
        "first_training_season": 2013,
        "last_training_season": 2025,
        "calibration": "identity",
        "seed_free_seed_component": "neutral probability 0.5",
        "seed_free_blend": "Keep frozen weights; seed-only component contributes 0.5",
        "components": components,
        "streams": streams,
        "pairs": pairs,
        "selections": selections,
        "selection_scope": "Explored pre-2022 development outcomes; no fresh holdout claim",
    }


def validate_recipe(recipe: dict[str, Any]) -> None:
    if (
        recipe["protocol"] != "retrospective-frozen-portfolio"
        or recipe["prediction_season"] != 2026
        or recipe["selection_seasons"] != [2016, 2017, 2018, 2019, 2021]
        or recipe["first_training_season"] != 2013
        or recipe["last_training_season"] != 2025
        or recipe["calibration"] != "identity"
        or recipe["seed_free_seed_component"] != "neutral probability 0.5"
    ):
        raise ValueError("Changed frozen production contract")
    for key, component in recipe["components"].items():
        if key != "c_" + fingerprint(component)[:20]:
            raise ValueError("Component specification changed")
        if component["candidate"] not in [
            asdict(c) for c in modeling.candidates(component["population"])
        ]:
            raise ValueError("Unrecorded model candidate")
        for route in ROUTES:
            columns = feature_columns(component, route)
            if component["feature_routes"][route] != {
                "count": len(columns),
                "sha256": fingerprint(columns),
            }:
                raise ValueError("Component feature schema changed")
    streams = {s["id"]: s for s in recipe["streams"]}
    if len(streams) != 15 or len(recipe["pairs"]) != 50:
        raise ValueError("Expected fifteen procedures and fifty pairings")
    expected = {
        (m, w)
        for m, s in streams.items()
        if s["Gender"] == "M"
        for w, t in streams.items()
        if t["Gender"] == "W"
    }
    if {(p["M"], p["W"]) for p in recipe["pairs"]} != expected or len(expected) != 50:
        raise ValueError("Incomplete or duplicate portfolio pairing")
    if any(p["id"] != p["M"] + "__" + p["W"] for p in recipe["pairs"]):
        raise ValueError("Unsafe or inconsistent candidate identity")
    for stream in streams.values():
        weights = [p["weight"] for p in stream["components"]]
        if (
            not np.isfinite(weights).all()
            or min(weights) < 0
            or not np.isclose(sum(weights), 1, atol=1e-12, rtol=0)
        ):
            raise ValueError("Invalid frozen convex weights")
        for part in stream["components"]:
            component = recipe["components"][part["id"]]
            if component["population"] not in {stream["Gender"], "pooled_common"}:
                raise ValueError("Component training population does not match its stream")


def fit_component(
    frame: pd.DataFrame, component: dict[str, Any], route: str, config: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    train = frame.loc[frame.Season.between(2013, 2025) & frame.Season.ne(2020)].copy()
    population = component["population"]
    genders = ["M", "W"] if population == "pooled_common" else [population]
    train = train.loc[train.Gender.isin(genders)]
    inference.validate_games(train, 2025)
    years = list(range(2013, 2020)) + list(range(2021, 2026))
    if any(sorted(train.loc[train.Gender == g, "Season"].unique()) != years for g in genders):
        raise ValueError("Incomplete final training population")
    columns = feature_columns(component, route)
    candidate = modeling.Candidate(**component["candidate"])
    audit = {
        "population": population,
        "training_genders": genders,
        "route": route,
        "candidate": component["candidate"],
        "training_seasons": years,
        "training_games": len(train),
        "training_max_season": 2025,
        "eligible_features": len(columns),
        "fitted": bool(columns),
    }
    if not columns:
        if candidate.family != "seed" or route != "seed_free":
            raise ValueError("Only the seed-free seed baseline may use a neutral forecast")
        return {"model": None, "features": []}, {**audit, "retained_features": [], "constant": 0.5}
    if route == "seed_free":
        # Reuse the exact evaluated fitter. Seed inputs have zero training support
        # and are rejected by its training-only screen, before estimator fitting.
        for name in modeling.columns_for(candidate):
            if "seed" in name.lower():
                train[name] = np.nan
    # fit_candidate also returns predictions. A zero-valued, unlabeled probe only
    # satisfies that API; it does not influence fitting, screening or selection.
    probe = pd.DataFrame({name: [0.0] for name in modeling.columns_for(candidate)})
    probe["Season"] = 2026
    with threadpool_limits(limits=config["threads"]):
        fitted, _ = modeling.fit_candidate(
            train, probe, candidate, config["seed"], config["threads"]
        )
    kept = [modeling.columns_for(candidate)[i] for i in fitted.screen.indices_]
    if not set(kept).issubset(columns):
        raise ValueError("An excluded seed input survived the training screen")
    return {"model": fitted.model, "features": kept}, {**audit, "retained_features": kept}


def predict_chunk(
    rows: pd.DataFrame, recipe: dict[str, Any], fitted: dict[tuple[str, str], dict], threads: int
) -> pd.DataFrame:
    result = rows[["ID", "Gender"]].copy()
    result["feature_route"] = np.where(rows.diff_seed.notna(), "seeded", "seed_free")
    cache = {}
    for key in recipe["components"]:
        genders = {
            s["Gender"] for s in recipe["streams"] if any(p["id"] == key for p in s["components"])
        }
        values = np.full(len(rows), np.nan)
        for route in ROUTES:
            selected = rows.Gender.isin(genders) & result.feature_route.eq(route)
            if not selected.any():
                continue
            saved = fitted[key, route]
            values[selected] = (
                0.5
                if saved["model"] is None
                else forecast(saved["model"], rows.loc[selected], saved["features"], threads)
            )
        cache[key] = values
    for stream in recipe["streams"]:
        selected = rows.Gender.eq(stream["Gender"])
        p = sum(part["weight"] * cache[part["id"]][selected] for part in stream["components"])
        if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
            raise ValueError("Invalid final stream probability")
        result[stream["id"]] = np.nan
        result.loc[selected, stream["id"]] = p
    return result


def forecast(model: Any, frame: pd.DataFrame, columns: list[str], threads: int) -> np.ndarray:
    if not isinstance(model, modeling.XGBClassifier):
        return inference.forecast(model, frame, columns, threads)
    values = frame[columns].to_numpy(dtype=float)
    if np.isinf(values).any():
        raise ValueError("Infinite inference features")
    with threadpool_limits(limits=threads):
        forward = np.asarray(model.predict_proba(values)[:, 1], dtype=float)
        reverse = np.asarray(model.predict_proba(-values)[:, 1], dtype=float)
    if (
        not np.isfinite([forward, reverse]).all()
        or ((forward < 0) | (forward > 1) | (reverse < 0) | (reverse > 1)).any()
    ):
        raise ValueError("Invalid component probabilities")
    # XGBoost returns float32. Promote before arithmetic so swapped forecasts
    # sum to one at float64 precision, without changing any saved OOF evidence.
    p, q = (forward + 1 - reverse) / 2, (reverse + 1 - forward) / 2
    if not np.allclose(p + q, 1, atol=1e-12, rtol=0):
        raise ValueError("Team-swap probability symmetry failed")
    return p


def execute(
    frame: pd.DataFrame,
    teams: pd.DataFrame,
    sample: pd.DataFrame,
    recipe: dict[str, Any],
    store: TaskStore,
    config: dict[str, Any],
) -> dict[str, Any]:
    validate_recipe(recipe)
    inference.validate_config(config)
    validate_submission(sample, sample)
    teams = teams.loc[teams.Season == 2026].copy()
    pairs = sample_pairs(sample, teams)
    if not pairs.Season.eq(2026).all() or set(pairs.Gender) != {"M", "W"}:
        raise ValueError("The complete 2026 template must include both tournaments")
    fitted, audits, chunks = {}, [], []
    for key, component in recipe["components"].items():
        for route in ROUTES:

            def fit(target: Path, component: dict = component, route: str = route) -> list[Path]:
                model, audit = fit_component(frame, component, route, config)
                joblib.dump(model, target / "model.joblib")
                atomic_json(target / "audit.json", audit)
                return [target / "model.joblib", target / "audit.json"]

            saved = store.task(f"fit_{key}_{route}", fit)
            fitted[key, route] = joblib.load(saved / "model.joblib")
            audits.append({"component": key, **json.loads((saved / "audit.json").read_text())})
    # Build one full-schema feature chunk, predict all relevant components, then
    # discard features. Only compact probabilities are checkpointed.
    chunk_size = min(config["chunk_size"], 512)
    for start in range(0, len(sample), chunk_size):
        chunk = pairs.iloc[start : start + chunk_size]
        expected = sample.ID.iloc[start : start + chunk_size].tolist()

        def predict(
            target: Path, chunk: pd.DataFrame = chunk, expected: list = expected
        ) -> list[Path]:
            rows = pair_features(teams, chunk)
            if rows.ID.tolist() != expected:
                raise ValueError("Feature construction changed template order")
            predictions = predict_chunk(rows, recipe, fitted, config["threads"])
            predictions.to_parquet(target / "predictions.parquet", index=False)
            return [target / "predictions.parquet"]

        target = store.task(f"predict_{start:06d}", predict)
        chunks.append(target / "predictions.parquet")
        store.log.emit(
            "prediction_progress", completed=min(start + chunk_size, len(sample)), total=len(sample)
        )
    forecasts = pd.concat([pd.read_parquet(p) for p in chunks], ignore_index=True)
    if forecasts.ID.tolist() != sample.ID.tolist():
        raise ValueError("Incomplete or misordered prediction chunks")
    records = []
    for pair in recipe["pairs"]:

        def export(target: Path, pair: dict = pair) -> list[Path]:
            p = np.where(forecasts.Gender.eq("M"), forecasts[pair["M"]], forecasts[pair["W"]])
            output = pd.DataFrame({"ID": sample.ID, "Pred": p})
            validate_submission(output, sample)
            path = target / "submission.csv"
            output.to_csv(path, index=False, float_format="%.17g")
            validate_submission(pd.read_csv(path), sample)
            return [path]

        target = store.task("csv_" + pair["id"], export)
        path = target / "submission.csv"
        records.append(
            {
                "candidate_id": pair["id"],
                "path": str(path.relative_to(store.root)),
                "rows": len(sample),
                "bytes": path.stat().st_size,
                "sha256": digest(path),
            }
        )
    if len({r["sha256"] for r in records}) != 50:
        raise ValueError("Final prediction vectors are duplicated; do not count renamed copies")

    def publish(target: Path) -> list[Path]:
        pd.DataFrame(records).to_csv(target / "submission_manifest.csv", index=False)
        forecasts.groupby(["Gender", "feature_route"]).size().reset_index(name="rows").to_csv(
            target / "routes.csv", index=False
        )
        atomic_json(target / "recipe.json", recipe)
        atomic_json(target / "fit_audits.json", audits)
        summary = {
            "status": "completed",
            "fingerprint": store.run_fingerprint,
            "submission_files": 50,
            "distinct_submission_vectors": 50,
            "rows_per_file": len(sample),
            "fitted_models": sum(a["fitted"] for a in audits),
            "component_routes": len(audits),
            "neutral_routes": sum(not a["fitted"] for a in audits),
            "prediction_chunks": len(chunks),
            "training_max_season": 2025,
            "future_labels_used": False,
            "kaggle_submission_sent": False,
            "scope": "Retrospective sensitivity portfolio; final 2026 forecasts are unscored",
            "seed_free_scope": "Unseeded-team route lacks matched tournament OOF validation",
        }
        atomic_json(target / "summary.json", summary)
        return [
            target / name
            for name in [
                "submission_manifest.csv",
                "routes.csv",
                "recipe.json",
                "fit_audits.json",
                "summary.json",
            ]
        ]

    public = store.task("publication", publish)
    return json.loads((public / "summary.json").read_text())


def prepared(root: Path, inputs: Path) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    workflow.lineage(root)
    portfolio.check(root, portfolio.publication(root))
    receipts = production_inputs.verify(root, inputs)
    for name in production_inputs.MEMBERS:
        _, record = workflow.evidence(root, name)
        manifest = json.loads((inputs / name / "run/manifest.json").read_text())
        summary = json.loads((inputs / name / "run/summary.json").read_text())
        if (
            manifest != record["manifest"]
            or summary["fingerprint"] != record["summary"]["fingerprint"]
            or summary["status"] != "completed"
        ):
            raise ValueError("Production inputs are stale for the published research")
    _, models = workflow.evidence(root, "model_comparison")
    if (
        receipts["feature_store"]["sha256"]["run/features.parquet"]
        != models["manifest"]["inputs"]["data"]["features.parquet"]
    ):
        raise ValueError("Final fitting and model selection use different matrices")
    history = pd.read_parquet(inputs / "model_comparison/run/candidate_predictions.parquet")
    recipe = freeze(
        history,
        json.loads((root / portfolio.CONFIG).read_text()),
        json.loads((root / "configs/model_comparison.json").read_text()),
    )
    return history, recipe, receipts


def run(root: Path, inputs: Path, destination: Path) -> Path:
    _, recipe, receipts = prepared(root, inputs)
    if recipe != json.loads((root / REPORT / "recipe.json").read_text()):
        raise ValueError("Freeze and review the concrete recipe before final fitting")
    if receipts != json.loads((root / REPORT / "input_receipts.json").read_text()):
        raise ValueError("Production inputs differ from the frozen member receipts")
    config = json.loads((root / "configs/inference.json").read_text())
    sources = sorted((root / "src").rglob("*.py")) + [
        root / p
        for p in [
            "configs/prediction_portfolio.json",
            "configs/inference.json",
            "configs/model_comparison.json",
            "pyproject.toml",
            "uv.lock",
        ]
    ]
    identity = {
        "recipe": recipe,
        "inputs": receipts,
        "config": config,
        "source": {str(p.relative_to(root)): digest(p) for p in sources},
        "environment": {k: v for k, v in runtime_identity().items() if k != "platform"},
    }
    identity["environment"].update({p: version(p) for p in ["xgboost-cpu", "lightgbm"]})
    key = fingerprint(identity)
    output = destination / key
    archive_record = root / REPORT / "archive.json"
    if not output.exists() and archive_record.is_file():
        record = json.loads(archive_record.read_text())
        if record["fingerprint"] == key:
            from march_mania.publication.production_release import recover

            recover(root, destination)
    output.mkdir(parents=True, exist_ok=True)
    with FileLock(str(output / ".lock"), timeout=0):
        log = EventLog(output / "events.jsonl")
        log.emit("run_started", fingerprint=key)
        atomic_json(output / "manifest.json", {"fingerprint": key, "inputs": identity})
        try:
            summary = execute(
                pd.read_parquet(inputs / "feature_store/run/features.parquet"),
                pd.read_parquet(inputs / "feature_store/run/teams.parquet"),
                pd.read_csv(inputs / "feature_store/raw/SampleSubmissionStage2.csv"),
                recipe,
                TaskStore(output, key, log, config["heartbeat_seconds"]),
                config,
            )
            if production_inputs.verify(root, inputs) != receipts or any(
                digest(root / p) != h for p, h in identity["source"].items()
            ):
                raise ValueError("Production input or source changed during execution")
            with zipfile.ZipFile(output / "source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
                for path in sources:
                    archive.write(path, str(path.relative_to(root)))
            atomic_json(output / "summary.json", summary)
            atomic_json(destination / "latest.json", {"fingerprint": key, "directory": key})
            for path in (output / "publication").iterdir():
                if (
                    path.name != "checkpoint.json"
                    and path.is_file()
                    and path.suffix in {".csv", ".json"}
                ):
                    verified_write(root / REPORT / path.name, path.read_bytes(), digest(path))
            atomic_json(
                root / REPORT / "run.json",
                {
                    "fingerprint": key,
                    "inputs": identity,
                    "sha256": {
                        p.name: digest(p)
                        for p in (output / "publication").iterdir()
                        if p.name != "checkpoint.json"
                        and p.is_file()
                        and p.suffix in {".csv", ".json"}
                    },
                },
            )
            log.emit("run_completed", **summary)
            return output
        except BaseException as error:
            log.emit("run_failed", error_type=type(error).__name__, error=str(error))
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--restore-inputs", action="store_true")
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--generate", action="store_true")
    parser.add_argument("--inputs", type=Path, default=Path("outputs/production_inputs"))
    parser.add_argument("--output", type=Path, default=Path("outputs/prediction_production"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if args.restore_inputs:
        production_inputs.restore(root, args.inputs)
    elif args.freeze:
        _, recipe, receipts = prepared(root, args.inputs)
        atomic_json(root / REPORT / "recipe.json", recipe)
        atomic_json(root / REPORT / "input_receipts.json", receipts)
        print(
            json.dumps(
                {
                    "status": "frozen",
                    "components": len(recipe["components"]),
                    "candidate_files": len(recipe["pairs"]),
                    "recipe_sha256": fingerprint(recipe),
                }
            )
        )
    else:
        print(run(root, args.inputs, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
