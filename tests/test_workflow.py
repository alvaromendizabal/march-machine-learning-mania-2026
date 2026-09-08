"""Current-data handoffs, scientific comparison and explicit notebook export controls."""

from __future__ import annotations

import copy
import hashlib
import json
import zipfile
from pathlib import Path

import nbformat
import pandas as pd
import pytest

from march_mania import modeling
from march_mania.publication import workflow
from march_mania.publication.artifacts import restore_archive
from march_mania.runtime import atomic_json, digest


def test_mode_is_explicit(monkeypatch):
    monkeypatch.delenv("MARCH_NOTEBOOK_MODE", raising=False)
    assert workflow.execution_mode() == "review"
    monkeypatch.setenv("MARCH_NOTEBOOK_MODE", "train")
    assert workflow.execution_mode() == "train"
    monkeypatch.setenv("MARCH_NOTEBOOK_MODE", "silent")
    with pytest.raises(ValueError, match="review or train"):
        workflow.execution_mode()


@pytest.fixture
def feature_contract():
    return {
        "source": {"features.py": "a", "pyproject.toml": "b", "uv.lock": "c"},
        "data": {"games.csv": "d"},
        "config": {"cutoff": 132},
        "environment": {"numpy": "2.2.6"},
    }


@pytest.mark.parametrize(
    "part,key",
    [
        ("source", "features.py"),
        ("data", "games.csv"),
        ("config", "cutoff"),
        ("environment", "numpy"),
    ],
)
def test_changed_computation_is_never_reused(feature_contract, part, key):
    changed = copy.deepcopy(feature_contract)
    changed[part][key] = "changed"
    assert not workflow.same_feature_computation(feature_contract, changed)


def test_extra_packaging_only_keeps_original_feature_identity(feature_contract):
    changed = copy.deepcopy(feature_contract)
    changed["source"].update(
        {"uv.lock": "extra-model-package", "pyproject.toml": "new-entry-point"}
    )
    assert workflow.same_feature_computation(feature_contract, changed)
    assert feature_contract["source"]["uv.lock"] == "c"


def test_pointer_cannot_escape_or_claim_incomplete_work(tmp_path):
    base = tmp_path / "outputs/feature_store"
    atomic_json(base / "latest.json", {"directory": "../../elsewhere", "fingerprint": "a" * 64})
    with pytest.raises(ValueError, match="pointer"):
        workflow.current_directory(tmp_path, "feature_store")
    atomic_json(base / "latest.json", {"directory": "a" * 64, "fingerprint": "a" * 64})
    atomic_json(base / ("a" * 64) / "summary.json", {"status": "failed", "fingerprint": "a" * 64})
    with pytest.raises(ValueError, match="completed"):
        workflow.current_directory(tmp_path, "feature_store")


def test_evidence_checks_real_bytes(tmp_path):
    folder = tmp_path / "reports/test"
    folder.mkdir(parents=True)
    table = folder / "metrics.csv"
    table.write_text("brier\n0.2\n")
    atomic_json(
        folder / "run.json",
        {"sha256": {"metrics.csv": digest(table)}, "summary": {"status": "completed"}},
    )
    workflow.evidence(tmp_path, "test")
    table.write_text("brier\n0.01\n")
    with pytest.raises(ValueError, match="Changed"):
        workflow.evidence(tmp_path, "test")


def test_lineage_rejects_an_unrelated_model_matrix(tmp_path):
    for name, record in {
        "feature_store": {"summary": {"status": "completed", "fingerprint": "new"}},
        "model_comparison": {
            "summary": {"status": "completed"},
            "manifest": {"inputs": {"feature_fingerprint": "old"}},
        },
    }.items():
        atomic_json(tmp_path / "reports" / name / "run.json", {**record, "sha256": {}})
    with pytest.raises(ValueError, match="stale"):
        workflow.lineage(tmp_path)


