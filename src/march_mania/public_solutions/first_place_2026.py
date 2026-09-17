"""Recreate the published March Mania 2026 first-place system inside this project.

This is a clean-room, functionally equivalent implementation organized around
the project's own paths and evidence model. It does not vendor the source repo
and never uses known 2026 tournament outcomes for model selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import trim_mean
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import accuracy_score, brier_score_loss
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import MinMaxScaler

REFERENCE_REPOSITORY = "harrisonhoran/kaggle-march-mania-2026-1st-place"
REFERENCE_COMMIT = "c4db013f88cf14a036ed4881bbffb05845f5bcd1"
REFERENCE_SCORE = 0.1097454

MEN_FEATURES = ("seed_diff", "opp_qlty_pts_won_diff", "harry_diff")
WOMEN_FEATURES = (
    "seed_diff",
    "avg_blk_diff",
    "opp_qlty_pts_won_diff",
    "harry_diff",
)

POWER_CONFERENCES = frozenset({"big_ten", "acc", "sec", "big_twelve", "big_east", "pac_twelve"})

STATUS_WEIGHTS = {
    "Out For Season": 1.0,
    "Out": 0.75,
    "Game Time Decision": 0.5,
}

NIT_2026 = (
    1120,
    1305,
    1206,
    1370,
    1375,
    1293,
    1251,
    1472,
    1307,
    1143,
    1161,
    1430,
    1358,
    1228,
    1386,
    1205,
    1448,
    1173,
    1463,
    1229,
    1298,
    1133,
    1423,
    1244,
    1409,
    1329,
    1455,
    1414,
    1372,
    1172,
    1461,
    1424,
)

WBIT_2026 = (
    3140,
    3295,
    3401,
    3428,
    3242,
    3243,
    3274,
    3390,
    3143,
    3206,
    3349,
    3458,
    3162,
    3217,
    3281,
    3361,
    3105,
    3151,
    3270,
    3184,
    3407,
    3210,
    3204,
    3258,
    3365,
    3346,
    3256,
    3333,
    3385,
    3371,
    3414,
    3298,
)

SCALER_CONFIGS = {
    "men": {"opp_pts": (-0.55, 0.55), "power_conf": (1.0, 1.3), "top12": (1.0, 1.2)},
    "women": {"opp_pts": (-0.50, 0.50), "power_conf": (1.0, 1.1)},
}

XGB_HPARAMS = {
    "men": {
        "max_depth": 2,
        "min_child_weight": 5,
        "subsample": 0.7,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
    },
    "women": {
        "max_depth": 2,
        "min_child_weight": 3,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
    },
}

OFFICIAL_FILES = (
    "MTeams.csv",
    "MRegularSeasonDetailedResults.csv",
    "MNCAATourneyDetailedResults.csv",
    "MNCAATourneySeeds.csv",
    "MTeamSpellings.csv",
    "MSecondaryTourneyTeams.csv",
    "MTeamConferences.csv",
    "WTeams.csv",
    "WRegularSeasonDetailedResults.csv",
    "WNCAATourneyDetailedResults.csv",
    "WNCAATourneySeeds.csv",
    "WTeamSpellings.csv",
    "WSecondaryTourneyTeams.csv",
    "WTeamConferences.csv",
    "SampleSubmissionStage2.csv",
)


@dataclass
class FeatureBundle:
    tournament: pd.DataFrame
    submission: pd.DataFrame
    team_seasons: pd.DataFrame
    coverage: pd.DataFrame


@dataclass
class ReferenceFit:
    gender: Literal["men", "women"]
    features: tuple[str, ...]
    models: list[Any]
    calibrator: IsotonicRegression
    oof_raw: np.ndarray
    oof_calibrated: np.ndarray
    oof_labels: np.ndarray
    fold_metrics: pd.DataFrame


def _read_csv(directory: Path, filename: str, **kwargs: Any) -> pd.DataFrame:
    path = directory / filename
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_csv(path, **kwargs)


def load_official(directory: Path) -> dict[str, pd.DataFrame]:
    """Load the official files used by the published reference."""
    return {
        "M_teams": _read_csv(directory, "MTeams.csv").assign(League="M"),
        "M_regular": _read_csv(directory, "MRegularSeasonDetailedResults.csv").assign(League="M"),
        "M_tourney": _read_csv(directory, "MNCAATourneyDetailedResults.csv").assign(League="M"),
        "M_seeds": _read_csv(directory, "MNCAATourneySeeds.csv").assign(League="M"),
        "M_spell": _read_csv(directory, "MTeamSpellings.csv", encoding="latin1").assign(League="M"),
        "M_secondary": _read_csv(directory, "MSecondaryTourneyTeams.csv").assign(League="M"),
        "M_conf": _read_csv(directory, "MTeamConferences.csv").assign(League="M"),
        "W_teams": _read_csv(directory, "WTeams.csv").assign(League="W"),
        "W_regular": _read_csv(directory, "WRegularSeasonDetailedResults.csv").assign(League="W"),
        "W_tourney": _read_csv(directory, "WNCAATourneyDetailedResults.csv").assign(League="W"),
        "W_seeds": _read_csv(directory, "WNCAATourneySeeds.csv").assign(League="W"),
        "W_spell": _read_csv(directory, "WTeamSpellings.csv", encoding="latin1").assign(League="W"),
        "W_secondary": _read_csv(directory, "WSecondaryTourneyTeams.csv").assign(League="W"),
        "W_conf": _read_csv(directory, "WTeamConferences.csv").assign(League="W"),
        "submission": _read_csv(directory, "SampleSubmissionStage2.csv"),
    }


def _swap_location(value: str) -> str:
    if value == "H":
        return "A"
    if value == "A":
        return "H"
    return value


def prepare_games(frame: pd.DataFrame) -> pd.DataFrame:
    """Recreate the reference's double-mirrored detailed-game representation."""
    df = frame.rename(columns={"WLoc": "location"}).copy()
    cols = [
        "Season",
        "DayNum",
        "LTeamID",
        "LScore",
        "WTeamID",
        "WScore",
        "NumOT",
        "location",
        "LFGM",
        "LFGA",
        "LFGM3",
        "LFGA3",
        "LFTM",
        "LFTA",
        "LOR",
        "LDR",
        "LAst",
        "LTO",
        "LStl",
        "LBlk",
        "LPF",
        "WFGM",
        "WFGA",
        "WFGM3",
        "WFGA3",
        "WFTM",
        "WFTA",
        "WOR",
        "WDR",
        "WAst",
        "WTO",
        "WStl",
        "WBlk",
        "WPF",
    ]
    df = df.loc[:, cols]

    df["WPoss"] = df["WFGA"] - df["WOR"] + df["WTO"] + df["WFTA"] * 0.475
    df["LPoss"] = df["LFGA"] - df["LOR"] + df["LTO"] + df["LFTA"] * 0.475
    df["Pace"] = 200 / (df["WPoss"] + df["LPoss"]) / 2
    df["WOffEff"] = df["WScore"] / df["WPoss"] * 70
    df["WDefEff"] = df["LScore"] / df["LPoss"] * 70
    df["LOffEff"] = df["LScore"] / df["LPoss"] * 70
    df["LDefEff"] = df["WScore"] / df["WPoss"] * 70
    df["WNetEff"] = df["WOffEff"] - df["WDefEff"]
    df["LNetEff"] = df["LOffEff"] - df["LDefEff"]
    df["WOffRebRate"] = df["WOR"] / (df["WOR"] + df["LDR"])
    df["LOffRebRate"] = df["LOR"] / (df["LOR"] + df["WDR"])
    df["WFTRate"] = df["WFTA"] / df["WFGA"]
    df["LFTRate"] = df["LFTA"] / df["LFGA"]

    overtime_factor = (40 + 5 * df["NumOT"]) / 40
    adjusted = [
        "LScore",
        "WScore",
        "LFGM",
        "LFGA",
        "LFGM3",
        "LFGA3",
        "LFTM",
        "LFTA",
        "LOR",
        "LDR",
        "LAst",
        "LTO",
        "LStl",
        "LBlk",
        "LPF",
        "WFGM",
        "WFGA",
        "WFGM3",
        "WFGA3",
        "WFTM",
        "WFTA",
        "WOR",
        "WDR",
        "WAst",
        "WTO",
        "WStl",
        "WBlk",
        "WPF",
        "Pace",
        "WPoss",
        "WOffEff",
        "WDefEff",
        "WNetEff",
        "LPoss",
        "LOffEff",
        "LDefEff",
        "LNetEff",
        "WOffRebRate",
        "LOffRebRate",
        "WFTRate",
        "LFTRate",
    ]
    for col in adjusted:
        df[col] = df[col] / overtime_factor

    swapped = df.copy()
    swapped["location"] = swapped["location"].map(_swap_location)

    winner_first = df.copy()
    winner_first.columns = [c.replace("W", "T1_").replace("L", "T2_") for c in winner_first.columns]
    swapped.columns = [c.replace("L", "T1_").replace("W", "T2_") for c in swapped.columns]

    out = pd.concat([winner_first, swapped], ignore_index=True)
    out["PointDiff"] = out["T1_Score"] - out["T2_Score"]
    out["win"] = (out["PointDiff"] > 0).astype(int)
    out["men_women"] = out["T1_TeamID"].astype(str).str.startswith("1").astype(int)
    return out


