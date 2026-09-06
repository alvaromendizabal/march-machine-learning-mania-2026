from __future__ import annotations

import json

import pandas as pd
import pytest

from march_mania.feature_store import run, validate_config


def settings():
    return {
        "protocol": "retrospective-feature-store",
        "first_season": 2013,
        "last_season": 2017,
        "validation_seasons": [2016, 2017],
        "feature_cutoff_day": 132,
        "minimum_prior_seasons": 3,
        "ridge_alpha": 20.0,
        "seed": 2026,
        "threads": 1,
        "heartbeat_seconds": 0.1,
    }


def test_feature_store_real_workflow_and_resume(raw, tmp_path):
    config = settings()
    output = tmp_path / "features"
    result = run(raw, output, config)
    assert result["status"] == "completed"
    assert result["fold_tasks"] == 160
    assert result["elapsed_seconds"] > 0
    assert result["sources"] == {
        "massey": False,
        "sample_submission": False,
        "player_availability": False,
        "roster_minutes": False,
    }
    models = {str(p): p.stat().st_mtime_ns for p in output.glob("fold_*/model.joblib")}
    resumed = run(raw, output, config)
    assert result["fingerprint"] == resumed["fingerprint"]
    assert models == {str(p): p.stat().st_mtime_ns for p in output.glob("fold_*/model.joblib")}
    forecasts = pd.read_parquet(output / "predictions.parquet")
    assert not forecasts.duplicated(["Gender", "Season", "ID", "block", "model"]).any()
    assert forecasts.groupby(["Gender", "Season", "ID"]).size().eq(40).all()
    events = [json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()]
    assert all("timestamp" in event and "elapsed_seconds" in event for event in events)
    assert sum(event["event"] == "task_reused" for event in events) == 172
    config["ridge_alpha"] = 21
    with pytest.raises(ValueError, match="changed"):
        run(raw, output, config)


def test_optional_rankings_and_sample_submission_are_integrated(raw, tmp_path):
    rows = [
        {
            "Season": season,
            "RankingDayNum": day,
            "SystemName": system,
            "TeamID": team,
            "OrdinalRank": team - 1000,
        }
        for season in range(2013, 2017)
        for day in [100, 130]
        for system in ["A", "B"]
        for team in range(1001, 1009)
    ]
    pd.DataFrame(rows).to_csv(raw / "MMasseyOrdinals.csv", index=False)
    sample = pd.DataFrame({"ID": ["2016_3001_3004", "2016_1002_1005"], "Pred": [0.5, 0.5]})
    sample.to_csv(raw / "SampleSubmissionStage2.csv", index=False)
    config = settings()
    config.update(last_season=2016, validation_seasons=[2016])
    output = tmp_path / "optional"
    result = run(raw, output, config)
    assert result["fold_tasks"] == 84
    assert result["sources"]["massey"] and result["sources"]["sample_submission"]
    features = pd.read_parquet(output / "submission_features.parquet")
    assert features.ID.tolist() == sample.ID.tolist()
    assert features.route.eq("seeded").all()
    predictions = pd.read_parquet(output / "predictions.parquet")
    assert set(predictions.loc[predictions.block == "rankings", "Gender"]) == {"M"}


@pytest.mark.parametrize(
    "field,value",
    [
        ("validation_seasons", [2026]),
        ("first_season", 2016),
        ("feature_cutoff_day", 150),
        ("threads", 0),
    ],
)
def test_feature_store_protocol_guards(field, value):
    config = settings()
    config[field] = value
    with pytest.raises(ValueError):
        validate_config(config)
