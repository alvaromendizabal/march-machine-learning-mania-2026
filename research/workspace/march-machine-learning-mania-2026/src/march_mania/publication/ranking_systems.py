"""Chronological research on individual ordinal systems beyond a compact consensus."""

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
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from march_mania.advanced_features import candidate_blocks
from march_mania.feature_selection import TrainingScreen
from march_mania.modeling import validate_matrix
from march_mania.publication.artifacts import safe_path
from march_mania.publication.capacity import KEYS, select_capacity, verified_reference
from march_mania.publication.workflow import (
    evidence,
    raw_directory,
    require_current_features,
    require_recorded_source,
)
from march_mania.rankings import publication_panel
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

FAMILIES = {
    "levels": ["level", "logit"],
    "deviations": ["deviation", "logit_deviation"],
    "momentum": ["change_7", "change_30", "change_60"],
    "availability": ["available"],
}
ARMS = ["strength", "consensus", *FAMILIES, "combined", "embedding"]


def validate_config(config: dict[str, Any]) -> None:
    years = config["validation_seasons"]
    if (
        config["protocol"] != "retrospective-ranking-system-research"
        or not years
        or years != sorted(set(years))
        or 2020 in years
        or max(years) >= 2022
        or config["catalog_first_season"] >= config["first_training_season"]
        or config["first_training_season"] >= min(years) - 1
        or config["feature_cutoff_day"] != 132
        or config["momentum_days"] != [7, 30, 60]
        or not 0 < config["logit_clip"] < 0.5
        or config["additional_capacity"] < 1
        or config["embedding_components"] < 1
        or config["minimum_inner_seasons"] < 2
        or config["models"] != ["logistic", "hist"]
        or config["threads"] < 1
        or config["heartbeat_seconds"] <= 0
    ):
        raise ValueError("Invalid chronological ranking-system protocol")


def system_catalog(rankings: pd.DataFrame, config: dict[str, Any]) -> list[str]:
    """A vocabulary available before the first tournament training labels."""
    names: set[str] = set()
    for year in range(config["catalog_first_season"], config["first_training_season"]):
        panel = publication_panel(rankings, year, config["feature_cutoff_day"])
        names.update(panel.SystemName.astype(str))
    if not names or any(not s.isalnum() for s in names):
        raise ValueError("Missing or invalid historical system vocabulary")
    return sorted(names)


def family_columns(systems: list[str]) -> dict[str, list[str]]:
    return {
        family: [f"diff_system_{system}_{kind}" for system in systems for kind in kinds]
        for family, kinds in FAMILIES.items()
    }


def system_snapshot(
    rankings: pd.DataFrame, year: int, systems: list[str], config: dict[str, Any]
) -> pd.DataFrame:
    cutoff = config["feature_cutoff_day"]
    panel = publication_panel(rankings, year, cutoff)
    values = panel.pivot(index="TeamID", columns="SystemName", values="rating")
    # Consensus includes all contemporaneously available systems, as in notebook 02.
    consensus = values.median(axis=1)
    values = values.reindex(columns=systems)
    clip = config["logit_clip"]
    bounded = values.clip(clip, 1 - clip)
    logits = pd.DataFrame(
        np.log(bounded.to_numpy() / (1 - bounded.to_numpy())),
        index=values.index,
        columns=systems,
    )
    center = consensus.clip(clip, 1 - clip)
    center_logit = np.log(center / (1 - center))
    tables = {
        "level": values,
        "logit": logits,
        "deviation": values.sub(consensus, axis=0),
        "logit_deviation": logits.sub(center_logit, axis=0),
        "available": values.notna().astype(float),
    }
    for lag in config["momentum_days"]:
        past = publication_panel(rankings, year, cutoff - lag)
        previous = past.pivot(index="TeamID", columns="SystemName", values="rating")
        tables[f"change_{lag}"] = values - previous.reindex(index=values.index, columns=systems)
    return pd.DataFrame(
        {
            f"diff_system_{system}_{kind}": tables[kind][system]
            for system in systems
            for kinds in FAMILIES.values()
            for kind in kinds
        },
        index=values.index,
    )