def build_name_map(m_spell: pd.DataFrame, m_teams: pd.DataFrame) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for row in m_spell.itertuples(index=False):
        mapping[str(row.TeamNameSpelling).lower()] = int(row.TeamID)
    for row in m_teams.itertuples(index=False):
        mapping[str(row.TeamName).lower()] = int(row.TeamID)

    aliases = {
        "saint mary's": "st mary's ca",
        "saint joseph's": "st joseph's pa",
        "saint louis": "st louis",
        "loyola chicago": "loyola-chicago",
        "college of charleston": "col charleston",
        "florida atlantic": "fla atlantic",
        "middle tennessee": "mid tennessee",
        "stephen f austin": "sf austin",
        "george washington": "g washington",
        "little rock": "ark little rock",
        "south dakota st": "s dakota st",
        "north carolina st": "nc state",
        "western kentucky": "w kentucky",
        "western carolina": "w carolina",
        "coastal carolina": "coastal car",
    }
    for alias, target in aliases.items():
        if target in mapping:
            mapping[alias] = mapping[target]
    return mapping


def ap_week6(ap_data: pd.DataFrame, name_map: dict[str, int]) -> pd.DataFrame:
    ap = ap_data.loc[ap_data["WEEK"].eq(6)].copy()
    ap["Top12"] = ap["AP RANK"].le(12).astype(int)
    ap = ap.rename(columns={"YEAR": "Season", "TEAM": "TeamName"})
    ap["TeamName"] = ap["TeamName"].astype(str).str.replace(".", "", regex=False)
    ap["TeamID"] = ap["TeamName"].str.lower().map(name_map)
    ap["Top12"] = ap["Top12"].fillna(0)
    return ap


