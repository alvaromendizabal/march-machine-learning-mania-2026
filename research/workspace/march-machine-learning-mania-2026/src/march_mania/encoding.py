"""Forward-only NCAA target histories: no row uses its own season's labels."""

from __future__ import annotations

import numpy as np
import pandas as pd

ENCODING_FAMILIES = {
    "target_team": ["te_team_mean", "te_team_uncertainty", "te_team_support"],
    "target_seed": ["te_seed_mean", "te_seed_uncertainty", "te_seed_support"],
    "target_rank": ["te_rank_mean", "te_rank_uncertainty", "te_rank_support"],
}
ENCODING_FEATURES = [c for columns in ENCODING_FAMILIES.values() for c in columns]


def encode_history(
    teams: pd.DataFrame,
    games: pd.DataFrame,
    *,
    prior_games: float = 20,
    half_life_seasons: float = 3,
    window_seasons: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Encode team, seed and fixed rank decile from earlier training seasons only.

    Both team perspectives enter the history once, before model augmentation.
    Thus the prior win probability is exactly 1/2. Decayed Beta pseudo-counts
    give a regularization/uncertainty feature, not a calibrated confidence bound.
    Cold starts receive the fixed prior; missing rank stays missing. Historical
    categories use the seed/rank from their own season, never today's category.
    """
    if prior_games <= 0 or half_life_seasons <= 0 or window_seasons < 1:
        raise ValueError("Encoding smoothing, half life and history window must be positive")
    if teams.Gender.nunique() != 1 or teams.duplicated(["Season", "TeamID"]).any():
        raise ValueError("Encode one gender with unique season/team keys")
    result = teams.drop(columns=ENCODING_FEATURES, errors="ignore").copy()
    categories = result[["Season", "TeamID", "seed", "rank_consensus"]].copy()
    categories["rank"] = np.floor(categories.rank_consensus * 10).clip(0, 9)
    categories = categories.rename(columns={"TeamID": "team"})
    legal = games.loc[games.Season.isin(teams.Season.unique()) & (games.Season != 2020)].copy()
    if (legal.DayNum <= 132).any() or legal.duplicated(
        ["Season", "DayNum", "WTeamID", "LTeamID"]
    ).any():
        raise ValueError("Target history requires unique post-cutoff physical games")
    long = pd.concat(
        [
            pd.DataFrame({"Season": legal.Season, "team": legal[side + "TeamID"], "win": value})
            for side, value in [("W", 1), ("L", 0)]
        ],
        ignore_index=True,
    ).merge(categories, on=["Season", "team"], how="left", validate="many_to_one")
    # Missing seeds indicate that a historical label could not be matched to its snapshot.
    if long.seed.isna().any():
        raise ValueError("Historical NCAA labels require their own season's seeded snapshot")
    for name in ENCODING_FEATURES:
        result[name] = np.nan
    audit = []
    for season in sorted(result.Season.unique()):
        selected = result.Season == season
        history = long.loc[long.Season.between(season - window_seasons, season - 1)].copy()
        history["weight"] = 0.5 ** ((season - 1 - history.Season) / half_life_seasons)
        history["wins"] = history.win * history.weight
        for category, columns in zip(
            ["team", "seed", "rank"], ENCODING_FAMILIES.values(), strict=True
        ):
            counts = history.groupby(category).agg(wins=("wins", "sum"), games=("weight", "sum"))
            values = categories.loc[selected, category]
            support = values.map(counts.games).fillna(0)
            wins = values.map(counts.wins).fillna(0)
            alpha, beta = wins + prior_games / 2, support - wins + prior_games / 2
            mean = alpha / (alpha + beta)
            uncertainty = np.sqrt(alpha * beta / ((alpha + beta) ** 2 * (alpha + beta + 1)))
            for column, series in zip(columns, [mean, uncertainty, np.log1p(support)], strict=True):
                result.loc[selected, column] = series.where(values.notna()).to_numpy()
            audit.append(
                {
                    "Gender": str(result.Gender.iloc[0]),
                    "Season": int(season),
                    "category": category,
                    "history_min_season": int(history.Season.min()) if len(history) else None,
                    "history_max_season": int(history.Season.max()) if len(history) else None,
                    "physical_history_games": len(history) // 2,
                    "known_categories": int(len(counts)),
                    "target_teams": int(selected.sum()),
                    "cold_start_teams": int((support == 0).sum()),
                    "missing_category_teams": int(values.isna().sum()),
                    "prior_games": prior_games,
                    "half_life_seasons": half_life_seasons,
                    "window_seasons": window_seasons,
                }
            )
    return result, pd.DataFrame(audit)
