"""Build notebook 02's feature store and run preregistered chronological ablations."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from filelock import FileLock
from threadpoolctl import threadpool_limits

from march_mania.advanced_features import (
    FAMILIES,
    INTERACTIONS,
    advanced_snapshot,
    candidate_blocks,
    elo_history,
    pair_features,
)
from march_mania.features import read_official
from march_mania.research import finalize_run, fit_fold
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
    years = config["validation_seasons"]
    if not years or years != sorted(set(years)) or any(y == 2020 or y >= 2022 for y in years):
        raise ValueError("Use unique sorted development seasons before 2022, excluding 2020")
    if not 2010 <= config["first_season"] < min(years) <= max(years) <= config["last_season"]:
        raise ValueError("Invalid feature-store season boundaries")
    if config["feature_cutoff_day"] != 132 or config["minimum_prior_seasons"] < 3:
        raise ValueError("Day 132 and at least three prior training seasons are required")
    if config["ridge_alpha"] <= 0 or config["threads"] < 1 or config["heartbeat_seconds"] <= 0:
        raise ValueError("Invalid computation settings")
    if config["protocol"] != "retrospective-feature-store":
        raise ValueError("The feature store is retrospective research")


def labeled_pairs(tables: dict[str, pd.DataFrame], gender: str, years: list[int]) -> pd.DataFrame:
    games = tables["NCAATourneyCompactResults"]
    games = games.loc[games.Season.isin(years) & (games.Season != 2020)].copy()
    if (games.DayNum <= 132).any():
        raise ValueError("Tournament labels overlap the feature cutoff")
    return pd.DataFrame(
        {
            "Gender": gender,
            "Season": games.Season,
            "DayNum": games.DayNum,
            "Team1ID": np.minimum(games.WTeamID, games.LTeamID),
            "Team2ID": np.maximum(games.WTeamID, games.LTeamID),
            "y": (games.WTeamID < games.LTeamID).astype(int),
        }
    )


def sample_pairs(sample: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    if list(sample.columns) != ["ID", "Pred"] or sample.ID.duplicated().any():
        raise ValueError("Sample submission must have unique ID,Pred columns")
    parsed = sample.ID.str.extract(r"^(\d{4})_(\d{4})_(\d{4})$")
    if parsed.isna().any().any():
        raise ValueError("Malformed submission ID")
    parsed = parsed.astype(int)
    parsed.columns = ["Season", "Team1ID", "Team2ID"]
    identity = teams[["Gender", "Season", "TeamID"]].drop_duplicates()
    for side in (1, 2):
        parsed = parsed.merge(
            identity.rename(columns={"TeamID": f"Team{side}ID", "Gender": f"gender{side}"}),
            on=["Season", f"Team{side}ID"],
            how="left",
            validate="many_to_one",
        )
    if (
        parsed[["gender1", "gender2"]].isna().any().any()
        or not parsed.gender1.eq(parsed.gender2).all()
    ):
        raise ValueError("Sample requests an unknown team, season, or mixed-gender game")
    parsed["Gender"] = parsed.gender1
    return parsed[["Gender", "Season", "Team1ID", "Team2ID"]]


def feature_registry() -> pd.DataFrame:
    rows = []
    reverse = {"diff_" + name: family for family, names in FAMILIES.items() for name in names}
    for name in candidate_blocks()["full"]:
        family = reverse.get(name, "interactions" if name in INTERACTIONS else "core")
        source = {
            "history": "prior-season NCAA results and seeds",
            "rankings": "Massey ordinals at or before DayNum 132",
            "dynamic": "regular-season compact history at or before DayNum 132",
        }.get(family, "current regular-season compact/detailed results and tournament seeds")
        rows.append(
            {
                "feature": name,
                "family": family,
                "source": source,
                "transformation": "team 1 minus team 2"
                if name.startswith("diff_")
                else "antisymmetric interaction; see advanced_features.py",
                "cutoff_day": 132,
                "swap_parity": -1,
                "missing_policy": "training-fold median; absent ranking family excluded",
                "evidence": "candidate; requires ablation",
            }
        )
    return pd.DataFrame(rows)


def run(
    raw: Path, output: Path, config: dict[str, Any], mirror_uri: str | None = None
) -> dict[str, Any]:
    validate_config(config)
    output.mkdir(parents=True, exist_ok=True)
    with FileLock(str(output / ".run.lock"), timeout=0):
        return _run(raw, output, config, mirror_uri)


def _run(raw: Path, output: Path, config: dict[str, Any], mirror_uri: str | None) -> dict[str, Any]:
    log = EventLog(output / "events.jsonl")
    log.emit("run_started", protocol=config["protocol"])
    data, paths = read_official(raw)
    optional = [
        p for p in [raw / "MMasseyOrdinals.csv", raw / "SampleSubmissionStage2.csv"] if p.exists()
    ]
    root = Path(__file__).resolve().parents[2]
    sources = [
        Path(__file__).parent / name
        for name in [
            "advanced_features.py",
            "feature_store.py",
            "features.py",
            "research.py",
            "research_report.py",
            "runtime.py",
        ]
    ]
    sources += [root / "pyproject.toml", root / "uv.lock"]
    identity = runtime_identity()
    inputs = {
        "config": config,
        "data": {p.name: digest(p) for p in paths + optional},
        "source": {str(p.relative_to(root)): digest(p) for p in sources},
        "environment": {k: v for k, v in identity.items() if k != "platform"},
    }
    run_hash = fingerprint(inputs)
    manifest = output / "manifest.json"
    if manifest.exists() and json.loads(manifest.read_text())["fingerprint"] != run_hash:
        raise ValueError(
            "Inputs/configuration/code/environment changed; choose a new output directory"
        )
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
    ).stdout.strip()
    atomic_json(
        manifest,
        {
            "fingerprint": run_hash,
            "inputs": inputs,
            "git_commit": commit,
            "evidence_status": config["protocol"],
            "platform": identity["platform"],
        },
    )
    mirror = Mirror(mirror_uri.rstrip("/") + "/" + run_hash) if mirror_uri else None
    store = TaskStore(output, run_hash, log, config["heartbeat_seconds"], mirror)
    if mirror:
        mirror.upload(manifest, "manifest.json")
        for path in paths + optional:
            mirror.upload(path, "raw/" + path.name)
            log.emit("input_uploaded", file=path.name)
    rankings = (
        pd.read_csv(raw / "MMasseyOrdinals.csv")
        if raw / "MMasseyOrdinals.csv" in optional
        else None
    )
    years = [y for y in range(config["first_season"], config["last_season"] + 1) if y != 2020]
    all_teams, matrices = [], []
    for gender, tables in data.items():

        def build_elo(target: Path, tables: dict[str, pd.DataFrame] = tables) -> list[Path]:
            history = elo_history(
                tables["RegularSeasonCompactResults"].loc[
                    tables["RegularSeasonCompactResults"].Season <= config["last_season"]
                ]
            )
            path = target / "elo.parquet"
            history.to_parquet(path, index=False)
            return [path]

        elo_path = store.task(f"elo_{gender.lower()}", build_elo)
        elo = pd.read_parquet(elo_path / "elo.parquet")
        for season in years:

            def build(
                target: Path,
                tables: dict[str, pd.DataFrame] = tables,
                gender: str = gender,
                season: int = season,
                elo: pd.DataFrame = elo,
            ) -> list[Path]:
                with threadpool_limits(limits=config["threads"]):
                    teams = advanced_snapshot(
                        tables,
                        gender,
                        season,
                        132,
                        config["ridge_alpha"],
                        rankings if gender == "M" else None,
                        elo.loc[elo.Season == season].drop(columns="Season"),
                    )
                path = target / "teams.parquet"
                teams.to_parquet(path, index=False)
                return [path]

            destination = store.task(f"snapshot_{gender.lower()}_{season}", build)
            all_teams.append(pd.read_parquet(destination / "teams.parquet"))
        teams = pd.concat(all_teams, ignore_index=True).query("Gender == @gender")
        pairs = labeled_pairs(tables, gender, years)
        matrix = pair_features(teams, pairs)
        matrix["y"], matrix["DayNum"] = pairs.y.to_numpy(), pairs.DayNum.to_numpy()
        if matrix.diff_seed.isna().any():
            raise ValueError("Missing tournament seed in labeled games")
        matrices.append(matrix)
    teams = pd.concat(all_teams, ignore_index=True)
    matrix = pd.concat(matrices, ignore_index=True)
    teams.to_parquet(output / "teams.parquet", index=False)
    matrix.to_parquet(output / "features.parquet", index=False)
    registry = feature_registry()
    registry.to_csv(output / "feature_registry.csv", index=False)
    coverage = (
        teams.groupby(["Gender", "Season"])
        .agg(
            teams=("TeamID", "size"),
            detailed_coverage=("detailed_coverage", "mean"),
            clean_coverage=("clean_coverage", "mean"),
            ranking_teams=("rank_consensus", "count"),
        )
        .reset_index()
    )
    coverage.to_csv(output / "coverage.csv", index=False)
    pd.DataFrame(
        {
            "feature": registry.feature,
            "missing_fraction": [matrix[name].isna().mean() for name in registry.feature],
            "unique_values": [matrix[name].nunique() for name in registry.feature],
        }
    ).to_csv(output / "diagnostics.csv", index=False)
    if raw / "SampleSubmissionStage2.csv" in optional:
        sample = pd.read_csv(raw / "SampleSubmissionStage2.csv")
        submission = pair_features(teams, sample_pairs(sample, teams))
        if submission.ID.tolist() != sample.ID.tolist():
            raise ValueError("Submission row order changed")
        submission["route"] = np.where(submission.diff_seed.notna(), "seeded", "unseeded")
        submission.to_parquet(output / "submission_features.parquet", index=False)
        log.emit(
            "submission_features_ready", rows=len(submission), status="features_only_no_submission"
        )
    availability = {
        "massey": rankings is not None,
        "sample_submission": raw / "SampleSubmissionStage2.csv" in optional,
        "player_availability": False,
        "roster_minutes": False,
    }
    atomic_json(output / "source_availability.json", availability)
    predictions = []
    tasks = [
        (gender, season, block, columns, model)
        for gender in ("M", "W")
        for season in config["validation_seasons"]
        for block, columns in candidate_blocks(rankings is not None and gender == "M").items()
        for model in ("logistic", "hist")
    ]
    for completed, (gender, season, block, columns, model) in enumerate(tasks, 1):
        train = matrix.loc[(matrix.Gender == gender) & (matrix.Season < season)]
        valid = matrix.loc[(matrix.Gender == gender) & (matrix.Season == season)]
        if train.Season.nunique() < config["minimum_prior_seasons"] or valid.empty:
            raise ValueError(f"Insufficient chronological data for {gender} {season}")

        def evaluate(
            target: Path,
            train: pd.DataFrame = train,
            valid: pd.DataFrame = valid,
            columns: list[str] = columns,
            model: str = model,
            block: str = block,
        ) -> list[Path]:
            with threadpool_limits(limits=config["threads"]):
                estimator, probability = fit_fold(train, valid, columns, model, config["seed"])
            result = valid[["Gender", "Season", "DayNum", "ID", "y"]].copy()
            result["p"], result["block"], result["model"] = probability, block, model
            result.to_parquet(target / "predictions.parquet", index=False)
            joblib.dump({"estimator": estimator, "features": columns}, target / "model.joblib")
            atomic_json(
                target / "fold.json",
                {
                    "train_seasons": sorted(train.Season.unique().tolist()),
                    "validation_season": int(valid.Season.iloc[0]),
                    "features": columns,
                    "physical_train_games": len(train),
                    "validation_games": len(valid),
                },
            )
            return [target / name for name in ("predictions.parquet", "model.joblib", "fold.json")]

        destination = store.task(f"fold_{gender.lower()}_{season}_{block}_{model}", evaluate)
        predictions.append(pd.read_parquet(destination / "predictions.parquet"))
        log.emit(
            "progress",
            completed=completed,
            total=len(tasks),
            percent=round(100 * completed / len(tasks), 1),
        )
    forecasts = pd.concat(predictions, ignore_index=True)
    forecasts.to_parquet(output / "predictions.parquet", index=False)
    comparisons = [(name, "strength") for name in [*FAMILIES, "interactions"]]
    comparisons += [
        ("full", "legacy_full"),
        *[("full", "without_" + name) for name in [*FAMILIES, "interactions"]],
    ]
    write_report(forecasts, output, config["seed"], comparisons)
    summary = {
        "status": "completed",
        "fingerprint": run_hash,
        "fold_tasks": len(tasks),
        "feature_count": len(registry),
        "team_snapshots": len(teams),
        "sources": availability,
        "evidence_status": config["protocol"],
        "remote_run_uri": mirror_uri.rstrip("/") + "/" + run_hash if mirror_uri else None,
    }
    return finalize_run(output, summary, mirror, log)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/kaggle/raw"))
    parser.add_argument("--output", type=Path, default=Path("outputs/feature_store"))
    parser.add_argument("--config", type=Path, default=Path("configs/feature_store.json"))
    parser.add_argument("--s3")
    args = parser.parse_args()
    try:
        run(args.raw, args.output, json.loads(args.config.read_text()), args.s3)
        return 0
    except Exception as error:
        EventLog(args.output / "events.jsonl").emit(
            "command_failed", error_type=type(error).__name__, error=str(error)
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
