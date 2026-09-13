from __future__ import annotations

import json

import pytest

from march_mania.notebook_support import review_source
from march_mania.runtime import digest


def test_old_local_schema_uses_current_recorded_evidence(tmp_path):
    local = tmp_path / "outputs/feature_store"
    local.mkdir(parents=True)
    (local / "summary.json").write_text(json.dumps({"status": "completed", "feature_count": 104}))
    reports = tmp_path / "reports/feature_store"
    reports.mkdir(parents=True)
    (reports / "metric.csv").write_text("brier\n0.2\n")
    (reports / "run.json").write_text(
        json.dumps(
            {
                "summary": {"feature_count": 124},
                "sha256": {"metric.csv": digest(reports / "metric.csv")},
            }
        )
    )
    result = review_source(tmp_path, "feature_store", 124)
    assert result[0] == reports and result[1]["feature_count"] == 124
    assert review_source(tmp_path, "feature_store", 125)[0] is None
    (reports / "metric.csv").write_text("brier\n0.1\n")
    with pytest.raises(ValueError, match="checksum"):
        review_source(tmp_path, "feature_store", 124)


def test_unsafe_completed_pointer_rejected(tmp_path):
    local = tmp_path / "outputs/feature_store"
    local.mkdir(parents=True)
    (local / "latest.json").write_text(json.dumps({"directory": "../x", "fingerprint": "../x"}))
    with pytest.raises(ValueError, match="pointer"):
        review_source(tmp_path, "feature_store")
