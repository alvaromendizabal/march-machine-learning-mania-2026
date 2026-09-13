"""A bounded XGBoost experiment with coverage guards and reusable temporal controls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from xgboost import XGBClassifier

from march_mania import modeling
from march_mania.advanced_features import candidate_blocks
from march_mania.feature_selection import ScreenedPredictor, TrainingScreen
from march_mania.publication import portfolio, workflow
from march_mania.runtime import EventLog, TaskStore, atomic_json, digest, fingerprint

CONFIG = "configs/xgboost_retraining.json"
REPORT = "reports/xgboost_retraining"
YEARS = [2014, 2015, 2016, 2017, 2018, 2019, 2021]


def validate_config(config: dict[str, Any]) -> None:
    variants = config["variants"]
    if (
        config["protocol"] != "retrospective-bounded-xgboost-retraining"
        or config["first_training_season"] != 2013
        or config["validation_seasons"] != [2016, 2017, 2018, 2019, 2021]
        or config["max_new_fits"] != 28
        or len(variants) != 7
        or len({v["name"] for v in variants}) != len(variants)
        or sum(v["reuse"] is None for v in variants) * len(YEARS) != 28
    ):
        raise ValueError("Preserve the bounded pre-2022 research protocol")
    for variant in variants:
        if variant["population"] not in {"M", "pooled_common"}:
            raise ValueError("Unknown training population")
        if variant["massey"] and variant["population"] != "M":
            raise ValueError("Massey experiments require men's data")
        if variant["capacity"] not in {64, 128} or variant["trees"] not in {120, 240}:
            raise ValueError("Unexpected model capacity")


def coverage_guard(frame: pd.DataFrame, coverage: pd.DataFrame, *, massey: bool) -> None:
    """Require actual legal team coverage in every included men's season."""
    if frame.empty or not frame.Season.between(2013, 2021).all() or frame.Season.eq(2020).any():
        raise ValueError("Only the declared development population may enter retraining")
    if not massey:
        return
    if not frame.Gender.eq("M").all():
        raise ValueError("Massey input must be men-only")
    actual = coverage.loc[coverage.Gender.eq("M") & coverage.Season.isin(frame.Season.unique())]
    if (
        actual.Season.duplicated().any()
        or set(actual.Season) != set(frame.Season)
        or not actual.ranking_teams.eq(actual.regular_teams).all()
        or not actual.latest_ranking_day.le(actual.cutoff_day).all()
        or not actual.ranking_systems.gt(0).all()
        or frame[["diff_rank_consensus", "diff_rank_mean"]].isna().any().any()
    ):
        raise ValueError("Missing or post-cutoff Massey coverage in an included season")


def columns_for(variant: dict[str, Any]) -> list[str]:
    columns = candidate_blocks(include_rankings=variant["massey"])["full"]
    return [name for name in columns if variant["coach"] or "coach" not in name]


def fit_variant(
    train: pd.DataFrame, valid: pd.DataFrame, variant: dict[str, Any], config: dict[str, Any]
) -> tuple[ScreenedPredictor, np.ndarray, list[str]]:
    if train.empty or valid.empty or train.Season.max() >= valid.Season.min():
        raise ValueError("Temporal overlap or empty training fold")
    columns = columns_for(variant)
    x, y = train[columns].to_numpy(float), train.y.to_numpy(int)
    x, y = np.concatenate([x, -x]), np.concatenate([y, 1 - y])
    with threadpool_limits(limits=config["threads"]):
        screen = TrainingScreen(max_features=variant["capacity"]).fit(x, y)
        model = XGBClassifier(
            n_estimators=variant["trees"],
            learning_rate=0.04,
            max_depth=2,
            min_child_weight=variant["child_weight"],
            reg_lambda=variant["reg_lambda"],
            tree_method="hist",
            device="cpu",
            n_jobs=config["threads"],
            random_state=config["seed"],
            eval_metric="logloss",
        )
        model.fit(screen.transform(x), y)
        saved = ScreenedPredictor(screen, model)
        p = modeling.predict_candidate(saved, valid[columns].to_numpy(float), config["threads"])
        reverse = modeling.predict_candidate(
            saved, -valid[columns].to_numpy(float), config["threads"]
        )
    if not np.allclose(p + reverse, 1, atol=1e-12, rtol=0):
        raise ValueError("Team-swap complementarity failed")
    return saved, p, columns


