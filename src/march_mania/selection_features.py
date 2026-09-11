"""Selection-day resume signals; no NCAA outcomes or later participation.

Seeds describe a selection-day resume, not information available during the
regular-season game. All weights and smoothing constants are fixed hypotheses.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

RESUME_FAMILIES = {
    "quality_volume": ["resume_quality_wins", "resume_elite_wins", "resume_seeded_wins"],
    "opportunity": [
        "resume_quality_win_rate",
        "resume_schedule_quality",
        "resume_elite_win_rate",
        "resume_seeded_win_rate",
    ],
    "context": [
        "resume_bad_loss_rate",
        "resume_away_quality_wins",
        "resume_quality_margin",
        "resume_late_quality_wins",
    ],
}
RESUME_COLUMNS = [name for names in RESUME_FAMILIES.values() for name in names]


def selection_snapshot(
    games: pd.DataFrame,
    seeds: pd.DataFrame,
    season: int,
    *,
    cutoff: int = 132,
    seeds_available_day: int = 132,
) -> pd.DataFrame:
    """One row per team; require the complete official current-season seed table.

    Availability is an explicit assumption: an undated CSV cannot establish its
    publication timestamp. Secondary-tournament entries are deliberately unused.
    """
    if cutoff != 132 or seeds_available_day > cutoff or seeds_available_day < 0:
        raise ValueError("Selection-day features require legal seed availability by day 132")
    required = {"Season", "DayNum", "WTeamID", "LTeamID", "WScore", "LScore", "WLoc"}
    if not required.issubset(games) or not {"Season", "TeamID", "Seed"}.issubset(seeds):
        raise ValueError("Missing official regular-season or seed columns")
    legal = games.loc[(games.Season == season) & (games.DayNum <= cutoff)].copy()
    selected = seeds.loc[seeds.Season == season, ["TeamID", "Seed"]].copy()
    if legal.empty or selected.empty:
        raise ValueError("No legal games or no current-season seeds")
    if selected.TeamID.duplicated().any() or selected.isna().any().any():
        raise ValueError("Duplicate or missing current-season seed identity")
    number = selected.Seed.astype(str).str.extract(r"^[A-Za-z](\d{2})(?:[ab])?$", expand=False)
    if number.isna().any() or not number.astype(int).between(1, 16).all():
        raise ValueError("Malformed tournament seed")
    selected["opponent_seed"] = number.astype(int)
    numeric = ["Season", "DayNum", "WTeamID", "LTeamID", "WScore", "LScore"]
    if not np.isfinite(legal[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite regular-season data")
    if (legal.WTeamID == legal.LTeamID).any() or (legal.WScore <= legal.LScore).any():
        raise ValueError("Invalid physical game or winning score")
    if (legal[["WScore", "LScore"]] < 0).any().any() or not legal.WLoc.isin(["H", "A", "N"]).all():
        raise ValueError("Invalid score or venue")
    keys = pd.DataFrame(
        {
            "day": legal.DayNum,
            "a": np.minimum(legal.WTeamID, legal.LTeamID),
            "b": np.maximum(legal.WTeamID, legal.LTeamID),
        }
    )
    if keys.duplicated().any():
        raise ValueError("Duplicate physical regular-season game")
    sides = []
    for winner in (True, False):
        own, opp = ("W", "L") if winner else ("L", "W")
        sides.append(
            pd.DataFrame(
                {
                    "TeamID": legal[own + "TeamID"],
                    "OpponentID": legal[opp + "TeamID"],
                    "win": float(winner),
                    "margin": legal[own + "Score"] - legal[opp + "Score"],
                    "away": (legal.WLoc != ("H" if winner else "A")).astype(float),
                    "late": (legal.DayNum > cutoff - 30).astype(float),
                }
            )
        )
    long = pd.concat(sides, ignore_index=True).merge(
        selected[["TeamID", "opponent_seed"]].rename(columns={"TeamID": "OpponentID"}),
        on="OpponentID",
        how="left",
        validate="many_to_one",
    )
    long["elite"] = long.opponent_seed.le(4).astype(float)
    long["seeded"] = long.opponent_seed.notna().astype(float)
    long["quality"] = np.select([long.elite.eq(1), long.seeded.eq(1)], [6.0, 4.0], default=0.25)
    long["qw"] = long.quality * long.win
    long["ew"] = long.elite * long.win
    long["sw"] = long.seeded * long.win
    long["bl"] = (1 - long.seeded) * (1 - long.win)
    long["unseeded"] = 1 - long.seeded
    long["away_qw"] = long.qw * long.away
    long["late_qw"] = long.qw * long.late
    long["qm"] = long.quality * long.margin
    g = long.groupby("TeamID", sort=True).sum(numeric_only=True)
    n = long.groupby("TeamID").size()
    result = pd.DataFrame(
        {
            "resume_quality_wins": g.qw,
            "resume_elite_wins": g.ew,
            "resume_seeded_wins": g.sw,
            "resume_quality_win_rate": (g.qw + 10) / (g.quality + 20),
            "resume_schedule_quality": g.quality / n,
            "resume_elite_win_rate": (g.ew + 2.5) / (g.elite + 5),
            "resume_seeded_win_rate": (g.sw + 2.5) / (g.seeded + 5),
            "resume_bad_loss_rate": (g.bl + 2.5) / (g.unseeded + 5),
            "resume_away_quality_wins": g.away_qw,
            "resume_quality_margin": g.qm / (g.quality + 20),
            "resume_late_quality_wins": g.late_qw,
        }
    ).reset_index()
    result.insert(0, "Season", season)
    if not np.isfinite(result[RESUME_COLUMNS].to_numpy()).all():
        raise ValueError("Nonfinite resume features")
    return result


def resume_pairs(teams: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    """Attach signed differences while preserving the physical-game row order."""
    if teams.duplicated(["Season", "TeamID"]).any():
        raise ValueError("Duplicate team snapshot")
    result = pairs.copy().reset_index(drop=True)
    for side in (1, 2):
        renamed = teams.rename(
            columns={
                "TeamID": f"Team{side}ID",
                **{name: f"side{side}_{name}" for name in RESUME_COLUMNS},
            }
        )
        result = result.merge(
            renamed, on=["Season", f"Team{side}ID"], how="left", sort=False, validate="many_to_one"
        )
    for name in RESUME_COLUMNS:
        result["diff_" + name] = result["side1_" + name] - result["side2_" + name]
    if result[["diff_" + x for x in RESUME_COLUMNS]].isna().any().any():
        raise ValueError("Pair requests a team without a legal snapshot")
    return result.drop(columns=[f"side{side}_{name}" for side in (1, 2) for name in RESUME_COLUMNS])
