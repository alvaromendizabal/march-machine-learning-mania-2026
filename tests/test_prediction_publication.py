"""Regression tests for the real training-Parquet to public-CSV handoff."""

import hashlib

import pandas as pd
import pytest

from march_mania.publication.workflow import materialize_predictions
from march_mania.runtime import digest


@pytest.fixture
def predictions():
    return pd.DataFrame({"ID": ["2016_1101_1102", "2016_1101_1103"], "y": [0, 1], "p": [0.2, 0.7]})


def test_parquet_is_materialized_before_publication(tmp_path, predictions):
    predictions.to_parquet(tmp_path / "predictions.parquet", index=False)
    csv = materialize_predictions(tmp_path)
    pd.testing.assert_frame_equal(pd.read_csv(csv), predictions)
    before = csv.stat().st_mtime_ns
    assert materialize_predictions(tmp_path) == csv
    assert csv.stat().st_mtime_ns == before


def test_conversion_replaces_stale_csv_not_training_data(tmp_path, predictions):
    source = tmp_path / "predictions.parquet"
    predictions.to_parquet(source, index=False)
    before = digest(source)
    (tmp_path / "predictions.csv").write_text("stale historical output")
    csv = materialize_predictions(tmp_path)
    expected = hashlib.sha256(predictions.to_csv(index=False).encode()).hexdigest()
    assert digest(csv) == expected and digest(source) == before


def test_missing_parquet_does_not_promote_old_csv(tmp_path):
    target = tmp_path / "predictions.csv"
    target.write_bytes(b"existing user result")
    with pytest.raises(FileNotFoundError):
        materialize_predictions(tmp_path)
    assert target.read_bytes() == b"existing user result"
