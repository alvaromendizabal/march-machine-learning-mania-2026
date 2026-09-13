"""Final portfolio fitting, temporal isolation, routing and checkpoint recovery."""

from __future__ import annotations

import copy
import json
import shutil
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from march_mania import modeling
from march_mania.publication import inference, production, production_release
from march_mania.runtime import EventLog, TaskStore, atomic_json, digest, fingerprint


@pytest.fixture(scope="module")
def data():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "configs/prediction_portfolio.json").read_text())
    model_config = json.loads((root / "configs/model_comparison.json").read_text())
    settings = {**json.loads((root / "configs/inference.json").read_text()), "threads": 1}
    rng = np.random.default_rng(71)
    history, games, matchups, team_rows = [], [], [], []
    columns = sorted(
        {
            c
            for route in ("M", "W", "pooled_common")
            for candidate in modeling.candidates(route)
            for c in modeling.columns_for(candidate)
        }
    )
    for gender, base in [("M", 1100), ("W", 3100)]:
        for season in [*range(2013, 2020), *range(2021, 2027)]:
            for i in range(20):
                row = {
                    "Gender": gender,
                    "Season": season,
                    "DayNum": 136 + i,
                    "ID": f"{season}_{base + i}_{base + i + 30}",
                    "y": i % 2,
                    **dict(zip(columns, rng.normal(size=len(columns)), strict=True)),
                }
                games.append(row)
                if season == 2026:
                    pair = {k: v for k, v in row.items() if k not in {"DayNum", "y"}}
                    if i % 2:
                        pair["diff_seed"] = np.nan
                    matchups.append(pair)
                    for team in [base + i, base + i + 30]:
                        team_rows.append({"Gender": gender, "Season": season, "TeamID": team})
                if season in config["development_seasons"]:
                    for route in (gender, "pooled_common"):
                        for j, candidate in enumerate(modeling.candidates(route)):
                            history.append(
                                {k: row[k] for k in modeling.KEYS}
                                | {
                                    "candidate": candidate.name,
                                    "family": candidate.family,
                                    "route": route,
                                    "p": 0.4 + 0.2 * row["y"] + j * 0.0001,
                                }
                            )
    requested = pd.DataFrame(matchups)
    return (
        pd.DataFrame(history),
        pd.DataFrame(games),
        requested,
        pd.DataFrame(team_rows),
        pd.DataFrame({"ID": requested.ID, "Pred": 0.5}),
        config,
        model_config,
        settings,
    )


def recipe_for(data):
    return production.freeze(data[0], data[5], data[6])


def test_freeze_ignores_future_results_and_matches_reference(data):
    recipe = recipe_for(data)
    future = data[0].assign(Season=2026, y=-99, p=np.nan)
    assert recipe == production.freeze(pd.concat([data[0], future]), data[5], data[6])
    production.validate_recipe(recipe)
    reference = inference.freeze_recipe(data[0], data[7])
    for gender, stream in [("M", "m_rank_logistic"), ("W", "w_logistic")]:
        chosen = next(s for s in recipe["streams"] if s["id"] == stream)
        component = recipe["components"][chosen["components"][0]["id"]]
        assert component["candidate"] == reference["genders"][gender]["candidate"]
    assert len(recipe["pairs"]) == len({p["id"] for p in recipe["pairs"]}) == 50


@pytest.mark.parametrize("change", ["duplicate", "missing_game", "conflicting_label"])
def test_incomplete_candidate_comparisons_fail(data, change):
    history = data[0].copy()
    selected = history.index[(history.family == "rank_logistic") & (history.Gender == "M")][0]
    if change == "duplicate":
        history = pd.concat([history, history.loc[[selected]]])
    elif change == "missing_game":
        history = history.drop(index=selected)
    else:
        history.loc[selected, "y"] = 1 - history.loc[selected, "y"]
    with pytest.raises(ValueError):
        production.freeze(history, data[5], data[6])


@pytest.mark.parametrize("family", ["logistic", "hist", "xgboost", "lightgbm"])
def test_real_estimators_ignore_future_labels_and_seed_free_inputs(data, family):
    candidate = next(c for c in modeling.candidates("M") if c.family == family)
    component = {"population": "M", "candidate": asdict(candidate)}
    first, audit = production.fit_component(data[1], component, "seed_free", data[7])
    altered = data[1].copy()
    altered.loc[altered.Season == 2026, "y"] = -99
    for column in modeling.columns_for(candidate):
        if "seed" in column:
            altered[column] = 1e12
    second, _ = production.fit_component(altered, component, "seed_free", data[7])
    requested = data[2].loc[data[2].Gender == "M"]
    p = production.forecast(first["model"], requested, first["features"], 1)
    q = production.forecast(second["model"], requested, second["features"], 1)
    np.testing.assert_array_equal(p, q)
    reverse = requested.copy()
    reverse[first["features"]] *= -1
    np.testing.assert_allclose(
        p + production.forecast(first["model"], reverse, first["features"], 1),
        1,
        rtol=0,
        atol=1e-12,
    )
    assert audit["training_max_season"] == 2025
    assert audit["training_games"] == 240
    assert not any("seed" in c for c in first["features"])
    assert np.isfinite(p).all()
    if family == "logistic":
        train = data[1].loc[(data[1].Gender == "M") & (data[1].Season < 2026)]
        reference_columns = production.feature_columns(component, "seed_free")
        reference = inference.fit_model(
            train, requested, reference_columns, candidate.parameter, data[7]
        )
        np.testing.assert_array_equal(
            p, inference.forecast(reference, requested, reference_columns, 1)
        )


