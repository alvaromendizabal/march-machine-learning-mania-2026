"""Verify the integrity and metrics of the real published final-prediction run."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from march_mania.publication import inference
from march_mania.publication.artifacts import safe_path
from march_mania.runtime import digest


def test_recorded_final_evidence_matches_predictions() -> None:
    """Audit the actual published run, not a fabricated example or cached notebook text."""
    root = Path(__file__).resolve().parents[1] / "reports/final_predictions"
    evidence = json.loads((root / "evidence.json").read_text())
    for name, expected in evidence["sha256"].items():
        assert digest(safe_path(root, name)) == expected
    summary = json.loads((root / "summary.json").read_text())
    recovery = json.loads((root / "resume.json").read_text())
    audits = json.loads((root / "fit_audits.json").read_text())
    assert summary["status"] == "completed" and recovery["status"] == "passed"
    assert summary["fingerprint"] == recovery["fingerprint"]
    assert summary["rows"] == 132133 and summary["final_training_max_season"] == 2025
    assert not summary["future_labels_used"] and not summary["kaggle_submission_sent"]
    assert recovery["restored_tasks"] == recovery["reused_tasks"] == 53
    assert recovery["identical_submission"] and recovery["repeated_fits"] == 0
    assert len(audits) == 4 and all(a["training_max_season"] == 2025 for a in audits)
    predictions = pd.read_csv(root / "benchmark_predictions.csv")
    inference.validate_games(predictions.loc[predictions.route.eq("seeded")], 2025)
    for row in pd.read_csv(root / "metrics.csv").itertuples():
        group = predictions.loc[
            (predictions.Gender == row.Gender) & (predictions.route == row.route)
        ]
        assert len(group) == row.games == 268
        assert float(np.square(group.p - group.y).mean()) == pytest.approx(row.brier, abs=1e-14)