def build_injury_adjustment(
    injuries: pd.DataFrame,
    player_bpr: pd.DataFrame,
    m_teams: pd.DataFrame,
) -> pd.Series:
    stats = player_bpr.copy()
    stats["Adj_BPR"] = (stats["BPR"].astype(float) * 0.7).round(3)
    merged = injuries.merge(stats, on="Player")
    weights = merged["Status"].map(STATUS_WEIGHTS).fillna(0)
    merged["Weighted_BPR"] = (merged["Adj_BPR"] * weights).round(3)
    merged = merged.merge(
        m_teams[["TeamID", "TeamName"]],
        left_on="Team_x",
        right_on="TeamName",
        how="left",
    )
    merged = merged.dropna(subset=["TeamID"])
    merged["TeamID"] = merged["TeamID"].astype(int)
    return merged.groupby("TeamID")["Weighted_BPR"].sum().round(2)


def opponent_quality_points(
    opponent_seed: pd.Series,
    secondary_tourney: pd.Series,
) -> np.ndarray:
    conditions = [
        opponent_seed.le(4),
        opponent_seed.le(16),
        secondary_tourney.notna(),
    ]
    return np.select(conditions, [6.0, 4.0, 2.0], default=0.25)


def _secondary_2026() -> pd.DataFrame:
    men = pd.DataFrame(
        {"Season": 2026, "TeamID": NIT_2026, "SecondaryTourney": "NIT", "League": "M"}
    )
    women = pd.DataFrame(
        {"Season": 2026, "TeamID": WBIT_2026, "SecondaryTourney": "WBIT", "League": "W"}
    )
    return pd.concat([men, women], ignore_index=True)


def _trimmed_mean_2pct(values: pd.Series) -> float:
    """Reference 2% trimmed mean without empty-slice warnings."""
    clean = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if clean.size == 0:
        return float("nan")
    return float(trim_mean(clean, 0.02))


