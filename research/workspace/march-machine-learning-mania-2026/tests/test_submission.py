from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from march_mania.publication.submission import release_submission, validate_submission
from march_mania.runtime import digest


@pytest.fixture
def sample():
    # Synthetic contract fixture, not a competition prediction or performance result.
    return pd.DataFrame({"ID": ["2026_1101_1102", "2026_3101_3102"], "Pred": [0.25, 0.75]})


@pytest.mark.parametrize(
    "values", [[np.nan, 0.5], [np.inf, 0.5], [-0.1, 0.2], [0.5, 1.1], [True, False], ["0.1", "0.2"]]
)
def test_invalid_probabilities_rejected(sample, values):
    predictions = sample.assign(Pred=values)
    with pytest.raises(ValueError):
        validate_submission(predictions, sample)


@pytest.mark.parametrize("kind", ["missing", "duplicate", "reversed", "season", "order", "columns"])
def test_invalid_matchups_rejected(sample, kind):
    predictions = sample.copy()
    if kind == "missing":
        predictions = predictions.iloc[:1]
    elif kind == "duplicate":
        predictions.loc[1, "ID"] = predictions.loc[0, "ID"]
    elif kind == "reversed":
        predictions.loc[0, "ID"] = "2026_1102_1101"
    elif kind == "season":
        predictions.loc[0, "ID"] = "2025_1101_1102"
    elif kind == "order":
        predictions = predictions.iloc[::-1]
    else:
        predictions = predictions[["Pred", "ID"]]
    with pytest.raises(ValueError):
        validate_submission(predictions, sample)


def test_release_preserves_exact_bytes_and_resumes_after_corruption(tmp_path, sample):
    source, template = tmp_path / "predictions.csv", tmp_path / "sample.csv"
    sample.to_csv(source, index=False)
    sample.assign(Pred=0.5).to_csv(template, index=False)
    run_root = tmp_path / "release"
    destination = release_submission(source, template, run_root, expected_sha256=digest(source))
    assert (destination / "submission.csv").read_bytes() == source.read_bytes()
    audit = json.loads((destination / "audit.json").read_text())
    assert audit["rows"] == 2 and audit["kaggle_submission_sent"] is False
    first_mtime = (destination / "submission.csv").stat().st_mtime_ns
    assert release_submission(source, template, run_root) == destination
    assert (destination / "submission.csv").stat().st_mtime_ns == first_mtime
    (destination / "submission.csv").write_text("corrupt")
    release_submission(source, template, run_root)
    assert (destination / "submission.csv").read_bytes() == source.read_bytes()
    with pytest.raises(ValueError, match="checksum"):
        release_submission(source, template, run_root, expected_sha256="0" * 64)


def test_exact_zero_and_one_are_legal_and_reported(sample):
    result = validate_submission(sample.assign(Pred=[0.0, 1.0]), sample)
    assert result["exact_zero_or_one"] == 2


def test_historical_evidence_allows_only_verified_line_ending_conversion(tmp_path):
    import hashlib

    from march_mania.publication.submission import verify_text_evidence

    path = tmp_path / "metric.csv"
    original = b"brier\r\n0.2\r\n"
    expected = hashlib.sha256(original).hexdigest()
    path.write_bytes(original)
    assert verify_text_evidence(path, expected) == "exact recorded bytes"
    path.write_bytes(original.replace(b"\r\n", b"\n"))
    assert "Git-normalized" in verify_text_evidence(path, expected)
    path.write_bytes(b"brier\n0.1\n")
    with pytest.raises(ValueError, match="checksum"):
        verify_text_evidence(path, expected)