def add_system_matchups(matrix: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    """No targets are accepted by the source transform; use one canonical matchup row."""
    if teams.index.has_duplicates or matrix.duplicated(["Season", "ID"]).any():
        raise ValueError("Duplicate system team or game rows")
    first = teams.reindex(matrix.Team1ID).reset_index(drop=True)
    second = teams.reindex(matrix.Team2ID).reset_index(drop=True)
    indicators = [c for c in teams.columns.astype(str) if c.endswith("_available")]
    first[indicators] = first[indicators].fillna(0)
    second[indicators] = second[indicators].fillna(0)
    return pd.concat([matrix.reset_index(drop=True), first - second], axis=1)


class SystemPredictor:
    """Persist training-only base selection, additional representation and learner."""

    def __init__(self, base_count: int, mode: str, config: dict[str, Any], template: Any):
        self.base_count, self.mode, self.config = base_count, mode, config
        self.template = template

    def fit(self, values: np.ndarray, labels: np.ndarray) -> SystemPredictor:
        self.input_count = values.shape[1]
        self.base_screen = TrainingScreen().fit(values[:, : self.base_count], labels)
        base = self.base_screen.transform(values[:, : self.base_count])
        extra = values[:, self.base_count :]
        self.extra_indices = np.array([], dtype=int)
        self.extra_screen: TrainingScreen | None = None
        self.embedding: PCA | None = None
        self.scaler: StandardScaler | None = None
        self.extra_audit = pd.DataFrame()
        if extra.shape[1]:
            safe = np.nan_to_num(extra, nan=0.0)
            norms = np.linalg.norm(safe, axis=0)
            usable = norms > 1e-12
            if self.mode == "embedding":
                self.extra_indices = np.flatnonzero(usable)
                self.extra_audit = pd.DataFrame(
                    {
                        "index": np.arange(extra.shape[1]),
                        "status": np.where(usable, "embedded", "constant_or_missing"),
                    }
                )
                if usable.any():
                    self.scaler = StandardScaler().fit(safe[:, usable])
                    scaled = self.scaler.transform(safe[:, usable])
                    self.embedding = PCA(
                        n_components=min(
                            self.config["embedding_components"], int(usable.sum()), len(values) - 1
                        ),
                        svd_solver="full",
                    ).fit(scaled)
            else:
                safe_base = np.nan_to_num(base, nan=0.0)
                bnorm = np.linalg.norm(safe_base, axis=0)
                correlations = np.abs(
                    (safe.T @ safe_base) / np.maximum(norms[:, None] * bnorm, 1e-30)
                )
                duplicates = correlations.max(axis=1) >= 0.995
                screened = extra.copy()
                screened[:, duplicates] = np.nan
                try:
                    self.extra_screen = TrainingScreen(
                        max_features=self.config["additional_capacity"]
                    ).fit(screened, labels)
                except ValueError as error:
                    if str(error) != "No informative training candidates":
                        raise
                    self.extra_audit = pd.DataFrame(
                        {"index": np.arange(extra.shape[1]), "status": "constant_or_missing"}
                    )
                else:
                    self.extra_indices = self.extra_screen.indices_
                    self.extra_audit = self.extra_screen.audit_.copy()
                self.extra_audit.loc[duplicates, "status"] = "redundant_base"
        self.model = clone(self.template).fit(self.transform(values), labels)
        return self

    def transform(self, values: np.ndarray) -> np.ndarray:
        if values.ndim != 2 or values.shape[1] != self.input_count or np.isinf(values).any():
            raise ValueError("Ranking-system predictor schema changed")
        base = self.base_screen.transform(values[:, : self.base_count])
        extra = values[:, self.base_count :][:, self.extra_indices]
        if self.embedding is not None and self.scaler is not None:
            extra = self.embedding.transform(self.scaler.transform(np.nan_to_num(extra, nan=0.0)))
        if not extra.shape[1]:
            return base
        return np.column_stack([base, extra])

    def predict_proba(self, values: np.ndarray) -> np.ndarray:
        return np.asarray(self.model.predict_proba(self.transform(values)), dtype=float)


def fit_systems(
    train: pd.DataFrame,
    valid: pd.DataFrame,
    base: list[str],
    extra: list[str],
    mode: str,
    template: Any,
    config: dict[str, Any],
) -> tuple[SystemPredictor, np.ndarray]:
    if (
        train.empty
        or valid.empty
        or train.Season.max() >= valid.Season.min()
        or valid.Season.nunique() != 1
    ):
        raise ValueError("Invalid chronological ranking-system fold")
    columns = base + extra
    if (
        len(columns) != len(set(columns))
        or not set(base).issubset(candidate_blocks()["full"])
        or any(not c.startswith("diff_system_") for c in extra)
    ):
        raise ValueError("Invalid ranking-system feature schema")
    x, y = train[columns].to_numpy(float), train.y.to_numpy(int)
    x, y = np.concatenate([x, -x]), np.concatenate([y, 1 - y])
    estimator = SystemPredictor(len(base), mode, config, template).fit(x, y)
    return estimator, symmetric_probability(estimator, valid[columns].to_numpy(float))


def summarize(predictions: pd.DataFrame, config: dict[str, Any], output: Path) -> None:
    fixed = predictions.loc[predictions.Season.isin(config["validation_seasons"])].copy()
    selected, decisions = [], []
    options = ARMS[1:]
    for model, group in predictions.groupby("model"):
        selectable = group.loc[group.block.isin(options)].assign(
            capacity=lambda x: x.block.map({b: i for i, b in enumerate(options)})
        )
        for year in config["validation_seasons"]:
            index = select_capacity(selectable, year, config["minimum_inner_seasons"])
            arm = options[index]
            selected.append(
                group.loc[(group.Season == year) & (group.block == arm)].assign(block="nested")
            )
            decisions.append(
                {
                    "model": model,
                    "Season": year,
                    "block": arm,
                    "history_last_season": int(group.loc[group.Season < year].Season.max()),
                }
            )
    evaluation = pd.concat([fixed, *selected], ignore_index=True)
    metrics: list[dict[str, Any]] = []
    yearly: list[dict[str, Any]] = []
    for (model, block), group in evaluation.groupby(["model", "block"]):
        losses = group.assign(loss=(group.y - group.p) ** 2).groupby("Season").loss.mean()
        metrics.append(
            {
                "model": model,
                "block": block,
                "games": len(group),
                "macro_season_brier": float(losses.mean()),
                **probability_metrics(group.y.to_numpy(), group.p.to_numpy()),
            }
        )
        yearly.extend(
            {"model": model, "block": block, "Season": int(str(year)), "brier": float(loss)}
            for year, loss in losses.items()
        )
    contrasts = [(b, "consensus") for b in [*ARMS, "nested"] if b != "consensus"]
    paired_season_intervals(evaluation, config["seed"], contrasts).to_csv(
        output / "intervals.csv", index=False
    )
    pd.DataFrame(metrics).to_csv(output / "leaderboard.csv", index=False)
    pd.DataFrame(yearly).to_csv(output / "metrics_by_season.csv", index=False)
    pd.DataFrame(decisions).to_csv(output / "selection.csv", index=False)
    evaluation.to_csv(output / "evaluation.csv", index=False)


def run(root: Path) -> Path:
    config = json.loads((root / "configs/ranking_systems.json").read_text())
    validate_config(config)
    features = require_current_features(root)
    _, parent = evidence(root, "feature_store")
    require_recorded_source(root, "feature_store", parent)
    _, models = evidence(root, "model_comparison")
    if (
        digest(features / "features.parquet")
        != models["manifest"]["inputs"]["data"]["features.parquet"]
    ):
        raise ValueError("Feature matrix differs from the trained notebook 03 input")
    raw = raw_directory(root) / "MMasseyOrdinals.csv"
    expected = parent["manifest"]["inputs"]["data"][raw.name]
    if digest(raw) != expected:
        raise ValueError("Ranking source no longer matches notebook 02")
    inputs = {
        "config": config,
        "feature_fingerprint": parent["summary"]["fingerprint"],
        "data": {"features.parquet": digest(features / "features.parquet"), raw.name: expected},
        "source": {
            **models["manifest"]["inputs"]["source"],
            **parent["manifest"]["inputs"]["source"],
            **{
                p: digest(root / p)
                for p in [
                    "src/march_mania/publication/ranking_systems.py",
                    "src/march_mania/publication/capacity.py",
                    "src/march_mania/publication/workflow.py",
                ]
            },
        },
        "environment": {k: v for k, v in runtime_identity().items() if k != "platform"},
    }
    key = fingerprint(inputs)
    output = root / "outputs/ranking_systems" / key
    output.mkdir(parents=True, exist_ok=True)
    with FileLock(str(output / ".run.lock"), timeout=0):
        _run(features, raw, output, key, inputs)
    atomic_json(output.parent / "latest.json", {"fingerprint": key, "directory": key})
    publish(root, output)
    return output


def _run(features: Path, raw: Path, output: Path, key: str, inputs: dict[str, Any]) -> None:
    config, feature_key = inputs["config"], inputs["feature_fingerprint"]
    log = EventLog(output / "events.jsonl")
    log.emit("run_started", fingerprint=key)
    atomic_json(output / "manifest.json", {"fingerprint": key, "inputs": inputs})
    store = TaskStore(output, key, log, config["heartbeat_seconds"])

    def build(target: Path) -> list[Path]:
        matrix = pd.read_parquet(features / "features.parquet")
        matrix = matrix.loc[
            (matrix.Gender == "M")
            & matrix.Season.between(
                config["first_training_season"], max(config["validation_seasons"])
            )
        ].copy()
        validate_matrix(matrix)
        base = list(dict.fromkeys(KEYS + ["Team1ID", "Team2ID"] + candidate_blocks()["rankings"]))
        matrix = matrix[base]
        rankings = pd.read_csv(raw)
        rankings = rankings.loc[rankings.Season <= max(config["validation_seasons"])].copy()
        systems = system_catalog(rankings, config)
        frames: list[pd.DataFrame] = []
        coverage: list[dict[str, Any]] = []
        for year, group in matrix.groupby("Season"):
            season = int(str(year))
            teams = system_snapshot(rankings, season, systems, config)
            frames.append(add_system_matchups(group, teams))
            coverage.extend(
                {
                    "Season": season,
                    "system": s,
                    "published_teams": int(teams[f"diff_system_{s}_available"].sum()),
                    "matchup_pair_coverage": float(
                        frames[-1][f"diff_system_{s}_level"].notna().mean()
                    ),
                }
                for s in systems
            )
            log.emit("snapshot_completed", season=season, systems=len(systems))
        pd.concat(frames, ignore_index=True).to_parquet(target / "matrix.parquet", index=False)
        pd.DataFrame(coverage).to_csv(target / "coverage.csv", index=False)
        atomic_json(
            target / "catalog.json",
            {
                "systems": systems,
                "families": family_columns(systems),
                "catalog_last_season": config["first_training_season"] - 1,
            },
        )
        return [target / n for n in ["matrix.parquet", "coverage.csv", "catalog.json"]]

    generated = store.task("matrix", build)
    matrix = pd.read_parquet(generated / "matrix.parquet")
    catalog = json.loads((generated / "catalog.json").read_text())
    families = catalog["families"]
    extra_blocks = {
        "strength": [],
        "consensus": [],
        **families,
        "combined": sum(families.values(), []),
        "embedding": families["levels"] + families["deviations"],
    }
    frames, audits, screening = [], [], []
    for model_name in config["models"]:
        original = verified_reference(
            features,
            f"fold_m_{min(config['validation_seasons'])}_rankings_{model_name}",
            feature_key,
        )
        template = joblib.load(original / "model.joblib")["estimator"].model
        for year in sorted(matrix.Season.unique()):
            if year == config["first_training_season"]:
                continue
            train, valid = matrix.loc[matrix.Season < year], matrix.loc[matrix.Season == year]
            for arm in ARMS:
                reference_block = "strength" if arm == "strength" else "rankings"
                base = candidate_blocks()[reference_block]
                extra = extra_blocks[arm]
                old_name = f"fold_m_{year}_{reference_block}_{model_name}"
                inherited = (
                    arm in ["strength", "consensus"]
                    and (features / old_name / "checkpoint.json").exists()
                )

                def fit(
                    target: Path,
                    train: pd.DataFrame = train,
                    valid: pd.DataFrame = valid,
                    base: list[str] = base,
                    extra: list[str] = extra,
                    arm: str = arm,
                    inherited: bool = inherited,
                    old_name: str = old_name,
                    template: Any = template,
                ) -> list[Path]:
                    if inherited:
                        old = verified_reference(features, old_name, feature_key)
                        fold = json.loads((old / "fold.json").read_text())
                        saved = pd.read_parquet(old / "predictions.parquet")
                        if (
                            fold["train_seasons"] != sorted(train.Season.unique().tolist())
                            or fold["requested_features"] != base
                            or not saved[KEYS].equals(valid[KEYS].reset_index(drop=True))
                        ):
                            raise ValueError(
                                "Original ranking control population or schema differs"
                            )
                        for name in [
                            "model.joblib",
                            "predictions.parquet",
                            "screening.csv",
                            "fold.json",
                        ]:
                            shutil.copy2(old / name, target / name)
                    else:
                        with threadpool_limits(limits=config["threads"]):
                            estimator, p = fit_systems(
                                train, valid, base, extra, arm, template, config
                            )
                        valid[KEYS].assign(p=p).to_parquet(
                            target / "predictions.parquet", index=False
                        )
                        joblib.dump(
                            {"estimator": estimator, "features": base + extra},
                            target / "model.joblib",
                        )
                        audit = estimator.base_screen.audit_.copy().assign(
                            feature=base, scope="base"
                        )
                        if extra:
                            additional = estimator.extra_audit.copy().assign(
                                feature=extra, scope="additional"
                            )
                            audit = pd.concat([audit, additional], ignore_index=True)
                        audit.to_csv(target / "screening.csv", index=False)
                        atomic_json(
                            target / "fold.json",
                            {
                                "train_seasons": sorted(train.Season.unique().tolist()),
                                "requested_features": base + extra,
                                "retained_count": estimator.transform(
                                    train[base + extra].to_numpy(float)
                                ).shape[1],
                                "extra_dimensions": estimator.transform(
                                    train[base + extra].to_numpy(float)
                                ).shape[1]
                                - len(estimator.base_screen.indices_),
                                "training_games": len(train),
                            },
                        )
                    atomic_json(target / "origin.json", {"reference_reused": inherited})
                    return [
                        target / n
                        for n in [
                            "model.joblib",
                            "predictions.parquet",
                            "screening.csv",
                            "fold.json",
                            "origin.json",
                        ]
                    ]

                task = store.task(f"{model_name}_{year}_{arm}", fit)
                frames.append(
                    pd.read_parquet(task / "predictions.parquet")[KEYS + ["p"]].assign(
                        model=model_name, block=arm
                    )
                )
                audit = pd.read_csv(task / "screening.csv").assign(
                    model=model_name, block=arm, Season=year
                )
                if "scope" not in audit:
                    audit["scope"] = "base"
                screening.append(audit)
                fold = json.loads((task / "fold.json").read_text())
                audits.append(
                    {
                        "model": model_name,
                        "block": arm,
                        "Season": int(year),
                        "candidate_count": len(base + extra),
                        "retained_count": fold["retained_count"],
                        "extra_dimensions": fold.get("extra_dimensions", 0),
                        "training_games": len(train),
                        "validation_games": len(valid),
                        "reference_reused": inherited,
                    }
                )
    predictions = pd.concat(frames, ignore_index=True)
    predictions.to_csv(output / "predictions.csv", index=False)
    pd.DataFrame(audits).to_csv(output / "fit_audit.csv", index=False)
    screens = pd.concat(screening, ignore_index=True)
    screens.to_csv(output / "screening.csv", index=False)
    screens.groupby(["model", "block", "Season", "scope", "status"]).size().rename(
        "count"
    ).reset_index().to_csv(output / "screening_summary.csv", index=False)
    screens.loc[screens.status.isin(["retained", "embedded"])].groupby(
        ["model", "block", "feature", "status"]
    ).Season.nunique().rename("seasons").reset_index().to_csv(output / "stability.csv", index=False)
    summarize(predictions, config, output)
    for name in ["catalog.json", "coverage.csv"]:
        shutil.copy2(generated / name, output / name)
    atomic_json(
        output / "summary.json",
        {
            "status": "completed",
            "fingerprint": key,
            "feature_fingerprint": feature_key,
            "systems": len(catalog["systems"]),
            "additional_candidates": len(extra_blocks["combined"]),
            "candidate_count_with_consensus": len(candidate_blocks()["rankings"])
            + len(extra_blocks["combined"]),
            "fit_tasks": len(audits),
            "inherited_reference_fits": sum(a["reference_reused"] for a in audits),
            "validation_seasons": config["validation_seasons"],
            "benchmark_labels_used": False,
            "final_recipe_changed": False,
        },
    )
    log.emit(
        "run_completed", fits=len(audits), inherited=sum(a["reference_reused"] for a in audits)
    )


def publish(root: Path, output: Path) -> None:
    destination = root / "reports/ranking_systems"
    destination.mkdir(parents=True, exist_ok=True)
    names = [
        "leaderboard.csv",
        "intervals.csv",
        "metrics_by_season.csv",
        "selection.csv",
        "evaluation.csv",
        "predictions.csv",
        "fit_audit.csv",
        "screening_summary.csv",
        "stability.csv",
        "catalog.json",
        "coverage.csv",
    ]
    for name in names:
        shutil.copy2(output / name, destination / name)
    atomic_json(
        destination / "run.json",
        {
            "summary": json.loads((output / "summary.json").read_text()),
            "manifest": json.loads((output / "manifest.json").read_text()),
            "sha256": {n: digest(destination / n) for n in names},
        },
    )


def review(root: Path) -> tuple[Path, dict[str, Any]]:
    folder, record = evidence(root, "ranking_systems")
    _, parent = evidence(root, "feature_store")
    inputs = record["manifest"]["inputs"]
    if inputs["feature_fingerprint"] != parent["summary"]["fingerprint"] or inputs[
        "config"
    ] != json.loads((root / "configs/ranking_systems.json").read_text()):
        raise ValueError("Stale ranking-system feature lineage or configuration")
    for name, expected in inputs["source"].items():
        if digest(safe_path(root, name)) != expected:
            raise ValueError(f"Stale ranking-system source: {name}")
    return folder, record


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    # Keep persisted predictor classes importable even when invoked with python -m.
    from march_mania.publication.ranking_systems import run as run_study

    print(run_study(Path.cwd()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
