import numpy as np
import pandas as pd
import pytest

from march_mania.selection_features import RESUME_COLUMNS, resume_pairs, selection_snapshot


def inputs():
    games = pd.DataFrame(
        [
            [2021, 100, 1, 2, 80, 70, "H"],
            [2021, 120, 3, 1, 85, 75, "N"],
            [2021, 130, 1, 4, 90, 60, "A"],
        ],
        columns=["Season", "DayNum", "WTeamID", "LTeamID", "WScore", "LScore", "WLoc"],
    )
    seeds = pd.DataFrame(
        [[2021, 1, "W01"], [2021, 2, "X04"], [2021, 3, "Z12"]], columns=["Season", "TeamID", "Seed"]
    )
    return games, seeds


def test_exact_quality_and_opportunity():
    g, s = inputs()
    t = selection_snapshot(g, s, 2021).set_index("TeamID")
    assert t.loc[1, "resume_quality_wins"] == 6.25
    assert t.loc[1, "resume_elite_wins"] == 1
    assert t.loc[1, "resume_seeded_wins"] == 1
    assert t.loc[1, "resume_quality_win_rate"] == pytest.approx(16.25 / 30.25)
    assert t.loc[1, "resume_away_quality_wins"] == 0.25
    assert t.loc[1, "resume_late_quality_wins"] == 0.25
    assert t.loc[1, "resume_quality_margin"] == pytest.approx((60 - 40 + 7.5) / 30.25)
    assert np.isfinite(t[RESUME_COLUMNS].to_numpy()).all()


def test_future_rows_and_other_seasons_cannot_change_snapshot():
    g, s = inputs()
    extra = pd.concat([g.assign(DayNum=140), g.assign(Season=2022)], ignore_index=True)
    pd.testing.assert_frame_equal(
        selection_snapshot(g, s, 2021),
        selection_snapshot(pd.concat([g, extra]), pd.concat([s, s.assign(Season=2022)]), 2021),
    )


def test_swap_row_order_and_unknown_team():
    g, s = inputs()
    t = selection_snapshot(g, s, 2021)
    pairs = pd.DataFrame(
        {"Season": [2021, 2021], "Team1ID": [3, 1], "Team2ID": [1, 4], "ID": [9, 2]}
    )
    a = resume_pairs(t, pairs)
    reverse = pairs.rename(columns={"Team1ID": "Team2ID", "Team2ID": "Team1ID"})
    cols = ["diff_" + x for x in RESUME_COLUMNS]
    np.testing.assert_allclose(a[cols], -resume_pairs(t, reverse)[cols])
    assert a.ID.tolist() == [9, 2]
    with pytest.raises(ValueError, match="without a legal"):
        resume_pairs(t, pairs.assign(Team1ID=999))


@pytest.mark.parametrize("cutoff,available", [(100, 132), (132, 133), (132, -1)])
def test_seed_availability(cutoff, available):
    g, s = inputs()
    with pytest.raises(ValueError, match="availability"):
        selection_snapshot(g, s, 2021, cutoff=cutoff, seeds_available_day=available)


@pytest.mark.parametrize("seed", ["W00", "W17", "banana", "W01c"])
def test_bad_seeds(seed):
    g, s = inputs()
    s.loc[0, "Seed"] = seed
    with pytest.raises(ValueError, match="Malformed"):
        selection_snapshot(g, s, 2021)


def test_duplicate_and_invalid_games():
    g, s = inputs()
    with pytest.raises(ValueError, match="Duplicate physical"):
        selection_snapshot(pd.concat([g, g.iloc[:1]]), s, 2021)
    with pytest.raises(ValueError, match="Duplicate or missing"):
        selection_snapshot(g, pd.concat([s, s.iloc[:1]]), 2021)
    with pytest.raises(ValueError, match="winning score"):
        selection_snapshot(g.assign(WScore=0), s, 2021)
    with pytest.raises(ValueError, match="No legal"):
        selection_snapshot(g, s, 2022)


def test_seed_editions_and_nonseeded_prior():
    g, s = inputs()
    s = pd.concat([s, s.assign(Season=2020, Seed="W16")])
    t = selection_snapshot(g, s, 2021).set_index("TeamID")
    assert t.loc[4, "resume_elite_win_rate"] == pytest.approx(2.5 / 6)
    assert t.loc[4, "resume_seeded_win_rate"] == pytest.approx(2.5 / 6)
    assert t.loc[4, "resume_bad_loss_rate"] == 0.5


def test_fit_temporal_boundaries_and_training_only_screen():
    from march_mania.selection_study import fit_comparison

    train = pd.DataFrame(
        {
            "Season": [2013, 2013, 2014, 2014],
            "y": [0, 1, 0, 1],
            "diff_seed": [2.0, -2.0, 4.0, -4.0],
            "diff_margin": [0.0, 0.0, 0.0, 0.0],
        }
    )
    valid = pd.DataFrame(
        {
            "Season": [2016, 2016],
            "y": [0, 1],
            "diff_seed": [3.0, -3.0],
            "diff_margin": [999.0, -999.0],
        }
    )
    model, prediction, retained = fit_comparison(train, valid, ["diff_seed", "diff_margin"])
    assert retained == ["diff_seed"]
    assert prediction.sum() == pytest.approx(1.0)
    with pytest.raises(ValueError, match="overlapping"):
        fit_comparison(train, valid.assign(Season=2014), ["diff_seed"])
    with pytest.raises(ValueError, match="registered"):
        fit_comparison(train, valid, ["diff_y"])
