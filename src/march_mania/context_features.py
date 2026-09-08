"""Additional basketball hypotheses using only the current legal regular season."""

from __future__ import annotations

import numpy as np
import pandas as pd

from march_mania.features import team_games

CONTEXT_FAMILIES = {
    "ball_control": [
        side + rate
        for side in ("", "opp_")
        for rate in ("assist_ratio", "assist_turnover", "steal_rate", "block_rate", "foul_rate")
    ],
    "schedule_context": [
        "neutral_margin",
        "road_margin",
        "elite_win_posterior",
        "elite_fraction",
        "games_last_14",
        "overtime_fraction",
    ],
    "scoring_shape": [
        "pythagorean_win",
        "rating_balance",
        "rating_imbalance",
        "margin_lower_tail",
    ],
}

CONFERENCE_FEATURES = [
    "conference_known",
    "conference_teams",
    "conference_mean_strength",
    "conference_median_strength",
    "conference_upper_strength",
    "conference_strength_sd",
    "conference_team_percentile",
    "conference_nonconference_support",
    "conference_nonconference_win_posterior",
    "conference_nonconference_margin",
    "conference_nonconference_opponent_strength",
    "conference_nonconference_adjusted_margin",
]


def conference_snapshot(
    membership: pd.DataFrame | None,
    compact: pd.DataFrame,
    ratings: pd.DataFrame,
    season: int,
    cutoff: int,
) -> pd.DataFrame:
    """Season-specific peers and interconference results known by the snapshot.

    Annual membership is never propagated across a realignment. Independent teams
    are not treated as a single competitive conference. The fixed 20-game prior
    shrinks sparse interconference results; no NCAA tournament labels are read.
    """
    result = ratings[["TeamID"]].copy()
    result = pd.concat(
        [result, pd.DataFrame(np.nan, index=result.index, columns=CONFERENCE_FEATURES)], axis=1
    )
    result["conference_known"] = 0.0
    if membership is None:
        return result
    required = ["Season", "TeamID", "ConfAbbrev"]
    if not set(required).issubset(membership):
        raise ValueError("Conference membership requires Season, TeamID, ConfAbbrev")
    current = membership.loc[membership.Season == season, required].copy()
    if current.isna().any().any() or current.TeamID.duplicated().any():
        raise ValueError("Missing or duplicate season-specific conference membership")
    current = current.loc[~current.ConfAbbrev.str.lower().isin(["ind", "independent"])]
    peers = ratings[["TeamID", "strength"]].merge(
        current, on="TeamID", how="left", validate="one_to_one"
    )
    names = result.TeamID.map(peers.set_index("TeamID").ConfAbbrev)
    grouped = peers.groupby("ConfAbbrev").strength
    aggregates: dict[str, pd.Series] = {
        "teams": pd.Series(np.log1p(grouped.count()), index=grouped.count().index),
        "mean_strength": grouped.mean(),
        "median_strength": grouped.median(),
        "upper_strength": grouped.quantile(0.75),
        "strength_sd": grouped.std(),
    }
    for name, values in aggregates.items():
        result["conference_" + name] = names.map(values)
    peers["percentile"] = grouped.rank(pct=True)
    result["conference_team_percentile"] = result.TeamID.map(peers.set_index("TeamID").percentile)
    result["conference_known"] = names.notna().astype(float)
    legal = compact.loc[(compact.Season == season) & (compact.DayNum <= cutoff)]
    games = team_games(legal)
    lookup = peers.set_index("TeamID")
    games["conference"] = games.TeamID.map(lookup.ConfAbbrev)
    games["opponent_conference"] = games.OpponentID.map(lookup.ConfAbbrev)
    games["opponent_strength"] = games.OpponentID.map(lookup.strength)
    # An unknown opponent conference is not silently interpreted as interconference.
    games = games.loc[
        games.conference.notna()
        & games.opponent_conference.notna()
        & games.conference.ne(games.opponent_conference)
    ].copy()
    games["margin"] = games.points - games.allowed
    games["adjusted_margin"] = games.margin + games.opponent_strength
    stats = games.groupby("conference").agg(
        support=("win", "size"),
        wins=("win", "sum"),
        margin=("margin", "sum"),
        opponent_strength=("opponent_strength", "sum"),
        adjusted_margin=("adjusted_margin", "sum"),
    )
    support = names.map(stats.support).fillna(0)
    result["conference_nonconference_support"] = np.log1p(support).where(names.notna())
    result["conference_nonconference_win_posterior"] = (
        (names.map(stats.wins).fillna(0) + 10) / (support + 20)
    ).where(names.notna())
    for name in ("margin", "opponent_strength", "adjusted_margin"):
        result["conference_nonconference_" + name] = (
            names.map(stats[name]).fillna(0) / (support + 20)
        ).where(names.notna())
    return result


