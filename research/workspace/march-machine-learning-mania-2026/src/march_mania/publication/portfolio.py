"""Audit 50 development candidate plans from completed, current-lineage predictions.

This inexpensive release does not fit models, freeze final hyperparameters, read
2026 labels, generate submission CSVs, or contact Kaggle. Historical nested scores
describe selection procedures, not the performance of a newly frozen estimator.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from march_mania.modeling import candidates
from march_mania.publication import inference, workflow
from march_mania.publication.artifacts import verified_write
from march_mania.research_report import probability_metrics
from march_mania.runtime import EventLog, digest, fingerprint

CONFIG = "configs/prediction_portfolio.json"
REPORT = "reports/prediction_portfolio"
KEYS = ["Gender", "Season", "DayNum", "ID", "y"]


def validate_config(config: dict[str, Any]) -> None:
    if (
        config["protocol"] != "retrospective-development-portfolio"
        or config["development_seasons"] != [2016, 2017, 2018, 2019, 2021]
        or config["prediction_season"] != 2026
        or type(config["target_candidates"]) is not int
        or config["target_candidates"] != 50
        or config["calibration"] != "identity"
    ):
        raise ValueError("Use the recorded retrospective development portfolio contract")
    if set(config["streams"]) != {"M", "W"} or set(config["reference"]) != {"M", "W"}:
        raise ValueError("Both tournament populations are required")
    identifiers = []
    for gender, count in (("M", 10), ("W", 5)):
        streams = config["streams"][gender]
        if len(streams) != count:
            raise ValueError("The declared portfolio contains ten men's and five women's streams")
        identities = set()
        for stream in streams:
            route, family = stream["route"], stream["family"]
            if route not in {gender, "pooled_common"}:
                raise ValueError("Invalid training population")
            if family not in ({c.family for c in candidates(route)} - {"seed"}) | {"blend"}:
                raise ValueError("Use a previously evaluated model family")
            if not re.fullmatch(gender.lower() + r"_[a-z_]+", stream["id"]):
                raise ValueError("Unsafe or ambiguous stream identifier")
            identifiers.append(stream["id"])
            identities.add((route, family))
        if len(identities) != count:
            raise ValueError("Duplicate modeling procedures do not make distinct candidates")
        if config["reference"][gender] not in {s["id"] for s in streams}:
            raise ValueError("Missing reference stream")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate stream identifiers")
    for gender, family in (("M", "rank_logistic"), ("W", "logistic")):
        reference = next(
            s for s in config["streams"][gender] if s["id"] == config["reference"][gender]
        )
        if (reference["route"], reference["family"]) != (gender, family):
            raise ValueError("Keep the existing separate logistic reference procedures")


def aligned_streams(
    predictions: pd.DataFrame,
    selection: pd.DataFrame,
    weights: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Align physical games and verify that every choice used only earlier seasons."""
    validate_config(config)
    required = [*KEYS, "model", "block", "p"]
    if predictions.empty or predictions[required].isna().any().any():
        raise ValueError("Missing development prediction values")
    if set(predictions.Season) != set(config["development_seasons"]):
        raise ValueError("Only the five recorded development seasons may enter this catalog")
    if predictions.duplicated(["Gender", "Season", "ID", "model", "block"]).any():
        raise ValueError("Duplicate physical game within a prediction stream")
    truth = predictions.groupby(["Gender", "Season", "ID"])[["y", "DayNum"]].nunique()
    if truth.gt(1).any().any():
        raise ValueError("Conflicting physical-game labels or dates")
    unique_games = predictions[KEYS].drop_duplicates().sort_values(["Gender", "Season", "ID"])
    inference.validate_games(unique_games, 2021)
    if set(unique_games.Gender) != {"M", "W"}:
        raise ValueError("Both tournament populations are required")
    if not np.isfinite(predictions.p).all() or not predictions.p.between(0, 1).all():
        raise ValueError("Invalid development probabilities")
    streams, audits = {}, []
    for gender, specifications in config["streams"].items():
        reference = unique_games.loc[unique_games.Gender == gender].reset_index(drop=True)
        if set(reference.Season) != set(config["development_seasons"]):
            raise ValueError("Incomplete tournament seasons")
        for specification in specifications:
            name, route, family = (specification[k] for k in ("id", "route", "family"))
            rows = (
                predictions.loc[
                    (predictions.Gender == gender)
                    & (predictions.block == route)
                    & (predictions.model == ("blend" if family == "blend" else family + "_raw")),
                    [*KEYS, "p"],
                ]
                .sort_values(["Season", "ID"])
                .reset_index(drop=True)
            )
            if not rows[KEYS].equals(reference):
                raise ValueError("Candidate streams must cover identical physical games")
            families = (
                sorted({c.family for c in candidates(route) if not c.family.startswith("rank_")})
                if family == "blend"
                else [family]
            )
            for component in families:
                chosen = selection.loc[
                    (selection.Gender == gender)
                    & (selection.route == route)
                    & (selection.family == component)
                ].sort_values("Season")
                if chosen.Season.tolist() != config["development_seasons"]:
                    raise ValueError("Missing or duplicate earlier-season selection records")
                allowed = {c.name for c in candidates(route) if c.family == component}
                for row in chosen.itertuples(index=False):
                    earlier = [
                        s for s in (2014, 2015, *config["development_seasons"]) if s < row.Season
                    ]
                    if (
                        row.candidate not in allowed
                        or row.history_last_season != max(earlier)
                        or row.history_seasons != len(earlier)
                    ):
                        raise ValueError(
                            "Selection history crosses a season boundary or is incomplete"
                        )
                    audits.append(
                        {
                            "stream": name,
                            "Gender": gender,
                            "route": route,
                            "family": component,
                            "Season": int(row.Season),
                            "candidate": row.candidate,
                            "history_last_season": int(row.history_last_season),
                            "history_seasons": int(row.history_seasons),
                            "applied_calibration": "identity",
                        }
                    )
            if family == "blend":
                verify_blend(predictions, weights, rows, gender, route, families)
            streams[name] = rows
    return streams, pd.DataFrame(audits)


