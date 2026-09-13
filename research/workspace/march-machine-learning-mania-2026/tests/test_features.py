from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from march_mania.features import feature_blocks, matchups, read_official, snapshot, validate_games
from march_mania.research import fit_fold, symmetric_probability, validate_config


def make_snapshot(tables, season=2016):
    return snapshot(
        tables["RegularSeasonCompactResults"],
        tables["RegularSeasonDetailedResults"],
        tables["NCAATourneySeeds"],
        "M",
        season,
        132,
        20,
        30,
    )


def test_cutoff_and_future_seasons_cannot_change_snapshot(raw):
    tables = read_official(raw)[0]["M"]
    before = make_snapshot(tables)
    for name in ("RegularSeasonCompactResults", "RegularSeasonDetailedResults"):
        future = tables[name].loc[tables[name].Season == 2016].copy()
        future.DayNum = 150
        future.WScore = 150
        tables[name] = pd.concat([tables[name], future])
        tables[name].loc[tables[name].Season > 2016, "WScore"] = 500
    pd.testing.assert_frame_equal(before, make_snapshot(tables))


def test_tournament_outcomes_are_labels_only(raw):
    tables = read_official(raw)[0]["M"]
    teams = make_snapshot(tables)
    labels = tables["NCAATourneyCompactResults"].query("Season == 2016").copy()
    first = matchups(teams, labels, "M")
    labels[["WTeamID", "LTeamID"]] = labels[["LTeamID", "WTeamID"]].to_numpy()
    second = matchups(teams, labels, "M")
    pd.testing.assert_frame_equal(first.drop(columns="y"), second.drop(columns="y"))
    np.testing.assert_array_equal(first.y, 1 - second.y)


def test_pair_features_change_sign_when_snapshots_swap(raw):
    tables = read_official(raw)[0]["M"]
    teams = make_snapshot(tables)
    labels = tables["NCAATourneyCompactResults"].query("Season == 2016").head(1)
    a, b = int(labels.WTeamID.iloc[0]), int(labels.LTeamID.iloc[0])
    swapped = teams.copy()
    swapped.TeamID = swapped.TeamID.replace({a: b, b: a})
    first = matchups(teams, labels, "M")
    second = matchups(swapped, labels, "M")
    np.testing.assert_allclose(first[feature_blocks()["full"]], -second[feature_blocks()["full"]])


def test_nonlinear_matchup_is_not_sum_of_differences(raw):
    tables = read_official(raw)[0]["M"]
    teams = make_snapshot(tables)
    labels = tables["NCAATourneyCompactResults"].query("Season == 2016")
    result = matchups(teams, labels, "M")
    design = np.column_stack([result.diff_efg, result.diff_opp_efg, np.ones(len(result))])
    residual = (
        result.matchup_efg - design @ np.linalg.lstsq(design, result.matchup_efg, rcond=None)[0]
    )
    assert np.linalg.norm(residual) > 1e-8


def test_invalid_games_fail_before_modeling(raw):
    frame = pd.read_csv(raw / "MRegularSeasonCompactResults.csv")
    with pytest.raises(ValueError, match="Duplicate"):
        validate_games(pd.concat([frame, frame.head(1)]))
    frame.loc[0, "WScore"] = -1
    with pytest.raises(ValueError, match="nonnegative"):
        validate_games(frame)


def test_missing_snapshot_is_not_silently_imputed(raw):
    tables = read_official(raw)[0]["M"]
    teams = make_snapshot(tables).query("TeamID != 1001")
    with pytest.raises(ValueError, match="Missing pre-tournament"):
        matchups(teams, tables["NCAATourneyCompactResults"].query("Season == 2016"), "M")


@pytest.mark.parametrize("model", ["logistic", "hist"])
def test_fold_symmetry_and_temporal_guard(raw, model):
    tables = read_official(raw)[0]["M"]
    teams = pd.concat([make_snapshot(tables, season) for season in [2015, 2016]])
    frame = matchups(
        teams, tables["NCAATourneyCompactResults"].query("Season in [2015, 2016]"), "M"
    )
    train, valid = frame.query("Season == 2015"), frame.query("Season == 2016")
    from threadpoolctl import threadpool_limits

    with threadpool_limits(limits=1):
        estimator, p = fit_fold(train, valid, feature_blocks()["full"], model, 19)
        reverse = symmetric_probability(estimator, -valid[feature_blocks()["full"]].to_numpy())
    np.testing.assert_allclose(p + reverse, 1, atol=1e-14)
    with pytest.raises(ValueError, match="temporal"):
        fit_fold(valid, valid, ["diff_seed"], model, 19)
    with pytest.raises(ValueError, match="Unknown feature"):
        fit_fold(train, valid, ["y"], model, 19)


@pytest.mark.parametrize(
    "field,value",
    [
        ("validation_seasons", [2022]),
        ("validation_seasons", [2016, 2016]),
        ("feature_cutoff_day", 150),
        ("ridge_alpha", 0),
        ("threads", 0),
    ],
)
def test_invalid_protocol_rejected(config, field, value):
    config[field] = value
    with pytest.raises(ValueError):
        validate_config(config)
