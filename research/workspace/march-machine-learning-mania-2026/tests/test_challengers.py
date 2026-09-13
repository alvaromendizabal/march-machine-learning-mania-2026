"""Final challenger temporal boundaries, seed exclusion and immutable women's rows."""

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from march_mania.publication import challengers, production, retraining
from march_mania.runtime import EventLog, TaskStore

ROOT = Path(__file__).resolve().parents[1]


def training_frame():
    rng = np.random.default_rng(42)
    rows = []
    for season in challengers.YEARS:
        for gender, team in [("M", 1101), ("W", 3101)]:
            for i in range(6):
                signal = rng.normal()
                rows.append(
                    {
                        "ID": f"{season}_{team}_{team + i + 1}",
                        "Gender": gender,
                        "Season": season,
                        "DayNum": 134,
                        "y": int(signal > 0),
                        "signal": signal,
                        "diff_seed": rng.normal(),
                        "interact_seed_signal": rng.normal(),
                    }
                )
    return pd.DataFrame(rows)


def test_final_fits_ignore_future_labels_and_features_and_remove_seed(monkeypatch):
    config, variants = challengers.configuration(ROOT)
    columns = ["signal", "diff_seed", "interact_seed_signal"]
    monkeypatch.setattr(retraining, "columns_for", lambda _: columns)
    frame = training_frame()
    future = frame.loc[frame.Season.eq(2025)].copy()
    future["Season"] = 2026
    future["ID"] = future.ID.str.replace("2025", "2026")
    future["y"] = 1 - future.y
    future[columns] = np.inf
    clean, audit = challengers.fit_final(frame, variants[0], "seed_free", config)
    dirty, _ = challengers.fit_final(pd.concat([frame, future]), variants[0], "seed_free", config)
    assert clean["model"].get_booster().save_raw() == dirty["model"].get_booster().save_raw()
    assert clean["features"] == dirty["features"] == ["signal"]
    assert audit["training_max_season"] == 2025
    assert audit["training_games"] == len(frame)
    p = production.forecast(clean["model"], frame, clean["features"], 2)
    reverse = production.forecast(
        clean["model"], frame.assign(signal=-frame.signal), clean["features"], 2
    )
    np.testing.assert_allclose(p + reverse, 1, rtol=0, atol=1e-12)


@pytest.mark.parametrize("invalid", ["missing_season", "duplicate", "bad_day", "bad_label"])
def test_final_training_rejects_invalid_physical_games(invalid):
    config, variants = challengers.configuration(ROOT)
    frame = training_frame()
    if invalid == "missing_season":
        frame = frame.loc[frame.Season.ne(2013)]
    elif invalid == "duplicate":
        frame = pd.concat([frame, frame.iloc[:1]])
    elif invalid == "bad_day":
        frame.loc[0, "DayNum"] = 132
    else:
        frame.loc[0, "y"] = 2
    with pytest.raises(ValueError):
        challengers.fit_final(frame, variants[0], "seeded", config)


def example_export():
    baseline = b"ID,Pred\n2026_1101_1102,0.5\n2026_1101_1103,0.5\n2026_3101_3102,0.5000000000000\n"
    forecasts = pd.DataFrame(
        {
            "ID": ["2026_1101_1102", "2026_1101_1103"],
            **{
                name: [0.6 + i * 0.05, 0.25 + i * 0.02]
                for i, name in enumerate(challengers.VARIANTS)
            },
        }
    )
    return baseline, forecasts


def test_exports_preserve_women_bytes_and_resume_without_work(tmp_path):
    config, _ = challengers.configuration(ROOT)
    baseline, forecasts = example_export()
    store = TaskStore(tmp_path, "example", EventLog(tmp_path / "events.jsonl"))
    target = store.task(
        "exports", lambda folder: challengers.export(folder, baseline, forecasts, config)
    )
    with zipfile.ZipFile(target / "prediction_challengers.zip") as zipped:
        csvs = [n for n in zipped.namelist() if n.startswith("m_")]
        assert len(csvs) == 6
        assert len({zipped.read(n) for n in csvs}) == 6
        for name in csvs:
            content = zipped.read(name)
            assert content.splitlines(keepends=True)[-1] == baseline.splitlines(keepends=True)[-1]
            actual = pd.read_csv(io.BytesIO(content))
            assert actual.Pred.between(0, 1).all()
            assert actual.ID.tolist() == pd.read_csv(io.BytesIO(baseline)).ID.tolist()
    assert (
        store.task("exports", lambda _: pytest.fail("Completed export should be reused")) == target
    )
    checkpoint = json.loads((target / "checkpoint.json").read_text())
    assert len(checkpoint["outputs"]) == 9


@pytest.mark.parametrize("invalid", ["reordered", "nonfinite", "out_of_range"])
def test_exports_reject_misalignment_and_invalid_probabilities(tmp_path, invalid):
    config, _ = challengers.configuration(ROOT)
    baseline, forecasts = example_export()
    if invalid == "reordered":
        forecasts = forecasts.iloc[::-1]
    else:
        forecasts.loc[0, challengers.VARIANTS[0]] = np.nan if invalid == "nonfinite" else 1.1
    with pytest.raises(ValueError):
        challengers.export(tmp_path, baseline, forecasts, config)