def context_snapshot(
    compact: pd.DataFrame,
    detailed: pd.DataFrame,
    ratings: pd.DataFrame,
    season: int,
    cutoff: int,
) -> pd.DataFrame:
    """Twenty candidates; unavailable extra box fields remain missing, never fabricated.

    Priors, thresholds and exponents are fixed before development evaluation.
    Venue margins shrink toward zero with five pseudo-games. Elite opponents are
    the top quartile of same-season pre-cutoff adjusted margin ratings. These are
    descriptive season aggregates, not pre-game backtests of regular-season games.
    """
    games = compact.loc[(compact.Season == season) & (compact.DayNum <= cutoff)]
    detail = detailed.loc[(detailed.Season == season) & (detailed.DayNum <= cutoff)]
    long = team_games(games)
    long["margin"] = long.points - long.allowed
    long["overtime"] = np.tile(games.get("NumOT", pd.Series(0, index=games.index)), 2) > 0
    long = long.merge(
        ratings[["TeamID", "strength"]].rename(columns={"TeamID": "OpponentID"}),
        on="OpponentID",
        validate="many_to_one",
    )
    threshold = ratings.strength.quantile(0.75)
    rows = []
    for team, group in long.groupby("TeamID", sort=True):
        elite = group.loc[group.strength >= threshold]
        points, allowed = group.points.sum(), group.allowed.sum()
        # Fixed 11.5 exponent, evaluated as a hypothesis rather than tuned on the labels.
        pythagorean = 1 / (1 + (allowed / max(points, 1)) ** 11.5)
        row = {
            "TeamID": team,
            "elite_win_posterior": (elite.win.sum() + 2.5) / (len(elite) + 5),
            "elite_fraction": len(elite) / len(group),
            "games_last_14": int(group.DayNum.gt(cutoff - 14).sum()),
            "overtime_fraction": group.overtime.mean(),
            "pythagorean_win": pythagorean,
            "margin_lower_tail": group.margin.quantile(0.10),
        }
        for name, location in [("neutral", 0), ("road", -1)]:
            selected = group.loc[group.home == location]
            row[name + "_margin"] = selected.margin.sum() / (len(selected) + 5)
        rows.append(row)
    output = pd.DataFrame(rows).merge(
        ratings[["TeamID", "adj_offense", "adj_defense"]],
        on="TeamID",
        validate="one_to_one",
    )
    output["rating_balance"] = output[["adj_offense", "adj_defense"]].min(axis=1)
    output["rating_imbalance"] = abs(output.adj_offense - output.adj_defense)
    output = output.drop(columns=["adj_offense", "adj_defense"])
    box = team_games(detail, detailed=True)
    for field in ("Ast", "Stl", "Blk", "PF"):
        for prefix, sides in [("", ("W", "L")), ("opp_", ("L", "W"))]:
            columns = [side + field for side in sides]
            if all(column in detail for column in columns):
                values = np.concatenate(
                    [detail[column].to_numpy(dtype=float) for column in columns]
                )
                if not np.isfinite(values).all() or (values < 0).any():
                    raise ValueError(f"Invalid extra box-score values: {field}")
                box[prefix + field] = values
            else:
                box[prefix + field] = np.nan
    totals = box.groupby("TeamID").sum(numeric_only=True, min_count=1)
    possessions = (
        totals.FGA
        - totals.OR
        + totals.TO
        + 0.475 * totals.FTA
        + totals.opp_FGA
        - totals.opp_OR
        + totals.opp_TO
        + 0.475 * totals.opp_FTA
    ) / 2
    extra = pd.DataFrame(index=totals.index)
    for side, other in [("", "opp_"), ("opp_", "")]:
        for name, numerator, denominator in [
            ("assist_ratio", totals[side + "Ast"], totals[side + "FGM"]),
            ("assist_turnover", totals[side + "Ast"], totals[side + "TO"]),
            ("steal_rate", totals[side + "Stl"], possessions),
            ("block_rate", totals[side + "Blk"], totals[other + "FGA"] - totals[other + "FGA3"]),
            ("foul_rate", totals[side + "PF"], possessions),
        ]:
            extra[side + name] = numerator / denominator.replace(0, np.nan)
    return output.merge(extra.reset_index(), on="TeamID", how="left", validate="one_to_one")
