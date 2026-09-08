"""Season-local basketball signals with explicit temporal and statistical contracts.

Ratings use regular-season information available by the snapshot cutoff. Shooting
posteriors use a contemporaneous league prior, not tournament outcomes. All
matchup features reverse sign when the two teams exchange places.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.linear_model import Ridge

from march_mania.candidate_features import CANDIDATE_FAMILIES, candidate_snapshot
from march_mania.coach_features import COACH_FEATURES, coach_snapshot
from march_mania.context_features import CONTEXT_FAMILIES, context_snapshot
from march_mania.encoding import ENCODING_FAMILIES, ENCODING_FEATURES
from march_mania.features import KEYS, feature_blocks, snapshot, team_games
from march_mania.rankings import LEVEL_FEATURES, TREND_FEATURES, ranking_snapshot

FAMILIES = {
    "adjusted": ["adj_offense", "adj_defense", "recent_offense", "recent_defense"],
    "four_factors": [
        f"adjusted_{rate}_{side}"
        for rate in ("efg", "tov", "orb", "ftr")
        for side in ("offense", "defense")
    ],
    "form": [
        "residual_sd",
        "residual_downside",
        "recent_residual",
        "road_residual",
        "schedule_sd",
        "strong_opponent_margin",
        "close_win_posterior",
        "rest_days",
    ],
    "shooting": [
        f"{side}{shot}_{stat}"
        for side in ("", "opp_")
        for shot in ("two", "three", "free")
        for stat in ("posterior", "uncertainty")
    ],
    "tempo": ["tempo", "tempo_sd", "three_dependence", "possession_gap", "clean_coverage"],
    "dynamic": ["elo", "elo_mov", "elo_change", "elo_mov_change"],
    "history": ["prior_wins", "prior_appearances", "prior_seed"],
    "rankings": LEVEL_FEATURES,
    "rank_trends": TREND_FEATURES,
    **ENCODING_FAMILIES,
    **CONTEXT_FAMILIES,
    **CANDIDATE_FAMILIES,
    "coach_history": COACH_FEATURES,
}
INTERACTIONS = [
    "pace_strength",
    "uncertainty_strength",
    "three_variance_strength",
    "shooting_style",
    "offense_defense",
    "recent_offense_defense",
]


def possession_games(games: pd.DataFrame) -> pd.DataFrame:
    """Two team rows per game, shared possessions, and pace per 40 minutes."""
    long = team_games(games, detailed=True)
    estimates = []
    for side in ("", "opp_"):
        estimates.append(
            long[side + "FGA"] - long[side + "OR"] + long[side + "TO"] + 0.475 * long[side + "FTA"]
        )
    if any((estimate <= 0).any() for estimate in estimates):
        raise ValueError("Nonpositive game possessions")
    long["possessions"] = (estimates[0] + estimates[1]) / 2
    long["possession_gap"] = abs(estimates[0] - estimates[1]) / long.possessions
    overtime = games.get("NumOT", pd.Series(0, index=games.index)).to_numpy(dtype=float)
    if not np.isfinite(overtime).all() or (overtime < 0).any():
        raise ValueError("Invalid overtime duration")
    long["tempo"] = long.possessions * 40 / np.tile(40 + 5 * overtime, 2)
    long["efficiency"] = 100 * long.points / long.possessions
    long["clean"] = long.possession_gap <= 0.10
    return long


def efficiency_ratings(long: pd.DataFrame, alpha: float, cutoff: int) -> pd.DataFrame:
    """Additive offense/defense ridge model; positive ratings are better on both sides."""
    clean = long.loc[long.clean].copy()
    if clean.empty:
        raise ValueError("No games pass the preregistered possession-quality threshold")
    teams = np.sort(pd.unique(clean[["TeamID", "OpponentID"]].to_numpy().ravel()))
    lookup = {team: i for i, team in enumerate(teams)}
    n, k = len(clean), len(teams)
    design = sparse.csr_matrix(
        (
            np.r_[np.ones(2 * n), clean.home],
            (
                np.tile(np.arange(n), 3),
                np.r_[
                    clean.TeamID.map(lookup), clean.OpponentID.map(lookup) + k, np.full(n, 2 * k)
                ],
            ),
        ),
        shape=(n, 2 * k + 1),
    )
    output = pd.DataFrame({"TeamID": teams})
    for name, weights in [
        ("adj", np.ones(n)),
        ("recent", 0.5 ** ((cutoff - clean.DayNum.to_numpy(dtype=float)) / 30)),
    ]:
        model = Ridge(alpha=alpha, fit_intercept=True, solver="lsqr", tol=1e-8)
        model.fit(design, clean.efficiency, sample_weight=weights)
        output[name + "_offense"] = model.coef_[:k]
        output[name + "_defense"] = -model.coef_[k : 2 * k]
        if name == "adj":
            clean["residual"] = clean.efficiency - model.predict(design)
    rows = []
    for team, group in clean.groupby("TeamID"):
        recent = 0.5 ** ((cutoff - group.DayNum.to_numpy(dtype=float)) / 30)
        road = group.loc[group.home <= 0, "residual"]
        # Shrink road residuals toward zero when away/neutral samples are scarce.
        rows.append(
            {
                "TeamID": team,
                "residual_sd": group.residual.std(),
                "residual_downside": group.residual.quantile(0.10),
                "recent_residual": np.average(group.residual, weights=recent),
                "road_residual": road.sum() / (len(road) + 5),
            }
        )
    return output.merge(pd.DataFrame(rows), on="TeamID", validate="one_to_one")


def shooting_posteriors(long: pd.DataFrame, prior_attempts: float = 100) -> pd.DataFrame:
    """Beta-binomial posterior mean/SD; zero-attempt teams inherit a finite league prior."""
    if prior_attempts <= 0:
        raise ValueError("Prior attempts must be positive")
    totals = long.groupby("TeamID").sum(numeric_only=True)
    output = pd.DataFrame(index=totals.index)
    for side in ("", "opp_"):
        for shot, made, attempts in [
            (
                "two",
                totals[side + "FGM"] - totals[side + "FGM3"],
                totals[side + "FGA"] - totals[side + "FGA3"],
            ),
            ("three", totals[side + "FGM3"], totals[side + "FGA3"]),
            ("free", totals[side + "FTM"], totals[side + "FTA"]),
        ]:
            if (attempts < 0).any() or (made < 0).any() or (made > attempts).any():
                raise ValueError("Inconsistent shooting attempts")
            league = (made.sum() + 0.5) / (attempts.sum() + 1)
            a = made + prior_attempts * league
            b = attempts - made + prior_attempts * (1 - league)
            output[f"{side}{shot}_posterior"] = a / (a + b)
            output[f"{side}{shot}_uncertainty"] = np.sqrt(a * b / ((a + b) ** 2 * (a + b + 1)))
    return output.reset_index()


def adjusted_factors(long: pd.DataFrame, alpha: float) -> pd.DataFrame:
    """Opponent-adjusted Four Factors; a shared sparse design, four target fits."""
    clean = long.loc[long.clean & (long.FGA > 0) & ((long.OR + long.opp_DR) > 0)].copy()
    if clean.empty:
        raise ValueError("No valid Four Factor observations")
    teams = np.sort(pd.unique(clean[["TeamID", "OpponentID"]].to_numpy().ravel()))
    index = {team: i for i, team in enumerate(teams)}
    n, k = len(clean), len(teams)
    design = sparse.csr_matrix(
        (
            np.r_[np.ones(2 * n), clean.home],
            (
                np.tile(np.arange(n), 3),
                np.r_[clean.TeamID.map(index), clean.OpponentID.map(index) + k, np.full(n, 2 * k)],
            ),
        ),
        shape=(n, 2 * k + 1),
    )
    targets = (
        np.column_stack(
            [
                (clean.FGM + 0.5 * clean.FGM3) / clean.FGA,
                -clean.TO / clean.possessions,
                clean.OR / (clean.OR + clean.opp_DR),
                clean.FTA / clean.FGA,
            ]
        )
        * 100
    )
    model = Ridge(alpha=alpha, fit_intercept=True, solver="lsqr", tol=1e-8)
    model.fit(design, targets)
    result = pd.DataFrame({"TeamID": teams})
    for i, rate in enumerate(("efg", "tov", "orb", "ftr")):
        result[f"adjusted_{rate}_offense"] = model.coef_[i, :k]
        result[f"adjusted_{rate}_defense"] = -model.coef_[i, k : 2 * k]
    return result


def elo_history(compact: pd.DataFrame, cutoff: int = 132) -> pd.DataFrame:
    """One chronological pass; simultaneous daily updates and annual carryover."""
    legal = compact.loc[compact.DayNum <= cutoff]
    ratings: dict[int, np.ndarray] = {}
    before_recent: dict[int, np.ndarray] = {}
    last_season: int | None = None
    season_teams: set[int] = set()
    rows = []

    def finish(year: int) -> None:
        for team in sorted(season_teams):
            value = ratings[team]
            change = value - before_recent.get(team, np.full(2, 1500.0))
            rows.append(
                {
                    "Season": year,
                    "TeamID": team,
                    "elo": value[0],
                    "elo_mov": value[1],
                    "elo_change": change[0],
                    "elo_mov_change": change[1],
                }
            )

    for (year, day), games in legal.groupby(["Season", "DayNum"], sort=True):
        if last_season != year:
            if last_season is not None:
                finish(last_season)
            gap = int(year - last_season) if last_season is not None else 1
            ratings = {team: 1500 + 0.65**gap * (value - 1500) for team, value in ratings.items()}
            before_recent = {team: value.copy() for team, value in ratings.items()}
            season_teams = set()
            last_season = int(year)
        updates: dict[int, np.ndarray] = {}
        ordered = games.sort_values(["WTeamID", "LTeamID"])
        values = ordered[["WTeamID", "LTeamID", "WScore", "LScore"]].to_numpy(dtype=float)
        for row, location in zip(values, ordered.WLoc.astype(str), strict=True):
            a, b = int(row[0]), int(row[1])
            season_teams.update([a, b])
            ra, rb = ratings.get(a, np.full(2, 1500.0)), ratings.get(b, np.full(2, 1500.0))
            home = {"H": 60, "A": -60, "N": 0}[location]
            probability = 1 / (1 + 10 ** (-(ra - rb + home) / 400))
            multiplier = np.array([1.0, min(np.log1p(row[2] - row[3]), 3.0)])
            change = 20 * multiplier * (1 - probability)
            updates[a] = updates.get(a, np.zeros(2)) + change
            updates[b] = updates.get(b, np.zeros(2)) - change
        for team, update in updates.items():
            ratings[team] = ratings.get(team, np.full(2, 1500.0)) + update
        if day <= cutoff - 30:
            before_recent = {team: value.copy() for team, value in ratings.items()}
    if last_season is not None:
        finish(last_season)
    return pd.DataFrame(rows)


def elo_snapshot(compact: pd.DataFrame, season: int, cutoff: int) -> pd.DataFrame:
    history = elo_history(compact.loc[compact.Season <= season], cutoff)
    return history.loc[history.Season == season].drop(columns="Season").reset_index(drop=True)


def advanced_snapshot(
    tables: dict[str, pd.DataFrame],
    gender: str,
    season: int,
    cutoff: int = 132,
    alpha: float = 20,
    rankings: pd.DataFrame | None = None,
    elo: pd.DataFrame | None = None,
) -> pd.DataFrame:
    compact, detailed, seeds = (
        tables[name]
        for name in [
            "RegularSeasonCompactResults",
            "RegularSeasonDetailedResults",
            "NCAATourneySeeds",
        ]
    )
    result = snapshot(compact, detailed, seeds, gender, season, cutoff, alpha, 30)
    detail = detailed.loc[(detailed.Season == season) & (detailed.DayNum <= cutoff)]
    if detail.empty:
        raise ValueError(f"Detailed games required for the rebuilt store: {gender} {season}")
    long = possession_games(detail)
    for addition in [
        efficiency_ratings(long, alpha, cutoff),
        adjusted_factors(long, alpha),
        shooting_posteriors(long),
        elo_snapshot(compact, season, cutoff) if elo is None else elo,
    ]:
        result = result.merge(addition, on="TeamID", how="left", validate="one_to_one")
    pace = long.groupby("TeamID").agg(
        tempo=("tempo", "mean"),
        tempo_sd=("tempo", "std"),
        possession_gap=("possession_gap", "mean"),
        clean_coverage=("clean", "mean"),
    )
    totals = long.groupby("TeamID").sum(numeric_only=True)
    pace["three_dependence"] = 3 * totals.FGM3 / totals.points.replace(0, np.nan)
    result = result.merge(pace.reset_index(), on="TeamID", validate="one_to_one")
    games = team_games(compact.loc[(compact.Season == season) & (compact.DayNum <= cutoff)])
    games["margin"] = games.points - games.allowed
    games = games.merge(
        result[["TeamID", "strength"]].rename(columns={"TeamID": "OpponentID"}),
        on="OpponentID",
        validate="many_to_one",
    )
    threshold = result.strength.quantile(0.75)
    rows = []
    for team, group in games.groupby("TeamID"):
        close = group.loc[group.margin.abs() <= 5]
        strong = group.loc[group.strength >= threshold]
        rows.append(
            {
                "TeamID": team,
                "schedule_sd": group.strength.std(),
                "strong_opponent_margin": strong.margin.sum() / (len(strong) + 5),
                "close_win_posterior": (close.win.sum() + 2.5) / (len(close) + 5),
                "rest_days": cutoff - group.DayNum.max(),
            }
        )
    result = result.merge(pd.DataFrame(rows), on="TeamID", validate="one_to_one")
    prior_seeds = seeds.loc[seeds.Season.between(season - 5, season - 1)]
    prior_results = tables["NCAATourneyCompactResults"]
    prior_results = prior_results.loc[prior_results.Season.between(season - 5, season - 1)]
    result["prior_wins"] = result.TeamID.map(prior_results.groupby("WTeamID").size()).fillna(0)
    result["prior_appearances"] = result.TeamID.map(prior_seeds.groupby("TeamID").size()).fillna(0)
    # 8.5 is the fixed midpoint of tournament seeds; shrink sparse prior appearances.
    prior = prior_seeds.groupby("TeamID").seed.agg(["sum", "count"])
    result["prior_seed"] = result.TeamID.map(
        (prior["sum"] + 2 * 8.5) / (prior["count"] + 2)
    ).fillna(8.5)
    if rankings is not None:
        result = result.merge(
            ranking_snapshot(rankings, season, cutoff),
            on="TeamID",
            how="left",
            validate="one_to_one",
        )
    else:
        for column in LEVEL_FEATURES + TREND_FEATURES:
            result[column] = np.nan
    for column in ENCODING_FEATURES:
        result[column] = np.nan
    result = result.merge(
        context_snapshot(compact, detailed, result, season, cutoff),
        on="TeamID",
        how="left",
        validate="one_to_one",
    )
    result = result.merge(
        candidate_snapshot(long, result, cutoff), on="TeamID", how="left", validate="one_to_one"
    )
    result = result.merge(
        coach_snapshot(
            tables.get("TeamCoaches"),
            compact,
            tables["NCAATourneyCompactResults"],
            result,
            season,
            cutoff,
        ),
        on="TeamID",
        how="left",
        validate="one_to_one",
    )
    result["snapshot_day"] = cutoff
    return result


def pair_features(teams: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    """Build feature-only matchups for arbitrary official IDs; labels never enter."""
    keys = ["Gender", "Season", "Team1ID", "Team2ID"]
    if pairs.duplicated(keys).any() or not (pairs.Team1ID < pairs.Team2ID).all():
        raise ValueError("Matchups require unique ordered team IDs")
    result = pairs[keys].reset_index(drop=True).copy()
    joined = result.copy()
    for side, key in [("a", "Team1ID"), ("b", "Team2ID")]:
        renamed = teams.rename(
            columns={"TeamID": key, **{c: f"{side}_{c}" for c in teams if c not in KEYS}}
        )
        joined = joined.merge(
            renamed, on=["Gender", "Season", key], how="left", validate="many_to_one"
        )
    if joined[["a_games", "b_games"]].isna().any().any():
        raise ValueError("Missing snapshot for a requested team")
    base = [
        column.removeprefix("diff_")
        for column in feature_blocks()["full"]
        if column.startswith("diff_")
    ]
    differences = {
        "diff_" + feature: joined["a_" + feature] - joined["b_" + feature]
        for feature in [*base, *[c for family in FAMILIES.values() for c in family]]
    }
    result = pd.concat([result, pd.DataFrame(differences)], axis=1)
    for rate in ["efg", "tov", "orb", "ftr", "three_rate"]:
        result["matchup_" + rate] = (
            joined["a_" + rate] * joined["b_opp_" + rate]
            - joined["b_" + rate] * joined["a_opp_" + rate]
        )
    result["matchup_strength_volatility"] = result.diff_strength / np.sqrt(
        joined.a_margin_sd**2 + joined.b_margin_sd**2 + 1
    )
    result["pace_strength"] = result.diff_strength * (joined.a_tempo + joined.b_tempo) / 140
    uncertainty = joined.a_three_uncertainty**2 + joined.b_three_uncertainty**2
    result["uncertainty_strength"] = result.diff_strength * np.sqrt(uncertainty)
    result["three_variance_strength"] = result.diff_strength * (
        joined.a_three_dependence + joined.b_three_dependence
    )
    for name, offense, defense in [
        ("shooting_style", "three_posterior", "opp_three_posterior"),
        ("offense_defense", "adj_offense", "adj_defense"),
        ("recent_offense_defense", "recent_offense", "recent_defense"),
    ]:
        result[name] = (
            joined["a_" + offense] * joined["b_" + defense]
            - joined["b_" + offense] * joined["a_" + defense]
        )
    result["ID"] = (
        result.Season.astype(str)
        + "_"
        + result.Team1ID.astype(str)
        + "_"
        + result.Team2ID.astype(str)
    )
    values = result.drop(columns=keys + ["ID"]).to_numpy(dtype=float)
    if np.isinf(values).any():
        raise ValueError("Infinite matchup feature")
    return result


def candidate_blocks(include_rankings: bool = True) -> dict[str, list[str]]:
    """Preregistered one-family additions plus full and drop-one ablations."""
    core = feature_blocks()["strength"]
    families = {
        name: ["diff_" + c for c in columns]
        for name, columns in FAMILIES.items()
        if include_rankings or name not in {"rankings", "rank_trends", "target_rank"}
    }
    families["interactions"] = INTERACTIONS
    full = list(
        dict.fromkeys(feature_blocks()["full"] + [c for cols in families.values() for c in cols])
    )
    blocks = {
        "seed": feature_blocks()["seed"],
        "strength": core,
        "legacy_full": feature_blocks()["full"],
    }
    blocks.update({name: core + cols for name, cols in families.items()})
    blocks["full"] = full
    blocks.update(
        {
            "without_" + name: [c for c in full if c not in columns]
            for name, columns in families.items()
        }
    )
    if include_rankings:
        ranked = {
            "diff_" + c
            for family in ("rankings", "rank_trends", "target_rank")
            for c in FAMILIES[family]
        }
        blocks["without_massey"] = [c for c in full if c not in ranked]
    return blocks
