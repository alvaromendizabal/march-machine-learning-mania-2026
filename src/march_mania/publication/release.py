"""Audit the current public research release without fitting models or private data."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any

import nbformat
import numpy as np
import pandas as pd

from march_mania.publication import capacity, ranking_systems, workflow
from march_mania.publication.notebooks import NOTEBOOKS, validate_execution
from march_mania.research_report import probability_metrics
from march_mania.runtime import EventLog, atomic_json, digest

REPORT = "reports/repository_release/repository_release_audit.json"
METRICS = "reports/repository_release/repository_release_audit.csv"
FIGURES = {
    "feature_capacity.png": "Does retaining more candidates improve Brier score?",
    "ranking_systems.png": "Does individual-system information beat the compact consensus?",
}


def audit_metrics(
    predictions: pd.DataFrame,
    scores: pd.DataFrame,
    keys: list[str],
    seasons: list[int],
) -> list[dict[str, Any]]:
    """Recompute every stream; reject population changes and weighted/macro confusion."""
    game_keys = ["Gender", "Season", "ID"]
    required = list(dict.fromkeys([*keys, *game_keys, "DayNum", "y", "p"]))
    if predictions.empty or predictions[required].isna().any().any():
        raise ValueError("Incomplete prediction rows")
    if set(predictions.Season) != set(seasons):
        raise ValueError("Prediction seasons differ from the declared evaluation")
    if predictions.duplicated(list(dict.fromkeys([*keys, *game_keys]))).any():
        raise ValueError("Duplicate physical game within a prediction stream")
    if scores.empty or scores[keys].isna().any().any() or scores.duplicated(keys).any():
        raise ValueError("Incomplete or duplicate metric streams")
    truth = predictions.groupby(game_keys)[["y", "DayNum"]].nunique()
    if truth.gt(1).any().any():
        raise ValueError("Different targets or dates for the same physical game")
    actual_streams = set(predictions[keys].itertuples(index=False, name=None))
    recorded_streams = set(scores[keys].itertuples(index=False, name=None))
    if actual_streams != recorded_streams:
        raise ValueError("Metric and prediction streams differ")
    universe = {
        gender: set(group[game_keys].itertuples(index=False, name=None))
        for gender, group in predictions.groupby("Gender")
    }
    mean_name = "mean_season_brier" if "mean_season_brier" in scores else "macro_season_brier"
    output = []
    for values, group in predictions.groupby(keys, sort=True):
        row = scores.loc[(scores[keys] == pd.Series(values, index=keys)).all(axis=1)].iloc[0]
        for gender, population in group.groupby("Gender"):
            if set(population[game_keys].itertuples(index=False, name=None)) != universe[gender]:
                raise ValueError("Prediction streams use different physical games")
        metrics = probability_metrics(group.y.to_numpy(), group.p.to_numpy())
        loss = (group.p - group.y).pow(2)
        metrics["brier"] = float(loss.mean())
        metrics[mean_name] = float(loss.groupby(group.Season).mean().mean())
        if int(row.games) != len(group):
            raise ValueError("Metric game count differs from saved predictions")
        for name, expected in metrics.items():
            if name not in row:
                raise ValueError(f"Missing recorded metric: {name}")
            if expected is None:
                if not pd.isna(row[name]):
                    raise ValueError(f"Undefined metric was reported: {name}")
            elif not np.isclose(float(row[name]), expected, rtol=0, atol=1e-12):
                raise ValueError(f"Recorded {name} differs from recomputed predictions")
        output.append(
            {
                **dict(zip(keys, values, strict=True)),
                "games": len(group),
                "mean_season_brier": metrics.pop(mean_name),
                **metrics,
            }
        )
    return output


def notebook_figures(root: Path) -> dict[str, bytes]:
    notebook = nbformat.read(root / "notebooks" / NOTEBOOKS[2], as_version=4)
    result = {}
    for cell in notebook.cells:
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            title = (
                data.get("application/vnd.plotly.v1+json", {})
                .get("layout", {})
                .get("title", {})
                .get("text")
            )
            for name, expected in FIGURES.items():
                if title == expected:
                    if name in result:
                        raise ValueError("Ambiguous notebook figure title")
                    result[name] = base64.b64decode(data["image/png"], validate=True)
    if set(result) != set(FIGURES):
        raise ValueError("Missing published Plotly figure and PNG fallback")
    return result


def cloud_receipt(root: Path, records: dict[str, Any]) -> dict[str, Any]:
    """Check the recorded AWS observation; this offline audit makes no live API claim."""
    receipt = json.loads((root / "reports/repository_release/cloud_verification.json").read_text())
    validation = root / "reports/validation"
    archives = {
        name: records[name]["archive"]
        for name in ("feature_store", "model_comparison", "benchmark")
    }
    for name, filename in (
        ("feature_capacity", "capacity"),
        ("ranking_systems", "ranking_systems"),
    ):
        archives[name] = json.loads((validation / f"{filename}.json").read_text())["archive"]
    archives["ranking_validation"] = json.loads((validation / "ranking_systems.json").read_text())[
        "native_validation"
    ]["archive"]
    rows = receipt["objects"]
    if len(rows) != len(archives) or {row["name"] for row in rows} != set(archives):
        raise ValueError("Cloud receipt is missing an archive")
    for row in rows:
        archive = archives[row["name"]]
        if (row["uri"], row["ContentLength"], row["VersionId"]) != (
            archive["uri"],
            archive["bytes"],
            archive["version_id"],
        ):
            raise ValueError("Cloud archive version or size differs")
        if row.get("ChecksumType") == "FULL_OBJECT" and row.get("ChecksumSHA256"):
            actual = base64.b64decode(row["ChecksumSHA256"], validate=True).hex()
        else:
            download = row["download_verification"]
            if (download["bytes"], download["version_id"]) != (
                archive["bytes"],
                archive["version_id"],
            ):
                raise ValueError("Download verification used a different object")
            actual = download["sha256"]
        if actual != archive["sha256"]:
            raise ValueError("Cloud archive SHA-256 differs")
    return {
        "checked_at": receipt["checked_at"],
        "archives_verified": len(rows),
        "scope": "Recorded live AWS observation; no cloud API call by this offline audit",
    }


def audit(root: Path) -> tuple[dict[str, Any], pd.DataFrame]:
    """Fail closed on stale sources, lineage, reports, figures, or notebook publication."""
    workflow.lineage(root)
    records = {
        name: workflow.evidence(root, name)[1] for name in ("feature_store", "model_comparison")
    }
    records["feature_capacity"] = capacity.review(root)[1]
    records["ranking_systems"] = ranking_systems.review(root)[1]
    records["benchmark"] = workflow.benchmark_evidence(root)[1]
    features = records["feature_store"]["summary"]
    feature_dir = root / "reports/feature_store"
    registry = pd.read_csv(feature_dir / "feature_registry.csv")
    screening = pd.read_csv(feature_dir / "screening_summary.csv")
    usage = pd.read_csv(feature_dir / "feature_usage.csv")
    if registry.feature.duplicated().any() or len(registry) != features["feature_count"]:
        raise ValueError("Candidate registry count differs from the research run")
    reasons = ["capacity", "near_constant", "no_training_signal", "redundant"]
    if not (
        (screening[reasons].sum(axis=1) == screening.rejected_count).all()
        and (screening.retained == screening.retained_count).all()
        and (screening.retained_count + screening.rejected_count == screening.candidate_count).all()
        and int(screening.candidate_count.sum()) == features["screening_decisions"]
        and int(screening.rejected_count.sum()) == features["rejected_decisions"]
    ):
        raise ValueError("Screening counts or rejection reasons do not reconcile")
    full = screening.loc[screening.block.eq("full")]
    retained_keys = ["Gender", "Season", "block", "model"]
    counts = usage.groupby(retained_keys).size().rename("actual").reset_index()
    paired = full.merge(counts, on=retained_keys, validate="one_to_one")
    if (
        len(paired) != len(full)
        or len(paired) != len(counts)
        or not (paired.actual == paired.retained_count).all()
        or usage.duplicated([*retained_keys, "feature"]).any()
    ):
        raise ValueError("Retained feature audit differs from screening decisions")
    ranking = records["ranking_systems"]["summary"]
    rank_dir = root / "reports/ranking_systems"
    catalog = json.loads((rank_dir / "catalog.json").read_text())
    additions = {feature for family in catalog["families"].values() for feature in family}
    if len(additions) != ranking["additional_candidates"]:
        raise ValueError("Ranking candidate catalog count differs")
    metric_rows: list[dict[str, Any]] = []
    for stage, filename, keys in (
        ("model_comparison", "predictions.csv", ["Gender", "block", "model"]),
        ("feature_capacity", "evaluation.csv", ["route", "model", "block"]),
        ("ranking_systems", "evaluation.csv", ["model", "block"]),
        ("benchmark", "benchmark_predictions.csv", ["Gender", "route"]),
    ):
        folder = root / "reports" / stage
        record = records[stage]
        summary = record["summary"]
        seasons = summary.get("validation_seasons", summary.get("benchmark_seasons"))
        score_file = "metrics.csv" if stage == "benchmark" else "leaderboard.csv"
        rows = audit_metrics(
            pd.read_csv(folder / filename), pd.read_csv(folder / score_file), keys, seasons
        )
        metric_rows.extend({"stage": stage, **row} for row in rows)
    native = json.loads((root / "reports/validation/ranking_systems.json").read_text())
    notebooks = {}
    for name in NOTEBOOKS:
        path = root / "notebooks" / name
        notebook = nbformat.read(path, as_version=4)
        validate_execution(notebook)
        expected = native["notebooks"][name]
        cells = sum(c.cell_type == "code" and bool(c.source.strip()) for c in notebook.cells)
        if digest(path) != expected["sha256"] or cells != expected["executed_code_cells"]:
            raise ValueError(f"Notebook differs from native publication receipt: {name}")
        notebooks[name] = expected
    figures = {}
    for name, data in notebook_figures(root).items():
        path = root / "reports/figures" / name
        expected_hash = hashlib.sha256(data).hexdigest()
        if digest(path) != expected_hash:
            raise ValueError(f"README figure differs from published notebook: {name}")
        figures[name] = expected_hash
    result = {
        "status": "passed",
        "scope": "Current public retrospective research; no new fits or Kaggle upload",
        "feature_search": {
            "status": "bounded_official_data_search_complete",
            "main_candidates": len(registry),
            "ranking_additions": ranking["additional_candidates"],
            "explored_definitions": len(registry) + ranking["additional_candidates"],
            "main_ablation_fits": features["fold_tasks"],
            "full_bank_retained_per_fit_min": int(full.retained_count.min()),
            "full_bank_retained_per_fit_max": int(full.retained_count.max()),
            "full_bank_unique_retained_across_fits": int(usage.feature.nunique()),
            "full_bank_never_retained": len(registry) - int(usage.feature.nunique()),
            "screening_decisions": int(screening.candidate_count.sum()),
            "retained_decisions": int(screening.retained_count.sum()),
            "rejected_decisions": int(screening.rejected_count.sum()),
            "rejection_reasons": {name: int(screening[name].sum()) for name in reasons},
            "selection_unit": "Temporal training fit; counts across fits are not a global set",
        },
        "runs": {
            name: {
                "fingerprint": record["summary"]["fingerprint"],
                "run_record_sha256": digest(root / "reports" / name / "run.json"),
                "public_files_verified": len(record["sha256"]),
            }
            for name, record in records.items()
        },
        "metrics": {
            "streams_recomputed": len(metric_rows),
            "absolute_tolerance": 1e-12,
            "metrics": "Brier (both averages), log loss, AUC, AP, F1, precision, recall, ECE",
        },
        "notebooks": notebooks,
        "figures": figures,
        "cloud": cloud_receipt(root, records),
        "limitations": [
            "Development seasons and the 2022-2025 benchmark were previously consumed.",
            "The broader bank has not demonstrated consistent improvement over compact anchors.",
            "Local scoring includes play-ins and differs from the Kaggle scored population.",
            "Historical 124-feature final predictions retain their separate release identity.",
            "Player availability, returning production and women's coach/rating parity "
            "lack verified source histories.",
        ],
        "highest_value_next_action": (
            "Freeze the protocol before adding timestamped independent inputs "
            "or evaluating a future tournament."
        ),
    }
    return result, pd.DataFrame(metric_rows).fillna("")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--write", action="store_true", help="Refresh the canonical public audit and figure exports"
    )
    mode.add_argument(
        "--check", action="store_true", help="Require the saved audit to match recomputed evidence"
    )
    args = parser.parse_args()
    root = Path.cwd()
    log = EventLog(root / "outputs/validation/release.jsonl")
    log.emit("release_audit_started")
    if args.write:
        for name, data in notebook_figures(root).items():
            path = root / "reports/figures" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    try:
        report, metrics = audit(root)
        csv = metrics.to_csv(index=False, lineterminator="\n")
        if args.write:
            atomic_json(root / REPORT, report)
            (root / METRICS).write_text(csv)
        elif (
            json.loads((root / REPORT).read_text()) != report or (root / METRICS).read_text() != csv
        ):
            raise ValueError(
                "Published release audit is stale; regenerate with --write after verifying changes"
            )
    except Exception as error:
        log.emit("release_audit_failed", error=str(error))
        raise
    log.emit(
        "release_audit_passed",
        streams=report["metrics"]["streams_recomputed"],
        notebooks=len(NOTEBOOKS),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
