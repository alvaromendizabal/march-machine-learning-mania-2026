"""Tests of temporal capacity selection, estimator equivalence and corruption gates."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from threadpoolctl import threadpool_limits

from march_mania.publication import capacity
from march_mania.research import fit_fold, symmetric_probability
from march_mania.runtime import atomic_json, digest


def example() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    rng = np.random.default_rng(53)
    columns = ["diff_seed", "diff_strength", "diff_recent_strength"]
    frame = pd.DataFrame(rng.normal(size=(100, 3)), columns=columns)
    frame["Season"] = np.repeat([2013, 2014], 50)
    frame["y"] = (frame.diff_strength + rng.normal(size=100) > 0).astype(int)
    frame.loc[::7, "diff_seed"] = np.nan
    return frame.iloc[:50].copy(), frame.iloc[50:].copy(), columns


@pytest.mark.parametrize("model_name", ["logistic", "hist"])
def test_capacity_128_matches_original_fit_and_discards_template_state(model_name):
    train, valid, columns = example()
    with threadpool_limits(limits=1):
        original, p = fit_fold(train, valid, columns, model_name, 2026)
        model, fitted, actual = capacity.fit_capacity(train, valid, columns, original.model, 128)
        np.testing.assert_array_equal(actual, p)
        altered = train.assign(y=1 - train.y)
        other, _ = fit_fold(altered, valid, columns, model_name, 2026)
        _, _, reproduced = capacity.fit_capacity(train, valid, columns, other.model, 128)
        np.testing.assert_array_equal(reproduced, p)
        swapped = -valid[fitted].to_numpy(float)
        np.testing.assert_allclose(actual + symmetric_probability(model, swapped), 1, atol=1e-14)
        changed = valid.assign(y=1 - valid.y, diff_strength=valid.diff_strength * 100)
        second, _, _ = capacity.fit_capacity(train, changed, columns, original.model, 1)
        first, _, _ = capacity.fit_capacity(train, valid, columns, original.model, 1)
        np.testing.assert_array_equal(first.screen.indices_, second.screen.indices_)


def histories() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "capacity": cap,
                "Season": year,
                "ID": str(i),
                "y": i % 2,
                "p": (0.1 if i % 2 == 0 else 0.9) if cap == 32 else 0.5,
            }
            for cap in [32, 128]
            for year in [2014, 2015, 2016]
            for i in range(4)
        ]
    )


def test_capacity_selection_ignores_outer_and_future_targets():
    frame = histories()
    assert capacity.select_capacity(frame, 2016) == 32
    changed = frame.copy()
    changed.loc[changed.Season >= 2016, ["y", "p"]] = np.nan
    assert capacity.select_capacity(changed, 2016) == 32
    assert capacity.select_capacity(frame.query("Season < 2016"), 2016) == 32
    with pytest.raises(ValueError, match="Insufficient"):
        capacity.select_capacity(frame, 2015)
    with pytest.raises(ValueError, match="identical"):
        capacity.select_capacity(frame.drop(index=0), 2016)
    with pytest.raises(ValueError, match="Duplicate"):
        capacity.select_capacity(pd.concat([frame, frame.iloc[[0]]]), 2016)


def test_capacity_ties_favor_smaller_and_weight_seasons_equally():
    frame = histories().assign(p=0.5)
    assert capacity.select_capacity(frame, 2016) == 32
    # The four-game season favors 32; the one-game season strongly favors 128.
    frame = pd.DataFrame(
        [
            {"capacity": cap, "Season": year, "ID": str(i), "y": 0, "p": p}
            for cap, year, count, p in [
                (32, 2014, 4, 0.1),
                (32, 2015, 1, 0.7),
                (128, 2014, 4, 0.4),
                (128, 2015, 1, 0.1),
            ]
            for i in range(count)
        ]
    )
    assert capacity.select_capacity(frame, 2016) == 128


def test_reference_reuse_checks_lineage_and_all_bytes(tmp_path):
    folder = tmp_path / "fold_m_2016_full_logistic"
    folder.mkdir()
    (folder / "model.joblib").write_bytes(b"reference fixture")
    atomic_json(
        folder / "checkpoint.json",
        {"fingerprint": "a" * 64, "outputs": {"model.joblib": digest(folder / "model.joblib")}},
    )
    assert capacity.verified_reference(tmp_path, folder.name, "a" * 64) == folder
    with pytest.raises(ValueError, match="lineage"):
        capacity.verified_reference(tmp_path, folder.name, "b" * 64)
    (folder / "model.joblib").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="corrupt"):
        capacity.verified_reference(tmp_path, folder.name, "a" * 64)


@pytest.mark.parametrize(
    "field,value",
    [
        ("validation_seasons", [2022]),
        ("capacities", [32, 32, 128]),
        ("reference_capacity", 64),
        ("minimum_inner_seasons", 1),
    ],
)
def test_capacity_config_rejects_benchmark_selection_and_invalid_search(field, value):
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "configs/feature_capacity.json").read_text())
    capacity.validate_config(config)
    changed = copy.deepcopy(config)
    changed[field] = value
    with pytest.raises(ValueError):
        capacity.validate_config(changed)


def test_complete_capacity_study_excludes_future_labels_and_resumes_without_refitting(
    tmp_path, monkeypatch
):
    import joblib

    from march_mania.advanced_features import candidate_blocks
    from march_mania.runtime import EventLog, TaskStore

    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "configs/feature_capacity.json").read_text())
    config.update(validation_seasons=[2016], capacities=[32, 128], threads=1)
    monkeypatch.setattr(capacity, "ROUTES", {"M_rankings": ("M", "full")})
    columns = candidate_blocks()["full"]
    rng = np.random.default_rng(29)
    frame = pd.DataFrame(0.0, index=range(40), columns=columns)
    active = ["diff_seed", "diff_strength", "diff_recent_strength"]
    frame[active] = rng.normal(size=(40, 3))
    frame["Season"] = np.repeat([2013, 2014, 2015, 2016, 2026], 8)
    frame["Gender"] = "M"
    frame["DayNum"] = 134
    frame["Team1ID"] = np.tile(np.arange(1001, 1017, 2), 5)
    frame["Team2ID"] = frame.Team1ID + 1
    frame["ID"] = (
        frame.Season.astype(str) + "_" + frame.Team1ID.astype(str) + "_" + frame.Team2ID.astype(str)
    )
    frame["y"] = np.tile([0, 1], 20)
    # These invalid targets must be removed before validation, fitting or scoring.
    frame.loc[frame.Season == 2026, "y"] = 999
    upstream = tmp_path / "features"
    upstream.mkdir()
    frame.to_parquet(upstream / "features.parquet", index=False)
    feature_key, run_key = "a" * 64, "b" * 64
    store = TaskStore(upstream, feature_key, EventLog(upstream / "events.jsonl"))
    train, valid = frame.query("Season < 2016"), frame.query("Season == 2016")
    for model_name in config["models"]:

        def reference(target, model_name=model_name):
            with threadpool_limits(limits=1):
                model, p = fit_fold(train, valid, active, model_name, config["seed"])
            joblib.dump({"estimator": model, "features": active}, target / "model.joblib")
            valid[capacity.KEYS].assign(p=p).to_parquet(target / "predictions.parquet", index=False)
            model.screen.audit_.to_csv(target / "screening.csv", index=False)
            atomic_json(
                target / "fold.json",
                {
                    "train_seasons": [2013, 2014, 2015],
                    "requested_features": columns,
                    "retained_count": len(active),
                },
            )
            return [
                target / name
                for name in ["model.joblib", "predictions.parquet", "screening.csv", "fold.json"]
            ]

        store.task(f"fold_m_2016_full_{model_name}", reference)
    output = tmp_path / "run"
    output.mkdir()
    inputs = {"config": config, "feature_fingerprint": feature_key}
    capacity._run(upstream, output, run_key, inputs)
    summary = json.loads((output / "summary.json").read_text())
    assert summary["fit_tasks"] == 12 and summary["new_fits"] == 10
    assert summary["inherited_reference_fits"] == 2
    before = {p: digest(p) for p in output.glob("*/model.joblib")}
    prediction_hash = digest(output / "predictions.csv")
    assert pd.read_csv(output / "predictions.csv").Season.max() == 2016
    choices = pd.read_csv(output / "selection.csv")
    assert choices.history_last_season.eq(2015).all()
    assert choices.history_seasons.eq(2).all()

    def forbidden(*args, **kwargs):
        raise AssertionError("Completed fits must be restored, not repeated")

    monkeypatch.setattr(capacity, "fit_capacity", forbidden)
    capacity._run(upstream, output, run_key, inputs)
    assert before == {p: digest(p) for p in before}
    assert prediction_hash == digest(output / "predictions.csv")
