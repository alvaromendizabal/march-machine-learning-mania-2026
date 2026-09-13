"""Evaluate and export bounded women's challengers, preserving the scored men's stream.

This independent runner reuses the frozen production fitters and input receipts;
it does not alter the completed men's experiment or its recorded source inventory.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from filelock import FileLock
from threadpoolctl import threadpool_limits

from march_mania import modeling
from march_mania.advanced_features import pair_features
from march_mania.feature_store import sample_pairs
from march_mania.publication import inference, portfolio, production, refinement
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

SCRIPT = "scripts/women_challengers.py"
CONFIG = "configs/women_challengers.json"
REPORT = "reports/women_challengers"
YEARS = [2014, 2015, 2016, 2017, 2018, 2019, 2021]
FINAL_YEARS = list(range(2013, 2020)) + list(range(2021, 2026))


def configuration(root: Path) -> dict[str, Any]:
    config = json.loads((root / CONFIG).read_text())
    expected = [
        ("conference_c010", "conference", 0.1, None),
        ("conference_c030", "conference", 0.3, "logistic_conference_1"),
        ("conference_c100", "conference", 1.0, None),
        ("conference_c300", "conference", 3.0, None),
        ("dynamic_c030", "dynamic", 0.3, "logistic_dynamic_1"),
    ]
    if (
        config["protocol"] != "bounded-women-logistic-challengers"
        or config["fold_seasons"] != YEARS
        or config["development_seasons"] != YEARS[2:]
        or config["first_training_season"] != 2013
        or config["prediction_season"] != 2026
        or config["temperatures"] != [0.9, 1.0, 1.1]
        or config["reference"] != "conference_c030_t100"
        or config["selection_metric"] != "mean_season_brier"
        or (config["max_historical_fits"], config["max_final_fits"], config["export_count"])
        != (21, 8, 6)
        or [tuple(v[k] for k in ["name", "block", "C", "reuse"]) for v in config["variants"]]
        != expected
        or config["men_source"] != "m_pooled_xgboost_t090__w_logistic.csv"
    ):
        raise ValueError("Preserve the declared women's challenger scope")
    for key in ["threads", "chunk_size", "heartbeat_seconds"]:
        if type(config[key]) is not int or config[key] < 1:
            raise ValueError("Positive integer runtime controls required")
    return config


def candidate(spec: dict[str, Any]) -> modeling.Candidate:
    return modeling.Candidate(spec["name"], "logistic", spec["block"], spec["C"])


def source_hashes(root: Path) -> dict[str, str]:
    names = [
        SCRIPT,
        CONFIG,
        "uv.lock",
        "reports/feature_store/run.json",
        "reports/model_comparison/run.json",
        "reports/prediction_refinement/generation.json",
    ]
    names += [str(p.relative_to(root)) for p in (root / "src/march_mania").rglob("*.py")]
    return {name: digest(root / name) for name in sorted(names)}


def adjusted(values: np.ndarray, temperature: float) -> np.ndarray:
    result = refinement.transform(
        values, values, {"kind": "temperature", "temperature": temperature}
    )
    return values.copy() if temperature == 1 else result


def fit_fold(
    frame: pd.DataFrame, spec: dict[str, Any], season: int, config: dict[str, Any]
) -> tuple[dict[str, Any], pd.DataFrame, dict[str, Any]]:
    if season not in YEARS:
        raise ValueError("Historical fitting cannot use a future validation season")
    women = frame.loc[
        frame.Gender.eq("W") & frame.Season.between(2013, 2021) & frame.Season.ne(2020)
    ]
    train, valid = women.loc[women.Season.lt(season)], women.loc[women.Season.eq(season)]
    inference.validate_games(train, season - 1)
    inference.validate_games(valid, 2021)
    with threadpool_limits(limits=config["threads"]):
        fitted, p = modeling.fit_candidate(
            train, valid, candidate(spec), config["seed"], config["threads"]
        )
    columns = modeling.columns_for(candidate(spec))
    audit = {
        "variant": spec["name"],
        "validation_season": season,
        "training_max_season": int(train.Season.max()),
        "training_games": len(train),
        "training_genders": ["W"],
        "retained_features": [columns[i] for i in fitted.screen.indices_],
    }
    return {"model": fitted, "features": columns}, valid[modeling.KEYS].assign(p=p), audit


def evaluate(raw: pd.DataFrame, config: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """Report fixed recipes and separately evaluate selection using strictly prior seasons."""
    expected_names = {v["name"] for v in config["variants"]}
    if (
        set(raw.variant) != expected_names
        or set(raw.Season) != set(YEARS)
        or not raw.Gender.eq("W").all()
        or raw.duplicated(["variant", "Season", "ID"]).any()
        or not raw.y.isin([0, 1]).all()
        or not np.isfinite(raw.p).all()
        or not raw.p.between(0, 1).all()
    ):
        raise ValueError("Invalid or incomplete historical women's predictions")
    reference_keys = (
        raw.loc[raw.variant.eq("conference_c030"), modeling.KEYS]
        .sort_values(["Season", "ID"])
        .reset_index(drop=True)
    )
    inference.validate_games(reference_keys, 2021)
    expanded = []
    for spec in config["variants"]:
        rows = (
            raw.loc[raw.variant.eq(spec["name"])]
            .sort_values(["Season", "ID"])
            .reset_index(drop=True)
        )
        if not rows[modeling.KEYS].equals(reference_keys):
            raise ValueError("Historical comparisons require identical games and labels")
        for temperature in config["temperatures"]:
            name = f"{spec['name']}_t{round(temperature * 100):03d}"
            expanded.append(
                rows.assign(
                    candidate_id=name,
                    temperature=temperature,
                    p=adjusted(rows.p.to_numpy(), temperature),
                )
            )
    predictions = pd.concat(expanded, ignore_index=True)
    dev = predictions.loc[predictions.Season.isin(config["development_seasons"])]
    reference = dev.loc[dev.candidate_id.eq(config["reference"])].sort_values(["Season", "ID"])
    catalog: list[dict[str, Any]] = []
    annual: list[dict[str, Any]] = []
    for group_name, rows in dev.groupby("candidate_id", sort=True):
        name = str(group_name)
        rows = rows.sort_values(["Season", "ID"])
        delta = (rows.p.to_numpy(dtype=float) - rows.y.to_numpy(dtype=float)) ** 2 - (
            reference.p.to_numpy(dtype=float) - reference.y.to_numpy(dtype=float)
        ) ** 2
        seasonal = pd.Series(delta).groupby(rows.Season.to_numpy()).mean().to_numpy()
        samples = (
            np.random.default_rng(config["seed"])
            .choice(seasonal, (4000, len(seasonal)))
            .mean(axis=1)
        )
        catalog.append(
            {
                "candidate_id": name,
                "variant": rows.variant.iloc[0],
                "temperature": rows.temperature.iloc[0],
                **portfolio.metrics(rows),
                "brier_delta": float(delta.mean()),
                "ci_low": float(np.quantile(samples, 0.025)),
                "ci_high": float(np.quantile(samples, 0.975)),
                "prediction_sha256": hashlib.sha256(
                    rows.p.to_numpy(dtype="<f8").tobytes()
                ).hexdigest(),
            }
        )
        annual.extend(
            {"candidate_id": name, "Season": season, **portfolio.metrics(group)}
            for season, group in rows.groupby("Season")
        )
    leaderboard = (
        pd.DataFrame(catalog)
        .sort_values([config["selection_metric"], "brier", "candidate_id"])
        .reset_index(drop=True)
    )
    finalists = (
        leaderboard.loc[leaderboard.candidate_id.ne(config["reference"])]
        .drop_duplicates("prediction_sha256")
        .head(config["export_count"])
        .reset_index(drop=True)
        .copy()
    )
    if len(finalists) != 6:
        raise ValueError("Require six distinct challengers")
    finalists.insert(0, "priority", range(1, 7))
    selections = []
    for season in config["development_seasons"]:
        earlier = predictions.loc[predictions.Season.lt(season)].copy()
        scores = (
            earlier.assign(loss=(earlier.p - earlier.y) ** 2)
            .groupby(["candidate_id", "Season"])
            .loss.mean()
            .groupby("candidate_id")
            .mean()
        )
        chosen = scores.sort_index().sort_values(kind="stable").index[0]
        selections.append(
            {
                "Season": season,
                "candidate_id": chosen,
                "history_last_season": int(earlier.Season.max()),
            }
        )
    return {
        "leaderboard.csv": leaderboard,
        "finalists.csv": finalists,
        "metrics_by_season.csv": pd.DataFrame(annual),
        "selection.csv": pd.DataFrame(selections),
        "predictions.csv": predictions,
    }


def study(root: Path, inputs: Path) -> dict[str, Any]:
    config = configuration(root)
    _, _, receipts = production.prepared(root, inputs)
    identity = {
        "config": config,
        "source": source_hashes(root),
        "input_receipts": receipts,
        "runtime": runtime_identity(),
    }
    key = fingerprint(identity)
    run = root / "outputs/women_challengers" / key
    log = EventLog(run / "events.jsonl")
    store = TaskStore(run, key, log, config["heartbeat_seconds"])
    frame = pd.read_parquet(
        inputs / "feature_store/run/features.parquet", filters=[("Season", "<=", 2021)]
    )
    controls = pd.read_parquet(inputs / "model_comparison/run/candidate_predictions.parquet")
    results, audits = [], []
    atomic_json(run / "manifest.json", {"fingerprint": key, "inputs": identity})
    with FileLock(str(run / ".study.lock"), timeout=0):
        for spec in config["variants"]:
            for season in YEARS:
                if spec["reuse"]:
                    rows = controls.loc[
                        controls.Gender.eq("W")
                        & controls.route.eq("W")
                        & controls.candidate.eq(spec["reuse"])
                        & controls.Season.eq(season),
                        modeling.KEYS + ["p"],
                    ].sort_values("ID")
                    valid = frame.loc[
                        frame.Gender.eq("W") & frame.Season.eq(season), modeling.KEYS
                    ].sort_values("ID")
                    if (
                        not rows[modeling.KEYS]
                        .reset_index(drop=True)
                        .equals(valid.reset_index(drop=True))
                    ):
                        raise ValueError("Saved women's control uses different games")
                    log.emit("control_reused", variant=spec["name"], season=season)
                else:

                    def fit(target: Path, spec: dict = spec, season: int = season) -> list[Path]:
                        saved, rows, audit = fit_fold(frame, spec, season, config)
                        joblib.dump(saved, target / "model.joblib")
                        restored = joblib.load(target / "model.joblib")
                        valid = frame.loc[frame.Gender.eq("W") & frame.Season.eq(season)]
                        actual = production.forecast(
                            restored["model"], valid, restored["features"], config["threads"]
                        )
                        if not np.array_equal(actual, rows.p):
                            raise ValueError("Restored historical model changes predictions")
                        rows.to_parquet(target / "predictions.parquet", index=False)
                        atomic_json(
                            target / "audit.json", {**audit, "reload_max_absolute_error": 0.0}
                        )
                        return [
                            target / n
                            for n in ["model.joblib", "predictions.parquet", "audit.json"]
                        ]

                    target = store.task(f"historical_{spec['name']}_{season}", fit)
                    rows = pd.read_parquet(target / "predictions.parquet")
                    audits.append(json.loads((target / "audit.json").read_text()))
                results.append(rows.assign(variant=spec["name"]))
        raw = pd.concat(results, ignore_index=True)
        tables = {"raw_predictions.csv": raw, **evaluate(raw, config)}
        report = root / REPORT
        report.mkdir(parents=True, exist_ok=True)
        for name, table in tables.items():
            table.to_csv(report / name, index=False)
            table.to_csv(run / name, index=False)
        atomic_json(report / "fit_audits.json", audits)
        selected = tables["predictions.csv"].merge(
            tables["selection.csv"][["Season", "candidate_id"]],
            on=["Season", "candidate_id"],
            validate="many_to_one",
        )
        summary = {
            "status": "completed",
            "fingerprint": key,
            "inputs": identity,
            "historical_fit_tasks": len(audits),
            "reused_control_folds": 14,
            "evaluated_hypotheses": 15,
            "women_development_games": 315,
            "forward_selection_metrics": portfolio.metrics(selected),
            "scope": config["scope"],
            "sha256": {n: digest(report / n) for n in [*tables, "fit_audits.json"]},
        }
        atomic_json(report / "summary.json", summary)
        atomic_json(run / "summary.json", summary)
        log.emit("study_completed", new_fit_tasks=len(audits), controls_reused=14)
        return summary


def review(root: Path) -> dict[str, Any]:
    config = configuration(root)
    report = root / REPORT
    summary = json.loads((report / "summary.json").read_text())
    identity = summary["inputs"]
    if (
        identity["config"] != config
        or identity["source"] != source_hashes(root)
        or fingerprint(identity) != summary["fingerprint"]
        or summary["historical_fit_tasks"] != 21
    ):
        raise ValueError("Women's study has stale source, configuration or fit count")
    for name, sha in summary["sha256"].items():
        if digest(report / name) != sha:
            raise ValueError("Women's evidence checksum mismatch")
    audits = json.loads((report / "fit_audits.json").read_text())
    expected = {(v["name"], y) for v in config["variants"] if not v["reuse"] for y in YEARS}
    if len(audits) != 21 or {(a["variant"], a["validation_season"]) for a in audits} != expected:
        raise ValueError("Incomplete historical fit inventory")
    if any(
        a["training_max_season"] >= a["validation_season"]
        or a["training_genders"] != ["W"]
        or a["reload_max_absolute_error"] != 0.0
        for a in audits
    ):
        raise ValueError("Historical fit violated time, population or reload boundaries")
    raw = pd.read_csv(report / "raw_predictions.csv", float_precision="round_trip")
    tables = evaluate(raw, config)
    for name, table in tables.items():
        pd.testing.assert_frame_equal(
            table,
            pd.read_csv(report / name, float_precision="round_trip"),
            check_exact=False,
            atol=1e-12,
            rtol=0,
        )
    selected = tables["predictions.csv"].merge(
        tables["selection.csv"][["Season", "candidate_id"]],
        on=["Season", "candidate_id"],
        validate="many_to_one",
    )
    pd.testing.assert_frame_equal(
        pd.DataFrame([portfolio.metrics(selected)]),
        pd.DataFrame([summary["forward_selection_metrics"]]),
        check_like=True,
        check_exact=False,
        atol=1e-12,
        rtol=0,
    )
    return summary


def read_baseline(root: Path, archive: Path, config: dict[str, Any]) -> bytes:
    generation = json.loads((root / refinement.REPORT / "generation.json").read_text())
    if digest(archive) != config["source_archive_sha256"] or generation["sha256"] != digest(
        archive
    ):
        raise ValueError("Use the exact preserved refinement ZIP")
    with zipfile.ZipFile(archive) as zipped:
        if len(zipped.namelist()) != len(set(zipped.namelist())):
            raise ValueError("Duplicate source archive entries")
        contents = zipped.read(config["men_source"])
    if hashlib.sha256(contents).hexdigest() != config["source_csv_sha256"]:
        raise ValueError("The men's source CSV changed")
    return contents


def export(
    target: Path, baseline_bytes: bytes, forecasts: pd.DataFrame, finalists: pd.DataFrame
) -> list[Path]:
    baseline = pd.read_csv(io.BytesIO(baseline_bytes), float_precision="round_trip")
    validate_submission(baseline, baseline)
    men = baseline.ID.str.fullmatch(r"2026_1\d{3}_1\d{3}").to_numpy()
    women = baseline.ID.str.fullmatch(r"2026_3\d{3}_3\d{3}").to_numpy()
    if (
        not (men | women).all()
        or not men.any()
        or not women.any()
        or forecasts.ID.tolist() != baseline.ID[women].tolist()
    ):
        raise ValueError("Missing population or misordered women's predictions")
    lines = baseline_bytes.decode().splitlines(keepends=True)
    men_bytes = "".join(line for line, keep in zip(lines[1:], men, strict=True) if keep)
    records: list[dict[str, Any]] = []
    paths = []
    for row in finalists.to_dict("records"):
        values = baseline.Pred.to_numpy().copy()
        values[women] = adjusted(forecasts[row["variant"]].to_numpy(), row["temperature"])
        path = target / f"m_pooled_xgboost_t090__w_{row['candidate_id']}.csv"
        path.write_text(
            lines[0]
            + "".join(
                lines[i + 1] if men[i] else f"{identifier},{values[i]:.17g}\n"
                for i, identifier in enumerate(baseline.ID)
            ),
            encoding="utf-8",
            newline="",
        )
        actual = pd.read_csv(path, float_precision="round_trip")
        validate_submission(actual, baseline)
        if not np.array_equal(values, actual.Pred):
            raise ValueError("Serialized predictions differ")
        actual_men = "".join(
            line
            for line, keep in zip(path.read_text().splitlines(keepends=True)[1:], men, strict=True)
            if keep
        )
        if actual_men != men_bytes:
            raise ValueError("Men's original prediction bytes changed")
        records.append(
            {
                "priority": row["priority"],
                "filename": path.name,
                "candidate_id": row["candidate_id"],
                "variant": row["variant"],
                "temperature": row["temperature"],
                "rows": len(actual),
                "men_rows": int(men.sum()),
                "women_rows": int(women.sum()),
                "sha256": digest(path),
                "bytes": path.stat().st_size,
                "status": "unscored",
                "men_rows_sha256": hashlib.sha256(men_bytes.encode()).hexdigest(),
            }
        )
        paths.append(path)
    if len(records) != 6 or len({r["sha256"] for r in records}) != 6:
        raise ValueError("Require six distinct submission files")
    manifest = target / "submission_manifest.csv"
    pd.DataFrame(records).to_csv(manifest, index=False)
    recipe = target / "recipe.json"
    atomic_json(
        recipe,
        {
            "men_source_sha256": hashlib.sha256(baseline_bytes).hexdigest(),
            "finalists": finalists.to_dict("records"),
        },
    )
    bundle = target / "women_challengers.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in [*paths, manifest, recipe]:
            member = zipfile.ZipInfo(path.name, date_time=(2026, 9, 9, 0, 0, 0))
            member.compress_type = zipfile.ZIP_DEFLATED
            zipped.writestr(member, path.read_bytes())
    with zipfile.ZipFile(bundle) as zipped:
        for record in records:
            if hashlib.sha256(zipped.read(record["filename"])).hexdigest() != record["sha256"]:
                raise ValueError("ZIP prediction checksum mismatch")
    return [*paths, manifest, recipe, bundle]


def generate(root: Path, inputs: Path, archive: Path) -> dict[str, Any]:
    summary = review(root)
    config = configuration(root)
    _, _, receipts = production.prepared(root, inputs)
    if receipts != summary["inputs"]["input_receipts"]:
        raise ValueError("Final fitting must use the study's pinned inputs")
    baseline_bytes = read_baseline(root, archive, config)
    baseline = pd.read_csv(io.BytesIO(baseline_bytes), float_precision="round_trip")
    finalists = pd.read_csv(root / REPORT / "finalists.csv", float_precision="round_trip")
    variants = [
        v
        for v in config["variants"]
        if v["name"] in set(finalists.variant) and v["name"] != "conference_c030"
    ]
    if len(variants) * 2 > config["max_final_fits"]:
        raise ValueError("Final fit budget exceeded")
    identity = {
        "study_fingerprint": summary["fingerprint"],
        "finalists_sha256": digest(root / REPORT / "finalists.csv"),
        "source_csv_sha256": config["source_csv_sha256"],
        "runtime": runtime_identity(),
    }
    key = fingerprint(identity)
    run = root / "outputs/women_challengers" / summary["fingerprint"] / ("final_" + key)
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
    validate_submission(baseline, sample)
    pairs = sample_pairs(sample, teams)
    pairs = pairs.loc[pairs.Gender.eq("W")].reset_index(drop=True)
    fitted, audits, chunks = {}, [], []
    with FileLock(str(run / ".lock"), timeout=0):
        for spec in variants:
            for route in production.ROUTES:

                def fit(target: Path, spec: dict = spec, route: str = route) -> list[Path]:
                    saved, audit = production.fit_component(
                        frame,
                        {"population": "W", "candidate": asdict(candidate(spec))},
                        route,
                        config,
                    )
                    joblib.dump(saved, target / "model.joblib")
                    restored = joblib.load(target / "model.joblib")
                    probe = frame.loc[frame.Gender.eq("W") & frame.Season.eq(2025)].tail(16)
                    before = production.forecast(
                        saved["model"], probe, saved["features"], config["threads"]
                    )
                    after = production.forecast(
                        restored["model"], probe, restored["features"], config["threads"]
                    )
                    if not np.array_equal(before, after):
                        raise ValueError("Restored final model changes probabilities")
                    atomic_json(
                        target / "audit.json",
                        {**audit, "variant": spec["name"], "reload_max_absolute_error": 0.0},
                    )
                    return [target / "model.joblib", target / "audit.json"]

                target = store.task(f"fit_{spec['name']}_{route}", fit)
                fitted[spec["name"], route] = joblib.load(target / "model.joblib")
                audits.append(json.loads((target / "audit.json").read_text()))
        chunk_size = min(config["chunk_size"], 512)
        for start in range(0, len(pairs), chunk_size):
            chunk = pairs.iloc[start : start + chunk_size]

            def predict(target: Path, chunk: pd.DataFrame = chunk) -> list[Path]:
                features = pair_features(teams, chunk)
                if "y" in features or not features.Season.eq(2026).all():
                    raise ValueError("Only label-free 2026 snapshots may enter prediction")
                result = features[["ID"]].copy()
                result["route"] = np.where(features.diff_seed.notna(), "seeded", "seed_free")
                for spec in variants:
                    values = np.full(len(features), np.nan)
                    for route in production.ROUTES:
                        mask = result.route.eq(route).to_numpy()
                        if mask.any():
                            saved = fitted[spec["name"], route]
                            values[mask] = production.forecast(
                                saved["model"],
                                features.loc[mask],
                                saved["features"],
                                config["threads"],
                            )
                    result[spec["name"]] = values
                result.to_parquet(target / "predictions.parquet", index=False)
                return [target / "predictions.parquet"]

            target = store.task(f"predict_{start:06d}", predict)
            chunks.append(target / "predictions.parquet")
        forecasts = pd.concat([pd.read_parquet(path) for path in chunks], ignore_index=True)
        expected = baseline.loc[baseline.ID.str.fullmatch(r"2026_3\d{3}_3\d{3}")]
        if forecasts.ID.tolist() != expected.ID.tolist():
            raise ValueError("Final women's chunk order changed")
        forecasts["conference_c030"] = expected.Pred.to_numpy()
        target = store.task(
            "exports", lambda path: export(path, baseline_bytes, forecasts, finalists)
        )
        for name in ["submission_manifest.csv"]:
            verified_write(
                root / REPORT / name, (target / name).read_bytes(), digest(target / name)
            )
        atomic_json(root / REPORT / "final_fit_audits.json", audits)
        forecasts.groupby("route").size().reset_index(name="rows").to_csv(
            root / REPORT / "routes.csv", index=False
        )
        bundle = target / "women_challengers.zip"
        verified_write(
            root / "submissions/women_challengers.zip", bundle.read_bytes(), digest(bundle)
        )
        result = {
            "status": "generated_and_validated",
            "fingerprint": key,
            "inputs": identity,
            "study_fingerprint": summary["fingerprint"],
            "submission_files": 6,
            "rows_per_file": len(sample),
            "fitted_models": len(audits),
            "prediction_chunks": len(chunks),
            "training_max_season": 2025,
            "men_predictions_unchanged": True,
            "future_labels_used": False,
            "kaggle_submission_sent": False,
            "archive": "submissions/women_challengers.zip",
            "sha256": digest(bundle),
            "bytes": bundle.stat().st_size,
            "reports_sha256": {
                n: digest(root / REPORT / n)
                for n in ["submission_manifest.csv", "final_fit_audits.json", "routes.csv"]
            },
        }
        atomic_json(root / REPORT / "generation.json", result)
        atomic_json(run / "summary.json", result)
        log.emit("generation_completed", files=6, models=len(audits), sha256=digest(bundle))
        return result


def check_generation(root: Path) -> dict[str, Any]:
    summary = review(root)
    result = json.loads((root / REPORT / "generation.json").read_text())
    if (
        result["study_fingerprint"] != summary["fingerprint"]
        or fingerprint(result["inputs"]) != result["fingerprint"]
        or result["inputs"]["finalists_sha256"] != digest(root / REPORT / "finalists.csv")
        or result["submission_files"] != 6
        or result["rows_per_file"] != 132133
        or not result["men_predictions_unchanged"]
        or result["future_labels_used"]
        or result["kaggle_submission_sent"]
    ):
        raise ValueError("Invalid women's generation receipt")
    for name, sha in result["reports_sha256"].items():
        if digest(root / REPORT / name) != sha:
            raise ValueError("Women's generation evidence changed")
    manifest = pd.read_csv(root / REPORT / "submission_manifest.csv")
    finalists = pd.read_csv(root / REPORT / "finalists.csv")
    audits = json.loads((root / REPORT / "final_fit_audits.json").read_text())
    expected = {
        (v, route)
        for v in set(finalists.variant) - {"conference_c030"}
        for route in production.ROUTES
    }
    if (
        len(audits) != len(expected)
        or result["fitted_models"] != len(expected)
        or len(expected) > configuration(root)["max_final_fits"]
        or {(a["variant"], a["route"]) for a in audits} != expected
        or any(
            a["training_genders"] != ["W"]
            or a["training_seasons"] != FINAL_YEARS
            or a["training_max_season"] != 2025
            or a["reload_max_absolute_error"] != 0.0
            or (
                a["route"] == "seed_free"
                and any("seed" in c.lower() for c in a["retained_features"])
            )
            for a in audits
        )
    ):
        raise ValueError("Invalid final women's fit inventory or temporal boundary")
    if (
        manifest.candidate_id.tolist() != finalists.candidate_id.tolist()
        or manifest.sha256.nunique() != 6
        or manifest.men_rows_sha256.nunique() != 1
        or not manifest.status.eq("unscored").all()
        or not manifest.rows.eq(132133).all()
        or not (manifest.men_rows + manifest.women_rows).eq(manifest.rows).all()
    ):
        raise ValueError("Incomplete women's submission inventory")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--study", action="store_true")
    actions.add_argument("--generate", action="store_true")
    actions.add_argument("--check", action="store_true")
    parser.add_argument("--inputs", type=Path, default=Path("outputs/retraining_inputs"))
    parser.add_argument(
        "--source-archive", type=Path, default=Path("submissions/prediction_refinement.zip")
    )
    root = Path(__file__).resolve().parents[1]
    args = parser.parse_args()
    result = (
        study(root, root / args.inputs)
        if args.study
        else generate(root, root / args.inputs, root / args.source_archive)
        if args.generate
        else check_generation(root)
    )
    print(json.dumps({k: result[k] for k in ["status", "fingerprint"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
