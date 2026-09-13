"""Small synthetic official-schema fixtures; never reported as competition evidence."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def write_fixture(raw: Path) -> Path:
    raw.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(19)
    for gender, base in [("M", 1000), ("W", 3000)]:
        regular, tournament, seeds = [], [], []
        for season in range(2013, 2018):
            teams = list(range(base + 1, base + 9))
            for i, team in enumerate(teams):
                seeds.append({"Season": season, "TeamID": team, "Seed": f"W{i + 1:02d}"})
            day = 10
            for i, a in enumerate(teams):
                for b in teams[i + 1 :]:
                    for _repeat in range(2):
                        winner, loser = (a, b) if rng.uniform() < 0.6 else (b, a)
                        record = {
                            "Season": season,
                            "DayNum": day,
                            "WTeamID": winner,
                            "LTeamID": loser,
                            "WScore": 78,
                            "LScore": 61,
                            "WLoc": ["H", "A", "N"][day % 3],
                            "NumOT": 0,
                        }
                        for side in ("W", "L"):
                            record.update(
                                {
                                    side + "FGM": 28 if side == "W" else 22,
                                    side + "FGA": int(rng.integers(55, 70)),
                                    side + "FGM3": 8 if side == "W" else 5,
                                    side + "FGA3": int(rng.integers(15, 25)),
                                    side + "FTM": 14 if side == "W" else 12,
                                    side + "FTA": int(rng.integers(16, 24)),
                                    side + "OR": int(rng.integers(6, 15)),
                                    side + "DR": int(rng.integers(18, 29)),
                                    side + "TO": int(rng.integers(7, 17)),
                                    side + "Ast": 14 if side == "W" else 10,
                                    side + "Stl": 7 if side == "W" else 5,
                                    side + "Blk": 4 if side == "W" else 2,
                                    side + "PF": 16 if side == "W" else 20,
                                }
                            )
                        regular.append(record)
                        day += 1
                    winner, loser = (a, b) if rng.uniform() < 0.5 else (b, a)
                    tournament.append(
                        {
                            "Season": season,
                            "DayNum": 136 + i,
                            "WTeamID": winner,
                            "LTeamID": loser,
                            "WScore": 75,
                            "LScore": 65,
                            "WLoc": "N",
                            "NumOT": 0,
                        }
                    )
        compact = ["Season", "DayNum", "WTeamID", "LTeamID", "WScore", "LScore", "WLoc", "NumOT"]
        pd.DataFrame(regular).to_csv(raw / f"{gender}RegularSeasonDetailedResults.csv", index=False)
        pd.DataFrame(regular)[compact].to_csv(
            raw / f"{gender}RegularSeasonCompactResults.csv", index=False
        )
        pd.DataFrame(tournament).to_csv(raw / f"{gender}NCAATourneyCompactResults.csv", index=False)
        pd.DataFrame(seeds).to_csv(raw / f"{gender}NCAATourneySeeds.csv", index=False)
    return raw


@pytest.fixture
def raw(tmp_path: Path) -> Path:
    return write_fixture(tmp_path / "raw")


@pytest.fixture
def config() -> dict:
    return {
        "protocol": "retrospective-feature-research",
        "first_training_season": 2013,
        "validation_seasons": [2016, 2017],
        "feature_cutoff_day": 132,
        "minimum_prior_seasons": 3,
        "include_play_in": True,
        "ridge_alpha": 20.0,
        "recent_half_life_days": 30.0,
        "seed": 2026,
        "threads": 1,
        "heartbeat_seconds": 0.1,
    }
