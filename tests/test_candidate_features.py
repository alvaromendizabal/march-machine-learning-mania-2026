"""Broad candidate schemas, time barriers, strict symmetry, and real screening behavior."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from threadpoolctl import threadpool_limits

from march_mania.advanced_features import (
    advanced_snapshot,
    candidate_blocks,
    pair_features,
    possession_games,
)
from march_mania.candidate_features import CANDIDATE_FAMILIES, candidate_snapshot
from march_mania.coach_features import COACH_FEATURES, coach_snapshot
from march_mania.feature_selection import TrainingScreen
from march_mania.feature_store import labeled_pairs
from march_mania.features import read_official


def test_registered_candidate_count_and_label_exclusion():
    assert sum(map(len, CANDIDATE_FAMILIES.values())) == 2944
    assert len(COACH_FEATURES) == 26
    columns = candidate_blocks()["full"]
    assert len(columns) == len(set(columns)) == 3106
    assert len(candidate_blocks(False)["full"]) == 3083
    assert len(candidate_blocks()["baseline_124"]) == 124
    assert len(candidate_blocks(False)["baseline_124"]) == 101
    for column in candidate_blocks()["expanded_non_massey_no_target_coach"]:
        assert not column.startswith(("diff_rank_", "diff_te_", "diff_coach_"))
    assert not {"y", "ID", "Season", "DayNum", "Team1ID", "Team2ID"}.intersection(columns)


def test_distribution_schema_order_invariance_and_undefined_windows(raw):
    tables = read_official(raw)[0]["M"]
    detail = tables["RegularSeasonDetailedResults"].query("Season == 2016")
    long = possession_games(detail)
    ratings = pd.DataFrame({"TeamID": sorted(long.TeamID.unique()), "strength": np.arange(8)})
    one = candidate_snapshot(long, ratings, 132)
    two = candidate_snapshot(long.sample(frac=1, random_state=8), ratings, 132)
    pd.testing.assert_frame_equal(one, two)
    assert one.shape == (8, 2945)
    assert not np.isinf(one.to_numpy()).any()
    assert one.filter(like="last30days").isna().all().all()
    with pytest.raises(ValueError, match="pre-cutoff"):
        candidate_snapshot(long.assign(DayNum=150), ratings, 132)


def test_new_candidates_ignore_current_labels_and_future_regular_games(raw):
    data = read_official(raw)[0]["M"]
    before = advanced_snapshot(data, "M", 2016)
    for name in ["RegularSeasonCompactResults", "RegularSeasonDetailedResults"]:
        changed = data[name].loc[data[name].Season == 2016].copy()
        changed.DayNum, changed.WScore = 150, 400
        data[name] = pd.concat([data[name], changed], ignore_index=True)
    data["NCAATourneyCompactResults"].loc[lambda f: f.Season >= 2016, "WScore"] = 10000
    pd.testing.assert_frame_equal(before, advanced_snapshot(data, "M", 2016))
    pairs = labeled_pairs(data, "M", [2016]).head(1)
    a, b = pairs.Team1ID.iloc[0], pairs.Team2ID.iloc[0]
    swapped = before.assign(TeamID=before.TeamID.replace({a: b, b: a}))
    columns = candidate_blocks()["full"]
    np.testing.assert_allclose(
        pair_features(before, pairs)[columns],
        -pair_features(swapped, pairs)[columns],
        equal_nan=True,
    )


def test_training_screen_removes_missing_constants_and_signed_duplicates():
    rng = np.random.default_rng(8)
    x = rng.normal(size=(100, 20))
    x[:, 0], x[:, 1], x[:, 2], x[:, 3] = 0, np.nan, x[:, 4], -x[:, 4]
    y = (x[:, 4] > 0).astype(int)
    with threadpool_limits(limits=1):
        first = TrainingScreen(max_features=6).fit(x, y)
        second = TrainingScreen(max_features=6).fit(x.copy(), y.copy())
    np.testing.assert_array_equal(first.indices_, second.indices_)
    assert len(first.indices_) <= 6
    assert first.audit_.status.iloc[0] == "constant"
    assert first.audit_.status.iloc[1] == "all_missing"
    assert sum(i in first.indices_ for i in [2, 3, 4]) == 1
    assert (first.audit_.status == "redundant").sum() >= 2
    np.testing.assert_allclose(first.transform(-x), -first.transform(x), equal_nan=True)
    # Transforming validation data cannot refit or alter training-only selection.
    before = first.indices_.copy()
    first.transform(np.full_like(x, 1e6))
    np.testing.assert_array_equal(first.indices_, before)
    assert np.array_equal(first.get_support().nonzero()[0], before)


@pytest.mark.parametrize("value", [np.inf, -np.inf])
def test_screen_rejects_infinity(value):
    x = np.array([[1.0, 2.0], [3.0, value]])
    with pytest.raises(ValueError, match="Invalid"):
        TrainingScreen().fit(x, [0, 1])


def test_screen_rejects_empty_and_uninformative_data():
    with pytest.raises(ValueError, match="Nonempty"):
        TrainingScreen().fit(np.empty((0, 3)), [])
    with pytest.raises(ValueError, match="No informative"):
        TrainingScreen().fit(np.zeros((5, 3)), [0, 0, 1, 1, 1])
    with pytest.raises(ValueError, match="both classes"):
        TrainingScreen().fit(np.ones((5, 3)), np.ones(5))


def test_coach_history_availability_intervals_and_future_embargo(raw):
    data = read_official(raw)[0]["M"]
    compact, tournament = data["RegularSeasonCompactResults"], data["NCAATourneyCompactResults"]
    teams = pd.DataFrame({"TeamID": sorted(compact.WTeamID.unique())})
    coaches = pd.DataFrame(
        [
            {
                "Season": year,
                "TeamID": team,
                "FirstDayNum": 0,
                "LastDayNum": 154,
                "CoachName": str(team),
            }
            for year in range(2013, 2018)
            for team in teams.TeamID
        ]
    )
    before = coach_snapshot(coaches, compact, tournament, teams, 2016, 132)
    assert before.coach_known.eq(1).all()
    assert before.coach_tenure.eq(3).all()
    assert before.coach_current_stint_days.eq(133).all()
    assert before.coach_changed_since_prior_season.eq(0).all()
    assert before.coach_prior_tournament_appearances_5.eq(3).all()
    assert before.coach_tournament_3_support.gt(0).all()
    tournament.loc[tournament.Season >= 2016, ["WTeamID", "WScore"]] = [9999, 200]
    coaches.loc[coaches.Season > 2016, "CoachName"] = "future coach"
    pd.testing.assert_frame_equal(
        before, coach_snapshot(coaches, compact, tournament, teams, 2016, 132)
    )
    absent = coach_snapshot(None, compact, tournament, teams, 2016, 132)
    assert absent.coach_known.eq(0).all()
    assert absent.drop(columns=["TeamID", "coach_known"]).isna().all().all()
    duplicate = pd.concat([coaches, coaches.query("Season == 2016").head(1)])
    with pytest.raises(ValueError, match="Overlapping"):
        coach_snapshot(duplicate, compact, tournament, teams, 2016, 132)
