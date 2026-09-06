"""Compact, auditable pre-tournament features built exclusively from official files.

All NCAA outcomes are passed separately as labels. Season snapshots use only
regular-season games at or before the declared cutoff. No fitted tournament
preprocessing or calibration lives in this module.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.linear_model import Ridge

BOX = ("FGM", "FGA", "FGM3", "FGA3", "FTM", "FTA", "OR", "DR", "TO")
FILES = (
    "RegularSeasonCompactResults",
    "RegularSeasonDetailedResults",
    "NCAATourneyCompactResults",
    "NCAATourneySeeds",
)
KEYS = ["Gender", "Season", "TeamID"]


def validate_games(frame: pd.DataFrame, detailed: bool = False) -> None:
    required = ["Season", "DayNum", "WTeamID", "LTeamID", "WScore", "LScore", "WLoc"]
    if detailed:
        required += [side + name for side in ("W", "L") for name in BOX]
    missing = sorted(set(required) - set(frame.columns.astype(str)))
    if missing:
        raise ValueError(f"Missing game columns: {missing}")
    if frame.empty or frame[required].isna().any().any():
        raise ValueError("Empty games or missing required game values")
    numeric = [c for c in required if c != "WLoc"]
    if not np.isfinite(frame[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Game values must be finite")
    if (frame[numeric] < 0).any().any():
        raise ValueError("Game values must be nonnegative")
    if not frame.WLoc.isin(["H", "A", "N"]).all():
        raise ValueError("Invalid game location")
    if (frame.WTeamID == frame.LTeamID).any() or (frame.WScore <= frame.LScore).any():
        raise ValueError("Invalid winner, opponent or score")
    identities = pd.DataFrame(
        {
            "Season": frame.Season,
            "DayNum": frame.DayNum,
            "Low": np.minimum(frame.WTeamID, frame.LTeamID),
            "High": np.maximum(frame.WTeamID, frame.LTeamID),
        }
    )
    if identities.duplicated().any():
        raise ValueError("Duplicate physical game")
    if detailed:
        for side in ("W", "L"):
            for made, attempts in [("FGM", "FGA"), ("FGM3", "FGA3"), ("FTM", "FTA")]:
                if (frame[side + made] > frame[side + attempts]).any():
                    raise ValueError("Made shots exceed attempts")
            if (frame[side + "FGM3"] > frame[side + "FGM"]).any():
                raise ValueError("Three-point makes exceed all field goals")


def read_official(raw: Path) -> tuple[dict[str, dict[str, pd.DataFrame]], list[Path]]:
    paths = [raw / f"{gender}{name}.csv" for gender in ("M", "W") for name in FILES]
    missing = [str(p) for p in paths if not p.is_file()]
    if missing:
        raise FileNotFoundError(
            "Place the official CSV files directly in the raw directory. Missing: "
            + ", ".join(missing)
        )
    data: dict[str, dict[str, pd.DataFrame]] = {}
    for gender in ("M", "W"):
        data[gender] = {}
        for name in FILES:
            frame = pd.read_csv(raw / f"{gender}{name}.csv")
            if "Results" in name:
                validate_games(frame, detailed="Detailed" in name)
            else:
                if not {"Season", "TeamID", "Seed"}.issubset(frame):
                    raise ValueError("Seeds require Season, TeamID, Seed")
                if frame[["Season", "TeamID", "Seed"]].isna().any().any():
                    raise ValueError("Missing seed values")
                if frame.duplicated(["Season", "TeamID"]).any():
                    raise ValueError("Duplicate tournament seed")
                parsed = frame.Seed.astype(str).str.extract(r"^[WXYZ](0[1-9]|1[0-6])[ab]?$")[0]
                if parsed.isna().any():
                    raise ValueError("Invalid seed code")
                frame["seed"] = parsed.astype(float)
            data[gender][name] = frame
    return data, paths


def team_games(frame: pd.DataFrame, detailed: bool = False) -> pd.DataFrame:
    rows = []
    for side, other, sign in [("W", "L", 1), ("L", "W", -1)]:
        result = pd.DataFrame(
            {
                "Season": frame.Season,
                "DayNum": frame.DayNum,
                "TeamID": frame[side + "TeamID"],
                "OpponentID": frame[other + "TeamID"],
                "points": frame[side + "Score"],
                "allowed": frame[other + "Score"],
                "home": sign * frame.WLoc.map({"H": 1, "A": -1, "N": 0}),
                "win": int(side == "W"),
            }
        )
        if detailed:
            for name in BOX:
                result[name] = frame[side + name]
                result["opp_" + name] = frame[other + name]
        rows.append(result)
    return pd.concat(rows, ignore_index=True)


def strength_ratings(
    games: pd.DataFrame, alpha: float, half_life: float, cutoff: int
) -> pd.DataFrame:
    """Ridge-adjusted scoring margin; home effect estimated from same legal games."""
    teams = np.sort(pd.unique(games[["WTeamID", "LTeamID"]].to_numpy().ravel()))
    lookup = {team: i for i, team in enumerate(teams)}
    n = len(games)
    row = np.concatenate([np.arange(n)] * 3)
    col = np.concatenate(
        [games.WTeamID.map(lookup), games.LTeamID.map(lookup), np.full(n, len(teams))]
    )
    values = np.concatenate([np.ones(n), -np.ones(n), games.WLoc.map({"H": 1, "A": -1, "N": 0})])
    design = sparse.csr_matrix((values, (row, col)), shape=(n, len(teams) + 1))
    model = Ridge(alpha=alpha, fit_intercept=False, solver="lsqr", tol=1e-8)
    margin = games.WScore - games.LScore
    model.fit(design, margin)
    full = model.coef_[: len(teams)].copy()
    weights = np.power(0.5, (cutoff - games.DayNum.to_numpy(dtype=float)) / half_life)
    model.fit(design, margin, sample_weight=weights)
    recent = model.coef_[: len(teams)].copy()
    return pd.DataFrame(
        {
            "TeamID": teams,
            "strength": full,
            "recent_strength": recent,
            "strength_change": recent - full,
        }
    )


def box_rates(frame: pd.DataFrame) -> pd.DataFrame:
    totals = frame.groupby("TeamID").sum(numeric_only=True)
    out = pd.DataFrame(index=totals.index)
    for prefix, other in [("", "opp_"), ("opp_", "")]:
        possessions = (
            totals[prefix + "FGA"]
            - totals[prefix + "OR"]
            + totals[prefix + "TO"]
            + 0.475 * totals[prefix + "FTA"]
        )
        if (possessions <= 0).any():
            raise ValueError("Nonpositive possession estimate")
        out[prefix + "efg"] = (totals[prefix + "FGM"] + 0.5 * totals[prefix + "FGM3"]) / totals[
            prefix + "FGA"
        ].replace(0, np.nan)
        out[prefix + "tov"] = totals[prefix + "TO"] / possessions
        out[prefix + "orb"] = totals[prefix + "OR"] / (
            totals[prefix + "OR"] + totals[other + "DR"]
        ).replace(0, np.nan)
        out[prefix + "ftr"] = totals[prefix + "FTA"] / totals[prefix + "FGA"].replace(0, np.nan)
        out[prefix + "three_rate"] = totals[prefix + "FGA3"] / totals[prefix + "FGA"].replace(
            0, np.nan
        )
    out["detail_games"] = frame.groupby("TeamID").size()
    return out.reset_index()


def snapshot(
    compact: pd.DataFrame,
    detailed: pd.DataFrame,
    seeds: pd.DataFrame,
    gender: str,
    season: int,
    cutoff: int,
    alpha: float,
    half_life: float,
) -> pd.DataFrame:
    games = compact.loc[(compact.Season == season) & (compact.DayNum <= cutoff)].copy()
    detail = detailed.loc[(detailed.Season == season) & (detailed.DayNum <= cutoff)].copy()
    if games.empty:
        raise ValueError(f"No legal regular-season games for {gender} {season}")
    long = team_games(games)
    long["margin"] = long.points - long.allowed
    grouped = long.groupby("TeamID")
    result = grouped.agg(
        games=("win", "size"),
        win_rate=("win", "mean"),
        margin=("margin", "mean"),
        margin_sd=("margin", "std"),
    ).reset_index()
    ratings = strength_ratings(games, alpha, half_life, cutoff)
    result = result.merge(ratings, on="TeamID", validate="one_to_one")
    schedule = long.merge(
        ratings[["TeamID", "strength"]].rename(
            columns={"TeamID": "OpponentID", "strength": "opponent_strength"}
        ),
        on="OpponentID",
        validate="many_to_one",
    )
    result = result.merge(
        schedule.groupby("TeamID")
        .opponent_strength.mean()
        .rename("schedule_strength")
        .reset_index(),
        on="TeamID",
        validate="one_to_one",
    )
    if not detail.empty:
        compact_keys = games[["Season", "DayNum", "WTeamID", "LTeamID", "WScore", "LScore"]]
        match = detail.merge(
            compact_keys,
            on=list(compact_keys.columns),
            how="left",
            indicator=True,
            validate="one_to_one",
        )
        if not match["_merge"].eq("both").all():
            raise ValueError("Detailed games disagree with compact results")
        result = result.merge(
            box_rates(team_games(detail, detailed=True)),
            on="TeamID",
            how="left",
            validate="one_to_one",
        )
    else:
        for name in [
            "detail_games",
            *[p + n for p in ("", "opp_") for n in ("efg", "tov", "orb", "ftr", "three_rate")],
        ]:
            result[name] = np.nan
    result["detailed_coverage"] = result.detail_games.fillna(0) / result.games
    legal_seeds = seeds.loc[seeds.Season == season, ["TeamID", "seed"]]
    result = result.merge(legal_seeds, on="TeamID", how="left", validate="one_to_one")
    result["Gender"], result["Season"] = gender, season
    return result


def matchups(
    teams: pd.DataFrame, games: pd.DataFrame, gender: str, include_play_in: bool = True
) -> pd.DataFrame:
    selected = games.copy()
    if not include_play_in:
        selected = selected.loc[selected.DayNum >= 136].copy()
    out = pd.DataFrame(
        {
            "Gender": gender,
            "Season": selected.Season,
            "DayNum": selected.DayNum,
            "Team1ID": np.minimum(selected.WTeamID, selected.LTeamID),
            "Team2ID": np.maximum(selected.WTeamID, selected.LTeamID),
            "y": (selected.WTeamID < selected.LTeamID).astype(int),
        }
    )
    out = out.reset_index(drop=True)
    joined = out.copy()
    for label, key in [("a", "Team1ID"), ("b", "Team2ID")]:
        renamed = teams.rename(
            columns={"TeamID": key, **{c: f"{label}_{c}" for c in teams if c not in KEYS}}
        )
        joined = joined.merge(
            renamed, on=["Gender", "Season", key], how="left", validate="many_to_one"
        )
    if joined[["a_games", "b_games", "a_seed", "b_seed"]].isna().any().any():
        raise ValueError("Missing pre-tournament snapshot or seed for a labeled team")
    for feature in [
        "seed",
        "strength",
        "schedule_strength",
        "win_rate",
        "margin",
        "margin_sd",
        "recent_strength",
        "strength_change",
        "efg",
        "opp_efg",
        "tov",
        "opp_tov",
        "orb",
        "opp_orb",
        "ftr",
        "opp_ftr",
        "three_rate",
        "opp_three_rate",
        "detailed_coverage",
    ]:
        out["diff_" + feature] = joined["a_" + feature] - joined["b_" + feature]
    # Genuine cross-team products: swapping the teams negates every feature.
    # These are hypotheses, not calibrated probability estimates.
    for rate in ["efg", "tov", "orb", "ftr", "three_rate"]:
        out["matchup_" + rate] = (
            joined["a_" + rate] * joined["b_opp_" + rate]
            - joined["b_" + rate] * joined["a_opp_" + rate]
        )
    out["matchup_strength_volatility"] = out.diff_strength / np.sqrt(
        joined.a_margin_sd**2 + joined.b_margin_sd**2 + 1
    )
    out["ID"] = (
        out.Season.astype(str) + "_" + out.Team1ID.astype(str) + "_" + out.Team2ID.astype(str)
    )
    if out.duplicated(["Gender", "ID"]).any():
        raise ValueError("Duplicate NCAA matchup ID")
    features = [c for c in out if str(c).startswith(("diff_", "matchup_"))]
    if np.isinf(out[features].to_numpy(dtype=float)).any():
        raise ValueError("Infinite feature values")
    return out


def feature_blocks() -> dict[str, list[str]]:
    seed = ["diff_seed"]
    strength = seed + [
        "diff_strength",
        "diff_schedule_strength",
        "diff_win_rate",
        "diff_margin",
        "diff_margin_sd",
    ]
    efficiency = [
        "diff_" + prefix + rate
        for prefix in ("", "opp_")
        for rate in ("efg", "tov", "orb", "ftr", "three_rate")
    ]
    recent = ["diff_recent_strength", "diff_strength_change"]
    nonlinear = ["matchup_" + rate for rate in ("efg", "tov", "orb", "ftr", "three_rate")]
    nonlinear += ["matchup_strength_volatility"]
    core = strength + efficiency + ["diff_detailed_coverage"]
    return {
        "seed": seed,
        "strength": strength,
        "efficiency": core,
        "recent": core + recent,
        "matchup": core + nonlinear,
        "full": core + recent + nonlinear,
    }