def test_seed_only_missing_seed_route_is_explicitly_neutral(data):
    candidate = next(c for c in modeling.candidates("pooled_common") if c.family == "seed")
    saved, audit = production.fit_component(
        data[1],
        {"population": "pooled_common", "candidate": asdict(candidate)},
        "seed_free",
        data[7],
    )
    assert saved == {"model": None, "features": []}
    assert not audit["fitted"] and audit["constant"] == 0.5


@pytest.mark.parametrize("change", ["weight", "pair", "component", "future_selection"])
def test_recipe_mutations_are_rejected(data, change):
    recipe = copy.deepcopy(recipe_for(data))
    if change == "weight":
        recipe["streams"][0]["components"][0]["weight"] = 0.99
    elif change == "pair":
        recipe["pairs"][-1] = recipe["pairs"][0]
    elif change == "component":
        next(iter(recipe["components"].values()))["candidate"]["parameter"] = 999
    else:
        recipe["selection_seasons"].append(2026)
    with pytest.raises(ValueError):
        production.validate_recipe(recipe)


def test_full_fifty_file_execution_and_recovery(data, tmp_path, monkeypatch):
    recipe = recipe_for(data)
    root = tmp_path / "repository"
    public = root / production.REPORT
    source_root = Path(__file__).resolve().parents[1]
    receipts = {}
    for name, members in production.production_inputs.MEMBERS.items():
        archive = json.loads((source_root / "reports" / name / "run.json").read_text())["archive"]
        receipts[name] = {"archive": archive, "sha256": {p: "0" * 64 for p in members}}
        atomic_json(root / "reports" / name / "run.json", {"archive": archive})
    atomic_json(root / "configs/prediction_portfolio.json", data[5])
    atomic_json(public / "recipe.json", recipe)
    atomic_json(public / "input_receipts.json", receipts)
    assert production_release.check(root)["submission_files"] == 0
    identity = {"recipe": recipe, "inputs": receipts, "source": {}}
    key = fingerprint(identity)
    # Full feature mathematics is separately tested; this fixture supplies a
    # compact label-free matrix while retaining actual fitting and CSV assembly.
    indexed = data[2].set_index("ID", drop=False)
    monkeypatch.setattr(
        production,
        "pair_features",
        lambda teams, pairs: indexed.loc[
            pairs.Season.astype(str)
            + "_"
            + pairs.Team1ID.astype(str)
            + "_"
            + pairs.Team2ID.astype(str)
        ].reset_index(drop=True),
    )
    run = tmp_path / "run"
    store = TaskStore(run, key, EventLog(run / "events.jsonl"))
    atomic_json(run / "manifest.json", {"fingerprint": key, "inputs": identity})
    result = production.execute(data[1], data[3], data[4], recipe, store, data[7])
    assert result["submission_files"] == result["distinct_submission_vectors"] == 50
    files = list(run.glob("csv_*/submission.csv"))
    before = {str(p.relative_to(run)): digest(p) for p in files}
    assert len(before) == 50 and result["neutral_routes"] == 1

    def forbid(*args, **kwargs):
        raise AssertionError("Completed fits must not rerun")

    monkeypatch.setattr(production, "fit_component", forbid)
    production.execute(data[1], data[3], data[4], recipe, store, data[7])
    # A damaged probability chunk is repaired without refitting any component.
    next(run.glob("predict_*/predictions.parquet")).write_bytes(b"corrupt")
    production.execute(data[1], data[3], data[4], recipe, store, data[7])
    assert {str(p.relative_to(run)): digest(p) for p in files} == before
    atomic_json(run / "summary.json", result)
    for path in (run / "publication").iterdir():
        if path.name != "checkpoint.json" and path.suffix in {".csv", ".json"}:
            shutil.copyfile(path, public / path.name)
    atomic_json(
        public / "run.json",
        {
            "fingerprint": key,
            "inputs": identity,
            "sha256": {
                p.name: digest(p)
                for p in (run / "publication").iterdir()
                if p.name != "checkpoint.json" and p.suffix in {".csv", ".json"}
            },
        },
    )
    assert production_release.check(root)["submission_files"] == 50
    archive = tmp_path / "archive.zip"
    record = production_release.pack(root, run, archive)
    atomic_json(public / "archive.json", {**record, "status": "uploaded"})
    recovered = production_release.recover(root, tmp_path / "recovered", archive)
    assert {
        str(p.relative_to(recovered)): digest(p) for p in recovered.glob("csv_*/submission.csv")
    } == before
    production.execute(
        data[1],
        data[3],
        data[4],
        recipe,
        TaskStore(recovered, key, EventLog(recovered / "replay.jsonl")),
        data[7],
    )
    assert '"event": "task_started"' not in (recovered / "replay.jsonl").read_text()
    (public / "routes.csv").write_text("corrupt")
    with pytest.raises(ValueError, match="artifact changed"):
        production_release.check(root)


def test_failed_fit_does_not_publish_a_success(data, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("interrupted")

    monkeypatch.setattr(production, "fit_component", fail)
    with pytest.raises(RuntimeError, match="interrupted"):
        production.execute(
            data[1],
            data[3],
            data[4],
            recipe_for(data),
            TaskStore(tmp_path, "test", EventLog(tmp_path / "events.jsonl")),
            data[7],
        )
    assert not list(tmp_path.rglob("checkpoint.json"))
