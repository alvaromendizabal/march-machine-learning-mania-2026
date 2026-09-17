from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from march_mania.public_solutions import first_place_2026 as first


def test_reference_identity_and_features_are_pinned():
    assert first.REFERENCE_COMMIT == "c4db013f88cf14a036ed4881bbffb05845f5bcd1"
    assert first.REFERENCE_SCORE == pytest.approx(0.1097454)
    assert first.MEN_FEATURES == ("seed_diff", "opp_qlty_pts_won_diff", "harry_diff")
    assert first.WOMEN_FEATURES[-1] == "harry_diff"


def test_quality_point_priority_matches_published_logic():
    seed = pd.Series([1.0, 8.0, np.nan, np.nan])
    secondary = pd.Series([np.nan, np.nan, "NIT", np.nan])
    got = first.opponent_quality_points(seed, secondary)
    assert got.tolist() == [6.0, 4.0, 2.0, 0.25]


def test_mirror_creates_winner_and_loser_perspectives():
    row = {
        "Season": 2025,
        "DayNum": 10,
        "LTeamID": 1002,
        "LScore": 60,
        "WTeamID": 1001,
        "WScore": 70,
        "NumOT": 0,
        "WLoc": "H",
        "LFGM": 20,
        "LFGA": 50,
        "LFGM3": 5,
        "LFGA3": 15,
        "LFTM": 15,
        "LFTA": 20,
        "LOR": 8,
        "LDR": 20,
        "LAst": 10,
        "LTO": 12,
        "LStl": 5,
        "LBlk": 3,
        "LPF": 15,
        "WFGM": 25,
        "WFGA": 55,
        "WFGM3": 7,
        "WFGA3": 18,
        "WFTM": 13,
        "WFTA": 18,
        "WOR": 10,
        "WDR": 25,
        "WAst": 14,
        "WTO": 9,
        "WStl": 7,
        "WBlk": 4,
        "WPF": 13,
    }
    out = first.prepare_games(pd.DataFrame([row]))
    assert len(out) == 2
    assert sorted(out["win"].tolist()) == [0, 1]
    assert set(out["T1_TeamID"]) == {1001, 1002}


def test_reference_hyperparameters():
    men = first.reference_xgb_kwargs("men")
    women = first.reference_xgb_kwargs("women")
    assert men["n_estimators"] == women["n_estimators"] == 4000
    assert men["learning_rate"] == pytest.approx(0.003)
    assert men["max_depth"] == women["max_depth"] == 2
    assert men["min_child_weight"] == 5
    assert women["min_child_weight"] == 3
    assert men["early_stopping_rounds"] == 100


def test_sharpen_edges_leaves_middle_unchanged():
    p = np.array([0.02, 0.10, 0.50, 0.90, 0.98])
    out = first.sharpen_edges(p)
    assert out[0] < p[0]
    assert out[-1] > p[-1]
    assert out[1:4].tolist() == pytest.approx(p[1:4].tolist())


def test_published_feature_spec_matches_literal_final_feature_contract():
    spec = first.published_feature_spec()

    # Global table order is presentation metadata. The scientific contract is:
    # 1) every final feature appears exactly once, and
    # 2) filtering by gender preserves the literal estimator feature order.
    expected = set(first.MEN_FEATURES) | set(first.WOMEN_FEATURES)

    assert spec["feature"].is_unique
    assert set(spec["feature"]) == expected

    men = spec.loc[spec["men"], "feature"].tolist()
    women = spec.loc[spec["women"], "feature"].tolist()

    assert men == list(first.MEN_FEATURES)
    assert women == list(first.WOMEN_FEATURES)


def test_inventory_notebook_uses_supported_first_place_public_api():
    from pathlib import Path

    import nbformat

    root = Path(__file__).resolve().parents[1]
    notebook = nbformat.read(
        root / "notebooks/23_public_solution_reproduction_inventory.ipynb",
        as_version=4,
    )
    source = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    assert "first.published_feature_spec()" in source
    assert callable(first.published_feature_spec)