def verify_blend(
    predictions: pd.DataFrame,
    weights: pd.DataFrame,
    rows: pd.DataFrame,
    gender: str,
    route: str,
    families: list[str],
) -> None:
    """Reconstruct the saved blend using its raw components and recorded weights."""
    for season, expected in rows.groupby("Season"):
        chosen = weights.loc[
            (weights.Gender == gender) & (weights.route == route) & (weights.Season == season)
        ].sort_values("family")
        if (
            chosen.family.tolist() != families
            or not np.isfinite(chosen.weight).all()
            or not chosen.weight.between(0, 1).all()
            or not np.isclose(chosen.weight.sum(), 1, rtol=0, atol=1e-10)
        ):
            raise ValueError("Incomplete or invalid convex blend weights")
        reconstructed = np.zeros(len(expected))
        for component in chosen.to_dict("records"):
            part = predictions.loc[
                (predictions.Gender == gender)
                & (predictions.block == route)
                & (predictions.Season == season)
                & (predictions.model == str(component["family"]) + "_raw")
            ].sort_values("ID")
            if not part[KEYS].reset_index(drop=True).equals(expected[KEYS].reset_index(drop=True)):
                raise ValueError("Blend components cover different physical games")
            reconstructed += part.p.to_numpy(dtype=float) * float(component["weight"])
        if not np.allclose(reconstructed, expected.p.to_numpy(), rtol=0, atol=1e-12):
            raise ValueError("Saved blend differs from its recorded raw components and weights")


def metrics(rows: pd.DataFrame) -> dict[str, Any]:
    return {
        "games": len(rows),
        **probability_metrics(rows.y.to_numpy(), rows.p.to_numpy()),
        "mean_season_brier": float((rows.p - rows.y).pow(2).groupby(rows.Season).mean().mean()),
    }


def catalog(
    predictions: pd.DataFrame,
    selection: pd.DataFrame,
    weights: pd.DataFrame,
    config: dict[str, Any],
) -> dict[str, pd.DataFrame]:
    streams, choices = aligned_streams(predictions, selection, weights, config)
    reference = pd.concat([streams[config["reference"][g]] for g in ("M", "W")])
    reference_p = reference.p.to_numpy()
    stream_metrics = {name: metrics(rows) for name, rows in streams.items()}
    records, annual, vectors = [], [], {}
    for men, women in itertools.product(config["streams"]["M"], config["streams"]["W"]):
        name = men["id"] + "__" + women["id"]
        rows = pd.concat([streams[men["id"]], streams[women["id"]]])
        values = rows.p.to_numpy()
        vectors[name] = values
        records.append(
            {
                "candidate_id": name,
                "men_stream": men["id"],
                "women_stream": women["id"],
                "is_reference": all(
                    s["id"] == config["reference"][g] for g, s in (("M", men), ("W", women))
                ),
                **metrics(rows),
                "men_brier": stream_metrics[men["id"]]["brier"],
                "men_mean_season_brier": stream_metrics[men["id"]]["mean_season_brier"],
                "women_brier": stream_metrics[women["id"]]["brier"],
                "women_mean_season_brier": stream_metrics[women["id"]]["mean_season_brier"],
                "mean_absolute_difference_from_reference": float(
                    np.abs(values - reference_p).mean()
                ),
                "development_vector_sha256": hashlib.sha256(
                    values.astype("<f8").tobytes()
                ).hexdigest(),
                "status": "development_candidate_plan",
            }
        )
        for season, group in rows.groupby("Season"):
            annual.append({"candidate_id": name, "Season": int(str(season)), **metrics(group)})
    candidates_frame = pd.DataFrame(records)
    if (
        len(candidates_frame) != config["target_candidates"]
        or candidates_frame.development_vector_sha256.duplicated().any()
    ):
        raise ValueError("Fifty distinct development prediction vectors are required")
    diversity = []
    for left, right in itertools.combinations(vectors, 2):
        delta = np.abs(vectors[left] - vectors[right])
        diversity.append(
            {
                "candidate_a": left,
                "candidate_b": right,
                "mean_absolute_difference": float(delta.mean()),
                "max_absolute_difference": float(delta.max()),
            }
        )
    return {
        "candidate_catalog.csv": candidates_frame,
        "metrics_by_season.csv": pd.DataFrame(annual),
        "selection_history.csv": choices,
        "prediction_diversity.csv": pd.DataFrame(diversity),
    }


