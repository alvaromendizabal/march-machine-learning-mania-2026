from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

BOX_STATS = [
    "FGM",
    "FGA",
    "FGM3",
    "FGA3",
    "FTM",
    "FTA",
    "OR",
    "DR",
    "Ast",
    "TO",
    "Stl",
    "Blk",
    "PF",
]


def invert_location(values: pd.Series) -> pd.Series:
    return values.map({"H": "A", "A": "H", "N": "N"}).fillna(values)


def _gender_from_table_name(name: str) -> str:
    if name.startswith("M"):
        return "M"
    if name.startswith("W"):
        return "W"
    raise ValueError(f"Cannot infer gender from table name: {name}")


def combine_teams(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for name in ("MTeams", "WTeams"):
        if name in tables:
            frame = tables[name].copy()
            frame.insert(0, "Gender", _gender_from_table_name(name))
            frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False)


def combine_seasons(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for name in ("MSeasons", "WSeasons"):
        if name in tables:
            frame = tables[name].copy()
            frame.insert(0, "Gender", _gender_from_table_name(name))
            frame["DayZero"] = pd.to_datetime(frame["DayZero"], errors="coerce")
            frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False)


def combine_seeds(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for name in ("MNCAATourneySeeds", "WNCAATourneySeeds"):
        if name not in tables:
            continue
        frame = tables[name].copy()
        frame.insert(0, "Gender", _gender_from_table_name(name))
        parsed = (
            frame["Seed"]
            .astype("string")
            .str.extract(r"^(?P<Region>[WXYZ])(?P<SeedNum>\d{2})(?P<PlayIn>[ab]?)$")
        )
        frame["Region"] = parsed["Region"]
        frame["SeedNum"] = pd.to_numeric(parsed["SeedNum"], errors="coerce").astype("Int64")
        frame["PlayIn"] = parsed["PlayIn"].replace("", pd.NA)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False)


def combine_team_conferences(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for name in ("MTeamConferences", "WTeamConferences"):
        if name in tables:
            frame = tables[name].copy()
            frame.insert(0, "Gender", _gender_from_table_name(name))
            frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False)


def combine_game_cities(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for name in ("MGameCities", "WGameCities"):
        if name in tables:
            frame = tables[name].copy()
            frame.insert(0, "Gender", _gender_from_table_name(name))
            frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False)


