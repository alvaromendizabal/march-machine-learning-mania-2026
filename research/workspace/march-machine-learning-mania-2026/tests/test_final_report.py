"""Observed score joins must preserve previous evidence and complete file identity."""

import json
import runpy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from march_mania.publication import scoreboard

ROOT = Path(__file__).resolve().parents[1]
API = runpy.run_path(str(ROOT / "scripts/final_report.py"))


def inputs():
    old = scoreboard.scores(ROOT)
    observed = pd.read_csv(ROOT / "reports/final_results/latest_scores.csv")
    manifests = []
    for name, batch in zip(
        ["prediction_challengers", "women_challengers"], API["BATCHES"][2:], strict=True
    ):
        frame = pd.read_csv(ROOT / "reports" / name / "submission_manifest.csv")
        manifests.append(frame[["filename", "rows", "bytes", "sha256"]].assign(batch=batch))
    provenance = json.loads((ROOT / "reports/final_results/provenance.json").read_text())
    return old, observed, pd.concat(manifests, ignore_index=True), provenance


def test_final_scores_preserve_all_old_observations_and_file_hashes():
    old, observed, manifests, provenance = inputs()
    actual = API["reconcile"](old, observed, manifests, provenance)
    assert len(actual) == actual.filename.nunique() == actual.sha256.nunique() == 70
    assert actual.iloc[0].filename == API["WINNER"]
    assert actual.iloc[0].private_brier == 0.1222672
    pd.testing.assert_frame_equal(
        old.sort_values("filename").reset_index(drop=True),
        actual.loc[actual.filename.isin(old.filename)]
        .sort_values("filename")
        .reset_index(drop=True),
    )
    history = API["progression"](actual)
    assert history.total_files.tolist() == [50, 58, 64, 70]
    np.testing.assert_allclose(
        history.best_so_far_brier, [0.1229419, 0.1225463, 0.1223389, 0.1222672], atol=1e-12
    )


@pytest.mark.parametrize(
    "bad", ["previous", "unknown", "duplicate", "missing", "nonfinite", "range", "disagreement"]
)
def test_unverified_score_observations_are_rejected(bad):
    old, observed, manifests, provenance = inputs()
    if bad == "previous":
        observed.loc[19, ["private_brier", "public_brier"]] = 0.12
    elif bad == "unknown":
        observed.loc[0, "filename"] = "unknown.csv"
    elif bad == "duplicate":
        observed.loc[0, "filename"] = observed.loc[1, "filename"]
    elif bad == "missing":
        observed = observed.iloc[1:]
    elif bad == "nonfinite":
        observed.loc[0, "private_brier"] = np.nan
    elif bad == "range":
        observed.loc[0, ["private_brier", "public_brier"]] = -0.1
    else:
        observed.loc[0, "public_brier"] = 0.2
    with pytest.raises(ValueError):
        API["reconcile"](old, observed, manifests, provenance)