def publication(root: Path) -> dict[str, bytes]:
    """Rebuild compact evidence entirely from committed, checksum-verified research."""
    workflow.lineage(root)
    folder, record = workflow.evidence(root, "model_comparison")
    config = json.loads((root / CONFIG).read_text())
    frames = catalog(
        pd.read_csv(folder / "predictions.csv"),
        pd.read_csv(folder / "selection.csv"),
        pd.read_csv(folder / "ensemble_weights.csv"),
        config,
    )
    files = {
        name: frame.to_csv(index=False, lineterminator="\n").encode()
        for name, frame in frames.items()
    }
    inputs = {
        "config": config,
        "feature_fingerprint": record["manifest"]["inputs"]["feature_fingerprint"],
        "model_fingerprint": record["summary"]["fingerprint"],
        "evidence": {
            name: digest(folder / name)
            for name in ("predictions.csv", "selection.csv", "ensemble_weights.csv", "run.json")
        },
        "source": {
            "src/march_mania/publication/portfolio.py": digest(
                root / "src/march_mania/publication/portfolio.py"
            )
        },
    }
    summary = {
        "status": "development_catalog_complete",
        "fingerprint": fingerprint(inputs),
        "inputs": inputs,
        "candidate_plans": len(frames["candidate_catalog.csv"]),
        "distinct_development_vectors": int(
            frames["candidate_catalog.csv"].development_vector_sha256.nunique()
        ),
        "component_streams": len(frames["selection_history.csv"].stream.unique()),
        "selection_records": len(frames["selection_history.csv"]),
        "physical_development_games_per_candidate": int(
            frames["candidate_catalog.csv"].games.iloc[0]
        ),
        "minimum_pairwise_mean_absolute_difference": float(
            frames["prediction_diversity.csv"].mean_absolute_difference.min()
        ),
        "reference_candidate": config["reference"]["M"] + "__" + config["reference"]["W"],
        "score_scope": (
            "Nested earlier-season selection procedures on already-explored development years; "
            "not final-estimator validation or an untouched holdout"
        ),
        "portfolio_scope": (
            "Retrospective family/population pairings; correlated sensitivity candidates, "
            "not 50 independent experiments or a promoted winner"
        ),
        "generation_status": "not_started",
        "final_hyperparameters_frozen": False,
        "submission_files_generated": 0,
        "new_model_fits": 0,
        "benchmark_or_2026_labels_used": False,
        "kaggle_submission_sent": False,
        "sha256": {name: hashlib.sha256(content).hexdigest() for name, content in files.items()},
    }
    files["manifest.json"] = (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode()
    return files


def check(root: Path, files: dict[str, bytes]) -> None:
    for name, expected in files.items():
        path = root / REPORT / name
        if not path.is_file() or path.read_bytes() != expected:
            raise ValueError(f"Changed or missing portfolio evidence: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    log = EventLog(root / "outputs/validation/portfolio.jsonl")
    log.emit("catalog_started", mode="write" if args.write else "check")
    try:
        files = publication(root)
        if args.write:
            for name, content in files.items():
                verified_write(root / REPORT / name, content, hashlib.sha256(content).hexdigest())
        check(root, files)
        log.emit("catalog_completed", candidates=50, submission_files=0, new_model_fits=0)
    except BaseException as error:
        log.emit("catalog_failed", error_type=type(error).__name__, error=str(error))
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
