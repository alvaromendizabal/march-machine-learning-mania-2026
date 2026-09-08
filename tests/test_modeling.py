"""Temporal decisions, framework execution, symmetry and interrupted-run contracts."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from threadpoolctl import threadpool_limits

from march_mania import modeling
from march_mania.advanced_features import candidate_blocks
from march_mania.model_report import paired_intervals
from march_mania.runtime import atomic_json


@pytest.fixture
def model_config():
    config = json.loads(Path("configs/model_comparison.json").read_text())
    config.update(validation_seasons=[2016], threads=1, permutation_repeats=1)
    return config


@pytest.fixture
def matrix():
    rng = np.random.default_rng(77)
    records = []
    for gender, base in [("M", 1100), ("W", 3100)]:
        for season in [2013, 2014, 2015, 2016]:
            for i in range(24):
                records.append(
                    {
                        "Gender": gender,
                        "Season": season,
                        "DayNum": 136,
                        "Team1ID": base + i,
                        "Team2ID": base + 100,
                        "ID": f"{season}_{base + i}_{base + 100}",
                        "y": i % 2,
                        **dict(
                            zip(
                                candidate_blocks()["full"],
                                rng.normal(size=len(candidate_blocks()["full"])),
                                strict=True,
                            )
                        ),
                    }
                )
    return pd.DataFrame(records)


@pytest.mark.parametrize(
    "family", ["seed", "logistic", "hist", "xgboost", "lightgbm", "rank_logistic"]
)
def test_every_engine_executes_with_symmetric_finite_probabilities(matrix, family):
    train = matrix.loc[(matrix.Gender == "M") & (matrix.Season < 2016)]
    valid = matrix.loc[(matrix.Gender == "M") & (matrix.Season == 2016)]
    candidate = next(c for c in modeling.candidates("M") if c.family == family)
    with threadpool_limits(limits=1):
        model, p = modeling.fit_candidate(train, valid, candidate, 77, 1)
        reverse = modeling.predict_candidate(
            model, -valid[modeling.columns_for(candidate)].to_numpy(), 1
        )
    assert np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()
    np.testing.assert_allclose(p + reverse, 1, atol=1e-7, rtol=0)
    with pytest.raises(ValueError, match="Temporal"):
        modeling.fit_candidate(valid, train, candidate, 77, 1)


def test_pooling_has_identical_common_features_and_rankings_are_explicit():
    men = {c.name: modeling.columns_for(c) for c in modeling.candidates("M")}
    women = {c.name: modeling.columns_for(c) for c in modeling.candidates("W")}
    pooled = {c.name: modeling.columns_for(c) for c in modeling.candidates("pooled_common")}
    assert women == pooled
    assert {k: men[k] for k in pooled} == pooled
    assert len(pooled["logistic_full_0"]) == len(candidate_blocks()["full"]) - 23
    assert all("rank" not in f for cols in pooled.values() for f in cols)


def forecasts():
    records = []
    for season in [2014, 2015, 2016, 2017]:
        for name, family, p in [
            ("seed", "seed", [0.7, 0.3]),
            ("a", "logistic", [0.8, 0.2]),
            ("b", "logistic", [0.2, 0.8]),
        ]:
            for index, y in enumerate([1, 0]):
                records.append(
                    {
                        "Gender": "M",
                        "Season": season,
                        "DayNum": 136,
                        "ID": f"{season}_{index}",
                        "y": y,
                        "p": p[index],
                        "candidate": name,
                        "family": family,
                        "route": "M",
                    }
                )
    return pd.DataFrame(records)


def test_outer_and_future_labels_cannot_change_selection_calibration_or_blend(model_config):
    frame = forecasts()
    before, decisions = modeling.evaluate_context(frame, "M", "M", 2016, model_config)
    frame.loc[frame.Season >= 2016, "y"] = 1 - frame.loc[frame.Season >= 2016, "y"]
    after, changed = modeling.evaluate_context(frame, "M", "M", 2016, model_config)
    assert changed == decisions
    np.testing.assert_array_equal(before.p, after.p)
    assert decisions["logistic"]["candidate"] == "a"
    assert all(r["fit_last_season"] < r["season"] for r in decisions["logistic"]["crossfit"])
    assert sum(decisions["blend"]["weights"].values()) == pytest.approx(1)


def test_calibration_bounds_symmetry_and_forbidden_history():
    frame = forecasts().query("candidate == 'a' and Season < 2016")
    temperature, _ = modeling.calibrate_from_history(frame, 2016, [0.5, 2.0])
    assert 0.5 <= temperature <= 2
    p = np.linspace(0, 1, 11)
    np.testing.assert_allclose(
        modeling.temperature_probability(p, temperature)
        + modeling.temperature_probability(1 - p, temperature),
        1,
    )
    with pytest.raises(ValueError, match="earlier"):
        modeling.calibrate_from_history(frame, 2015, [0.5, 2.0])
    with pytest.raises(ValueError, match="Temperature"):
        modeling.temperature_probability(p, 0)
    with pytest.raises(ValueError, match="probabilities"):
        modeling.temperature_probability(np.array([np.nan]), 1)


def test_simplex_and_equal_season_weighting():
    seasons = np.array([2014, 2015, 2015])
    np.testing.assert_allclose(modeling.season_weights(seasons), [0.5, 0.25, 0.25])
    y = np.array([1, 0, 1])
    w = modeling.simplex_weights(np.column_stack([y * 0.8 + 0.1, 0.9 - y * 0.8]), y, seasons, 0.01)
    assert w[0] > 0.9 and w.sum() == pytest.approx(1) and (w >= 0).all()
    with pytest.raises(ValueError, match="probabilities"):
        modeling.simplex_weights(np.array([[1.1]]), np.array([1]), np.array([2014]), 0.01)


def test_selector_rejects_unmatched_games_and_future_outcomes():
    frame = forecasts().query("Season < 2016")
    with pytest.raises(ValueError, match="identical"):
        modeling.select_candidate(
            frame.drop(frame.query("candidate == 'a'").index[0]), "logistic", 2016
        )
    with pytest.raises(ValueError, match="earlier"):
        modeling.select_candidate(frame, "logistic", 2015)


def test_matrix_validation(matrix):
    modeling.validate_matrix(matrix)
    with pytest.raises(ValueError, match="duplicate"):
        modeling.validate_matrix(pd.concat([matrix, matrix.iloc[:1]]))
    with pytest.raises(ValueError, match="post-cutoff"):
        modeling.validate_matrix(matrix.assign(DayNum=120))
    with pytest.raises(ValueError, match="lower-TeamID"):
        modeling.validate_matrix(matrix.assign(ID=matrix.ID + "_bad"))
    with pytest.raises(ValueError, match="Infinite"):
        modeling.validate_matrix(matrix.assign(diff_seed=np.inf))


def test_config_boundaries(model_config):
    modeling.validate_config(model_config)
    for changes in [
        {"validation_seasons": [2022]},
        {"minimum_inner_seasons": 1},
        {"protocol": "untouched"},
        {"threads": 0},
        {"calibration_temperature_bounds": [0, 1]},
        {"ensemble_l2": 0},
    ]:
        with pytest.raises(ValueError):
            modeling.validate_config({**model_config, **changes})


def test_unknown_engine_and_single_class_training(matrix):
    train, valid = matrix.query("Season < 2016"), matrix.query("Season == 2016")
    candidate = modeling.Candidate("seed", "seed", "seed", 0.1)
    with pytest.raises(ValueError, match="Unknown"):
        modeling.fit_candidate(train, valid, replace(candidate, family="unknown"), 77, 1)
    with pytest.raises(ValueError, match="both classes"):
        modeling.fit_candidate(train.assign(y=1), valid, candidate, 77, 1)


def test_end_to_end_resume_integrity_and_failed_run(matrix, model_config, tmp_path, monkeypatch):
    upstream = tmp_path / "features"
    upstream.mkdir()
    matrix.to_parquet(upstream / "features.parquet", index=False)
    atomic_json(
        upstream / "summary.json",
        {"status": "completed", "fingerprint": "synthetic", "feature_count": 124},
    )
    monkeypatch.setattr(
        modeling,
        "candidates",
        lambda _: [
            modeling.Candidate("seed", "seed", "seed", 0.1),
            modeling.Candidate("logistic", "logistic", "strength", 0.1),
        ],
    )
    runs = tmp_path / "runs"
    summary = modeling.run(upstream, runs, model_config)
    output = runs / summary["fingerprint"]
    assert summary["fit_tasks"] == 18 and summary["selection_tasks"] == 4
    assert summary["physical_validation_games"] == 48
    times = {p: p.stat().st_mtime_ns for p in output.glob("fit_*/model.joblib")}
    resumed = modeling.run(upstream, runs, model_config)
    assert resumed["fingerprint"] == summary["fingerprint"]
    assert times == {p: p.stat().st_mtime_ns for p in times}
    assert (output / "permutation.csv").is_file()
    predictions = pd.read_parquet(output / "predictions.parquet")
    assert len(paired_intervals(predictions, 77)) == 20
    with pytest.raises(ValueError):
        paired_intervals(predictions.iloc[1:], 77)
    model = next(iter(times))
    model.write_bytes(b"interrupted write")
    modeling.run(upstream, runs, model_config)
    assert model.stat().st_size > 100
    assert all(p.stat().st_mtime_ns == timestamp for p, timestamp in times.items() if p != model)
    events = [json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()]
    assert any(e["event"] == "checkpoint_invalid" for e in events)
    assert all("timestamp" in e and "elapsed_seconds" in e for e in events)
    monkeypatch.setattr(
        modeling,
        "fit_candidate",
        lambda *a: (_ for _ in ()).throw(InterruptedError("simulated interruption")),
    )
    with pytest.raises(InterruptedError):
        modeling.run(upstream, tmp_path / "failed", model_config)
    assert not (tmp_path / "failed/latest.json").exists()
    failed = json.loads(next((tmp_path / "failed").glob("*/summary.json")).read_text())
    assert failed["status"] == "failed"
