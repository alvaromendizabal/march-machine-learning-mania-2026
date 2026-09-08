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
from march_mania.encoding import encode_history
from march_mania.feature_selection import screening_audit
from march_mania.features import read_official
from march_mania.matchup_artifacts import write_submission_features
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
            "rankings": "Massey publication cohorts at or before DayNum 132",
            "rank_trends": "matched Massey systems at historical as-of cutoffs",
            "target_team": "NCAA team outcomes from strictly earlier training seasons",
            "target_seed": "NCAA outcomes grouped by historical season seed",
            "target_rank": "NCAA outcomes grouped by historical pre-cutoff Massey decile",
            "dynamic": "regular-season compact history at or before DayNum 132",
            "coach_history": "official coach intervals; strictly prior-season outcomes",
            "distribution": "pre-cutoff detailed game distributions across fixed windows",
            "venue_profile": "pre-cutoff home, away and neutral game cohorts",
            "opponent_profile": "pre-cutoff opponents grouped by current legal strength",
            "trajectory": "pre-cutoff daily rates, slopes and momentum",
            "peer_profile": "same-season pre-cutoff peer ranks and normalization",
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
                "missing_policy": "training-fold preprocessing; unavailable/zero columns audited",
                "label_policy": "strictly prior seasons; fixed prior and smoothing"
                if family.startswith("target_") or family == "coach_history"
                else "no current/future tournament outcomes",
                "evidence": "candidate; requires ablation",
            }
        )
    return pd.DataFrame(rows)


