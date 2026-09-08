"""Coach tenure and forward-only team/coach histories from official coach intervals."""

from __future__ import annotations

import numpy as np
import pandas as pd

from march_mania.features import team_games

COACH_FEATURES = ["coach_known", "coach_tenure", "coach_prior_teams", "coach_prior_seasons"] + [
    f"coach_{source}_{window}_{stat}"
    for source in ("regular", "tournament")
    for window in (1, 3, 5)
    for stat in ("support", "win_posterior", "margin")
]


def coach_snapshot(
    coaches: pd.DataFrame | None,
    compact: pd.DataFrame,
    tournament: pd.DataFrame,
    teams: pd.DataFrame,
    season: int,
    cutoff: int,
) -> pd.DataFrame:
    """No current-season NCAA result or post-cutoff coaching change is visible.

    Missing official coach tables (including women's data) remain explicitly
    unavailable, not a fabricated coach identity. Same-season regular-season
    performance is represented by team snapshots; coach performance uses only
    earlier seasons, with assignments matched to the actual game day.
    """
    result = teams[["TeamID"]].copy()
    missing = pd.DataFrame(np.nan, index=result.index, columns=COACH_FEATURES)
    result = pd.concat([result, missing], axis=1)
    result["coach_known"] = 0.0
    if coaches is None:
        return result
    required = ["Season", "TeamID", "FirstDayNum", "LastDayNum", "CoachName"]
    if not set(required).issubset(coaches) or coaches[required].isna().any().any():
        raise ValueError("Official coach intervals require complete named columns")
    legal = coaches.loc[
        (coaches.Season <= season) & (coaches.FirstDayNum <= coaches.LastDayNum)
    ].copy()
    if len(legal) != int((coaches.Season <= season).sum()):
        raise ValueError("Reversed coach interval")
    active = legal.loc[
        (legal.Season == season) & (legal.FirstDayNum <= cutoff) & (legal.LastDayNum >= cutoff)
    ]
    if active.TeamID.duplicated().any():
        raise ValueError("Overlapping active coach intervals")
    current = active.set_index("TeamID").CoachName
    result["coach_known"] = result.TeamID.isin(current.index).astype(float)
    history = legal.loc[legal.Season < season]
    for index, team in result.TeamID.items():
        if team not in current:
            continue
        name = current.loc[team]
        previous = history.loc[history.CoachName == name]
        tenure = 0
        for year in range(season - 1, int(legal.Season.min()) - 1, -1):
            if not ((previous.Season == year) & (previous.TeamID == team)).any():
                break
            tenure += 1
        result.loc[index, ["coach_tenure", "coach_prior_teams", "coach_prior_seasons"]] = [
            tenure,
            previous.TeamID.nunique(),
            previous.Season.nunique(),
        ]
    for source, games in (("regular", compact), ("tournament", tournament)):
        old = games.loc[games.Season.between(season - 5, season - 1)]
        long = team_games(old)
        joined = long.merge(history, on=["Season", "TeamID"], how="left", validate="many_to_many")
        assigned = joined.loc[
            (joined.DayNum >= joined.FirstDayNum) & (joined.DayNum <= joined.LastDayNum)
        ].copy()
        if assigned.duplicated(["Season", "DayNum", "TeamID", "OpponentID"]).any():
            raise ValueError("Historical game assigned to overlapping coach intervals")
        assigned["margin"] = assigned.points - assigned.allowed
        names = result.TeamID.map(current)
        for window in (1, 3, 5):
            frame = assigned.loc[assigned.Season >= season - window]
            stats = frame.groupby("CoachName").agg(
                games=("win", "size"), wins=("win", "sum"), margin=("margin", "sum")
            )
            support = names.map(stats.games).fillna(0)
            wins = names.map(stats.wins).fillna(0)
            margin = names.map(stats.margin).fillna(0)
            for stat, values in (
                ("support", np.log1p(support)),
                ("win_posterior", (wins + 10) / (support + 20)),
                ("margin", margin / (support + 20)),
            ):
                result[f"coach_{source}_{window}_{stat}"] = values.where(names.notna())
    return result
