"""Record observed Kaggle scores and audit a bounded post-result sensitivity round.

The 2026 scores informed the hypotheses. Historical checks remain retrospective;
they cannot undo that exposure. The original frozen production recipe is retained.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.special import expit, logit

from march_mania.publication import portfolio, workflow
from march_mania.publication.artifacts import verified_write
from march_mania.publication.submission import validate_submission
from march_mania.runtime import EventLog, TaskStore, atomic_json, digest, fingerprint

CONFIG = "configs/prediction_refinement.json"
REPORT = "reports/prediction_refinement"
SCORES = "reports/prediction_production/kaggle_scores.csv"
ANCHOR = "m_pooled_xgboost"
WOMEN = "w_logistic"
PARTNERS = {"m_rank_logistic", "m_pooled_hist"}
SCOPE = (
    "Post-result exploratory adjustments motivated by observed 2026 Kaggle scores. "
    "Historical selection procedures cover already-explored 2016-2019 and 2021; "
    "they are not validation of the final fitted estimators or an untouched holdout."
)


def validate_config(config: dict[str, Any]) -> None:
    if (
        config["protocol"] != "post-result-exploratory-refinement"
        or config["anchor"] != ANCHOR
        or config["women_stream"] != WOMEN
        or config["development_seasons"] != [2016, 2017, 2018, 2019, 2021]
        or config["2026_results_informed_hypotheses"] is not True
        or config["fresh_holdout"] is not False
        or config["new_model_fits"] != 0
        or re.fullmatch(r"[0-9a-f]{64}", config["source_archive_sha256"]) is None
        or len(config["variants"]) != 8
    ):
        raise ValueError("Preserve the bounded post-result refinement contract")
    names, definitions = set(), set()
    for variant in config["variants"]:
        name, kind = variant["candidate_id"], variant["kind"]
        if re.fullmatch(r"m_[a-z0-9_]+__w_logistic", name) is None or name in names:
            raise ValueError("Variant names must be unique and safe")
        weight, temperature, partner = (
            variant[k] for k in ("anchor_weight", "temperature", "partner")
        )
        if kind == "blend":
            if weight not in {0.25, 0.5, 0.75} or temperature != 1 or partner not in PARTNERS:
                raise ValueError("Use the three fixed convex weights and recorded partners")
        elif kind == "temperature":
            if weight != 1 or temperature not in {0.9, 1.1} or partner is not None:
                raise ValueError("Use the two fixed confidence adjustments")
        else:
            raise ValueError("Unknown adjustment")
        definition = (kind, weight, temperature, partner)
        if definition in definitions:
            raise ValueError("Duplicate transformations do not make distinct variants")
        definitions.add(definition)
        names.add(name)


def transform(anchor: np.ndarray, partner: np.ndarray, variant: dict[str, Any]) -> np.ndarray:
    """Convex mixtures and temperature scaling preserve probability complementarity."""
    for values in (anchor, partner):
        if not np.isfinite(values).all() or not ((values >= 0) & (values <= 1)).all():
            raise ValueError("Invalid component probability")
    if anchor.shape != partner.shape:
        raise ValueError("Component arrays must be aligned")
    if variant["kind"] == "blend":
        weight = variant["anchor_weight"]
        if not 0 <= weight <= 1:
            raise ValueError("Blend weights must be convex")
        return weight * anchor + (1 - weight) * partner
    if variant["kind"] != "temperature" or not np.isfinite(variant["temperature"]):
        raise ValueError("Invalid transformation")
    if variant["temperature"] <= 0:
        raise ValueError("Temperature must be positive")
    return expit(logit(anchor) / variant["temperature"])


def score_table(root: Path) -> pd.DataFrame:
    """Bind each screenshot score to exactly one completed production CSV checksum."""
    provenance = json.loads((root / SCORES).with_suffix(".json").read_text())
    if digest(root / SCORES) != provenance["scores_sha256"]:
        raise ValueError("Score transcription changed without a provenance update")
    scores = pd.read_csv(root / SCORES)
    manifest = pd.read_csv(root / "reports/prediction_production/submission_manifest.csv")
    production = json.loads((root / "reports/prediction_production/summary.json").read_text())
    if provenance["production_fingerprint"] != production["fingerprint"]:
        raise ValueError("Scores belong to a different production lineage")
    if (
        len(scores) != 50
        or scores.isna().any().any()
        or scores.candidate_id.duplicated().any()
        or manifest.candidate_id.duplicated().any()
        or set(scores.candidate_id) != set(manifest.candidate_id)
        or not set(scores.source_image).issubset(provenance["sources"])
        or not np.isfinite(scores[["private_brier", "public_brier"]]).all().all()
        or not scores.private_brier.between(0, 1).all()
        or not scores.public_brier.between(0, 1).all()
        or not scores.private_brier.equals(scores.public_brier)
    ):
        raise ValueError("Scores must match all fifty complete screenshot observations")
    result = scores.merge(manifest, on="candidate_id", validate="one_to_one")
    result["filename"] = result.candidate_id + ".csv"
    result["men_stream"] = result.candidate_id.str.split("__").str[0]
    result["women_stream"] = result.candidate_id.str.split("__").str[1]
    result["status"] = "Complete (after deadline)"
    result["recorded_at_utc"] = provenance["recorded_at_utc"]
    return result.sort_values(["private_brier", "candidate_id"]).reset_index(drop=True)


def historical(root: Path, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate adjustments on aligned, earlier-season-selected prediction streams."""
    validate_config(config)
    workflow.lineage(root)
    folder, _ = workflow.evidence(root, "model_comparison")
    streams, _ = portfolio.aligned_streams(
        pd.read_csv(folder / "predictions.csv"),
        pd.read_csv(folder / "selection.csv"),
        pd.read_csv(folder / "ensemble_weights.csv"),
        json.loads((root / portfolio.CONFIG).read_text()),
    )
    anchor, women = streams[ANCHOR], streams[WOMEN]
    baseline = pd.concat([anchor, women])
    baseline_brier = portfolio.metrics(baseline)["brier"]
    baseline_seasons = (baseline.p - baseline.y).pow(2).groupby(baseline.Season).mean()
    procedures = [(s + "__" + WOMEN, streams[s]) for s in [ANCHOR, *sorted(PARTNERS)]]
    for variant in config["variants"]:
        partner = streams[variant["partner"]] if variant["partner"] else anchor
        if not anchor[portfolio.KEYS].equals(partner[portfolio.KEYS]):
            raise ValueError("Historical component games differ")
        probabilities = transform(anchor.p.to_numpy(), partner.p.to_numpy(), variant)
        procedures.append((variant["candidate_id"], anchor.assign(p=probabilities)))
    catalog, annual = [], []
    for name, men in procedures:
        frame = pd.concat([men, women])
        metrics = portfolio.metrics(frame)
        season_brier = (frame.p - frame.y).pow(2).groupby(frame.Season).mean()
        deltas = season_brier - baseline_seasons
        catalog.append(
            {
                "candidate_id": name,
                "is_new_adjustment": name in {v["candidate_id"] for v in config["variants"]},
                **metrics,
                "men_brier": portfolio.metrics(men)["brier"],
                "women_brier": portfolio.metrics(women)["brier"],
                "brier_delta_vs_anchor": metrics["brier"] - baseline_brier,
                "improved_seasons": int((deltas < -1e-12).sum()),
                "worst_season_delta": float(deltas.max()),
                "historical_prediction_sha256": hashlib.sha256(
                    frame.p.to_numpy(dtype="<f8").tobytes()
                ).hexdigest(),
            }
        )
        for season, group in frame.groupby("Season"):
            annual.append(
                {
                    "candidate_id": name,
                    "Season": int(str(season)),
                    **portfolio.metrics(group),
                    "brier_delta_vs_anchor": float(deltas.loc[season]),
                }
            )
    return (
        pd.DataFrame(catalog).sort_values(["brier", "candidate_id"]).reset_index(drop=True),
        pd.DataFrame(annual),
    )


