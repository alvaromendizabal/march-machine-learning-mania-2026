"""Verify real portfolio evidence and reject plausible population/lineage mistakes."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from march_mania.publication import portfolio

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    folder = ROOT / "reports/model_comparison"
    return (
        pd.read_csv(folder / "predictions.csv"),
        pd.read_csv(folder / "selection.csv"),
        pd.read_csv(folder / "ensemble_weights.csv"),
        json.loads((ROOT / portfolio.CONFIG).read_text()),
    )


def test_published_catalog_is_reproducible_without_training_or_private_inputs(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Catalog publication must not train or open private parquet inputs")

    monkeypatch.setattr(portfolio.inference, "fit_model", forbid)
    monkeypatch.setattr(pd, "read_parquet", forbid)
    files = portfolio.publication(ROOT)
    portfolio.check(ROOT, files)
    manifest = json.loads(files["manifest.json"])
    assert manifest["candidate_plans"] == manifest["distinct_development_vectors"] == 50
    assert manifest["component_streams"] == 15
    assert manifest["selection_records"] == 95
    assert manifest["physical_development_games_per_candidate"] == 649
    assert manifest["submission_files_generated"] == manifest["new_model_fits"] == 0
    assert manifest["final_hyperparameters_frozen"] is False
    assert manifest["generation_status"] == "not_started"


def test_all_pairings_match_physical_games_and_known_development_leader(inputs):
    tables = portfolio.catalog(*inputs)
    candidates = tables["candidate_catalog.csv"]
    assert candidates.is_reference.sum() == 1
    leader = candidates.loc[candidates.candidate_id == "m_pooled_blend__w_logistic"].iloc[0]
    assert leader.men_brier == pytest.approx(0.1883238669167293, abs=1e-12)
    assert leader.women_brier == pytest.approx(0.1448228270179444, abs=1e-12)
    assert leader.brier == pytest.approx((334 * leader.men_brier + 315 * leader.women_brier) / 649)
    assert len(tables["metrics_by_season.csv"]) == 250
    assert len(tables["prediction_diversity.csv"]) == 1225
    assert tables["prediction_diversity.csv"].mean_absolute_difference.gt(0).all()
    shuffled = portfolio.catalog(
        inputs[0].sample(frac=1, random_state=10),
        inputs[1].sample(frac=1, random_state=20),
        inputs[2].sample(frac=1, random_state=30),
        inputs[3],
    )
    for name in tables:
        pd.testing.assert_frame_equal(tables[name], shuffled[name])


@pytest.mark.parametrize(
    "change", ["duplicate", "missing", "target", "future", "nan", "infinity", "range"]
)
def test_invalid_or_contaminated_development_rows_fail(inputs, change):
    predictions, selection, weights, config = inputs
    row = predictions.index[
        (predictions.Gender == "M") & (predictions.block == "M") & (predictions.model == "hist_raw")
    ][0]
    if change == "duplicate":
        predictions = pd.concat([predictions, predictions.loc[[row]]])
    elif change == "missing":
        predictions = predictions.drop(index=row)
    elif change == "target":
        predictions.loc[row, "y"] = 1 - predictions.loc[row, "y"]
    elif change == "future":
        predictions.loc[row, "Season"] = 2026
    else:
        predictions.loc[row, "p"] = {"nan": np.nan, "infinity": np.inf, "range": 1.01}[change]
    with pytest.raises(ValueError):
        portfolio.aligned_streams(predictions, selection, weights, config)


@pytest.mark.parametrize(
    "change", ["future_history", "missing_history", "candidate_family", "duplicate_history"]
)
def test_selection_records_cannot_hide_leakage_or_missing_choices(inputs, change):
    predictions, selection, weights, config = inputs
    row = selection.index[
        (selection.Gender == "M") & (selection.route == "M") & (selection.family == "rank_logistic")
    ][0]
    if change == "future_history":
        selection.loc[row, "history_last_season"] = selection.loc[row, "Season"]
    elif change == "missing_history":
        selection.loc[row, "history_seasons"] -= 1
    elif change == "candidate_family":
        selection.loc[row, "candidate"] = "logistic_strength_1"
    else:
        selection = pd.concat([selection, selection.loc[[row]]])
    with pytest.raises(ValueError):
        portfolio.aligned_streams(predictions, selection, weights, config)


@pytest.mark.parametrize("change", ["missing", "invalid", "wrong_prediction"])
def test_blend_is_recomputed_from_recorded_raw_components(inputs, change):
    predictions, selection, weights, config = inputs
    row = weights.index[(weights.Gender == "M") & (weights.route == "pooled_common")][0]
    if change == "missing":
        weights = weights.drop(index=row)
    elif change == "invalid":
        weights.loc[row, "weight"] = -0.1
    else:
        row = predictions.index[
            (predictions.Gender == "M")
            & (predictions.block == "pooled_common")
            & (predictions.model == "blend")
        ][0]
        predictions.loc[row, "p"] += 0.001
    with pytest.raises(ValueError):
        portfolio.aligned_streams(predictions, selection, weights, config)


def test_duplicate_prediction_vectors_are_not_counted_as_more_candidates(inputs):
    predictions, selection, weights, config = inputs
    source = (
        predictions.loc[
            (predictions.Gender == "W")
            & (predictions.block == "W")
            & (predictions.model == "logistic_raw")
        ]
        .set_index("ID")
        .p
    )
    rows = (
        (predictions.Gender == "W")
        & (predictions.block == "pooled_common")
        & (predictions.model == "logistic_raw")
    )
    predictions.loc[rows, "p"] = predictions.loc[rows, "ID"].map(source)
    with pytest.raises(ValueError, match="distinct"):
        portfolio.catalog(predictions, selection, weights, config)


@pytest.mark.parametrize(
    "change", ["future", "route", "family", "duplicate", "reference", "calibration", "unsafe_id"]
)
def test_changed_contract_is_rejected(inputs, change):
    config = copy.deepcopy(inputs[3])
    stream = config["streams"]["M"][0]
    if change == "future":
        config["development_seasons"].append(2026)
    elif change == "route":
        stream["route"] = "W"
    elif change == "family":
        stream["family"] = "unrun_neural_network"
    elif change == "duplicate":
        config["streams"]["M"][1] = stream.copy()
    elif change == "reference":
        config["reference"]["M"] = "m_hist"
    elif change == "unsafe_id":
        stream["id"] = "../file"
    else:
        config["calibration"] = "leaderboard_temperature"
    with pytest.raises(ValueError):
        portfolio.validate_config(config)


def test_game_weighted_and_mean_season_brier_are_distinct():
    rows = pd.DataFrame({"Season": [2016, 2017, 2017], "y": [1, 0, 1], "p": [0.1, 0.2, 0.8]})
    result = portfolio.metrics(rows)
    assert result["brier"] == pytest.approx(0.89 / 3)
    assert result["mean_season_brier"] == pytest.approx((0.81 + 0.04) / 2)


def test_changed_or_missing_saved_evidence_fails(tmp_path):
    files = {
        p.name: p.read_bytes()
        for p in (ROOT / portfolio.REPORT).iterdir()
        if p.suffix in {".json", ".csv"}
    }
    folder = tmp_path / portfolio.REPORT
    folder.mkdir(parents=True)
    for name, content in files.items():
        (folder / name).write_bytes(content)
    portfolio.check(tmp_path, files)
    target = folder / "candidate_catalog.csv"
    target.write_bytes(target.read_bytes() + b"corruption")
    with pytest.raises(ValueError, match="candidate_catalog"):
        portfolio.check(tmp_path, files)
    target.unlink()
    with pytest.raises(ValueError, match="candidate_catalog"):
        portfolio.check(tmp_path, files)
