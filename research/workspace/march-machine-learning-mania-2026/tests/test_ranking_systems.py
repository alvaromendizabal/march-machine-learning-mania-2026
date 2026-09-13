"""Temporal source, representation, matched-control and recovery contracts."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from threadpoolctl import threadpool_limits

from march_mania.advanced_features import candidate_blocks
from march_mania.publication import ranking_systems as study
from march_mania.research import fit_fold, symmetric_probability
from march_mania.runtime import EventLog, TaskStore, atomic_json, digest


def config():
    return json.loads(
        (Path(__file__).resolve().parents[1] / "configs/ranking_systems.json").read_text()
    )


def source():
    return pd.DataFrame(
        [
            (year, day, system, team, rank)
            for year in range(2012, 2017)
            for day in [68, 98, 125, 128, 133]
            for system in ["AAA", "BBB"]
            for team, rank in [(1001, 1), (1002, 2), (1003, 3), (1004, 4)]
        ],
        columns=["Season", "RankingDayNum", "SystemName", "TeamID", "OrdinalRank"],
    )


def test_system_vocabulary_and_snapshots_ignore_future_editions_and_years():
    c, raw = config(), source()
    systems = study.system_catalog(raw, c)
    assert systems == ["AAA", "BBB"]
    snapshot = study.system_snapshot(raw, 2013, systems, c)
    changed = raw.copy()
    future = (changed.Season > 2013) | ((changed.Season == 2013) & (changed.RankingDayNum > 132))
    changed.loc[future, "OrdinalRank"] = -999
    changed.loc[changed.Season > 2012, "SystemName"] = changed.loc[
        changed.Season > 2012, "SystemName"
    ].replace({"BBB": "NEW"})
    assert study.system_catalog(changed, c) == systems
    changed = raw.copy()
    changed.loc[future, "OrdinalRank"] = -999
    pd.testing.assert_frame_equal(study.system_snapshot(changed, 2013, systems, c), snapshot)
    assert snapshot.loc[1001, "diff_system_AAA_level"] == 1
    assert snapshot.loc[1004, "diff_system_AAA_level"] == 0
    assert snapshot.filter(like="deviation").eq(0).all().all()
    assert snapshot.filter(like="change_").eq(0).all().all()
    assert np.isfinite(snapshot.to_numpy()).all()


def test_absence_from_latest_edition_is_not_backfilled_and_matchups_reverse():
    raw, c = source(), config()
    raw = raw.loc[
        ~(
            (raw.Season == 2013)
            & (raw.RankingDayNum == 128)
            & (raw.SystemName == "BBB")
            & (raw.TeamID == 1001)
        )
    ]
    teams = study.system_snapshot(raw, 2013, ["AAA", "BBB", "OLD"], c)
    assert np.isnan(teams.loc[1001, "diff_system_BBB_level"])
    assert teams.loc[1001, "diff_system_BBB_available"] == 0
    assert teams.filter(like="OLD").drop(columns="diff_system_OLD_available").isna().all().all()
    matrix = pd.DataFrame({"Season": [2013], "ID": ["game"], "Team1ID": [1001], "Team2ID": [1002]})
    forward = study.add_system_matchups(matrix, teams)
    swapped = study.add_system_matchups(matrix.assign(Team1ID=1002, Team2ID=1001), teams)
    np.testing.assert_allclose(forward[teams.columns], -swapped[teams.columns], equal_nan=True)
    assert forward.diff_system_BBB_available.iloc[0] == -1
    with pytest.raises(ValueError, match="Duplicate"):
        study.add_system_matchups(pd.concat([matrix, matrix]), teams)


def example():
    rng = np.random.default_rng(111)
    frame = pd.DataFrame(
        rng.normal(size=(120, 6)),
        columns=[
            "diff_seed",
            "diff_strength",
            "diff_recent_strength",
            "diff_system_A_level",
            "diff_system_B_level",
            "diff_system_C_level",
        ],
    )
    frame["Season"] = np.repeat([2013, 2014], 60)
    frame["y"] = (frame.diff_strength + rng.normal(size=120) > 0).astype(int)
    frame.loc[::7, "diff_system_A_level"] = np.nan
    frame["diff_system_D_level"] = frame.diff_seed  # exact duplicate of a base signal
    frame["diff_system_E_level"] = np.nan
    return frame.iloc[:60].copy(), frame.iloc[60:].copy()


@pytest.mark.parametrize("learner", ["logistic", "hist"])
def test_no_addition_matches_existing_control_exactly(learner):
    train, valid = example()
    base = ["diff_seed", "diff_strength", "diff_recent_strength"]
    with threadpool_limits(limits=1):
        original, p = fit_fold(train, valid, base, learner, 2026)
        model, q = study.fit_systems(train, valid, base, [], "consensus", original.model, config())
        np.testing.assert_array_equal(p, q)
        np.testing.assert_allclose(
            q + symmetric_probability(model, -valid[base].to_numpy(float)), 1, atol=1e-14
        )


@pytest.mark.parametrize("mode", ["combined", "embedding"])
def test_representation_fits_only_training_and_saved_model_reloads(mode, tmp_path):
    train, valid = example()
    base = ["diff_seed", "diff_strength", "diff_recent_strength"]
    extra = [c for c in train if c.startswith("diff_system_")]
    c = config()
    c.update(additional_capacity=2, embedding_components=2)
    with threadpool_limits(limits=1):
        template, _ = fit_fold(train, valid, base, "logistic", 2026)
        model, p = study.fit_systems(train, valid, base, extra, mode, template.model, c)
        changed = valid.copy()
        changed[extra] *= 1000
        changed.y = 1 - changed.y
        second, _ = study.fit_systems(train, changed, base, extra, mode, template.model, c)
        np.testing.assert_array_equal(model.extra_indices, second.extra_indices)
        np.testing.assert_array_equal(model.model[-1].coef_, second.model[-1].coef_)
        if mode == "embedding":
            np.testing.assert_array_equal(model.embedding.components_, second.embedding.components_)
            assert model.embedding.n_components_ == 2
        else:
            assert model.extra_audit.set_index("index").loc[3, "status"] == "redundant_base"
            assert len(model.extra_indices) == 2
        path = tmp_path / "model.joblib"
        joblib.dump(model, path)
        np.testing.assert_array_equal(
            symmetric_probability(joblib.load(path), valid[base + extra].to_numpy(float)), p
        )
        np.testing.assert_allclose(
            p + symmetric_probability(model, -valid[base + extra].to_numpy(float)), 1, atol=1e-14
        )
        with pytest.raises(ValueError, match="schema"):
            model.predict_proba(np.zeros((2, 1)))


def test_nested_arm_selection_ignores_outer_and_future_labels(tmp_path):
    rows = [
        {
            "Gender": "M",
            "model": "logistic",
            "block": arm,
            "Season": year,
            "ID": str(i),
            "y": i % 2,
            "p": 0.5 if arm == "consensus" else 0.6,
        }
        for arm in study.ARMS
        for year in [2014, 2015, 2016, 2017]
        for i in range(6)
    ]
    frame = pd.DataFrame(rows)
    c = config()
    c["validation_seasons"] = [2016, 2017]
    study.summarize(frame, c, tmp_path)
    first = pd.read_csv(tmp_path / "selection.csv")
    altered = frame.copy()
    altered.loc[altered.Season >= 2016, "y"] = 1 - altered.loc[altered.Season >= 2016, "y"]
    study.summarize(altered, c, tmp_path)
    second = pd.read_csv(tmp_path / "selection.csv")
    pd.testing.assert_frame_equal(first.query("Season == 2016"), second.query("Season == 2016"))
    assert first.block.eq("consensus").all()


@pytest.mark.parametrize(
    "field,value",
    [
        ("validation_seasons", [2022]),
        ("feature_cutoff_day", 133),
        ("additional_capacity", 0),
        ("logit_clip", 0),
    ],
)
def test_invalid_protocol_is_rejected(field, value):
    c = config()
    study.validate_config(c)
    c[field] = value
    with pytest.raises(ValueError):
        study.validate_config(c)


def test_complete_study_excludes_future_labels_and_resumes_without_fitting(tmp_path, monkeypatch):
    c = config()
    c.update(validation_seasons=[2016], threads=1)
    rng = np.random.default_rng(10)
    columns = candidate_blocks()["full"]
    frame = pd.DataFrame(0.0, index=range(40), columns=columns)
    frame[["diff_seed", "diff_strength", "diff_recent_strength"]] = rng.normal(size=(40, 3))
    frame["Season"] = np.repeat([2013, 2014, 2015, 2016, 2026], 8)
    frame["Gender"], frame["DayNum"] = "M", 134
    frame["Team1ID"] = np.tile([1001, 1001, 1001, 1002, 1002, 1003, 1001, 1002], 5)
    frame["Team2ID"] = np.tile([1002, 1003, 1004, 1003, 1004, 1004, 1005, 1005], 5)
    frame["ID"] = (
        frame.Season.astype(str) + "_" + frame.Team1ID.astype(str) + "_" + frame.Team2ID.astype(str)
    )
    frame["y"] = np.tile([0, 1], 20)
    frame.loc[frame.Season == 2026, "y"] = 999
    upstream = tmp_path / "features"
    upstream.mkdir()
    frame.to_parquet(upstream / "features.parquet", index=False)
    raw = tmp_path / "MMasseyOrdinals.csv"
    source().to_csv(raw, index=False)
    feature_key, key = "a" * 64, "b" * 64
    tasks = TaskStore(upstream, feature_key, EventLog(upstream / "events.jsonl"))
    for block in ["rankings", "strength"]:
        for learner in c["models"]:

            def reference(target, block=block, learner=learner):
                base = candidate_blocks()[block]
                train, valid = frame.query("Season < 2016"), frame.query("Season == 2016")
                with threadpool_limits(limits=1):
                    model, p = fit_fold(train, valid, base, learner, c["seed"])
                joblib.dump({"estimator": model, "features": base}, target / "model.joblib")
                valid[study.KEYS].assign(p=p).to_parquet(
                    target / "predictions.parquet", index=False
                )
                model.screen.audit_.assign(feature=base).to_csv(
                    target / "screening.csv", index=False
                )
                atomic_json(
                    target / "fold.json",
                    {
                        "train_seasons": [2013, 2014, 2015],
                        "requested_features": base,
                        "retained_count": len(model.screen.indices_),
                    },
                )
                return [
                    target / n
                    for n in ["model.joblib", "predictions.parquet", "screening.csv", "fold.json"]
                ]

            tasks.task(f"fold_m_2016_{block}_{learner}", reference)
    output = tmp_path / "run"
    inputs = {"feature_fingerprint": feature_key, "config": c}
    study._run(upstream, raw, output, key, inputs)
    summary = json.loads((output / "summary.json").read_text())
    assert summary["fit_tasks"] == 48 and summary["inherited_reference_fits"] == 4
    before = {str(p): digest(p) for p in output.rglob("model.joblib")}
    predictions = digest(output / "predictions.csv")

    def forbidden(*args, **kwargs):
        raise AssertionError("Recovery must not refit")

    monkeypatch.setattr(study, "fit_systems", forbidden)
    study._run(upstream, raw, output, key, copy.deepcopy(inputs))
    assert before == {str(p): digest(p) for p in output.rglob("model.joblib")}
    assert predictions == digest(output / "predictions.csv")
    assert pd.read_csv(output / "predictions.csv").Season.max() == 2016
