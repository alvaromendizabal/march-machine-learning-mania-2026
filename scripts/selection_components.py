"""Disentangle resume components and compact representations without retuning LR.

This is exploratory follow-up on already-consumed development seasons. It cannot
supply an untouched confirmation or justify a leaderboard claim.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from filelock import FileLock

from march_mania.runtime import EventLog, Mirror, TaskStore, atomic_json, digest, fingerprint
from march_mania.selection_features import RESUME_COLUMNS
from march_mania.selection_study import BASE, VALID, fit_comparison

MINIMAL = ["diff_seed", "diff_adj_offense", "diff_adj_defense"]
ARMS = {
    "baseline": BASE,
    **{"single_" + x.removeprefix("resume_"): BASE + ["diff_" + x] for x in RESUME_COLUMNS},
    "minimal": MINIMAL,
    "minimal_quality": MINIMAL + ["diff_resume_quality_wins"],
}


def validated_matrix(parent: Path) -> pd.DataFrame:
    """Verify source and data checksums from the original completed study first."""
    record = json.loads((parent / "manifest.json").read_text())
    summary = json.loads((parent / "summary.json").read_text())
    if summary["status"] != "completed" or summary["fingerprint"] != record["fingerprint"]:
        raise ValueError("Need a completed matching parent study")
    pieces = []
    for task in sorted(parent.glob("snapshot_*")):
        checkpoint = json.loads((task / "checkpoint.json").read_text())
        if checkpoint["fingerprint"] != record["fingerprint"]:
            raise ValueError("Parent checkpoint belongs to another study")
        for relative, expected in checkpoint["outputs"].items():
            if digest(task / relative) != expected:
                raise ValueError("Corrupt parent snapshot")
        pieces.append(pd.read_parquet(task / "matrix.parquet"))
    if len(pieces) != 16:
        raise ValueError("Expected 16 verified gender-season snapshots")
    return pd.concat(pieces, ignore_index=True)


def run(parent: Path, root: Path, s3: str | None = None) -> dict:
    config = {
        "arms": ARMS,
        "validation_seasons": VALID,
        "model": "fixed logistic C=0.1",
        "screen_gate": "delta <= -0.001 and improvement in at least 4 of 5 seasons",
        "promotion": "candidate only; no production replacement",
        "max_fits": 140,
    }
    identity = fingerprint(
        {
            "parent": digest(parent / "manifest.json"),
            "script": digest(Path(__file__)),
            "config": config,
        }
    )
    output = root / identity
    output.mkdir(parents=True, exist_ok=True)
    with FileLock(str(output / ".run.lock"), timeout=0):
        started = time.monotonic()
        log = EventLog(output / "events.jsonl")
        mirror = Mirror(s3.rstrip("/") + "/" + identity) if s3 else None
        store = TaskStore(output, identity, log, 15, mirror)
        matrix = validated_matrix(parent)
        atomic_json(
            output / "manifest.json",
            {
                "fingerprint": identity,
                "config": config,
                "parent": str(parent),
                "parent_manifest_sha256": digest(parent / "manifest.json"),
                "script_sha256": digest(Path(__file__)),
                "max_new_fits": 140,
            },
        )
        results = []
        for gender in ("M", "W"):
            for season in VALID:
                train = matrix.loc[(matrix.Gender == gender) & (matrix.Season < season)]
                valid = matrix.loc[(matrix.Gender == gender) & (matrix.Season == season)]
                for arm, columns in ARMS.items():

                    def build(
                        target: Path,
                        train: pd.DataFrame = train,
                        valid: pd.DataFrame = valid,
                        columns: list[str] = columns,
                        arm: str = arm,
                    ) -> list[Path]:
                        if arm == "baseline":
                            gender_key = str(valid.Gender.iloc[0]).lower()
                            season_key = int(valid.Season.iloc[0])
                            original = parent / f"fold_{gender_key}_{season_key}_strength_baseline"
                            record = json.loads((original / "checkpoint.json").read_text())
                            for relative, expected in record["outputs"].items():
                                if digest(original / relative) != expected:
                                    raise ValueError("Corrupt reusable baseline")
                            for name in ["model.joblib", "fold.json"]:
                                shutil.copy2(original / name, target / name)
                            original_frame = pd.read_parquet(original / "predictions.parquet")
                            original_frame.drop(columns="control").to_parquet(
                                target / "predictions.parquet", index=False
                            )
                            return [
                                target / "predictions.parquet",
                                target / "model.joblib",
                                target / "fold.json",
                            ]
                        model, p, retained = fit_comparison(train, valid, columns)
                        frame = valid[
                            ["Gender", "Season", "DayNum", "Team1ID", "Team2ID", "y"]
                        ].copy()
                        frame["p"] = p
                        frame["arm"] = arm
                        frame.to_parquet(target / "predictions.parquet", index=False)
                        joblib.dump({"model": model, "columns": retained}, target / "model.joblib")
                        atomic_json(
                            target / "fold.json",
                            {
                                "train_max_season": int(train.Season.max()),
                                "validation_season": int(valid.Season.iloc[0]),
                                "retained": retained,
                                "train_games": len(train),
                                "validation_games": len(valid),
                            },
                        )
                        return [
                            target / "predictions.parquet",
                            target / "model.joblib",
                            target / "fold.json",
                        ]

                    task = store.task(f"fold_{gender.lower()}_{season}_{arm}", build)
                    results.append(pd.read_parquet(task / "predictions.parquet"))
                log.emit(
                    "fold_progress",
                    gender=gender,
                    season=season,
                    completed_fits=len(results),
                    total_fits=140,
                )
        predictions = pd.concat(results, ignore_index=True)
        predictions.to_parquet(output / "predictions.parquet", index=False)
        rows = []
        for scope, frame in [
            ("all_tournament", predictions),
            ("main_draw_day136", predictions.loc[predictions.DayNum >= 136]),
        ]:
            for (gender, season, arm), group in frame.groupby(["Gender", "Season", "arm"]):
                rows.append(
                    {
                        "scope": scope,
                        "Gender": gender,
                        "Season": season,
                        "arm": arm,
                        "games": len(group),
                        "brier": float(np.mean((group.y - group.p) ** 2)),
                    }
                )
        metrics = pd.DataFrame(rows)
        base = metrics.loc[
            metrics.arm == "baseline", ["scope", "Gender", "Season", "brier"]
        ].rename(columns={"brier": "baseline_brier"})
        compared = metrics.merge(base, on=["scope", "Gender", "Season"], validate="many_to_one")
        compared["delta"] = compared.brier - compared.baseline_brier
        compared.to_csv(output / "metrics_by_season.csv", index=False)
        leaders = (
            compared.groupby(["scope", "Gender", "arm"])
            .agg(
                mean_season_brier=("brier", "mean"),
                mean_delta=("delta", "mean"),
                improved_seasons=("delta", lambda x: int((x < 0).sum())),
                worst_delta=("delta", "max"),
            )
            .reset_index()
        )
        leaders["exploratory_screen_pass"] = (leaders.mean_delta <= -0.001) & (
            leaders.improved_seasons >= 4
        )
        leaders.to_csv(output / "leaderboard.csv", index=False)
        result = {
            "status": "completed",
            "fingerprint": identity,
            "parent": str(parent),
            "fold_tasks": len(results),
            "new_fits": len(results) - 10,
            "reused_baselines": 10,
            "new_feature_definitions": 0,
            "question": "Component signal versus redundant groups",
            "elapsed_seconds": time.monotonic() - started,
            "output": str(output),
            "leaderboard": leaders.to_dict(orient="records"),
            "new_kaggle_submission": False,
        }
        atomic_json(output / "summary.json", result)
        atomic_json(root / "latest.json", result)
        if mirror:
            for name in [
                "manifest.json",
                "metrics_by_season.csv",
                "leaderboard.csv",
                "summary.json",
                "predictions.parquet",
            ]:
                mirror.upload(output / name, name)
        print(json.dumps(result, indent=2))
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--s3")
    args = parser.parse_args()
    run(args.parent, args.output, args.s3)


if __name__ == "__main__":
    main()