def _trimmed_team_seasons(regular: pd.DataFrame) -> pd.DataFrame:
    boxcols = [
        "T1_Score",
        "T1_FGM",
        "T1_FGA",
        "T1_FGM3",
        "T1_FGA3",
        "T1_FTM",
        "T1_FTA",
        "T1_OR",
        "T1_DR",
        "T1_Ast",
        "T1_TO",
        "T1_Stl",
        "T1_Blk",
        "T1_PF",
        "T2_Score",
        "T2_FGM",
        "T2_FGA",
        "T2_FGM3",
        "T2_FGA3",
        "T2_FTM",
        "T2_FTA",
        "T2_OR",
        "T2_DR",
        "T2_Ast",
        "T2_TO",
        "T2_Stl",
        "T2_Blk",
        "T2_PF",
        "PointDiff",
        "Pace",
        "T1_Poss",
        "T1_OffEff",
        "T1_DefEff",
        "T1_NetEff",
        "T2_Poss",
        "T2_OffEff",
        "T2_DefEff",
        "T2_NetEff",
        "T1_Opp_Qlty_Pts",
        "T1_Power",
        "T1_OffRebRate",
        "T2_OffRebRate",
        "T1_FTRate",
        "T2_FTRate",
        "T1_Top12",
    ]
    grouped = (
        regular.groupby(["Season", "T1_TeamID"])[boxcols].agg(_trimmed_mean_2pct).reset_index()
    )
    grouped["T1_NetEff_std"] = (
        regular.groupby(["Season", "T1_TeamID"])["T1_NetEff"].std().to_numpy()
    )
    # Preserve the published implementation exactly: despite the feature name,
    # this sums all opponent-quality points, not the win-filtered helper.
    grouped["T1_Opp_Qlty_Pts_Won"] = (
        regular.groupby(["Season", "T1_TeamID"])["T1_Opp_Qlty_Pts"].sum().to_numpy()
    )
    grouped["T1_Top12"] = grouped["T1_Top12"].fillna(0)
    win_pct = regular.groupby(["Season", "T1_TeamID"])["win"].mean().rename("win_pct").reset_index()
    return grouped.merge(win_pct, on=["Season", "T1_TeamID"])


def _apply_harry_rating(team_seasons: pd.DataFrame) -> pd.DataFrame:
    out = team_seasons.copy()
    for gender, cfg in SCALER_CONFIGS.items():
        is_men = out["T1_TeamID"].astype(int).lt(3000)
        mask = is_men if gender == "men" else ~is_men
        if not bool(mask.any()):
            continue
        out.loc[mask, "T1_Opp_Qlty_Pts_MinMax"] = (
            MinMaxScaler(feature_range=cfg["opp_pts"])
            .fit_transform(out.loc[mask, ["T1_Opp_Qlty_Pts"]])
            .ravel()
        )
        out.loc[mask, "T1_Power_MinMax"] = (
            MinMaxScaler(feature_range=cfg["power_conf"])
            .fit_transform(out.loc[mask, ["T1_Power"]])
            .ravel()
        )
        if gender == "men":
            out.loc[mask, "T1_Top12_MinMax"] = (
                MinMaxScaler(feature_range=cfg["top12"])
                .fit_transform(out.loc[mask, ["T1_Top12"]])
                .ravel()
            )
        else:
            out.loc[mask, "T1_Top12_MinMax"] = 1.0

    out["T1_harry_Rating"] = (
        out["T1_NetEff"]
        * (1 + out["T1_Opp_Qlty_Pts_MinMax"])
        * out["T1_Power_MinMax"]
        * out["T1_Top12_MinMax"]
    )
    return out


def _side_profiles(team_seasons: pd.DataFrame, side: Literal["T1", "T2"]) -> pd.DataFrame:
    out = team_seasons.copy()
    prefix = f"{side}_avg_"
    out.columns = [prefix + c.replace("T1_", "").replace("T2_", "opponent_") for c in out.columns]
    out = out.rename(
        columns={
            f"{side}_avg_Season": "Season",
            f"{side}_avg_TeamID": f"{side}_TeamID",
            f"{side}_avg_Opp_Qlty_Pts_Won": f"{side}_Opp_Qlty_Pts_Won",
        }
    )
    return out


