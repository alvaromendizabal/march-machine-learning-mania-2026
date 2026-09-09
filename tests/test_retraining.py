"""Massey availability, temporal selection and training-only screening contracts."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from march_mania.publication import retraining

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "change",
    ["missing_season", "missing_team", "future_edition", "women", "missing_rank", "future_year"],
)
def test_massey_guard_rejects_ineligible_populations(change):
    frame = pd.DataFrame(
        {
            "Season": [2013, 2014],
            "Gender": ["M", "M"],
            "diff_rank_consensus": [0.1, 0.2],
            "diff_rank_mean": [0.1, 0.2],
        }
    )
    coverage = pd.DataFrame(
        {
            "Season": [2013, 2014],
            "Gender": ["M", "M"],
            "ranking_teams": [350, 350],
            "regular_teams": [350, 350],
            "latest_ranking_day": [128, 128],
            "cutoff_day": [132, 132],
            "ranking_systems": [60, 60],
        }
    )
    retraining.coverage_guard(frame, coverage, massey=True)
    if change == "missing_season":
        coverage = coverage.iloc[:1]
    elif change == "missing_team":
        coverage.loc[0, "ranking_teams"] = 349
    elif change == "future_edition":
        coverage.loc[0, "latest_ranking_day"] = 133
    elif change == "women":
        frame.loc[0, "Gender"] = "W"
    elif change == "missing_rank":
        frame.loc[0, "diff_rank_consensus"] = np.nan
    else:
        frame.loc[0, "Season"] = 2026
    with pytest.raises(ValueError):
        retraining.coverage_guard(frame, coverage, massey=True)


def test_future_outcomes_cannot_change_earlier_model_selection():
    config = json.loads((ROOT / retraining.CONFIG).read_text())
    rows = []
    for name, p in [("pooled_reference", 0.7), ("alternative", 0.3)]:
        for season in retraining.YEARS:
            for index, y in enumerate([0, 1]):
                rows.append(
                    {
                        "variant": name,
                        "Gender": "M",
                        "Season": season,
                        "DayNum": 134,
                        "ID": f"{season}_1101_{1102 + index}",
                        "y": y,
                        "p": p if y else 1 - p,
                    }
                )
    predictions = pd.DataFrame(rows)
    _, expected = retraining.evaluate(predictions, config)
    predictions.loc[predictions.Season.eq(2021), "y"] = (
        1 - predictions.loc[predictions.Season.eq(2021), "y"]
    )
    _, actual = retraining.evaluate(predictions, config)
    pd.testing.assert_frame_equal(actual, expected)
    assert actual.history_last_season.lt(actual.Season).all()
    with pytest.raises(ValueError):
        retraining.evaluate(pd.concat([predictions, predictions.iloc[:1]]), config)


def test_validation_labels_do_not_change_fitted_screen_or_estimator(monkeypatch):
    config = json.loads((ROOT / retraining.CONFIG).read_text())
    variant = config["variants"][1]
    monkeypatch.setattr(retraining, "columns_for", lambda _: ["signal", "other"])
    rng = np.random.default_rng(123)
    train = pd.DataFrame(
        {
            "Season": [2013] * 100,
            "signal": rng.normal(size=100),
            "other": rng.normal(size=100),
            "y": np.tile([0, 1], 50),
        }
    )
    valid = pd.DataFrame(
        {"Season": [2014, 2014], "signal": [0.8, -0.2], "other": [-0.5, 0.7], "y": [0, 1]}
    )
    model, p, _ = retraining.fit_variant(train, valid, variant, config)
    second, p2, _ = retraining.fit_variant(train, valid.assign(y=1 - valid.y), variant, config)
    assert model.model.get_booster().save_raw() == second.model.get_booster().save_raw()
    np.testing.assert_array_equal(model.screen.indices_, second.screen.indices_)
    np.testing.assert_array_equal(p, p2)
    with pytest.raises(ValueError, match="Temporal overlap"):
        retraining.fit_variant(train.assign(Season=2014), valid, variant, config)
