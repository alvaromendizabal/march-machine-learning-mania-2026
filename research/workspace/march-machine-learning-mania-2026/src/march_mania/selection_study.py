"""Bounded, restartable feature-only comparisons on consumed development seasons."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from filelock import FileLock
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from march_mania.advanced_features import efficiency_ratings, possession_games
from march_mania.features import feature_blocks, snapshot
from march_mania.runtime import (
    EventLog,
    Mirror,
    TaskStore,
    atomic_json,
    digest,
    fingerprint,
    runtime_identity,
)
from march_mania.selection_features import (
    RESUME_COLUMNS,
    RESUME_FAMILIES,
    resume_pairs,
    selection_snapshot,
)

YEARS = [2013, 2014, 2015, 2016, 2017, 2018, 2019, 2021]
VALID = [2016, 2017, 2018, 2019, 2021]
BASE = feature_blocks()["strength"]
CONTROLS = {
    "strength": BASE,
    "adjusted": BASE
    + ["diff_adj_offense", "diff_adj_defense", "diff_recent_offense", "diff_recent_defense"],
}
ARMS = {
    "baseline": [],
    **RESUME_FAMILIES,
    "all": RESUME_COLUMNS,
    **{
        "without_" + family: [x for x in RESUME_COLUMNS if x not in names]
        for family, names in RESUME_FAMILIES.items()
    },
}
CONFIG = {
    "first_season": 2013,
    "validation_seasons": VALID,
    "cutoff": 132,
    "seed_availability_day": 132,
    "C": 0.1,
    "ridge_alpha": 20.0,
    "recent_half_life": 30.0,
    "threads": 2,
    "controls": CONTROLS,
    "arms": ARMS,
    "protocol": "retrospective-development-feature-ablation",
    "max_folds": 10,
}


def fit_comparison(
    train: pd.DataFrame, valid: pd.DataFrame, columns: list[str]
) -> tuple[Any, np.ndarray, list[str]]:
    """Screen constant/missing inputs using training rows only, then fit fixed LR."""
    if train.empty or valid.empty or train.Season.max() >= valid.Season.min():
        raise ValueError("Empty or temporally overlapping fold")
    if not columns or not set(columns).issubset(
        CONTROLS["adjusted"] + ["diff_" + x for x in RESUME_COLUMNS]
    ):
        raise ValueError("Only registered signed feature columns may enter the model")
    x: np.ndarray = train[columns].to_numpy(dtype=float)
    keep = (np.isfinite(x).mean(axis=0) >= 0.95) & (np.nanstd(x, axis=0) > 1e-12)
    retained = [c for c, use in zip(columns, keep, strict=True) if use]
    if not retained:
        raise ValueError("No usable training features")
    x = x[:, keep]
    y = train.y.to_numpy(dtype=int)
    if not set(y) == {0, 1}:
        raise ValueError("Training requires both binary classes")
    model = make_pipeline(
        SimpleImputer(strategy="median"),
        StandardScaler(),
        LogisticRegression(C=0.1, max_iter=2000, fit_intercept=False, random_state=2026),
    )
    with threadpool_limits(limits=2):
        model.fit(np.concatenate([x, -x]), np.r_[y, 1 - y])
    v = valid[retained].to_numpy(dtype=float)
    probability = (model.predict_proba(v)[:, 1] + 1 - model.predict_proba(-v)[:, 1]) / 2
    if not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any():
        raise ValueError("Invalid prediction")
    return model, probability, retained


def build_matrix(raw: Path, store: TaskStore) -> pd.DataFrame:
    frames = []
    for gender in ("M", "W"):
        compact = pd.read_csv(raw / f"{gender}RegularSeasonCompactResults.csv")
        detail = pd.read_csv(raw / f"{gender}RegularSeasonDetailedResults.csv")
        seeds = pd.read_csv(raw / f"{gender}NCAATourneySeeds.csv")
        seeds["seed"] = seeds.Seed.str.extract(r"(\d+)", expand=False).astype(int)
        tournament = pd.read_csv(raw / f"{gender}NCAATourneyCompactResults.csv")
        for season in YEARS:

            def build(
                target: Path,
                season: int = season,
                gender: str = gender,
                compact: pd.DataFrame = compact,
                detail: pd.DataFrame = detail,
                seeds: pd.DataFrame = seeds,
                tournament: pd.DataFrame = tournament,
            ) -> list[Path]:
                # Current source is rebuilt, rather than trusting an old workspace matrix.
                with threadpool_limits(limits=2):
                    teams = snapshot(compact, detail, seeds, gender, season, 132, 20.0, 30.0)
                    legal_detail = detail.loc[(detail.Season == season) & (detail.DayNum <= 132)]
                    adjusted = efficiency_ratings(possession_games(legal_detail), 20.0, 132)
                teams = teams.merge(adjusted, on="TeamID", validate="one_to_one")
                resume = selection_snapshot(compact, seeds, season)
                g = tournament.loc[tournament.Season == season]
                if g.empty or (g.DayNum <= 132).any():
                    raise ValueError("Invalid tournament labels")
                pairs = pd.DataFrame(
                    {
                        "Gender": gender,
                        "Season": season,
                        "DayNum": g.DayNum,
                        "Team1ID": np.minimum(g.WTeamID, g.LTeamID),
                        "Team2ID": np.maximum(g.WTeamID, g.LTeamID),
                        "y": (g.WTeamID < g.LTeamID).astype(int),
                    }
                )
                pairs = resume_pairs(resume, pairs)
                source_cols = [x.removeprefix("diff_") for x in CONTROLS["adjusted"]]
                for side in (1, 2):
                    t = teams[["TeamID", *source_cols]].rename(
                        columns={
                            "TeamID": f"Team{side}ID",
                            **{c: f"s{side}_{c}" for c in source_cols},
                        }
                    )
                    pairs = pairs.merge(t, on=f"Team{side}ID", how="left", validate="many_to_one")
                for c in source_cols:
                    pairs["diff_" + c] = pairs[f"s1_{c}"] - pairs[f"s2_{c}"]
                pairs = pairs[
                    [
                        "Gender",
                        "Season",
                        "DayNum",
                        "Team1ID",
                        "Team2ID",
                        "y",
                        *CONTROLS["adjusted"],
                        *["diff_" + c for c in RESUME_COLUMNS],
                    ]
                ]
                if pairs.duplicated(["Season", "Team1ID", "Team2ID"]).any():
                    raise ValueError("Repeated tournament game")
                path = target / "matrix.parquet"
                pairs.to_parquet(path, index=False)
                audit = target / "audit.json"
                atomic_json(
                    audit,
                    {
                        "Gender": gender,
                        "Season": season,
                        "regular_max_day": int(
                            compact.loc[
                                (compact.Season == season) & (compact.DayNum <= 132), "DayNum"
                            ].max()
                        ),
                        "seeded_teams": int((seeds.Season == season).sum()),
                        "games": len(pairs),
                        "cutoff": 132,
                        "tournament_labels_used_in_features": False,
                    },
                )
                return [path, audit]

            target = store.task(f"snapshot_{gender.lower()}_{season}", build)
            frames.append(pd.read_parquet(target / "matrix.parquet"))
    return pd.concat(frames, ignore_index=True)


def run(raw: Path, root: Path, mirror_uri: str | None = None, max_folds: int = 10) -> dict:
    if not 1 <= max_folds <= 10:
        raise ValueError("A stage is bounded to 1--10 gender-season folds")
    paths = [
        raw / f"{g}{name}.csv"
        for g in ("M", "W")
        for name in (
            "RegularSeasonCompactResults",
            "RegularSeasonDetailedResults",
            "NCAATourneySeeds",
            "NCAATourneyCompactResults",
        )
    ]
    source = Path(__file__).parent
    inputs = {
        "config": CONFIG,
        "data": {p.name: digest(p) for p in paths},
        "source": {p.name: digest(p) for p in source.glob("*.py")},
        "environment": runtime_identity(),
    }
    identity = fingerprint(inputs)
    output = root / identity
    output.mkdir(parents=True, exist_ok=True)
    with FileLock(str(output / ".run.lock"), timeout=0):
        log = EventLog(output / "events.jsonl")
        mirror = Mirror(mirror_uri.rstrip("/") + "/" + identity) if mirror_uri else None
        store = TaskStore(output, identity, log, 15, mirror)
        atomic_json(output / "manifest.json", {"fingerprint": identity, "inputs": inputs})
        if mirror:
            mirror.upload(output / "manifest.json", "manifest.json")
        started = time.monotonic()
        matrix = build_matrix(raw, store)
        predictions = []
        metrics = []
        completed_folds = 0
        for gender in ("M", "W"):
            for year in VALID:
                if completed_folds >= max_folds:
                    break
                train = matrix.loc[(matrix.Gender == gender) & (matrix.Season < year)]
                valid = matrix.loc[(matrix.Gender == gender) & (matrix.Season == year)]
                for control, base in CONTROLS.items():
                    for arm, addition in ARMS.items():
                        columns = base + ["diff_" + x for x in addition]

                        def evaluate(
                            target: Path,
                            train: pd.DataFrame = train,
                            valid: pd.DataFrame = valid,
                            columns: list[str] = columns,
                            control: str = control,
                            arm: str = arm,
                        ) -> list[Path]:
                            model, prob, retained = fit_comparison(train, valid, columns)
                            frame = valid[
                                ["Gender", "Season", "DayNum", "Team1ID", "Team2ID", "y"]
                            ].copy()
                            frame["p"] = prob
                            frame["control"] = control
                            frame["arm"] = arm
                            frame.to_parquet(target / "predictions.parquet", index=False)
                            joblib.dump(
                                {"model": model, "columns": retained}, target / "model.joblib"
                            )
                            atomic_json(
                                target / "fold.json",
                                {
                                    "train_seasons": sorted(train.Season.unique().tolist()),
                                    "train_games": len(train),
                                    "valid_games": len(valid),
                                    "retained": retained,
                                    "rejected": [c for c in columns if c not in retained],
                                },
                            )
                            return [
                                target / "predictions.parquet",
                                target / "model.joblib",
                                target / "fold.json",
                            ]

                        target = store.task(
                            f"fold_{gender.lower()}_{year}_{control}_{arm}", evaluate
                        )
                        frame = pd.read_parquet(target / "predictions.parquet")
                        predictions.append(frame)
                        metrics.append(
                            {
                                "Gender": gender,
                                "Season": year,
                                "control": control,
                                "arm": arm,
                                "games": len(frame),
                                "brier": float(np.mean((frame.y - frame.p) ** 2)),
                                "log_loss": float(log_loss(frame.y, frame.p, labels=[0, 1])),
                                "auc": float(roc_auc_score(frame.y, frame.p)),
                            }
                        )
                completed_folds += 1
                log.emit("fold_progress", completed=completed_folds, total=max_folds)
        all_predictions = pd.concat(predictions, ignore_index=True)
        metric_frame = pd.DataFrame(metrics)
        metric_frame.to_csv(output / "metrics_by_season.csv", index=False)
        all_predictions.to_parquet(output / "predictions.parquet", index=False)
        rows = []
        for (gender, control, arm), frame in all_predictions.groupby(["Gender", "control", "arm"]):
            subset = metric_frame.loc[
                (metric_frame.Gender == gender)
                & (metric_frame.control == control)
                & (metric_frame.arm == arm)
            ]
            rows.append(
                {
                    "Gender": gender,
                    "control": control,
                    "arm": arm,
                    "games": len(frame),
                    "game_brier": float(np.mean((frame.y - frame.p) ** 2)),
                    "mean_season_brier": float(subset.brier.mean()),
                }
            )
        leaders = pd.DataFrame(rows)
        leaders.to_csv(output / "leaderboard.csv", index=False)
        result = {
            "status": "completed" if completed_folds == 10 else "partial-stage",
            "fingerprint": identity,
            "completed_gender_season_folds": completed_folds,
            "fold_tasks": len(metrics),
            "candidate_features": len(RESUME_COLUMNS),
            "elapsed_seconds": time.monotonic() - started,
            "leaderboard": rows,
            "output": str(output),
            "evaluation_seasons": VALID,
            "holdout_status": "previously explored development seasons; not untouched",
            "new_kaggle_submission": False,
        }
        atomic_json(output / "summary.json", result)
        if mirror:
            for name in [
                "metrics_by_season.csv",
                "predictions.parquet",
                "leaderboard.csv",
                "summary.json",
                "events.jsonl",
            ]:
                mirror.upload(output / name, name)
        atomic_json(root / "latest.json", result)
        print(json.dumps(result, indent=2))
        return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--s3")
    p.add_argument("--max-folds", type=int, default=10)
    args = p.parse_args()
    run(args.raw, args.output, args.s3, args.max_folds)


if __name__ == "__main__":
    main()
