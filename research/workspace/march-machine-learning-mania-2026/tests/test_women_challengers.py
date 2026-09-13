"""Women's temporal selection, inference boundaries and immutable men's CSV rows."""

import io
import runpy
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from march_mania import modeling
from march_mania.publication import production
from march_mania.runtime import EventLog, TaskStore

ROOT = Path(__file__).resolve().parents[1]
API = runpy.run_path(str(ROOT / "scripts/women_challengers.py"))


def training_frame():
    rng = np.random.default_rng(42)
    rows = []
    for season in API["FINAL_YEARS"]:
        for i in range(12):
            signal = rng.normal()
            rows.append(
                {
                    "Gender": "W",
                    "Season": season,
                    "DayNum": 134,
                    "ID": f"{season}_3101_{3102 + i}",
                    "y": int(signal > 0),
                    "signal": signal,
                    "diff_seed": rng.normal(),
                }
            )
    return pd.DataFrame(rows)


def test_women_fits_exclude_future_labels_and_features(monkeypatch):
    config = API["configuration"](ROOT)
    spec = config["variants"][2]
    monkeypatch.setattr(modeling, "columns_for", lambda _: ["signal", "diff_seed"])
    frame = training_frame()
    future = frame.loc[frame.Season.eq(2025)].copy().assign(Season=2026, signal=np.inf)
    future["ID"] = future.ID.str.replace("2025", "2026")
    future["y"] = 1 - future.y
    clean, p, audit = API["fit_fold"](frame, spec, 2021, config)
    dirty, p2, _ = API["fit_fold"](pd.concat([frame, future]), spec, 2021, config)
    np.testing.assert_array_equal(clean["model"].model[-1].coef_, dirty["model"].model[-1].coef_)
    pd.testing.assert_frame_equal(p, p2)
    assert audit["training_max_season"] == 2019
    component = {
        "population": "W",
        "candidate": {
            "name": spec["name"],
            "family": "logistic",
            "block": spec["block"],
            "parameter": spec["C"],
        },
    }
    final, final_audit = production.fit_component(
        pd.concat([frame, future]), component, "seed_free", config
    )
    assert final["features"] == ["signal"]
    assert final_audit["training_max_season"] == 2025
    values = production.forecast(final["model"], frame, final["features"], 2)
    reverse = production.forecast(
        final["model"], frame.assign(signal=-frame.signal), final["features"], 2
    )
    np.testing.assert_allclose(values + reverse, 1, rtol=0, atol=1e-12)
    with pytest.raises(ValueError, match="future validation"):
        API["fit_fold"](frame, spec, 2026, config)


def historical():
    config = API["configuration"](ROOT)
    rows = []
    for i, spec in enumerate(config["variants"]):
        for season in API["YEARS"]:
            for j, y in enumerate([0, 1]):
                rows.append(
                    {
                        "Gender": "W",
                        "Season": season,
                        "DayNum": 134,
                        "ID": f"{season}_3101_{3102 + j}",
                        "y": y,
                        "variant": spec["name"],
                        "p": 0.18 + i * 0.03 if y == 0 else 0.7 - i * 0.02,
                    }
                )
    return pd.DataFrame(rows)


def test_later_outcomes_cannot_change_forward_choices():
    config = API["configuration"](ROOT)
    raw = historical()
    expected = API["evaluate"](raw, config)
    raw.loc[raw.Season.eq(2021), "y"] = 1 - raw.loc[raw.Season.eq(2021), "y"]
    actual = API["evaluate"](raw, config)
    pd.testing.assert_frame_equal(actual["selection.csv"], expected["selection.csv"])
    assert actual["selection.csv"].history_last_season.lt(actual["selection.csv"].Season).all()
    assert len(actual["finalists.csv"]) == 6
    assert config["reference"] not in set(actual["finalists.csv"].candidate_id)


@pytest.mark.parametrize("invalid", ["future", "duplicate", "labels", "nonfinite", "missing"])
def test_comparison_rejects_invalid_games(invalid):
    config = API["configuration"](ROOT)
    raw = historical()
    if invalid == "future":
        raw.loc[0, "Season"] = 2026
    elif invalid == "duplicate":
        raw = pd.concat([raw, raw.iloc[:1]])
    elif invalid == "labels":
        raw.loc[0, "y"] = 1 - raw.loc[0, "y"]
    elif invalid == "nonfinite":
        raw.loc[0, "p"] = np.nan
    else:
        raw = raw.iloc[1:]
    with pytest.raises(ValueError):
        API["evaluate"](raw, config)


def export_example():
    baseline = (
        b"ID,Pred\n2026_1101_1102,0.3000000000\n2026_1101_1103,0.875000\n"
        b"2026_3101_3102,0.5\n2026_3101_3103,0.5\n"
    )
    forecasts = pd.DataFrame(
        {
            "ID": ["2026_3101_3102", "2026_3101_3103"],
            "conference_c100": [0.65, 0.8],
            "conference_c300": [0.7, 0.78],
        }
    )
    rows = [
        {"candidate_id": f"{variant}_t{round(t * 100):03d}", "variant": variant, "temperature": t}
        for variant in ["conference_c100", "conference_c300"]
        for t in [0.9, 1, 1.1]
    ]
    finalists = pd.DataFrame(rows).assign(priority=range(1, 7))
    return baseline, forecasts, finalists


def test_women_export_preserves_men_and_recovers_corrupt_checkpoint(tmp_path):
    baseline, forecasts, finalists = export_example()
    store = TaskStore(tmp_path, "women", EventLog(tmp_path / "events.jsonl"))
    calls = []

    def work(target):
        calls.append(1)
        return API["export"](target, baseline, forecasts, finalists)

    target = store.task("exports", work)
    with zipfile.ZipFile(target / "women_challengers.zip") as zipped:
        names = [n for n in zipped.namelist() if n.startswith("m_")]
        assert len(names) == 6
        assert len({zipped.read(n) for n in names}) == 6
        for name in names:
            data = zipped.read(name)
            assert data.splitlines(keepends=True)[:3] == baseline.splitlines(keepends=True)[:3]
            observed = pd.read_csv(io.BytesIO(data))
            assert observed.Pred.between(0, 1).all()
            assert observed.ID.tolist() == pd.read_csv(io.BytesIO(baseline)).ID.tolist()
    store.task("exports", work)
    assert len(calls) == 1
    (target / names[0]).write_text("corrupt")
    store.task("exports", work)
    assert len(calls) == 2


@pytest.mark.parametrize("invalid", ["reordered", "nan", "probability"])
def test_women_export_rejects_invalid_probabilities(tmp_path, invalid):
    baseline, forecasts, finalists = export_example()
    if invalid == "reordered":
        forecasts = forecasts.iloc[::-1]
    else:
        forecasts.loc[0, "conference_c100"] = np.nan if invalid == "nan" else 1.2
    with pytest.raises(ValueError):
        API["export"](tmp_path, baseline, forecasts, finalists)
