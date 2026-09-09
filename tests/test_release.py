"""Catch plausible stale-release failures using real evidence and adversarial predictions."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from march_mania.publication import release
from march_mania.research_report import probability_metrics

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def prediction_pair():
    # Unequal season sizes ensure a macro/game-weighted mix-up cannot pass.
    rows = pd.DataFrame(
        {
            "Gender": ["M"] * 4,
            "Season": [2022, 2023, 2023, 2023],
            "DayNum": [134, 134, 135, 136],
            "ID": ["a", "b", "c", "d"],
            "y": [1, 0, 1, 0],
            "p": [0.1, 0.2, 0.9, 0.1],
            "model": ["logistic"] * 4,
        }
    )
    metrics = probability_metrics(rows.y.to_numpy(), rows.p.to_numpy())
    scores = pd.DataFrame(
        [
            {
                "Gender": "M",
                "model": "logistic",
                "games": 4,
                "macro_season_brier": float(
                    np.square(rows.p - rows.y).groupby(rows.Season).mean().mean()
                ),
                **metrics,
            }
        ]
    )
    return rows, scores


def test_release_recomputes_actual_published_evidence():
    report, metrics = release.audit(ROOT)
    assert report == json.loads((ROOT / release.REPORT).read_text())
    assert report["feature_search"]["explored_definitions"] == 3946
    assert report["feature_search"]["full_bank_unique_retained_across_fits"] == 251
    assert report["cloud"]["archives_verified"] == 6
    assert len(report["notebooks"]) == 6
    assert metrics.to_csv(index=False, lineterminator="\n") == (ROOT / release.METRICS).read_text()


@pytest.mark.parametrize(
    "change", ["brier", "macro_season_brier", "duplicate", "population", "target", "nan", "future"]
)
def test_metrics_reject_wrong_scores_and_unmatched_games(prediction_pair, change):
    rows, scores = prediction_pair
    if change == "brier":
        scores.loc[0, "brier"] += 0.01
    elif change == "macro_season_brier":
        scores.loc[0, "macro_season_brier"] = scores.loc[0, "brier"]
    elif change == "duplicate":
        rows = pd.concat([rows, rows.iloc[:1]], ignore_index=True)
    elif change in {"population", "target"}:
        second = rows.assign(model="hist")
        if change == "population":
            second = second.iloc[1:]
        else:
            second.loc[0, "y"] = 0
        rows = pd.concat([rows, second], ignore_index=True)
        scores = pd.concat([scores, scores.assign(model="hist")], ignore_index=True)
    elif change == "nan":
        rows.loc[0, "p"] = np.nan
    else:
        rows.loc[0, "Season"] = 2026
    with pytest.raises(ValueError):
        release.audit_metrics(rows, scores, ["Gender", "model"], [2022, 2023])


def test_unequal_season_sizes_keep_both_brier_definitions(prediction_pair):
    rows, scores = prediction_pair
    result = release.audit_metrics(rows, scores, ["Gender", "model"], [2022, 2023])[0]
    assert result["brier"] == pytest.approx(0.2175)
    assert result["mean_season_brier"] == pytest.approx(0.415)


@pytest.mark.parametrize("change", ["source", "report", "notebook", "cloud", "figure"])
def test_release_rejects_stale_or_corrupted_published_artifacts(tmp_path, change):
    for name in ("src", "configs", "reports", "notebooks"):
        shutil.copytree(ROOT / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy2(ROOT / name, tmp_path / name)
    if change == "source":
        path = tmp_path / "src/march_mania/features.py"
        path.write_text(path.read_text() + "\n# Changed computation source\n")
    elif change == "report":
        path = tmp_path / "reports/model_comparison/predictions.csv"
        frame = pd.read_csv(path)
        frame.loc[0, "p"] += 0.01
        frame.to_csv(path, index=False)
    elif change == "notebook":
        path = tmp_path / "notebooks" / release.NOTEBOOKS[0]
        notebook = json.loads(path.read_text())
        notebook["cells"][0]["source"] = "Changed published analysis"
        path.write_text(json.dumps(notebook))
    elif change == "cloud":
        path = tmp_path / "reports/repository_release/cloud_verification.json"
        cloud = json.loads(path.read_text())
        cloud["objects"][0]["ContentLength"] += 1
        path.write_text(json.dumps(cloud))
    else:
        (tmp_path / "reports/figures/feature_capacity.png").write_bytes(b"different figure")
    with pytest.raises(ValueError):
        release.audit(tmp_path)