def _add_matchup_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["seed_diff"] = out["T1_seed"] - out["T2_seed"]
    out["opp_qlty_pts_won_diff"] = out["T1_Opp_Qlty_Pts_Won"] - out["T2_Opp_Qlty_Pts_Won"]
    out["avg_blk_diff"] = out["T1_avg_Blk"] - out["T2_avg_Blk"]
    out["harry_diff"] = out["T1_avg_harry_Rating"] - out["T2_avg_harry_Rating"]
    return out


def build_reference_features(
    official_dir: Path,
    ap_poll_path: Path,
    injury_path: Path,
    bpr_path: Path,
) -> FeatureBundle:
    """Build the published first-place feature matrices from raw inputs."""
    raw = load_official(official_dir)
    ap_data = pd.read_csv(ap_poll_path)
    injuries = pd.read_csv(injury_path)
    bpr = pd.read_csv(bpr_path)

    raw["M_conf"]["Power"] = raw["M_conf"]["ConfAbbrev"].isin(POWER_CONFERENCES).astype(int)
    raw["W_conf"]["Power"] = raw["W_conf"]["ConfAbbrev"].isin(POWER_CONFERENCES).astype(int)

    regular_results = pd.concat([raw["M_regular"], raw["W_regular"]], ignore_index=True)
    tourney_results = pd.concat([raw["M_tourney"], raw["W_tourney"]], ignore_index=True)
    seeds = pd.concat([raw["M_seeds"], raw["W_seeds"]], ignore_index=True)
    conf = pd.concat([raw["M_conf"], raw["W_conf"]], ignore_index=True)
    secondary = pd.concat([raw["M_secondary"], raw["W_secondary"]], ignore_index=True)[
        ["Season", "TeamID", "SecondaryTourney", "League"]
    ]
    secondary = pd.concat([secondary, _secondary_2026()], ignore_index=True)

    cutoff = 2003
    regular_results = regular_results.loc[regular_results["Season"].ge(cutoff)]
    tourney_results = tourney_results.loc[tourney_results["Season"].ge(cutoff)]
    seeds = seeds.loc[seeds["Season"].ge(cutoff)].copy()
    conf = conf.loc[conf["Season"].ge(cutoff)].copy()
    secondary = secondary.loc[secondary["Season"].ge(cutoff)].copy()

    regular = prepare_games(regular_results)
    tournament = prepare_games(tourney_results)

    seeds["seed"] = seeds["Seed"].astype(str).str[1:3].astype(int)
    seed_t1 = seeds[["Season", "TeamID", "seed"]].rename(
        columns={"TeamID": "T1_TeamID", "seed": "T1_seed"}
    )
    seed_t2 = seeds[["Season", "TeamID", "seed"]].rename(
        columns={"TeamID": "T2_TeamID", "seed": "T2_seed"}
    )
    conf_t1 = conf[["Season", "TeamID", "Power"]].rename(
        columns={"TeamID": "T1_TeamID", "Power": "T1_Power"}
    )
    conf_t2 = conf[["Season", "TeamID", "Power"]].rename(
        columns={"TeamID": "T2_TeamID", "Power": "T2_Power"}
    )

    ap = ap_week6(ap_data, build_name_map(raw["M_spell"], raw["M_teams"]))
    ap_t1 = ap[["Season", "TeamID", "Top12"]].rename(
        columns={"TeamID": "T1_TeamID", "Top12": "T1_Top12"}
    )
    ap_t2 = ap[["Season", "TeamID", "Top12"]].rename(
        columns={"TeamID": "T2_TeamID", "Top12": "T2_Top12"}
    )

    sec_t1 = secondary[["Season", "TeamID", "SecondaryTourney"]].rename(
        columns={"TeamID": "T1_TeamID", "SecondaryTourney": "T1_Tourney"}
    )
    sec_t2 = secondary[["Season", "TeamID", "SecondaryTourney"]].rename(
        columns={"TeamID": "T2_TeamID", "SecondaryTourney": "T2_Tourney"}
    )

    for join in (seed_t1, seed_t2, conf_t1, conf_t2, ap_t1, ap_t2, sec_t1, sec_t2):
        keys = ["Season", "T1_TeamID"] if "T1_TeamID" in join.columns else ["Season", "T2_TeamID"]
        regular = regular.merge(join, on=keys, how="left")

    regular["T1_Opp_Qlty_Pts"] = opponent_quality_points(regular["T2_seed"], regular["T2_Tourney"])
    regular["T1_Tourney_Quality_Game"] = regular["T1_Opp_Qlty_Pts"].gt(1).astype(int)
    regular["T1_Tourney_Quality_Win"] = (
        regular["win"].eq(1) & regular["T1_Tourney_Quality_Game"].eq(1)
    ).astype(int)
    regular["T1_Tourney_Quality_Loss"] = (
        regular["win"].eq(0) & regular["T1_Tourney_Quality_Game"].eq(1)
    ).astype(int)
    regular["T1_Opp_Qlty_Pts_Won"] = np.where(regular["win"].eq(1), regular["T1_Opp_Qlty_Pts"], 0)

    team_seasons = _trimmed_team_seasons(regular)
    injury = build_injury_adjustment(injuries, bpr, raw["M_teams"])
    mask_2026 = team_seasons["Season"].eq(2026)
    team_seasons.loc[mask_2026, "T1_NetEff"] -= (
        team_seasons.loc[mask_2026, "T1_TeamID"].map(injury).fillna(0)
    )
    team_seasons = _apply_harry_rating(team_seasons)

    ss_t1 = _side_profiles(team_seasons, "T1")
    ss_t2 = _side_profiles(team_seasons, "T2")

    tournament = tournament[
        ["Season", "T1_TeamID", "T2_TeamID", "PointDiff", "win", "men_women"]
    ].copy()
    for join in (seed_t1, seed_t2, ss_t1, ss_t2, conf_t1, conf_t2, ap_t1, ap_t2):
        keys = ["Season", "T1_TeamID"] if "T1_TeamID" in join.columns else ["Season", "T2_TeamID"]
        tournament = tournament.merge(join, on=keys, how="left")
    tournament = _add_matchup_features(tournament)
    tournament = tournament.loc[
        :,
        [
            "Season",
            "men_women",
            "T1_TeamID",
            "T2_TeamID",
            "PointDiff",
            "win",
            "seed_diff",
            "opp_qlty_pts_won_diff",
            "avg_blk_diff",
            "harry_diff",
        ],
    ]

    submission = raw["submission"].copy()
    parts = submission["ID"].str.split("_", expand=True)
    submission["Season"] = parts[0].astype(int)
    submission["T1_TeamID"] = parts[1].astype(int)
    submission["T2_TeamID"] = parts[2].astype(int)
    submission["men_women"] = submission["T1_TeamID"].astype(str).str.startswith("1").astype(int)
    for join in (seed_t1, seed_t2, ss_t1, ss_t2, conf_t1, conf_t2, ap_t1, ap_t2):
        keys = ["Season", "T1_TeamID"] if "T1_TeamID" in join.columns else ["Season", "T2_TeamID"]
        submission = submission.merge(join, on=keys, how="left")
    submission = _add_matchup_features(submission)

    coverage_rows = []
    for gender_name, flag, features in (
        ("men", 1, MEN_FEATURES),
        ("women", 0, WOMEN_FEATURES),
    ):
        subset = tournament.loc[tournament["men_women"].eq(flag)]
        for feature in features:
            coverage_rows.append(
                {
                    "dataset": "historical_tournament",
                    "gender": gender_name,
                    "feature": feature,
                    "rows": int(len(subset)),
                    "non_null": int(subset[feature].notna().sum()),
                    "coverage": float(subset[feature].notna().mean()),
                }
            )
        ssub = submission.loc[submission["men_women"].eq(flag)]
        for feature in features:
            coverage_rows.append(
                {
                    "dataset": "submission_2026",
                    "gender": gender_name,
                    "feature": feature,
                    "rows": int(len(ssub)),
                    "non_null": int(ssub[feature].notna().sum()),
                    "coverage": float(ssub[feature].notna().mean()),
                }
            )

    return FeatureBundle(
        tournament=tournament,
        submission=submission,
        team_seasons=team_seasons,
        coverage=pd.DataFrame(coverage_rows),
    )


