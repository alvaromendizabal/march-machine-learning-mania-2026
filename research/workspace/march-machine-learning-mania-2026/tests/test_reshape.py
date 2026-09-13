import pandas as pd

from march_mania.reshape import (
    canonicalize_compact_results,
    detailed_results_to_team_long,
    parse_submission_tables,
)


def test_compact_is_oriented_by_lower_team_id():
    tables = {
        "MRegularSeasonCompactResults": pd.DataFrame(
            {
                "Season": [2025, 2025],
                "DayNum": [10, 11],
                "WTeamID": [1102, 1101],
                "WScore": [80, 75],
                "LTeamID": [1101, 1103],
                "LScore": [70, 60],
                "WLoc": ["H", "A"],
                "NumOT": [0, 0],
            }
        )
    }
    result = canonicalize_compact_results(tables)
    assert result["Team1ID"].tolist() == [1101, 1101]
    assert result["Team1Win"].tolist() == [0, 1]
    assert result["Team1Margin"].tolist() == [-10, 15]


def test_detailed_creates_two_rows_per_game():
    row = {
        "Season": 2025,
        "DayNum": 10,
        "WTeamID": 1102,
        "WScore": 80,
        "LTeamID": 1101,
        "LScore": 70,
        "WLoc": "H",
        "NumOT": 0,
    }
    for stat, w_value, l_value in [
        ("FGM", 30, 25),
        ("FGA", 60, 58),
        ("FGM3", 8, 7),
        ("FGA3", 20, 18),
        ("FTM", 12, 13),
        ("FTA", 16, 18),
        ("OR", 8, 7),
        ("DR", 25, 23),
        ("Ast", 18, 15),
        ("TO", 10, 12),
        ("Stl", 7, 5),
        ("Blk", 4, 3),
        ("PF", 17, 19),
    ]:
        row[f"W{stat}"] = w_value
        row[f"L{stat}"] = l_value
    tables = {"MRegularSeasonDetailedResults": pd.DataFrame([row])}
    result = detailed_results_to_team_long(tables)
    assert len(result) == 2
    assert set(result["Win"]) == {0, 1}
    assert set(result["TeamID"]) == {1101, 1102}


def test_submission_parser():
    tables = {
        "SampleSubmissionStage2": pd.DataFrame(
            {"ID": ["2026_1101_1102", "2026_3101_3102"], "Pred": [0.5, 0.5]}
        )
    }
    result = parse_submission_tables(tables)
    assert result["Gender"].tolist() == ["M", "W"]
    assert result["Team1ID"].tolist() == [1101, 3101]