@pytest.fixture
def old_predictions():
    return pd.DataFrame(
        {
            "Gender": ["M", "M"],
            "Season": [2016, 2016],
            "ID": ["a", "b"],
            "block": ["M", "M"],
            "model": ["seed_raw", "seed_raw"],
            "y": [0, 1],
            "p": [0.2, 0.7],
        }
    )


def test_paired_retraining_retains_identical_reference_predictions(old_predictions):
    extra = old_predictions.assign(model="rank_xgboost_raw", p=[0.1, 0.8])
    result = workflow.matched_comparison(old_predictions, pd.concat([old_predictions, extra]))
    assert result.games.iloc[0] == 2
    assert result.max_probability_change.iloc[0] == 0
    assert result.old_brier.iloc[0] == pytest.approx(result.new_brier.iloc[0])


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "labels"])
def test_paired_scores_refuse_mismatched_games(old_predictions, mutation):
    changed = old_predictions.copy()
    if mutation == "missing":
        changed = changed.iloc[1:]
    elif mutation == "duplicate":
        changed = pd.concat([changed, changed.iloc[:1]])
    else:
        changed["y"] = 1 - changed.y
    with pytest.raises(ValueError):
        workflow.matched_comparison(old_predictions, changed)


def test_restoring_complete_trusted_archive_preserves_binary_tasks(tmp_path):
    source = tmp_path / "archive.zip"
    content = b"opaque estimator bytes; never deserialized by restoration"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("run/fit/model.joblib", content)
        archive.writestr(
            "archive_manifest.json",
            json.dumps(
                {
                    "schema": 1,
                    "sha256": {"run/fit/model.joblib": hashlib.sha256(content).hexdigest()},
                }
            ),
        )
    restore_archive(source, tmp_path / "tables", digest(source))
    assert not (tmp_path / "tables/run/fit/model.joblib").exists()
    restore_archive(source, tmp_path / "complete", digest(source), complete_run=True)
    assert (tmp_path / "complete/run/fit/model.joblib").read_bytes() == content


def test_ranked_tree_hypothesis_is_men_only_and_has_56_extra_fits():
    extra = [c for c in modeling.candidates("M") if c.family in {"rank_xgboost", "rank_lightgbm"}]
    assert len(extra) * 7 == 56
    assert {len(modeling.columns_for(c)) for c in extra} == {19, 124}
    assert all(
        not c.family.startswith("rank_")
        for route in ["W", "pooled_common"]
        for c in modeling.candidates(route)
    )


def test_notebook_export_is_opt_in_and_historical_scores_are_not_current():
    root = Path(__file__).resolve().parents[1]
    final = nbformat.read(next((root / "notebooks").glob("04*.ipynb")), as_version=4)
    research = nbformat.read(next((root / "notebooks").glob("05*.ipynb")), as_version=4)
    cells = "\n".join(c.source for c in final.cells if c.cell_type == "code")
    assert "GENERATE_SUBMISSION = False" in cells
    assert "if GENERATE_SUBMISSION:" in cells and "generate_submission(ROOT)" in cells
    assert 'download="submission.csv"' in cells
    assert "kaggle.api" not in cells and "competition_submit" not in cells
    assert "kaggle_scores.csv" not in "\n".join(
        c.source for c in research.cells if c.cell_type == "code"
    )


def test_generation_refuses_stale_model_without_replacing_export(tmp_path, monkeypatch):
    feature_run = tmp_path / "features"
    model_run = tmp_path / ("a" * 64)
    atomic_json(tmp_path / "configs/model_comparison.json", {})
    export = tmp_path / "submissions/submission.csv"
    export.parent.mkdir()
    export.write_bytes(b"existing user file")
    monkeypatch.setattr(workflow, "require_current_features", lambda _: feature_run)
    monkeypatch.setattr(workflow, "current_directory", lambda *a: model_run)
    monkeypatch.setattr(modeling, "run_inputs", lambda *a: {"changed": True})
    with pytest.raises(ValueError, match="Model inputs/code changed"):
        workflow.generate_submission(tmp_path)
    assert export.read_bytes() == b"existing user file"
