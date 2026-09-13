"""Publication-cohort ordinal features; every statistic is available at its cutoff."""

from __future__ import annotations

import numpy as np
import pandas as pd

LEVEL_FEATURES = [
    "rank_consensus",
    "rank_mean",
    "rank_disagreement",
    "rank_iqr",
    "rank_lower",
    "rank_upper",
    "rank_top25",
    "rank_top50",
    "rank_systems",
    "rank_coverage",
    "rank_age",
    "rank_max_age",
    "rank_logit",
]
TREND_FEATURES = [
    "rank_momentum",
    "rank_short_momentum",
    "rank_long_momentum",
    "rank_acceleration",
    "rank_momentum_sd",
    "rank_matched_fraction",
    "rank_dispersion_change",
]
RANK_FEATURES = LEVEL_FEATURES + TREND_FEATURES


def publication_panel(rankings: pd.DataFrame, season: int, cutoff: int) -> pd.DataFrame:
    """Normalize inside each published system/day, then select its latest legal edition.

    A team missing from that edition stays missing; mixing editions would change
    the meaning of ranks. No future edition contributes to the denominator.
    """
    required = ["Season", "RankingDayNum", "SystemName", "TeamID", "OrdinalRank"]
    if not set(required).issubset(rankings):
        raise ValueError("Invalid ranking schema")
    legal = rankings.loc[
        (rankings.Season == season) & rankings.RankingDayNum.between(cutoff - 14, cutoff),
        required,
    ].copy()
    numeric = legal[["Season", "RankingDayNum", "TeamID", "OrdinalRank"]].to_numpy(dtype=float)
    if (
        legal.isna().any().any()
        or not np.isfinite(numeric).all()
        or not np.equal(numeric, np.floor(numeric)).all()
        or (legal.OrdinalRank <= 0).any()
        or legal.SystemName.astype(str).str.strip().eq("").any()
        or legal.duplicated(required[:-1]).any()
    ):
        raise ValueError("Duplicate or invalid ordinal ranks")
    latest = legal.groupby("SystemName").RankingDayNum.transform("max")
    selected = legal.loc[legal.RankingDayNum == latest].copy()
    cohort = selected.groupby(["SystemName", "RankingDayNum"]).OrdinalRank.transform("max")
    selected["rating"] = 1 - (selected.OrdinalRank - 1) / (cohort - 1).clip(lower=1)
    selected["age"] = cutoff - selected.RankingDayNum
    return selected.sort_values(["SystemName", "TeamID"]).reset_index(drop=True)


def ranking_snapshot(rankings: pd.DataFrame, season: int, cutoff: int = 132) -> pd.DataFrame:
    current = publication_panel(rankings, season, cutoff)
    if current.empty:
        return pd.DataFrame(columns=["TeamID", *RANK_FEATURES], dtype=float)
    current["top25"] = current.OrdinalRank <= 25
    current["top50"] = current.OrdinalRank <= 50
    result = current.groupby("TeamID").agg(
        rank_consensus=("rating", "median"),
        rank_mean=("rating", "mean"),
        rank_disagreement=("rating", "std"),
        rank_systems=("SystemName", "nunique"),
        rank_age=("age", "mean"),
        rank_max_age=("age", "max"),
        rank_top25=("top25", "mean"),
        rank_top50=("top50", "mean"),
    )
    quantiles = current.groupby("TeamID").rating.quantile(np.array([0.25, 0.75])).unstack()
    result["rank_lower"], result["rank_upper"] = quantiles[0.25], quantiles[0.75]
    result["rank_iqr"] = result.rank_upper - result.rank_lower
    result["rank_coverage"] = result.rank_systems / current.SystemName.nunique()
    clipped = result.rank_consensus.clip(0.01, 0.99)
    result["rank_logit"] = np.log(clipped / (1 - clipped))
    for lag, name in [
        (7, "rank_short_momentum"),
        (30, "rank_momentum"),
        (60, "rank_long_momentum"),
    ]:
        past = publication_panel(rankings, season, cutoff - lag)
        paired = current.merge(
            past, on=["SystemName", "TeamID"], suffixes=("_now", "_past"), validate="one_to_one"
        )
        paired["change"] = paired.rating_now - paired.rating_past
        result[name] = paired.groupby("TeamID").change.median()
        if lag == 30:
            group = paired.groupby("TeamID")
            result["rank_momentum_sd"] = group.change.std()
            result["rank_matched_fraction"] = group.size() / result.rank_systems
            result["rank_dispersion_change"] = group.rating_now.std() - group.rating_past.std()
    result["rank_acceleration"] = result.rank_short_momentum / 7 - result.rank_momentum / 30
    return result.reset_index()[["TeamID", *RANK_FEATURES]]