def review(root: Path, *, write: bool = False) -> dict[str, Any]:
    config = json.loads((root / CONFIG).read_text())
    scores = score_table(root)
    catalog, annual = historical(root, config)
    tables = {
        "observed_scores.csv": scores,
        "historical_catalog.csv": catalog,
        "metrics_by_season.csv": annual,
    }
    payloads = {
        name: frame.to_csv(index=False, lineterminator="\n").encode()
        for name, frame in tables.items()
    }
    anchor_score = scores.loc[scores.candidate_id.eq(ANCHOR + "__" + WOMEN)].iloc[0]
    reference = scores.loc[scores.candidate_id.eq("m_rank_logistic__w_logistic")].iloc[0]
    summary = {
        "status": "historical_checks_complete",
        "scope": SCOPE,
        "observed_submissions": len(scores),
        "best_observed_candidate": str(scores.iloc[0].candidate_id),
        "best_observed_brier": float(scores.iloc[0].private_brier),
        "reference_observed_brier": float(reference.private_brier),
        "observed_anchor_improvement": float(reference.private_brier - anchor_score.private_brier),
        "women_logistic_best_for_all_men_streams": bool(
            scores.loc[scores.groupby("men_stream").private_brier.idxmin()]
            .women_stream.eq(WOMEN)
            .all()
        ),
        "new_adjustments": len(config["variants"]),
        "historical_games_per_candidate": int(catalog.games.iloc[0]),
        "new_model_fits": 0,
        "original_production_recipe_changed": False,
        "historically_best_new_adjustment": str(
            catalog.loc[catalog.is_new_adjustment].iloc[0].candidate_id
        ),
        "inputs": {
            name: digest(root / name)
            for name in [
                CONFIG,
                SCORES,
                str(Path(SCORES).with_suffix(".json")),
                "src/march_mania/publication/refinement.py",
                "reports/prediction_portfolio/manifest.json",
                "reports/prediction_production/submission_manifest.csv",
            ]
        },
        "sha256": {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()},
    }
    payloads["summary.json"] = (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode()
    for name, data in payloads.items():
        path = root / REPORT / name
        if write:
            verified_write(path, data, hashlib.sha256(data).hexdigest())
        elif not path.is_file() or path.read_bytes() != data:
            raise ValueError(f"Stale refinement evidence: {name}")
    return summary


def generate(root: Path, archive: Path) -> dict[str, Any]:
    """Create eight named CSVs from verified saved predictions with zero new fits."""
    summary = review(root)
    config = json.loads((root / CONFIG).read_text())
    if digest(archive) != config["source_archive_sha256"]:
        raise ValueError("Source ZIP differs from the frozen production download")
    hashes = (
        pd.read_csv(root / "reports/prediction_production/submission_manifest.csv")
        .set_index("candidate_id")
        .sha256.to_dict()
    )
    frames, contents = {}, {}
    with zipfile.ZipFile(archive) as source:
        if len(source.namelist()) != len(set(source.namelist())):
            raise ValueError("Duplicate members in source archive")
        for stream in [ANCHOR, *sorted(PARTNERS)]:
            name = stream + "__" + WOMEN
            data = source.read(name + ".csv")
            if hashlib.sha256(data).hexdigest() != hashes[name]:
                raise ValueError("Source prediction differs from its production manifest")
            contents[stream] = data
            frames[stream] = pd.read_csv(io.BytesIO(data), float_precision="round_trip")
    baseline = frames[ANCHOR]
    for frame in frames.values():
        validate_submission(frame, baseline)
    men = baseline.ID.str.fullmatch(r"2026_1\d{3}_1\d{3}").to_numpy()
    women = baseline.ID.str.fullmatch(r"2026_3\d{3}_3\d{3}").to_numpy()
    if not (men | women).all() or not men.any() or not women.any():
        raise ValueError("Unknown or missing tournament population")
    if any(
        not np.array_equal(f.Pred.to_numpy()[women], baseline.Pred.to_numpy()[women])
        for f in frames.values()
    ):
        raise ValueError("Women must share the same frozen logistic predictions")
    inputs = {"config": config, "research": summary["inputs"], "source_sha256": digest(archive)}
    production_fingerprint = json.loads((root / SCORES).with_suffix(".json").read_text())[
        "production_fingerprint"
    ]
    key = fingerprint(inputs)
    run = root / "outputs/prediction_refinement" / key
    log = EventLog(run / "events.jsonl")
    store = TaskStore(run, key, log, heartbeat_seconds=15)
    original_lines = contents[ANCHOR].decode().splitlines(keepends=True)

    def work(target: Path) -> list[Path]:
        rows, paths = [], []
        for variant in config["variants"]:
            partner = frames[variant["partner"]] if variant["partner"] else baseline
            probabilities = baseline.Pred.to_numpy().copy()
            probabilities[men] = transform(
                probabilities[men], partner.Pred.to_numpy()[men], variant
            )
            lines = [original_lines[0]]
            for i, identifier in enumerate(baseline.ID):
                lines.append(
                    f"{identifier},{probabilities[i]:.17g}\n" if men[i] else original_lines[i + 1]
                )
            output = target / (variant["candidate_id"] + ".csv")
            output.write_text("".join(lines), encoding="utf-8", newline="")
            observed = pd.read_csv(output, float_precision="round_trip")
            validate_submission(observed, baseline)
            if not np.array_equal(observed.Pred.to_numpy(), probabilities):
                raise ValueError("Serialized probabilities differ from the defined transformation")
            rows.append(
                {
                    "candidate_id": variant["candidate_id"],
                    "path": output.name,
                    "rows": len(observed),
                    "sha256": digest(output),
                    "bytes": output.stat().st_size,
                    "source_production_fingerprint": production_fingerprint,
                }
            )
            paths.append(output)
            log.emit("candidate_completed", candidate=variant["candidate_id"], rows=len(observed))
        if len({r["sha256"] for r in rows}) != len(rows):
            raise ValueError("Adjustments must produce distinct prediction files")
        manifest = target / "submission_manifest.csv"
        pd.DataFrame(rows).to_csv(manifest, index=False, lineterminator="\n")
        recipe = target / "recipe.json"
        atomic_json(recipe, {"scope": SCOPE, "inputs": inputs})
        bundle = target / "prediction_refinement.zip"
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zipped:
            for path in [*paths, manifest, recipe]:
                member = zipfile.ZipInfo(path.name, date_time=(2026, 9, 9, 0, 0, 0))
                member.compress_type = zipfile.ZIP_DEFLATED
                zipped.writestr(member, path.read_bytes())
        with zipfile.ZipFile(bundle) as zipped:
            for row in rows:
                if hashlib.sha256(zipped.read(str(row["path"]))).hexdigest() != row["sha256"]:
                    raise ValueError("Packaged CSV differs from the recorded prediction")
        return [*paths, manifest, recipe, bundle]

    target = store.task("predictions", work)
    bundle = target / "prediction_refinement.zip"
    published = root / "submissions/prediction_refinement.zip"
    verified_write(published, bundle.read_bytes(), digest(bundle))
    manifest = target / "submission_manifest.csv"
    verified_write(root / REPORT / manifest.name, manifest.read_bytes(), digest(manifest))
    receipt = {
        "status": "generated_and_validated",
        "fingerprint": key,
        "inputs": inputs,
        "submission_files": 8,
        "rows_per_file": len(baseline),
        "new_model_fits": 0,
        "women_predictions_unchanged": True,
        "kaggle_submission_sent": False,
        "archive": str(published.relative_to(root)),
        "sha256": digest(bundle),
        "bytes": bundle.stat().st_size,
        "scope": SCOPE,
    }
    atomic_json(root / REPORT / "generation.json", receipt)
    log.emit("generation_completed", files=8, new_model_fits=0)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    action.add_argument("--generate", action="store_true")
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    log = EventLog(root / "outputs/validation/refinement.jsonl")
    log.emit("refinement_started")
    if args.generate:
        result = generate(root, args.archive or root / "submissions/prediction_portfolio.zip")
    else:
        if args.archive is not None:
            parser.error("--archive requires --generate")
        result = review(root, write=args.write)
    log.emit("refinement_completed", status=result["status"], new_model_fits=0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