def evaluate(
    predictions: pd.DataFrame, config: dict[str, Any]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Report fixed recipes and select the next season using only previous OOF games."""
    if (
        predictions.empty
        or not set(predictions.Season).issubset(YEARS)
        or predictions.duplicated(["variant", "Gender", "Season", "ID"]).any()
        or not predictions.Gender.eq("M").all()
        or not predictions.y.isin([0, 1]).all()
        or not np.isfinite(predictions.p).all()
        or not predictions.p.between(0, 1).all()
    ):
        raise ValueError("Invalid or out-of-protocol historical predictions")
    development = predictions.loc[predictions.Season.isin(config["validation_seasons"])]
    anchor = development.loc[development.variant.eq(config["reference"])].sort_values(
        ["Season", "ID"]
    )
    catalog = []
    for name, rows in development.groupby("variant"):
        rows = rows.sort_values(["Season", "ID"])
        if (
            not rows[modeling.KEYS]
            .reset_index(drop=True)
            .equals(anchor[modeling.KEYS].reset_index(drop=True))
        ):
            raise ValueError("Model comparisons must use identical games and labels")
        annual_delta = (rows.p.to_numpy(dtype=float) - rows.y.to_numpy(dtype=float)) ** 2 - (
            anchor.p.to_numpy(dtype=float) - anchor.y.to_numpy(dtype=float)
        ) ** 2
        seasonal = pd.Series(annual_delta).groupby(rows.Season.to_numpy()).mean()
        catalog.append(
            {
                "variant": name,
                **portfolio.metrics(rows),
                "brier_delta": float(annual_delta.mean()),
                "improved_seasons": int(seasonal.lt(0).sum()),
                "worst_season_delta": float(seasonal.max()),
            }
        )
    selections = []
    for season in config["validation_seasons"]:
        history = predictions.loc[predictions.Season.lt(season)].copy()
        losses = history.assign(loss=(history.p - history.y) ** 2)
        scores = losses.groupby(["variant", "Season"]).loss.mean().groupby("variant").mean()
        selected = scores.sort_index().sort_values(kind="stable").index[0]
        selections.append(
            {
                "Season": season,
                "variant": selected,
                "history_last_season": int(history.Season.max()),
                "history_seasons": int(history.Season.nunique()),
            }
        )
    return pd.DataFrame(catalog).sort_values("brier"), pd.DataFrame(selections)


def run(root: Path, input_root: Path) -> dict[str, Any]:
    config = json.loads((root / CONFIG).read_text())
    validate_config(config)
    workflow.lineage(root)
    paths = {
        "features": input_root / "feature_store/run/features.parquet",
        "controls": input_root / "model_comparison/run/candidate_predictions.parquet",
    }
    receipts = json.loads((root / "reports/prediction_production/input_receipts.json").read_text())
    for name, stage, member in [
        ("features", "feature_store", "run/features.parquet"),
        ("controls", "model_comparison", "run/candidate_predictions.parquet"),
    ]:
        if digest(paths[name]) != receipts[stage]["sha256"][member]:
            raise ValueError("Input differs from the verified current research archive")
    inputs = {
        "config": config,
        "data": {k: digest(p) for k, p in paths.items()},
        "source": digest(Path(__file__)),
        "feature_fingerprint": json.loads((root / "reports/feature_store/run.json").read_text())[
            "summary"
        ]["fingerprint"],
    }
    key = fingerprint(inputs)
    output = root / "outputs/xgboost_retraining" / key
    log = EventLog(output / "events.jsonl")
    store = TaskStore(output, key, log, config["heartbeat_seconds"])
    atomic_json(output / "manifest.json", {"fingerprint": key, "inputs": inputs})
    frame = pd.read_parquet(
        paths["features"], filters=[("Season", ">=", 2013), ("Season", "<=", 2021)]
    )
    modeling.validate_matrix(frame)
    controls = pd.read_parquet(paths["controls"])
    coverage = pd.read_csv(root / "reports/feature_store/source_coverage.csv")
    forecasts, audits = [], []
    completed = 0
    log.emit("study_started", new_fit_limit=28, reusable_controls=21)
    for variant in config["variants"]:
        population = (
            frame if variant["population"] == "pooled_common" else frame.loc[frame.Gender.eq("M")]
        )
        coverage_guard(population, coverage, massey=variant["massey"])
        for season in YEARS:
            train = population.loc[population.Season.lt(season)]
            valid = frame.loc[frame.Season.eq(season) & frame.Gender.eq("M")]
            if variant["reuse"]:
                rows = controls.loc[
                    controls.route.eq(variant["population"])
                    & controls.candidate.eq(variant["reuse"])
                    & controls.Season.eq(season)
                    & controls.Gender.eq("M")
                ].sort_values("ID")
                if (
                    not rows[modeling.KEYS]
                    .reset_index(drop=True)
                    .equals(valid[modeling.KEYS].sort_values("ID").reset_index(drop=True))
                ):
                    raise ValueError("Saved control covers different games")
                rows = rows[modeling.KEYS + ["p"]].copy()
                log.emit("control_reused", variant=variant["name"], season=season)
            else:

                def fit(
                    target: Path,
                    train: pd.DataFrame = train,
                    valid: pd.DataFrame = valid,
                    variant: dict[str, Any] = variant,
                    season: int = season,
                ) -> list[Path]:
                    model, p, columns = fit_variant(train, valid, variant, config)
                    result = valid[modeling.KEYS].assign(p=p)
                    result.to_csv(target / "predictions.csv", index=False)
                    joblib.dump({"model": model, "features": columns}, target / "model.joblib")
                    selected = [columns[i] for i in model.screen.indices_]
                    model.screen.audit_.assign(feature=columns).to_csv(
                        target / "screening.csv", index=False
                    )
                    atomic_json(
                        target / "fold.json",
                        {
                            "variant": variant["name"],
                            "validation_season": season,
                            "training_seasons": sorted(int(s) for s in train.Season.unique()),
                            "training_games": len(train),
                            "validation_games": len(valid),
                            "candidate_features": len(columns),
                            "retained_features": selected,
                            "massey_features_retained": sum(
                                "rank" in c or "massey" in c for c in selected
                            ),
                            "coach_features_retained": sum("coach" in c for c in selected),
                        },
                    )
                    return [
                        target / n
                        for n in ["predictions.csv", "model.joblib", "screening.csv", "fold.json"]
                    ]

                target = store.task(f"fit_{variant['name']}_{season}", fit)
                rows = pd.read_csv(target / "predictions.csv")
                audits.append(json.loads((target / "fold.json").read_text()))
            forecasts.append(rows.assign(variant=variant["name"]))
            completed += 1
            log.emit("study_progress", completed=completed, total=49)
    predictions = pd.concat(forecasts, ignore_index=True)
    catalog, choices = evaluate(predictions, config)
    selected = predictions.merge(
        choices[["Season", "variant"]], on=["Season", "variant"], validate="many_to_one"
    )
    selected_metrics = portfolio.metrics(selected)
    summary = {
        "status": "completed",
        "fingerprint": key,
        "inputs": inputs,
        "new_fit_tasks": 28,
        "reused_control_fits": 21,
        "recipes": 7,
        "validation_seasons": config["validation_seasons"],
        "best_fixed_variant": str(catalog.iloc[0].variant),
        "forward_selection_metrics": selected_metrics,
        "scope": config["scope"],
        "new_submission_files": 0,
    }
    annual = predictions.loc[predictions.Season.isin(config["validation_seasons"])].groupby(
        ["variant", "Season"]
    )
    tables = {
        "predictions.csv": predictions,
        "leaderboard.csv": catalog,
        "selection.csv": choices,
        "metrics_by_season.csv": pd.DataFrame(
            [
                {"variant": name, "Season": season, **portfolio.metrics(rows)}
                for (name, season), rows in annual
            ]
        ),
    }
    folder = root / REPORT
    folder.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(folder / name, index=False)
        table.to_csv(output / name, index=False)
    atomic_json(folder / "fit_audits.json", audits)
    summary["sha256"] = {name: digest(folder / name) for name in [*tables, "fit_audits.json"]}
    atomic_json(folder / "summary.json", summary)
    atomic_json(output / "summary.json", summary)
    log.emit("study_completed", new_fit_tasks=28, reused_control_fits=21)
    return summary


def review(root: Path) -> dict[str, Any]:
    workflow.lineage(root)
    config = json.loads((root / CONFIG).read_text())
    validate_config(config)
    summary = json.loads((root / REPORT / "summary.json").read_text())
    if summary["inputs"]["config"] != config or summary["inputs"]["source"] != digest(
        Path(__file__)
    ):
        raise ValueError("Retraining evidence has stale source or configuration")
    feature_key = json.loads((root / "reports/feature_store/run.json").read_text())["summary"][
        "fingerprint"
    ]
    receipts = json.loads((root / "reports/prediction_production/input_receipts.json").read_text())
    expected_data = {
        "features": receipts["feature_store"]["sha256"]["run/features.parquet"],
        "controls": receipts["model_comparison"]["sha256"]["run/candidate_predictions.parquet"],
    }
    if (
        summary["inputs"]["feature_fingerprint"] != feature_key
        or summary["inputs"]["data"] != expected_data
        or summary["fingerprint"] != fingerprint(summary["inputs"])
    ):
        raise ValueError("Retraining input lineage mismatch")
    for name, expected in summary["sha256"].items():
        if digest(root / REPORT / name) != expected:
            raise ValueError("Retraining evidence checksum mismatch")
    predictions = pd.read_csv(root / REPORT / "predictions.csv")
    catalog, choices = evaluate(predictions, config)
    pd.testing.assert_frame_equal(
        catalog.reset_index(drop=True),
        pd.read_csv(root / REPORT / "leaderboard.csv"),
        check_exact=False,
        atol=1e-12,
        rtol=0,
    )
    pd.testing.assert_frame_equal(choices, pd.read_csv(root / REPORT / "selection.csv"))
    selected = predictions.merge(
        choices[["Season", "variant"]], on=["Season", "variant"], validate="many_to_one"
    )
    pd.testing.assert_frame_equal(
        pd.DataFrame([portfolio.metrics(selected)]),
        pd.DataFrame([summary["forward_selection_metrics"]]),
        check_like=True,
        check_exact=False,
        atol=1e-12,
        rtol=0,
    )
    annual = predictions.loc[predictions.Season.isin(config["validation_seasons"])].groupby(
        ["variant", "Season"]
    )
    pd.testing.assert_frame_equal(
        pd.DataFrame(
            [
                {"variant": name, "Season": season, **portfolio.metrics(rows)}
                for (name, season), rows in annual
            ]
        ),
        pd.read_csv(root / REPORT / "metrics_by_season.csv"),
        check_exact=False,
        atol=1e-12,
        rtol=0,
    )
    if not choices.history_last_season.lt(choices.Season).all():
        raise ValueError("Forward selection leaked a future season")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--run", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--inputs", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if args.run:
        run(root, args.inputs or root / "outputs/retraining_inputs")
    else:
        review(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