def published_feature_spec() -> pd.DataFrame:
    """Return the literal final feature contract from the pinned public reference.

    Row order intentionally preserves both model feature orders when filtered by
    gender: MEN_FEATURES and WOMEN_FEATURES.
    """
    return pd.DataFrame(
        [
            {
                "feature": "seed_diff",
                "men": True,
                "women": True,
                "definition": "T1 tournament seed minus T2 tournament seed",
            },
            {
                "feature": "avg_blk_diff",
                "men": False,
                "women": True,
                "definition": "T1 minus T2 2%-trimmed mean blocks",
            },
            {
                "feature": "opp_qlty_pts_won_diff",
                "men": True,
                "women": True,
                "definition": (
                    "T1 minus T2 published opponent-quality aggregate. "
                    "The exact reference route preserves the public implementation "
                    "that sums T1_Opp_Qlty_Pts for the field named "
                    "T1_Opp_Qlty_Pts_Won."
                ),
            },
            {
                "feature": "harry_diff",
                "men": True,
                "women": True,
                "definition": "T1 minus T2 custom harry_Rating",
            },
        ]
    )


def reference_xgb_kwargs(gender: Literal["men", "women"]) -> dict[str, Any]:
    return {
        "eval_metric": "rmse",
        "n_estimators": 4000,
        "learning_rate": 0.003,
        "early_stopping_rounds": 100,
        **XGB_HPARAMS[gender],
    }


