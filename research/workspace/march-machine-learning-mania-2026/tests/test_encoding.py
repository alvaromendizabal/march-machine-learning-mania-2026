from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from march_mania.encoding import ENCODING_FEATURES, encode_history


def example():
    teams = pd.DataFrame(
        [
            {"Gender": "M", "Season": year, "TeamID": team, "seed": seed, "rank_consensus": rank}
            for year in range(2013, 2018)
            for team, seed, rank in [(1, 1, 1.0), (2, 16, 0.0), (3, 8, 0.5)]
        ]
    )
    games = pd.DataFrame(
        [{"Season": year, "DayNum": 136, "WTeamID": 1, "LTeamID": 2} for year in range(2013, 2018)]
    )
    return teams, games


def test_forward_encoding_has_known_posterior_and_prior_for_cold_start():
    teams, games = example()
    result, audit = encode_history(teams, games)
    first = result.query("Season == 2013")
    assert first.te_team_mean.eq(0.5).all()
    assert first.te_team_support.eq(0).all()
    second = result.query("Season == 2014").set_index("TeamID")
    assert second.loc[1, "te_team_mean"] == pytest.approx(11 / 21)
    assert second.loc[2, "te_team_mean"] == pytest.approx(10 / 21)
    assert second.loc[3, "te_team_mean"] == 0.5
    assert second.loc[1, "te_team_uncertainty"] < first.te_team_uncertainty.iloc[0]
    assert audit.loc[audit.history_max_season.notna()].eval("history_max_season < Season").all()
    assert np.isfinite(result[ENCODING_FEATURES]).all().all()


def test_current_and_future_labels_cannot_change_training_or_validation_encodings():
    teams, games = example()
    expected, _ = encode_history(teams, games)
    changed = games.copy()
    mask = changed.Season >= 2016
    changed.loc[mask, ["WTeamID", "LTeamID"]] = changed.loc[mask, ["LTeamID", "WTeamID"]].to_numpy()
    actual, _ = encode_history(teams, changed)
    pd.testing.assert_frame_equal(expected.query("Season <= 2016"), actual.query("Season <= 2016"))
    assert not expected.query("Season == 2017")[ENCODING_FEATURES].equals(
        actual.query("Season == 2017")[ENCODING_FEATURES]
    )
    # Removing the validation/future labels entirely produces identical past features.
    actual, _ = encode_history(teams, games.query("Season < 2016"))
    pd.testing.assert_frame_equal(expected.query("Season <= 2016"), actual.query("Season <= 2016"))


def test_historical_categories_do_not_use_current_seed_or_rank():
    teams, games = example()
    # Team 1 switches from seed 1 to seed 16; its past wins remain attributed to seed 1.
    teams.loc[(teams.Season == 2014) & (teams.TeamID == 1), ["seed", "rank_consensus"]] = [16, 0]
    result, _ = encode_history(teams, games)
    row = result.query("Season == 2014 and TeamID == 1").iloc[0]
    assert row.te_team_mean == pytest.approx(11 / 21)
    assert row.te_seed_mean == pytest.approx(10 / 21)
    assert row.te_rank_mean == pytest.approx(10 / 21)


def test_encoding_is_row_order_invariant_gender_isolated_and_missing_rank_stays_missing():
    teams, games = example()
    expected, _ = encode_history(teams, games)
    actual, _ = encode_history(teams.sample(frac=1), games.sample(frac=1))
    pd.testing.assert_frame_equal(expected.sort_index(), actual.sort_index())
    teams.rank_consensus = np.nan
    result, _ = encode_history(teams, games)
    assert result.filter(like="te_rank").isna().all().all()
    teams.loc[0, "Gender"] = "W"
    with pytest.raises(ValueError, match="one gender"):
        encode_history(teams, games)


def test_encoding_window_and_history_beginning_are_explicit():
    teams, games = example()
    # Encodings use only seasons represented in the training feature contract.
    future = teams.query("Season >= 2015")
    result, audit = encode_history(future, games, window_seasons=1)
    assert result.query("Season == 2015").te_team_mean.eq(0.5).all()
    assert audit.query("Season == 2017").history_min_season.eq(2016).all()
    with pytest.raises(ValueError, match="positive"):
        encode_history(teams, games, prior_games=0)
