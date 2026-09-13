"""Fit three bounded challengers and export six explicit, unscored submissions."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from importlib.metadata import version
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from filelock import FileLock

from march_mania.advanced_features import pair_features
from march_mania.feature_store import sample_pairs
from march_mania.publication import inference, production, refinement, retraining
from march_mania.publication.artifacts import verified_write
from march_mania.publication.submission import validate_submission
from march_mania.runtime import (
    EventLog,
    TaskStore,
    atomic_json,
    digest,
    fingerprint,
    runtime_identity,
)

CONFIG = "configs/prediction_challengers.json"
REPORT = "reports/prediction_challengers"
VARIANTS = ["pooled_64_features", "pooled_less_regularized", "pooled_240_trees"]
ALIASES = ["f064", "lighter", "trees240"]
YEARS = list(range(2013, 2020)) + list(range(2021, 2026))
SCOPE = (
    "Six exploratory submissions requested after observing 2026 scores. Three previously "
    "evaluated pooled XGBoost recipes, each at temperature 1.0 and 0.90. No 2026 tournament "
    "outcomes enter fitting or prediction. Historical comparisons are already explored, "
    "and seed-free routes lack matched tournament validation. All six are unscored."
)


def configuration(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config = json.loads((root / CONFIG).read_text())
    expected = {
        "protocol": "post-result-bounded-challenger-submissions",
        "variants": VARIANTS,
        "temperatures": [0.9, 1.0],
        "prediction_season": 2026,
        "first_training_season": 2013,
        "last_training_season": 2025,
        "excluded_seasons": [2020],
        "max_new_fits": 6,
        "seed": 2026,
        "women_source": "m_pooled_xgboost__w_logistic.csv",
        "2026_results_informed_hypotheses": True,
        "fresh_holdout": False,
    }
    if any(config.get(k) != v for k, v in expected.items()):
        raise ValueError("Preserve the explicit six-file challenger contract")
    for key in ["threads", "chunk_size", "heartbeat_seconds"]:
        if type(config[key]) is not int or config[key] <= 0:
            raise ValueError("Positive integer runtime controls required")
    study = json.loads((root / retraining.CONFIG).read_text())
    retraining.validate_config(study)
    catalog = {v["name"]: v for v in study["variants"]}
    variants = [catalog[name] for name in VARIANTS]
    if any(v["population"] != "pooled_common" or v["massey"] for v in variants):
        raise ValueError("Challengers must use the evaluated common pooled features")
    return config, variants


def source_hashes(root: Path) -> dict[str, str]:
    names = [
        CONFIG,
        retraining.CONFIG,
        "uv.lock",
        "reports/xgboost_retraining/summary.json",
        "reports/prediction_production/submission_manifest.csv",
        "reports/feature_store/run.json",
        "reports/model_comparison/run.json",
    ]
    names += [str(p.relative_to(root)) for p in (root / "src/march_mania").rglob("*.py")]
    return {name: digest(root / name) for name in sorted(names)}


def fit_final(
    frame: pd.DataFrame, variant: dict[str, Any], route: str, config: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    if route not in production.ROUTES:
        raise ValueError("Unknown feature route")
    train = frame.loc[frame.Season.isin(YEARS)].copy()
    inference.validate_games(train, 2025)
    if set(train.Gender) != {"M", "W"} or any(
        sorted(train.loc[train.Gender.eq(g), "Season"].unique()) != YEARS for g in ["M", "W"]
    ):
        raise ValueError("Incomplete pooled final training population")
    columns = retraining.columns_for(variant)
    if route == "seed_free":
        train.loc[:, [c for c in columns if "seed" in c.lower()]] = np.nan
    probe = pd.DataFrame({c: [0.0] for c in columns}).assign(Season=2026)
    fitted, _, columns = retraining.fit_variant(train, probe, variant, config)
    kept = [columns[i] for i in fitted.screen.indices_]
    if route == "seed_free" and any("seed" in c.lower() for c in kept):
        raise ValueError("Seed input survived seed-free training")
    saved = {"model": fitted.model, "features": kept, "screen": fitted.screen}
    audit = {
        "variant": variant["name"],
        "route": route,
        "parameters": variant,
        "training_seasons": YEARS,
        "training_max_season": 2025,
        "training_genders": ["M", "W"],
        "training_games": len(train),
        "training_games_by_gender": train.groupby("Gender").size().to_dict(),
        "eligible_features": len(columns),
        "retained_features": kept,
        "future_labels_used": False,
    }
    return saved, audit


def read_baseline(root: Path, archive: Path, config: dict[str, Any]) -> bytes:
    if digest(archive) != config["source_archive_sha256"]:
        raise ValueError("Source ZIP differs from the preserved production archive")
    manifest = pd.read_csv(root / "reports/prediction_production/submission_manifest.csv")
    expected = manifest.set_index("candidate_id").loc[config["women_source"][:-4], "sha256"]
    with zipfile.ZipFile(archive) as source:
        if len(source.namelist()) != len(set(source.namelist())):
            raise ValueError("Duplicate members in source ZIP")
        contents = source.read(config["women_source"])
    if hashlib.sha256(contents).hexdigest() != expected:
        raise ValueError("Source CSV differs from its recorded checksum")
    return contents


def export(
    target: Path, baseline_bytes: bytes, forecasts: pd.DataFrame, config: dict[str, Any]
) -> list[Path]:
    """Replace men's rows only; preserve women's original bytes and template order."""
    baseline = pd.read_csv(io.BytesIO(baseline_bytes), float_precision="round_trip")
    validate_submission(baseline, baseline)
    men = baseline.ID.str.fullmatch(r"2026_1\d{3}_1\d{3}").to_numpy()
    women = baseline.ID.str.fullmatch(r"2026_3\d{3}_3\d{3}").to_numpy()
    if not (men | women).all() or not men.any() or not women.any():
        raise ValueError("Missing or unknown tournament population")
    if forecasts.ID.tolist() != baseline.ID[men].tolist():
        raise ValueError("Men's predictions differ from template order")
    lines = baseline_bytes.decode().splitlines(keepends=True)
    women_bytes = "".join(line for line, keep in zip(lines[1:], women, strict=True) if keep)
    rows: list[dict[str, Any]] = []
    paths = []
    for name, alias in zip(config["variants"], ALIASES, strict=True):
        for temperature in config["temperatures"]:
            p = baseline.Pred.to_numpy().copy()
            values = forecasts[name].to_numpy(dtype=float)
            adjusted = refinement.transform(
                values, values, {"kind": "temperature", "temperature": temperature}
            )
            p[men] = values if temperature == 1 else adjusted
            filename = f"m_pooled_xgboost_{alias}_t{round(100 * temperature):03d}__w_logistic.csv"
            output = target / filename
            output.write_text(
                lines[0]
                + "".join(
                    f"{identifier},{p[i]:.17g}\n" if men[i] else lines[i + 1]
                    for i, identifier in enumerate(baseline.ID)
                ),
                encoding="utf-8",
                newline="",
            )
            actual = pd.read_csv(output, float_precision="round_trip")
            validate_submission(actual, baseline)
            actual_lines = output.read_text().splitlines(keepends=True)
            observed_women = "".join(
                line for line, keep in zip(actual_lines[1:], women, strict=True) if keep
            )
            if not np.array_equal(actual.Pred, p) or observed_women != women_bytes:
                raise ValueError("Prediction serialization or women's bytes changed")
            rows.append(
                {
                    "priority": len(rows) + 1,
                    "filename": filename,
                    "variant": name,
                    "temperature": temperature,
                    "rows": len(actual),
                    "men_rows": int(men.sum()),
                    "women_rows": int(women.sum()),
                    "sha256": digest(output),
                    "bytes": output.stat().st_size,
                    "status": "unscored",
                    "women_rows_sha256": hashlib.sha256(women_bytes.encode()).hexdigest(),
                    "mean_absolute_men_change_vs_original": float(
                        np.abs(p[men] - baseline.Pred[men]).mean()
                    ),
                }
            )
            paths.append(output)
    if len(rows) != 6 or len({r["sha256"] for r in rows}) != 6:
        raise ValueError("Require six distinct prediction vectors")
    manifest = target / "submission_manifest.csv"
    pd.DataFrame(rows).to_csv(manifest, index=False)
    recipe = target / "recipe.json"
    atomic_json(recipe, {"scope": SCOPE, "config": config})
    bundle = target / "prediction_challengers.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in [*paths, manifest, recipe]:
            member = zipfile.ZipInfo(path.name, date_time=(2026, 9, 9, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            zipped.writestr(member, path.read_bytes())
    with zipfile.ZipFile(bundle) as zipped:
        for row in rows:
            if hashlib.sha256(zipped.read(str(row["filename"]))).hexdigest() != row["sha256"]:
                raise ValueError("Packaged CSV differs from its manifest")
    return [*paths, manifest, recipe, bundle]


def generate(root: Path, inputs: Path, archive: Path) -> dict[str, Any]:
    config, variants = configuration(root)
    study = retraining.review(root)
    _, _, receipts = production.prepared(root, inputs)
    baseline_bytes = read_baseline(root, archive, config)
    identity = {
        "config": config,
        "variants": variants,
        "source": source_hashes(root),
        "input_receipts": receipts,
        "study_fingerprint": study["fingerprint"],
        "runtime": {**runtime_identity(), "xgboost": version("xgboost-cpu")},
    }
    key = fingerprint(identity)
    run = root / "outputs/prediction_challengers" / key
    run.mkdir(parents=True, exist_ok=True)
    with FileLock(str(run / ".lock"), timeout=0):
        return execute(root, inputs, baseline_bytes, identity, run)


def execute(
    root: Path, inputs: Path, baseline_bytes: bytes, identity: dict[str, Any], run: Path
) -> dict[str, Any]:
    config, variants = identity["config"], identity["variants"]
    key = fingerprint(identity)
    log = EventLog(run / "events.jsonl")
    store = TaskStore(run, key, log, config["heartbeat_seconds"])
    atomic_json(run / "manifest.json", {"fingerprint": key, "inputs": identity})
    frame = pd.read_parquet(
        inputs / "feature_store/run/features.parquet", filters=[("Season", "<=", 2025)]
    )
    teams = pd.read_parquet(
        inputs / "feature_store/run/teams.parquet", filters=[("Season", "==", 2026)]
    )
    sample = pd.read_csv(inputs / "feature_store/raw/SampleSubmissionStage2.csv")
    baseline = pd.read_csv(io.BytesIO(baseline_bytes), float_precision="round_trip")
    validate_submission(baseline, sample)
    pairs = sample_pairs(sample, teams)
    if not pairs.Season.eq(2026).all() or set(pairs.Gender) != {"M", "W"}:
        raise ValueError("Require the complete 2026 template")
    pairs = pairs.loc[pairs.Gender.eq("M")].reset_index(drop=True)
    fitted, audits, chunks = {}, [], []
    for variant in variants:
        for route in production.ROUTES:

            def fit(target: Path, variant: dict = variant, route: str = route) -> list[Path]:
                saved, audit = fit_final(frame, variant, route, config)
                model_path = target / "model.joblib"
                joblib.dump(saved, model_path)
                reloaded = joblib.load(model_path)
                probe = frame.loc[frame.Season.eq(2025)].tail(16)
                a = production.forecast(saved["model"], probe, saved["features"], config["threads"])
                b = production.forecast(
                    reloaded["model"], probe, reloaded["features"], config["threads"]
                )
                if not np.array_equal(a, b):
                    raise ValueError("Reloaded model changes predictions")
                atomic_json(
                    target / "audit.json",
                    {**audit, "reload_max_absolute_error": float(np.abs(a - b).max())},
                )
                return [model_path, target / "audit.json"]

            target = store.task(f"fit_{variant['name']}_{route}", fit)
            fitted[variant["name"], route] = joblib.load(target / "model.joblib")
            audits.append(json.loads((target / "audit.json").read_text()))
    chunk_size = min(config["chunk_size"], 512)
    for start in range(0, len(pairs), chunk_size):
        chunk = pairs.iloc[start : start + chunk_size]

        def predict(target: Path, chunk: pd.DataFrame = chunk) -> list[Path]:
            features = pair_features(teams, chunk)
            if "y" in features or not features.Season.eq(2026).all():
                raise ValueError("Prediction features must be label-free 2026 snapshots")
            result = features[["ID"]].copy()
            result["route"] = np.where(features.diff_seed.notna(), "seeded", "seed_free")
            for variant in variants:
                values = np.full(len(features), np.nan)
                for route in production.ROUTES:
                    mask = result.route.eq(route).to_numpy()
                    if mask.any():
                        saved = fitted[variant["name"], route]
                        values[mask] = production.forecast(
                            saved["model"], features.loc[mask], saved["features"], config["threads"]
                        )
                result[variant["name"]] = values
            result.to_parquet(target / "predictions.parquet", index=False)
            return [target / "predictions.parquet"]

        target = store.task(f"predict_{start:06d}", predict)
        chunks.append(target / "predictions.parquet")
        if start % (10 * chunk_size) == 0:
            log.emit(
                "prediction_progress",
                completed=min(start + chunk_size, len(pairs)),
                total=len(pairs),
            )
    forecasts = pd.concat([pd.read_parquet(path) for path in chunks], ignore_index=True)
    target = store.task("exports", lambda folder: export(folder, baseline_bytes, forecasts, config))
    report = root / REPORT
    report.mkdir(parents=True, exist_ok=True)
    manifest = target / "submission_manifest.csv"
    verified_write(report / manifest.name, manifest.read_bytes(), digest(manifest))
    atomic_json(report / "fit_audits.json", audits)
    forecasts.groupby("route").size().reset_index(name="rows").to_csv(
        report / "routes.csv", index=False
    )
    bundle = target / "prediction_challengers.zip"
    published = root / "submissions/prediction_challengers.zip"
    verified_write(published, bundle.read_bytes(), digest(bundle))
    summary = {
        "status": "generated_and_validated",
        "fingerprint": key,
        "inputs": identity,
        "submission_files": 6,
        "rows_per_file": len(sample),
        "fitted_models": len(audits),
        "prediction_chunks": len(chunks),
        "training_max_season": 2025,
        "women_predictions_unchanged": True,
        "future_labels_used": False,
        "kaggle_submission_sent": False,
        "archive": str(published.relative_to(root)),
        "sha256": digest(bundle),
        "bytes": bundle.stat().st_size,
        "scope": SCOPE,
        "reports_sha256": {
            name: digest(report / name)
            for name in ["submission_manifest.csv", "fit_audits.json", "routes.csv"]
        },
    }
    atomic_json(report / "summary.json", summary)
    atomic_json(run / "summary.json", summary)
    log.emit("generation_completed", files=6, models=6, archive_sha256=digest(bundle))
    return summary


def review(root: Path) -> dict[str, Any]:
    config, variants = configuration(root)
    summary = json.loads((root / REPORT / "summary.json").read_text())
    identity = summary["inputs"]
    if (
        identity["source"] != source_hashes(root)
        or identity["config"] != config
        or identity["variants"] != variants
        or fingerprint(identity) != summary["fingerprint"]
    ):
        raise ValueError("Challenger source, recipe or lineage changed")
    for name, sha in summary["reports_sha256"].items():
        if digest(root / REPORT / name) != sha:
            raise ValueError("Challenger evidence checksum changed")
    manifest = pd.read_csv(root / REPORT / "submission_manifest.csv")
    audits = json.loads((root / REPORT / "fit_audits.json").read_text())
    expected_files = {
        f"m_pooled_xgboost_{alias}_t{round(100 * t):03d}__w_logistic.csv"
        for alias in ALIASES
        for t in config["temperatures"]
    }
    if (
        len(manifest) != 6
        or set(manifest.filename) != expected_files
        or manifest.sha256.nunique() != 6
        or not manifest.status.eq("unscored").all()
        or manifest.women_rows_sha256.nunique() != 1
        or not manifest.rows.eq(132133).all()
        or not (manifest.men_rows + manifest.women_rows).eq(manifest.rows).all()
        or len(audits) != 6
        or {(a["variant"], a["route"]) for a in audits}
        != {(v, r) for v in VARIANTS for r in production.ROUTES}
        or any(
            a["training_seasons"] != YEARS
            or a["future_labels_used"]
            or a["reload_max_absolute_error"] != 0
            or len(a["retained_features"]) > a["parameters"]["capacity"]
            or (
                a["route"] == "seed_free"
                and any("seed" in c.lower() for c in a["retained_features"])
            )
            for a in audits
        )
        or summary["submission_files"] != 6
        or summary["fitted_models"] != 6
        or summary["training_max_season"] != 2025
        or summary["future_labels_used"]
        or summary["kaggle_submission_sent"]
        or not summary["women_predictions_unchanged"]
    ):
        raise ValueError("Incomplete challenger publication")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--generate", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--inputs", type=Path, default=Path("outputs/retraining_inputs"))
    parser.add_argument(
        "--source-archive", type=Path, default=Path("submissions/prediction_portfolio.zip")
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    result = (
        generate(root, root / args.inputs, root / args.source_archive)
        if args.generate
        else review(root)
    )
    print(
        json.dumps({k: result[k] for k in ["status", "fingerprint", "submission_files", "sha256"]})
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
