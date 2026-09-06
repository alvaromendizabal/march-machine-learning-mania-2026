from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from threadpoolctl import threadpool_limits

from march_mania.advanced_features import (
    advanced_snapshot,
    candidate_blocks,
    efficiency_ratings,
    elo_snapshot,
    pair_features,
    possession_games,
    ranking_snapshot,
    shooting_posteriors,
)
from march_mania.feature_store import labeled_pairs, sample_pairs
from march_mania.features import read_official
from march_mania.research import fit_fold, symmetric_probability


def test_adjusted_model_recovers_known_offense_and_defense():
    offense, defense = np.array([-6.0, -2.0, 2.0, 6.0]), np.array([3.0, -3.0, 1.0, -1.0])
    rows = [
        {
            "TeamID": a,
            "OpponentID": b,
            "DayNum": day,
            "home": 0,
            "clean": True,
            "efficiency": 100 + offense[a] - defense[b],
        }
        for day in range(80, 121, 10)
        for a in range(4)
        for b in range(4)
        if a != b
    ]
    result = efficiency_ratings(pd.DataFrame(rows), 0.00001, 132).set_index("TeamID")
    np.testing.assert_allclose(result.adj_offense, offense, atol=0.0001)
    np.testing.assert_allclose(result.adj_defense, defense, atol=0.0001)
    assert result.residual_sd.max() < 0.0001


def test_shared_possessions_and_overtime_normalization(raw):
    games = pd.read_csv(raw / "MRegularSeasonDetailedResults.csv").head(1)
    regulation = possession_games(games)
    games.NumOT = 1
    overtime = possession_games(games)
    assert overtime.possessions.nunique() == 1
    np.testing.assert_allclose(overtime.tempo / regulation.tempo, 40 / 45)
    np.testing.assert_allclose(overtime.efficiency, regulation.efficiency)
    games.NumOT = -1
    with pytest.raises(ValueError, match="overtime"):
        possession_games(games)


def test_shooting_posterior_shrinks_sparse_samples(raw):
    games = pd.read_csv(raw / "MRegularSeasonDetailedResults.csv").query("Season == 2016")
    long = possession_games(games)
    posterior = shooting_posteriors(long)
    for name in posterior:
        if name.endswith("posterior"):
            assert posterior[name].between(0, 1).all()
        if name.endswith("uncertainty"):
            assert posterior[name].between(0, 0.5).all()
    zero = long.copy()
    zero[["FGM3", "FGA3", "opp_FGM3", "opp_FGA3"]] = 0
    assert np.isfinite(shooting_posteriors(zero).to_numpy()).all()
    duplicated = shooting_posteriors(pd.concat([long] * 10))
    assert (duplicated.three_uncertainty < posterior.three_uncertainty).all()
    with pytest.raises(ValueError, match="positive"):
        shooting_posteriors(long, 0)


def test_full_snapshot_ignores_current_tournament_and_future_data(raw):
    tables = read_official(raw)[0]["M"]
    original = advanced_snapshot(tables, "M", 2016)
    labels = tables["NCAATourneyCompactResults"]
    labels.loc[labels.Season >= 2016, "WTeamID"] = 9999
    for name in ["RegularSeasonCompactResults", "RegularSeasonDetailedResults"]:
        future = tables[name].loc[tables[name].Season == 2016].copy()
        future.DayNum = 150
        future.WScore = 200
        tables[name] = pd.concat([tables[name], future])
        tables[name].loc[tables[name].Season > 2016, "WScore"] = 500
    pd.testing.assert_frame_equal(original, advanced_snapshot(tables, "M", 2016))


def test_elo_is_independent_of_same_day_row_order(raw):
    games = pd.read_csv(raw / "MRegularSeasonCompactResults.csv")
    games.DayNum = 10 * (games.DayNum // 10)
    first = elo_snapshot(games, 2016, 132)
    second = elo_snapshot(games.sample(frac=1, random_state=1), 2016, 132)
    pd.testing.assert_frame_equal(first, second)


def test_rankings_use_asof_dates_staleness_and_matched_systems():
    rows = [
        {
            "Season": 2016,
            "RankingDayNum": day,
            "SystemName": system,
            "TeamID": team,
            "OrdinalRank": rank,
        }
        for day in [100, 130, 140]
        for system in ["A", "B"]
        for team, rank in [(1, 1), (2, 2)]
    ]
    ranks = pd.DataFrame(rows)
    first = ranking_snapshot(ranks, 2016, 132)
    ranks.loc[ranks.RankingDayNum == 140, "OrdinalRank"] = 9999
    pd.testing.assert_frame_equal(first, ranking_snapshot(ranks, 2016, 132))
    assert first.rank_momentum.eq(0).all()
    assert first.rank_age.eq(2).all()
    assert ranking_snapshot(ranks, 2016, 120).empty
    with pytest.raises(ValueError, match="Duplicate"):
        ranking_snapshot(pd.concat([ranks, ranks.head(1)]), 2016, 132)


def test_pair_features_and_model_probabilities_reverse_exactly(raw):
    tables = read_official(raw)[0]["M"]
    teams = pd.concat([advanced_snapshot(tables, "M", year) for year in [2015, 2016]])
    pairs = labeled_pairs(tables, "M", [2015, 2016])
    matrix = pair_features(teams, pairs)
    matrix["y"] = pairs.y.to_numpy()
    a, b = int(pairs.Team1ID.iloc[0]), int(pairs.Team2ID.iloc[0])
    swapped = teams.copy()
    swapped.TeamID = swapped.TeamID.replace({a: b, b: a})
    columns = candidate_blocks(False)["full"]
    np.testing.assert_allclose(
        pair_features(teams, pairs.head(1))[columns],
        -pair_features(swapped, pairs.head(1))[columns],
        equal_nan=True,
    )
    with threadpool_limits(limits=1):
        model, p = fit_fold(
            matrix.query("Season == 2015"),
            matrix.query("Season == 2016"),
            columns,
            "logistic",
            2026,
        )
        reverse = symmetric_probability(model, -matrix.query("Season == 2016")[columns].to_numpy())
    np.testing.assert_allclose(p + reverse, 1, atol=1e-14)
    assert not {"y", "ID", "Season", "Team1ID", "Team2ID"}.intersection(columns)
    with pytest.raises(ValueError, match="Missing snapshot"):
        pair_features(teams.query("TeamID != @a"), pairs)


def test_sample_submission_identity_and_order(raw):
    tables = read_official(raw)[0]["M"]
    teams = advanced_snapshot(tables, "M", 2016)
    sample = pd.DataFrame({"ID": ["2016_1003_1008", "2016_1001_1002"], "Pred": [0.5, 0.5]})
    result = pair_features(teams, sample_pairs(sample, teams))
    assert result.ID.tolist() == sample.ID.tolist()
    sample.loc[0, "ID"] = "2016_1001_9999"
    with pytest.raises(ValueError, match="unknown"):
        sample_pairs(sample, teams)
