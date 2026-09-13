from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from march_mania.rankings import RANK_FEATURES, publication_panel, ranking_snapshot


def rankings():
    return pd.DataFrame(
        [
            {
                "Season": 2016,
                "RankingDayNum": day,
                "SystemName": system,
                "TeamID": team,
                "OrdinalRank": rank,
            }
            for day in [70, 100, 124, 130, 133, 154]
            for system in ["A", "B"]
            for team, rank in [(1001, 1), (1002, 50), (1003, 100)]
        ]
    )


def test_every_publication_feature_ignores_future_and_is_order_invariant():
    raw = rankings()
    expected = ranking_snapshot(raw, 2016)
    raw.loc[raw.RankingDayNum > 132, "OrdinalRank"] = 999999
    raw = pd.concat([raw, raw.assign(Season=2017, OrdinalRank=999)])
    pd.testing.assert_frame_equal(expected, ranking_snapshot(raw.sample(frac=1), 2016))
    assert expected[RANK_FEATURES].notna().all().all()
    assert expected.rank_momentum.eq(0).all()


def test_publication_normalization_never_uses_future_or_mixes_editions():
    raw = rankings().query("RankingDayNum == 130").copy()
    old = raw.assign(RankingDayNum=129, OrdinalRank=10000)
    # One team disappears from A's latest edition: its old row must not carry forward.
    raw = raw.loc[~((raw.SystemName == "A") & (raw.TeamID == 1003))]
    panel = publication_panel(pd.concat([raw, old]), 2016, 132)
    assert not ((panel.SystemName == "A") & (panel.TeamID == 1003)).any()
    assert panel.query("SystemName == 'A' and TeamID == 1002").rating.iloc[0] == 0
    assert panel.query("SystemName == 'B' and TeamID == 1002").rating.iloc[0] == pytest.approx(
        50 / 99
    )
    result = ranking_snapshot(pd.concat([raw, old]), 2016)
    assert result.set_index("TeamID").loc[1003, "rank_coverage"] == 0.5


def test_momentum_uses_matched_systems_and_reports_sparse_uncertainty():
    raw = rankings()
    newer = raw.query("RankingDayNum == 130 and SystemName == 'A'").assign(SystemName="C")
    newer.OrdinalRank = [100, 50, 1]
    result = ranking_snapshot(pd.concat([raw, newer]), 2016)
    assert result.rank_momentum.eq(0).all()
    np.testing.assert_allclose(result.rank_matched_fraction, 2 / 3)
    single = ranking_snapshot(raw.query("SystemName == 'A'"), 2016)
    assert single.rank_disagreement.isna().all()
    assert single.rank_momentum_sd.isna().all()
    assert ranking_snapshot(raw, 2016, 95).empty


@pytest.mark.parametrize("bad", [0, -1, np.inf, 1.5, np.nan])
def test_invalid_current_ordinal_is_rejected(bad):
    raw = rankings()
    raw["OrdinalRank"] = raw.OrdinalRank.astype(float)
    raw.loc[raw.RankingDayNum == 130, "OrdinalRank"] = bad
    with pytest.raises(ValueError, match="invalid"):
        ranking_snapshot(raw, 2016)
