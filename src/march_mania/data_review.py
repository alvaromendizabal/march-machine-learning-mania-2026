"""Resumable raw-data inventory, basketball EDA and chronological split evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from filelock import FileLock

from march_mania.advanced_features import possession_games
from march_mania.feature_store import validate_config
from march_mania.features import FILES, read_official
from march_mania.research import finalize_run
from march_mania.runtime import EventLog, Mirror, TaskStore, atomic_json, digest, fingerprint


def inventory_file(path: Path) -> dict[str, Any]:
    """Bound memory while reading even the multi-million-row ranking file."""
    rows = missing = 0
    columns: list[str] = []
    first = last = None
    for chunk in pd.read_csv(path, chunksize=100_000, encoding="latin1"):
        columns = list(chunk.columns)
        rows += len(chunk)
        missing += int(chunk.isna().sum().sum())
        if "Season" in chunk and chunk.Season.notna().any():
            low, high = int(chunk.Season.min()), int(chunk.Season.max())
            first = low if first is None else min(first, low)
            last = high if last is None else max(last, high)
    return {
        "file": path.name,
        "rows": rows,
        "columns": len(columns),
        "bytes": path.stat().st_size,
        "first_season": first,
        "last_season": last,
        "missing_cells": missing,
        "sha256": digest(path),
        "column_names": ", ".join(columns),
        "feature_source": path.name
        in {
            f"{g}{name}.csv"
            for g in ("M", "W")
            for name in (*FILES, "TeamCoaches", "TeamConferences")
        }
        or path.name == "MMasseyOrdinals.csv",
    }


def season_review(data: dict, config: dict) -> pd.DataFrame:
    """Aggregate pre-cutoff box scores; no tournament outcomes used in EDA."""
    rows = []
    for gender, tables in data.items():
        compact = tables["RegularSeasonCompactResults"]
        detail = tables["RegularSeasonDetailedResults"]
        for season in range(config["first_season"], config["last_season"] + 1):
            games = compact.loc[(compact.Season == season) & (compact.DayNum <= 132)]
            box = detail.loc[(detail.Season == season) & (detail.DayNum <= 132)]
            if games.empty or box.empty:
                continue
            long = possession_games(box)
            row = {
                "Gender": gender,
                "Season": season,
                "regular_games": len(games),
                "detailed_games": len(box),
                "teams": len(pd.unique(games[["WTeamID", "LTeamID"]].to_numpy().ravel())),
                "latest_regular_day": int(games.DayNum.max()),
                "post_cutoff_rows_excluded": int(
                    ((compact.Season == season) & (compact.DayNum > 132)).sum()
                ),
                "mean_tempo": long.tempo.mean(),
                "mean_efficiency": long.efficiency.mean(),
                "clean_possession_fraction": long.clean.mean(),
                "three_attempt_share": long.FGA3.sum() / long.FGA.sum(),
                "neutral_game_fraction": games.WLoc.eq("N").mean(),
                "overtime_fraction": games.NumOT.gt(0).mean() if "NumOT" in games else 0.0,
                "used_for_tournament_validation": season in config["validation_seasons"],
            }
            rows.append(row)
    return pd.DataFrame(rows)


def split_review(data: dict, config: dict) -> pd.DataFrame:
    validate_config(config)
    rows = []
    for gender, tables in data.items():
        labels = tables["NCAATourneyCompactResults"]
        for season in config["validation_seasons"]:
            train = labels.loc[
                labels.Season.between(config["first_season"], season - 1) & labels.Season.ne(2020)
            ]
            valid = labels.loc[labels.Season.eq(season)]
            if train.Season.nunique() < config["minimum_prior_seasons"] or valid.empty:
                raise ValueError(f"Insufficient split data for {gender} {season}")
            if (train.DayNum <= 132).any() or (valid.DayNum <= 132).any():
                raise ValueError("Tournament label precedes the snapshot cutoff")
            rows.append(
                {
                    "Gender": gender,
                    "validation_season": season,
                    "training_seasons": ", ".join(map(str, sorted(train.Season.unique()))),
                    "training_max_season": int(train.Season.max()),
                    "training_games": len(train),
                    "validation_games": len(valid),
                    "snapshot_cutoff": 132,
                    "first_validation_day": int(valid.DayNum.min()),
                    "no_season_overlap": bool(train.Season.max() < season),
                }
            )
    return pd.DataFrame(rows)


def run(raw: Path, output: Path, config: dict, mirror_uri: str | None = None) -> dict:
    validate_config(config)
    files = sorted(raw.glob("*.csv"))
    if not files:
        raise FileNotFoundError("Run march-data first: no CSV files found in " + str(raw))
    hashes = {path.name: digest(path) for path in files}
    provenance_path = raw.parent / "data_manifest.json"
    provenance = json.loads(provenance_path.read_text()) if provenance_path.exists() else {}
    if provenance and hashes != provenance.get("sha256"):
        raise ValueError("Raw CSV set or checksum differs from the downloaded data manifest")
    inputs = {
        "data": hashes,
        "config": config,
        "source": digest(Path(__file__)),
        "features_source": digest(Path(__file__).with_name("features.py")),
        "advanced_source": digest(Path(__file__).with_name("advanced_features.py")),
        "provenance": provenance,
    }
    identity = fingerprint(inputs)
    destination = output / identity
    destination.mkdir(parents=True, exist_ok=True)
    with FileLock(str(destination / ".run.lock"), timeout=0):
        log = EventLog(destination / "events.jsonl")
        log.emit("data_review_started", files=len(files))
        mirror = Mirror(mirror_uri.rstrip("/") + "/" + identity) if mirror_uri else None
        store = TaskStore(destination, identity, log, config["heartbeat_seconds"], mirror)
        inventory = []
        for number, path in enumerate(files, 1):

            def inspect(target: Path, path: Path = path) -> list[Path]:
                record = target / "inventory.json"
                atomic_json(record, inventory_file(path))
                return [record]

            task = store.task("inventory_" + path.stem.lower(), inspect)
            inventory.append(json.loads((task / "inventory.json").read_text()))
            log.emit("inventory_progress", completed=number, total=len(files), file=path.name)

        def analyze(target: Path) -> list[Path]:
            data, _ = read_official(raw)
            season_review(data, config).to_csv(target / "seasons.csv", index=False)
            split_review(data, config).to_csv(target / "splits.csv", index=False)
            return [target / "seasons.csv", target / "splits.csv"]

        task = store.task("basketball_analysis", analyze)
        for name in ("seasons.csv", "splits.csv"):
            (destination / name).write_bytes((task / name).read_bytes())
        pd.DataFrame(inventory).to_csv(destination / "inventory.csv", index=False)
        atomic_json(destination / "manifest.json", {"fingerprint": identity, "inputs": inputs})
        summary = {
            "status": "completed",
            "fingerprint": identity,
            "files": len(files),
            "source": provenance.get("source", "local official-schema CSV files"),
            "download_recorded_at": provenance.get("retrieved_at"),
            "download_hashes_verified": bool(provenance),
            "total_bytes": sum(path.stat().st_size for path in files),
            "raw_directory": str(raw),
            "official_metric": "Brier score (lower is better)",
            "remote_run_uri": mirror_uri.rstrip("/") + "/" + identity if mirror_uri else None,
        }
        summary = finalize_run(destination, summary, mirror, log)
        atomic_json(output / "latest.json", {"fingerprint": identity, "directory": identity})
        return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/kaggle/raw"))
    parser.add_argument("--run-root", type=Path, default=Path("outputs/data_review"))
    parser.add_argument("--config", type=Path, default=Path("configs/feature_store.json"))
    parser.add_argument("--s3")
    args = parser.parse_args()
    try:
        run(args.raw, args.run_root, json.loads(args.config.read_text()), args.s3)
        return 0
    except Exception as error:
        EventLog(args.run_root / "events.jsonl").emit(
            "data_review_failed",
            error_type=type(error).__name__,
            error=str(error),
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
