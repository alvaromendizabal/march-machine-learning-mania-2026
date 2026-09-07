from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from march_mania.advanced_features import advanced_snapshot
from march_mania.context_features import CONTEXT_FAMILIES, context_snapshot
from march_mania.features import read_official


def test_extra_box_rates_match_independent_hand_calculation(raw):
    tables = read_official(raw)[0]["M"]
    result = advanced_snapshot(tables, "M", 2016).set_index("TeamID")
    games = tables["RegularSeasonDetailedResults"].query("Season == 2016")
    team = 1001
    assists = (
        games.loc[games.WTeamID == team, "WAst"].sum()
        + games.loc[games.LTeamID == team, "LAst"].sum()
    )
    turnovers = (
        games.loc[games.WTeamID == team, "WTO"].sum()
        + games.loc[games.LTeamID == team, "LTO"].sum()
    )
    assert result.loc[team, "assist_turnover"] == pytest.approx(assists / turnovers)
    for name in ["elite_win_posterior", "elite_fraction", "overtime_fraction", "pythagorean_win"]:
        assert result[name].between(0, 1).all()
    assert result.games_last_14.eq(0).all()
    assert result.rating_balance.eq(result[["adj_offense", "adj_defense"]].min(axis=1)).all()


def test_absent_box_fields_remain_missing_and_do_not_remove_other_features(raw):
    tables = read_official(raw)[0]["M"]
    detailed = tables["RegularSeasonDetailedResults"]
    detailed.drop(
        columns=[side + field for side in ("W", "L") for field in ("Ast", "Stl", "Blk", "PF")],
        inplace=True,
    )
    result = advanced_snapshot(tables, "M", 2016)
    assert result[CONTEXT_FAMILIES["ball_control"]].isna().all().all()
    assert result[CONTEXT_FAMILIES["scoring_shape"]].notna().all().all()


def test_invalid_extra_box_values_fail_explicitly(raw):
    tables = read_official(raw)[0]["M"]
    detailed = tables["RegularSeasonDetailedResults"]
    detailed.loc[detailed.Season == 2016, "WAst"] = -1
    with pytest.raises(ValueError, match="Invalid extra box-score"):
        advanced_snapshot(tables, "M", 2016)


def test_zero_denominators_are_missing_not_infinite(raw):
    tables = read_official(raw)[0]["M"]
    ratings = advanced_snapshot(tables, "M", 2016)
    detail = tables["RegularSeasonDetailedResults"].copy()
    detail[["WTO", "LTO"]] = 0
    result = context_snapshot(tables["RegularSeasonCompactResults"], detail, ratings, 2016, 132)
    assert result[["assist_turnover", "opp_assist_turnover"]].isna().all().all()
    assert not np.isinf(result.to_numpy()).any()


def test_context_is_invariant_to_future_games_and_row_order(raw):
    tables = read_official(raw)[0]["M"]
    ratings = advanced_snapshot(tables, "M", 2016)
    compact, detail = tables["RegularSeasonCompactResults"], tables["RegularSeasonDetailedResults"]
    result = context_snapshot(compact, detail, ratings, 2016, 132)
    future = detail.query("Season == 2016").copy()
    future.DayNum = 140
    future.WAst = -100
    changed = context_snapshot(
        compact.sample(frac=1, random_state=3),
        pd.concat([detail, future]).sample(frac=1, random_state=4),
        ratings,
        2016,
        132,
    )
    pd.testing.assert_frame_equal(result, changed)