def fit_reference_cv(
    tournament_features: pd.DataFrame,
    gender: Literal["men", "women"],
) -> ReferenceFit:
    features = MEN_FEATURES if gender == "men" else WOMEN_FEATURES
    data = tournament_features.loc[
        tournament_features["men_women"].eq(1 if gender == "men" else 0)
    ].copy()
    if data["Season"].ge(2026).any():
        raise ValueError("Known 2026 tournament outcomes are forbidden")
    data = data.dropna(subset=[*features, "win", "Season"]).reset_index(drop=True)
    n_splits = int(data["Season"].nunique())
    if n_splits < 2:
        raise ValueError("At least two seasons are required")

    X = data.loc[:, list(features)]
    y = data["win"].astype(int)
    groups = data["Season"].astype(int)
    splitter = GroupKFold(n_splits=n_splits)
    oof = np.full(len(data), np.nan)
    models: list[Any] = []
    rows = []

    for fold, (train_idx, test_idx) in enumerate(splitter.split(X, y, groups), start=1):
        model = xgb.XGBRegressor(**reference_xgb_kwargs(gender))
        model.fit(
            X.iloc[train_idx],
            y.iloc[train_idx],
            eval_set=[(X.iloc[test_idx], y.iloc[test_idx])],
            verbose=False,
        )
        pred = np.clip(model.predict(X.iloc[test_idx]), 0.01, 0.99)
        oof[test_idx] = pred
        labels = y.iloc[test_idx].to_numpy()
        brier = float(brier_score_loss(labels, pred))
        rows.append(
            {
                "gender": gender,
                "fold": fold,
                "holdout_seasons": ",".join(map(str, sorted(groups.iloc[test_idx].unique()))),
                "rows": int(len(test_idx)),
                "brier": brier,
                "rmse": float(np.sqrt(brier)),
                "accuracy": float(accuracy_score(labels, pred > 0.5)),
                "best_iteration": int(getattr(model, "best_iteration", -1)),
            }
        )
        models.append(model)

    calibrator = IsotonicRegression(y_min=0.001, y_max=0.999, out_of_bounds="clip")
    calibrator.fit(oof, y.to_numpy())
    calibrated = np.asarray(calibrator.predict(oof), dtype=float)
    return ReferenceFit(
        gender=gender,
        features=features,
        models=models,
        calibrator=calibrator,
        oof_raw=oof,
        oof_calibrated=calibrated,
        oof_labels=y.to_numpy(),
        fold_metrics=pd.DataFrame(rows),
    )


def sharpen_edges(
    probabilities: np.ndarray | pd.Series,
    temperature: float = 2.5,
    edge: float = 0.03,
) -> np.ndarray:
    p = np.asarray(probabilities, dtype=float)
    result = p.copy()
    mask = (p <= edge) | (p >= 1 - edge)
    x = p[mask]
    result[mask] = x**temperature / (x**temperature + (1 - x) ** temperature)
    return result


def predict_reference(fit: ReferenceFit, frame: pd.DataFrame) -> np.ndarray:
    X = frame.loc[:, list(fit.features)]
    raw = np.column_stack([model.predict(X) for model in fit.models]).mean(axis=1)
    calibrated = np.asarray(fit.calibrator.predict(raw), dtype=float)
    calibrated = np.clip(calibrated, 0.001, 0.999)
    return sharpen_edges(calibrated)
