"""Public reports are compact, explicit views of complete immutable research audits."""

import json

import pandas as pd
import pytest

from march_mania.publication.reporting import public_bytes
from march_mania.publication.workflow import evidence, publish_report
from march_mania.runtime import atomic_json, digest


def test_compact_audit_keeps_private_rows_and_verified_public_lineage(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    audit = run / "feature_usage.csv"
    pd.DataFrame(
        {
            "Gender": ["M"] * 4,
            "Season": [2016] * 4,
            "block": ["full", "full", "full", "without_massey"],
            "model": ["logistic"] * 4,
            "feature": ["z", "a", "b", "a"],
            "fitted": [True, True, False, True],
            "status": ["retained", "retained", "constant", "retained"],
        }
    ).to_csv(audit, index=False)
    original = audit.read_bytes()
    atomic_json(run / "summary.json", {"status": "completed", "feature_count": 3})
    atomic_json(run / "manifest.json", {"inputs": {"source": "real source"}})
    atomic_json(
        tmp_path / "reports/feature_store/run.json", {"sha256": {"feature_usage.csv": "old"}}
    )
    publish_report(tmp_path, "feature_store", run, {"sha256": "archive-digest"})
    folder, record = evidence(tmp_path, "feature_store")
    assert audit.read_bytes() == original
    assert pd.read_csv(folder / "feature_usage.csv").feature.tolist() == ["a", "z"]
    scope = record["public_report_scope"]["feature_usage.csv"]
    assert scope["complete_audit_sha256"] == digest(audit)
    assert scope["complete_audit"] == "archive:run/feature_usage.csv"
    published = (folder / "run.json").read_bytes()
    publish_report(tmp_path, "feature_store", run, {"sha256": "archive-digest"})
    assert (folder / "run.json").read_bytes() == published
    assert json.loads(published)["summary"]["feature_count"] == 3


def test_invalid_or_unbounded_public_table_is_rejected(tmp_path):
    table = tmp_path / "audit.csv"
    table.write_text("Gender,Season,feature,fitted\nM,2016,a,True\n")
    with pytest.raises(ValueError, match="schema"):
        public_bytes(table, feature_audit=True)
    table.write_bytes(b"x" * (8 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="8 MiB"):
        public_bytes(table)


def test_duplicate_retained_features_are_not_silently_deduplicated(tmp_path):
    table = tmp_path / "audit.csv"
    table.write_text(
        "Gender,Season,block,model,feature,fitted\n"
        "M,2016,full,logistic,a,True\nM,2016,full,logistic,a,True\n"
    )
    with pytest.raises(ValueError, match="unique"):
        public_bytes(table, feature_audit=True)