def prepare_inputs(raw: Path, config: dict[str, Any]) -> tuple:
    data, paths = read_official(raw)
    optional = [
        p for p in [raw / "MMasseyOrdinals.csv", raw / "SampleSubmissionStage2.csv"] if p.exists()
    ]
    root = Path(__file__).resolve().parents[2]
    sources = [
        Path(__file__).parent / name
        for name in [
            "advanced_features.py",
            "context_features.py",
            "candidate_features.py",
            "coach_features.py",
            "feature_selection.py",
            "matchup_artifacts.py",
            "rankings.py",
            "encoding.py",
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
    return data, paths, optional, root, identity, inputs


def run(
    raw: Path,
    output: Path,
    config: dict[str, Any],
    mirror_uri: str | None = None,
    *,
    managed: bool = False,
    require_massey: bool = False,
) -> dict[str, Any]:
    validate_config(config)
    if require_massey and not (raw / "MMasseyOrdinals.csv").is_file():
        raise FileNotFoundError("MMasseyOrdinals.csv is required; complete march-data first")
    prepared = prepare_inputs(raw, config)
    run_hash = fingerprint(prepared[-1])
    destination = output / run_hash if managed else output
    destination.mkdir(parents=True, exist_ok=True)
    with FileLock(str(destination / ".run.lock"), timeout=0):
        summary = _run(raw, destination, config, mirror_uri, prepared, require_massey)
        if managed:
            atomic_json(output / "latest.json", {"fingerprint": run_hash, "directory": run_hash})
        return summary


def _run(
    raw: Path,
    output: Path,
    config: dict[str, Any],
    mirror_uri: str | None,
    prepared: tuple,
    require_massey: bool,
) -> dict[str, Any]:
    log = EventLog(output / "events.jsonl")
    log.emit("run_started", protocol=config["protocol"], output_directory=str(output.resolve()))
    data, paths, optional, root, identity, inputs = prepared
    run_hash = fingerprint(inputs)
    manifest = output / "manifest.json"
    if manifest.exists() and json.loads(manifest.read_text())["fingerprint"] != run_hash:
        raise ValueError("Inputs changed; use --run-root for automatic versioned runs")
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
    if mirror:
        from march_mania.publication.artifacts import restore_tasks

        restore_tasks(mirror, output, run_hash, log)
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
    all_teams, matrices, encoding_audits = [], [], []
    for gender, tables in data.items():
        snapshots = []

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
            snapshots.append(pd.read_parquet(destination / "teams.parquet"))
        base_teams = pd.concat(snapshots, ignore_index=True)

        def build_encoding(
            target: Path,
            base_teams: pd.DataFrame = base_teams,
            tables: dict[str, pd.DataFrame] = tables,
        ) -> list[Path]:
            encoded, audit = encode_history(base_teams, tables["NCAATourneyCompactResults"])
            encoded.to_parquet(target / "teams.parquet", index=False)
            audit.to_csv(target / "encoding_audit.csv", index=False)
            return [target / "teams.parquet", target / "encoding_audit.csv"]

        encoded_path = store.task(f"encoding_{gender.lower()}", build_encoding)
        teams = pd.read_parquet(encoded_path / "teams.parquet")
        all_teams.append(teams)
        encoding_audits.append(pd.read_csv(encoded_path / "encoding_audit.csv"))
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
    pd.concat(encoding_audits, ignore_index=True).to_csv(output / "encoding_audit.csv", index=False)
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
    if require_massey:
        evaluated = coverage.loc[
            (coverage.Gender == "M") & coverage.Season.isin(config["validation_seasons"])
        ]
        if (evaluated.ranking_teams == 0).any():
            raise ValueError("Required Massey data has no legal coverage in a validation season")
    for row in coverage.to_dict("records"):
        log.emit("feature_coverage", **{str(k): v for k, v in row.items()})
    pd.DataFrame(
        {
            "feature": registry.feature,
            "missing_fraction": [matrix[name].isna().mean() for name in registry.feature],
            "unique_values": [matrix[name].nunique() for name in registry.feature],
        }
    ).to_csv(output / "diagnostics.csv", index=False)
    if raw / "SampleSubmissionStage2.csv" in optional:
        sample = pd.read_csv(raw / "SampleSubmissionStage2.csv")
        write_submission_features(
            teams,
            sample_pairs(sample, teams),
            sample,
            output / "submission_features.parquet",
            store,
        )
        log.emit(
            "submission_features_ready", rows=len(sample), status="features_only_no_submission"
        )
    availability = {
        "massey": rankings is not None,
        "sample_submission": raw / "SampleSubmissionStage2.csv" in optional,
        "player_availability": False,
        "roster_minutes": False,
        "mens_coaches": (raw / "MTeamCoaches.csv").is_file(),
        "womens_coaches": (raw / "WTeamCoaches.csv").is_file(),
    }
    atomic_json(output / "source_availability.json", availability)
    predictions, usage = [], []
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
            fitted = [
                c for c in columns if train[c].notna().any() and train[c].fillna(0).ne(0).any()
            ]
            if not fitted:
                raise ValueError("No informative training features in the requested block")
            with threadpool_limits(limits=config["threads"]):
                estimator, probability = fit_fold(train, valid, fitted, model, config["seed"])
            selection = screening_audit(estimator, fitted)
            selected = [fitted[i] for i in estimator.screen.indices_]
            coefficients = (
                dict(zip(selected, estimator.model[-1].coef_[0], strict=True))
                if model == "logistic"
                else {}
            )
            reasons = selection.set_index("feature").status.to_dict()
            selection.to_csv(target / "screening.csv", index=False)
            audit = pd.DataFrame(
                [
                    {
                        "Gender": str(valid.Gender.iloc[0]),
                        "Season": int(valid.Season.iloc[0]),
                        "block": block,
                        "model": model,
                        "feature": c,
                        "fitted": c in selected,
                        "train_nonmissing": int(train[c].notna().sum()),
                        "validation_nonmissing": int(valid[c].notna().sum()),
                        "train_games": len(train),
                        "validation_games": len(valid),
                        "standardized_coefficient": coefficients.get(c),
                        "status": reasons.get(c, "no_training_signal"),
                    }
                    for c in columns
                ]
            )
            audit.to_csv(target / "feature_usage.csv", index=False)
            result = valid[["Gender", "Season", "DayNum", "ID", "y"]].copy()
            result["p"], result["block"], result["model"] = probability, block, model
            result.to_parquet(target / "predictions.parquet", index=False)
            joblib.dump({"estimator": estimator, "features": fitted}, target / "model.joblib")
            atomic_json(
                target / "fold.json",
                {
                    "train_seasons": sorted(train.Season.unique().tolist()),
                    "validation_season": int(valid.Season.iloc[0]),
                    "features": selected,
                    "model_input_features": fitted,
                    "candidate_count": len(columns),
                    "retained_count": len(selected),
                    "rejected_count": len(columns) - len(selected),
                    "requested_features": columns,
                    "encoding_rule": "each row uses only strictly earlier training seasons",
                    "physical_train_games": len(train),
                    "validation_games": len(valid),
                },
            )
            return [
                target / name
                for name in (
                    "predictions.parquet",
                    "model.joblib",
                    "fold.json",
                    "feature_usage.csv",
                    "screening.csv",
                )
            ]

        destination = store.task(f"fold_{gender.lower()}_{season}_{block}_{model}", evaluate)
        predictions.append(pd.read_parquet(destination / "predictions.parquet"))
        usage.append(pd.read_csv(destination / "feature_usage.csv"))
        log.emit(
            "progress",
            completed=completed,
            total=len(tasks),
            percent=round(100 * completed / len(tasks), 1),
        )
    used = pd.concat(usage, ignore_index=True)
    used.to_csv(output / "feature_usage.csv", index=False)
    screening = (
        used.groupby(["Gender", "Season", "block", "model", "status"]).size().unstack(fill_value=0)
    )
    screening["candidate_count"] = screening.sum(axis=1)
    screening["retained_count"] = screening.get("retained", 0)
    screening["rejected_count"] = screening.candidate_count - screening.retained_count
    screening.reset_index().to_csv(output / "screening_summary.csv", index=False)
    used.loc[used.block == "full"].groupby(["Gender", "model", "feature"]).agg(
        folds=("Season", "size"),
        retained_folds=("fitted", "sum"),
        retention_rate=("fitted", "mean"),
    ).reset_index().to_csv(output / "selection_stability.csv", index=False)
    forecasts = pd.concat(predictions, ignore_index=True)
    forecasts.to_parquet(output / "predictions.parquet", index=False)
    comparisons = [(name, "strength") for name in [*FAMILIES, "interactions"]]
    comparisons += [
        ("full", "legacy_full"),
        *[("full", "without_" + name) for name in [*FAMILIES, "interactions"]],
    ]
    comparisons.append(("full", "without_massey"))
    write_report(forecasts, output, config["seed"], comparisons)
    summary = {
        "status": "completed",
        "fingerprint": run_hash,
        "fold_tasks": len(tasks),
        "feature_count": len(registry),
        "screened_candidates": len(registry),
        "selection_unit": "individual temporal training fold, not a global retained list",
        "retained_per_fit_min": int(screening.retained_count.min()),
        "retained_per_fit_max": int(screening.retained_count.max()),
        "screening_decisions": int(screening.candidate_count.sum()),
        "rejected_decisions": int(screening.rejected_count.sum()),
        "team_snapshots": len(teams),
        "sources": availability,
        "evidence_status": config["protocol"],
        "remote_run_uri": mirror_uri.rstrip("/") + "/" + run_hash if mirror_uri else None,
    }
    return finalize_run(output, summary, mirror, log)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/kaggle/raw"))
    destinations = parser.add_mutually_exclusive_group()
    destinations.add_argument("--output", type=Path, help="Exact run directory (strict identity)")
    destinations.add_argument("--run-root", type=Path, help="Parent for content-addressed runs")
    parser.add_argument("--require-massey", action="store_true")
    parser.add_argument("--config", type=Path, default=Path("configs/feature_store.json"))
    parser.add_argument("--s3")
    args = parser.parse_args()
    output = args.output or args.run_root or Path("outputs/feature_store")
    try:
        run(
            args.raw,
            output,
            json.loads(args.config.read_text()),
            args.s3,
            managed=args.output is None,
            require_massey=args.require_massey,
        )
        return 0
    except Exception as error:
        EventLog(output / "events.jsonl").emit(
            "command_failed", error_type=type(error).__name__, error=str(error)
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