def canonicalize_compact_results(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Create a lower-TeamID-oriented game table without aggregating features."""
    specs = [
        ("MRegularSeasonCompactResults", "M", "Regular"),
        ("WRegularSeasonCompactResults", "W", "Regular"),
        ("MNCAATourneyCompactResults", "M", "NCAA"),
        ("WNCAATourneyCompactResults", "W", "NCAA"),
    ]
    frames = []
    for name, gender, game_type in specs:
        if name not in tables:
            continue
        frame = tables[name].copy()
        low_is_winner = frame["WTeamID"] < frame["LTeamID"]
        out = frame.copy()
        out.insert(0, "Gender", gender)
        out.insert(1, "GameType", game_type)
        out["Team1ID"] = np.minimum(frame["WTeamID"], frame["LTeamID"])
        out["Team2ID"] = np.maximum(frame["WTeamID"], frame["LTeamID"])
        out["Team1Score"] = np.where(low_is_winner, frame["WScore"], frame["LScore"])
        out["Team2Score"] = np.where(low_is_winner, frame["LScore"], frame["WScore"])
        out["Team1Win"] = low_is_winner.astype("int8")
        out["Team1Margin"] = out["Team1Score"] - out["Team2Score"]
        out["Team1Loc"] = np.where(
            low_is_winner,
            frame["WLoc"],
            invert_location(frame["WLoc"]),
        )
        out["GameKey"] = (
            out["Gender"].astype(str)
            + "_"
            + out["Season"].astype(str)
            + "_"
            + out["DayNum"].astype(str)
            + "_"
            + out["Team1ID"].astype(str)
            + "_"
            + out["Team2ID"].astype(str)
        )
        frames.append(out)
    result = pd.concat(frames, ignore_index=True, sort=False)
    return result.sort_values(["Gender", "Season", "DayNum", "Team1ID", "Team2ID"]).reset_index(
        drop=True
    )


def detailed_results_to_team_long(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Reshape detailed games to two team-perspective rows per game; no derived metrics."""
    specs = [
        ("MRegularSeasonDetailedResults", "M", "Regular"),
        ("WRegularSeasonDetailedResults", "W", "Regular"),
        ("MNCAATourneyDetailedResults", "M", "NCAA"),
        ("WNCAATourneyDetailedResults", "W", "NCAA"),
    ]
    frames = []
    for name, gender, game_type in specs:
        if name not in tables:
            continue
        df = tables[name]
        base = pd.DataFrame(
            {
                "Gender": gender,
                "GameType": game_type,
                "Season": df["Season"],
                "DayNum": df["DayNum"],
                "NumOT": df["NumOT"],
            }
        )
        game_key = (
            gender
            + "_"
            + df["Season"].astype(str)
            + "_"
            + df["DayNum"].astype(str)
            + "_"
            + np.minimum(df["WTeamID"], df["LTeamID"]).astype(str)
            + "_"
            + np.maximum(df["WTeamID"], df["LTeamID"]).astype(str)
        )

        winner = base.copy()
        winner["GameKey"] = game_key
        winner["TeamID"] = df["WTeamID"].to_numpy()
        winner["OppTeamID"] = df["LTeamID"].to_numpy()
        winner["TeamScore"] = df["WScore"].to_numpy()
        winner["OppScore"] = df["LScore"].to_numpy()
        winner["Win"] = np.int8(1)
        winner["TeamLoc"] = df["WLoc"].to_numpy()

        loser = base.copy()
        loser["GameKey"] = game_key
        loser["TeamID"] = df["LTeamID"].to_numpy()
        loser["OppTeamID"] = df["WTeamID"].to_numpy()
        loser["TeamScore"] = df["LScore"].to_numpy()
        loser["OppScore"] = df["WScore"].to_numpy()
        loser["Win"] = np.int8(0)
        loser["TeamLoc"] = invert_location(df["WLoc"]).to_numpy()

        for stat in BOX_STATS:
            winner[f"Team{stat}"] = df[f"W{stat}"].to_numpy()
            winner[f"Opp{stat}"] = df[f"L{stat}"].to_numpy()
            loser[f"Team{stat}"] = df[f"L{stat}"].to_numpy()
            loser[f"Opp{stat}"] = df[f"W{stat}"].to_numpy()

        frames.extend([winner, loser])

    result = pd.concat(frames, ignore_index=True, sort=False)
    result["Margin"] = result["TeamScore"] - result["OppScore"]
    return result.sort_values(["Gender", "Season", "DayNum", "GameKey", "TeamID"]).reset_index(
        drop=True
    )


def parse_submission_tables(tables: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for name in ("SampleSubmissionStage1", "SampleSubmissionStage2"):
        if name not in tables:
            continue
        frame = tables[name].copy()
        parts = frame["ID"].astype("string").str.split("_", expand=True)
        if parts.shape[1] != 3:
            raise ValueError(f"Unexpected ID format in {name}")
        frame.insert(0, "SubmissionFile", name)
        frame["Season"] = pd.to_numeric(parts[0], errors="raise").astype("int16")
        frame["Team1ID"] = pd.to_numeric(parts[1], errors="raise").astype("int32")
        frame["Team2ID"] = pd.to_numeric(parts[2], errors="raise").astype("int32")
        frame["Gender"] = np.select(
            [
                (frame["Team1ID"] < 3000) & (frame["Team2ID"] < 3000),
                (frame["Team1ID"] >= 3000) & (frame["Team2ID"] >= 3000),
            ],
            ["M", "W"],
            default="INVALID",
        )
        frames.append(frame)
    return pd.concat(frames, ignore_index=True, sort=False)
