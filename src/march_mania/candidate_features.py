"""Broad season-local basketball hypotheses, generated without tournament targets.

Every statistic describes games available at the declared snapshot, not a
pre-game backtest of those regular-season games. Windows and transformations
are fixed before tournament validation. No external data is downloaded here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SIGNALS = (
    "margin",
    "points",
    "allowed",
    "efficiency",
    "allowed_efficiency",
    "tempo",
    "efg",
    "opp_efg",
    "tov",
    "opp_tov",
    "orb",
    "opp_orb",
    "ftr",
    "opp_ftr",
    "three_share",
    "opp_three_share",
    "three_accuracy",
    "opp_three_accuracy",
    "two_accuracy",
    "opp_two_accuracy",
    "free_accuracy",
    "opp_free_accuracy",
    "rebound_share",
    "opp_rebound_share",
    "shot_volume",
    "opp_shot_volume",
    "free_points_share",
    "opp_free_points_share",
    "three_points_share",
    "opp_three_points_share",
    "possession_gap",
    "win",
)
WINDOWS = ("season", "last7games", "last30days", "last60days")
STATS = ("mean", "median", "std", "min", "max", "count", "q10", "q25", "q75", "q90", "iqr", "skew")
SMALL_STATS = ("mean", "std", "count", "q25", "q75")
VENUES = ("home", "road", "neutral", "nonhome")
OPPONENTS = ("upper_quartile", "lower_quartile", "above_median")
TREND_STATS = ("slope_day", "recent_change", "acceleration", "mean_abs_change", "late_volatility")
PEER_STATS = ("percentile", "zscore", "recent_percentile", "consistency_percentile")


def names(family: str, contexts: tuple[str, ...], stats: tuple[str, ...]) -> list[str]:
    return [
        f"research_{family}_{context}_{signal}_{stat}"
        for context in contexts
        for signal in SIGNALS
        for stat in stats
    ]


CANDIDATE_FAMILIES = {
    "distribution": names("distribution", WINDOWS, STATS),
    "venue_profile": names("venue", VENUES, SMALL_STATS),
    "opponent_profile": names("opponent", OPPONENTS, SMALL_STATS),
    "trajectory": names("trajectory", ("season",), TREND_STATS),
    "peer_profile": names("peer", ("season",), PEER_STATS),
}


def game_signals(long: pd.DataFrame) -> pd.DataFrame:
    """Dimensionless rates with explicit undefined-denominator missingness."""
    result = long[["TeamID", "OpponentID", "DayNum", "home"]].copy()
    for name in ("points", "allowed", "efficiency", "tempo", "possession_gap", "win"):
        result[name] = long[name]
    result["margin"] = long.points - long.allowed
    result["allowed_efficiency"] = 100 * long.allowed / long.possessions
    for side, other in (("", "opp_"), ("opp_", "")):
        points = long.points if side == "" else long.allowed
        quantities = {
            "efg": (long[side + "FGM"] + 0.5 * long[side + "FGM3"], long[side + "FGA"]),
            "tov": (long[side + "TO"], long.possessions),
            "orb": (long[side + "OR"], long[side + "OR"] + long[other + "DR"]),
            "ftr": (long[side + "FTA"], long[side + "FGA"]),
            "three_share": (long[side + "FGA3"], long[side + "FGA"]),
            "three_accuracy": (long[side + "FGM3"], long[side + "FGA3"]),
            "two_accuracy": (
                long[side + "FGM"] - long[side + "FGM3"],
                long[side + "FGA"] - long[side + "FGA3"],
            ),
            "free_accuracy": (long[side + "FTM"], long[side + "FTA"]),
            "rebound_share": (
                long[side + "OR"] + long[side + "DR"],
                long.OR + long.DR + long.opp_OR + long.opp_DR,
            ),
            "shot_volume": (long[side + "FGA"], long.possessions),
            "free_points_share": (long[side + "FTM"], points),
            "three_points_share": (3 * long[side + "FGM3"], points),
        }
        for name, (numerator, denominator) in quantities.items():
            result[side + name] = numerator / denominator.replace(0, np.nan)
    if np.isinf(result[list(SIGNALS)].to_numpy(dtype=float)).any():
        raise ValueError("Infinite game-level candidate")
    return result


def aggregate(
    frame: pd.DataFrame, family: str, context: str, stats: tuple[str, ...]
) -> pd.DataFrame:
    """One vectorized aggregation per cohort; missing cohorts never become fake zero scores."""
    grouped = frame.groupby("TeamID", sort=True)[list(SIGNALS)]
    simple = [stat for stat in stats if stat not in {"q10", "q25", "q75", "q90", "iqr"}]
    result = grouped.agg(simple)
    quantiles = {q: grouped.quantile(q) for q in (0.10, 0.25, 0.75, 0.90)}
    additions = {}
    for signal in SIGNALS:
        for stat, q in (("q10", 0.10), ("q25", 0.25), ("q75", 0.75), ("q90", 0.90)):
            if stat in stats:
                additions[(signal, stat)] = quantiles[q][signal]
        if "iqr" in stats:
            additions[(signal, "iqr")] = quantiles[0.75][signal] - quantiles[0.25][signal]
    result = pd.concat([result, pd.DataFrame(additions)], axis=1)
    result = result.reindex(columns=pd.MultiIndex.from_product([SIGNALS, stats]))
    result.columns = names(family, (context,), stats)
    return result


def trajectories(frame: pd.DataFrame, cutoff: int) -> pd.DataFrame:
    """Vectorized daily trends; tied-day observations are averaged deterministically."""
    daily = frame.groupby(["TeamID", "DayNum"], sort=True)[list(SIGNALS)].mean().reset_index()
    x = daily.DayNum.to_numpy(dtype=float)[:, None]
    y = daily[list(SIGNALS)].to_numpy(dtype=float)
    mask = np.isfinite(y)
    safe = np.where(mask, y, 0.0)
    identity = daily.TeamID

    def totals(values: np.ndarray) -> pd.DataFrame:
        return pd.DataFrame(values, columns=SIGNALS).groupby(identity, sort=True).sum()

    n = totals(mask.astype(float))
    sx, sy = totals(mask * x), totals(safe)
    denominator = totals(mask * x * x) - sx * sx / n.replace(0, np.nan)
    slopes = (totals(safe * x) - sx * sy / n.replace(0, np.nan)) / denominator.replace(0, np.nan)
    slopes = slopes.where((n >= 3) & (denominator > 0))
    grouped = daily.groupby("TeamID", sort=True)[list(SIGNALS)]
    recent = daily.loc[daily.DayNum > cutoff - 30].groupby("TeamID")[list(SIGNALS)].mean()
    middle = (
        daily.loc[daily.DayNum.between(cutoff - 59, cutoff - 30)]
        .groupby("TeamID")[list(SIGNALS)]
        .mean()
    )
    early = daily.loc[daily.DayNum <= cutoff - 60].groupby("TeamID")[list(SIGNALS)].mean()
    absolute_change = grouped.diff().abs().groupby(identity).mean()
    late = daily.DayNum >= daily.groupby("TeamID").DayNum.transform("mean")
    volatility = daily.loc[late].groupby("TeamID")[list(SIGNALS)].std()
    items = [slopes, recent - middle, recent - 2 * middle + early, absolute_change, volatility]
    columns = {}
    for signal in SIGNALS:
        for stat, values in zip(TREND_STATS, items, strict=True):
            columns[f"research_trajectory_season_{signal}_{stat}"] = values[signal]
    return pd.DataFrame(columns)


def candidate_snapshot(long: pd.DataFrame, ratings: pd.DataFrame, cutoff: int) -> pd.DataFrame:
    """2,944 transparent team candidates, computed in bounded season-sized cohorts."""
    if long.empty or (long.DayNum > cutoff).any():
        raise ValueError("Candidates require nonempty pre-cutoff regular-season games")
    frame = game_signals(long).sort_values(["TeamID", "DayNum", "OpponentID"])
    groups = [aggregate(frame, "distribution", "season", STATS)]
    recent = frame.groupby("TeamID", sort=False).tail(7)
    groups.append(aggregate(recent, "distribution", "last7games", STATS))
    for window in (30, 60):
        groups.append(
            aggregate(
                frame.loc[frame.DayNum > cutoff - window],
                "distribution",
                f"last{window}days",
                STATS,
            )
        )
    for name, mask in (
        ("home", frame.home == 1),
        ("road", frame.home == -1),
        ("neutral", frame.home == 0),
        ("nonhome", frame.home <= 0),
    ):
        groups.append(aggregate(frame.loc[mask], "venue", name, SMALL_STATS))
    strength = ratings.set_index("TeamID").strength
    opponent = frame.OpponentID.map(strength)
    for name, mask in (
        ("upper_quartile", opponent >= strength.quantile(0.75)),
        ("lower_quartile", opponent <= strength.quantile(0.25)),
        ("above_median", opponent >= strength.median()),
    ):
        groups.append(aggregate(frame.loc[mask], "opponent", name, SMALL_STATS))
    groups.append(trajectories(frame, cutoff))
    mean = frame.groupby("TeamID")[list(SIGNALS)].mean()
    recent_mean = recent.groupby("TeamID")[list(SIGNALS)].mean()
    deviation = frame.groupby("TeamID")[list(SIGNALS)].std()
    peer = {}
    for signal in SIGNALS:
        values = mean[signal]
        scale = values.std()
        normalized = (
            (values - values.mean()) / scale if pd.notna(scale) and scale > 0 else values * np.nan
        )
        for stat, vector in zip(
            PEER_STATS,
            (
                values.rank(pct=True),
                normalized,
                recent_mean[signal].rank(pct=True),
                deviation[signal].rank(pct=True),
            ),
            strict=True,
        ):
            peer[f"research_peer_season_{signal}_{stat}"] = vector
    groups.append(pd.DataFrame(peer))
    result = pd.concat(groups, axis=1).reindex(
        columns=[c for columns in CANDIDATE_FAMILIES.values() for c in columns]
    )
    if result.columns.duplicated().any() or np.isinf(result.to_numpy(dtype=float)).any():
        raise ValueError("Duplicate or infinite candidate features")
    result.index.name = "TeamID"
    return result.astype(np.float32).reset_index()
