"""Benchmark-only fitting, temporal isolation, provenance and verified task replay."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from march_mania.publication import benchmark, inference, workflow
from march_mania.runtime import EventLog, TaskStore, atomic_json, digest, fingerprint

pytest_plugins = ["test_inference"]


def test_benchmark_has_no_future_fit_or_export_and_reuses_verified_tasks(
    tmp_path, inputs, settings, monkeypatch
):
    history, frame, _, _ = inputs
    recipe = inference.freeze_recipe(history, settings)
    store = TaskStore(tmp_path, fingerprint(settings), EventLog(tmp_path / "events.jsonl"))
    public = benchmark.execute(frame, recipe, store, settings)
    summary = json.loads((public / "summary.json").read_text())
    assert summary["model_fits"] == 16 and summary["physical_games"] == 48
    assert not summary["submission_generated"]
    assert not list(tmp_path.rglob("submission.csv"))
    audits = json.loads((public / "fit_audits.json").read_text())
    assert all(a["training_max_season"] < a["prediction_season"] < 2026 for a in audits)
    before = digest(public / "benchmark_predictions.csv")

    def forbidden(*args, **kwargs):
        raise AssertionError("Verified fits must not repeat")

    monkeypatch.setattr(inference, "fit_model", forbidden)
    benchmark.execute(frame, recipe, store, settings)
    assert digest(public / "benchmark_predictions.csv") == before
    events = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert sum(e["event"] == "task_reused" for e in events) == 33


def test_fresh_benchmark_ignores_all_future_targets_and_rejects_missing_years(
    tmp_path, inputs, settings
):
    history, frame, _, _ = inputs
    recipe = inference.freeze_recipe(history, settings)
    forecasts = []
    for name, changed in [("original", frame), ("changed", frame.copy())]:
        if name == "changed":
            changed.loc[changed.Season == 2026, "y"] = -999
        directory = tmp_path / name
        store = TaskStore(directory, fingerprint(settings), EventLog(directory / "events.jsonl"))
        result = benchmark.execute(changed, recipe, store, settings)
        forecasts.append(pd.read_csv(result / "benchmark_predictions.csv"))
    pd.testing.assert_frame_equal(*forecasts)
    directory = tmp_path / "missing"
    store = TaskStore(directory, fingerprint(settings), EventLog(directory / "events.jsonl"))
    with pytest.raises(ValueError, match="Missing retrospective"):
        benchmark.execute(frame.loc[frame.Season != 2022], recipe, store, settings)


def test_run_binds_benchmark_to_upstream_matrix_and_preserves_actual_evidence(
    tmp_path, inputs, settings
):
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / "src", tmp_path / "src")
    features, models = tmp_path / "features", tmp_path / "models"
    features.mkdir()
    models.mkdir()
    inputs[0].to_parquet(models / "candidate_predictions.parquet", index=False)
    inputs[1].to_parquet(features / "features.parquet", index=False)
    atomic_json(features / "summary.json", {"status": "completed", "fingerprint": "a" * 64})
    atomic_json(models / "summary.json", {"status": "completed", "fingerprint": "b" * 64})
    manifest = {
        "inputs": {
            "feature_fingerprint": "a" * 64,
            "data": {"features.parquet": digest(features / "features.parquet")},
            "environment": {"purpose": "synthetic test"},
        }
    }
    atomic_json(models / "manifest.json", manifest)
    result = benchmark.run(tmp_path, features, models, settings)
    recorded = json.loads((result / "manifest.json").read_text())["inputs"]
    assert recorded["feature_fingerprint"] == "a" * 64
    assert recorded["model_fingerprint"] == "b" * 64
    assert digest(result / "development_predictions.parquet") == digest(
        models / "candidate_predictions.parquet"
    )
    assert json.loads((result / "summary.json").read_text())["status"] == "completed"
    assert not list(tmp_path.rglob("submission.csv"))
    manifest["inputs"]["feature_fingerprint"] = "c" * 64
    atomic_json(models / "manifest.json", manifest)
    with pytest.raises(ValueError, match="lineage differ"):
        benchmark.run(tmp_path, features, models, settings)


@pytest.mark.parametrize(
    "changed", ["feature_fingerprint", "model_fingerprint", "source", "config"]
)
def test_review_rejects_stale_benchmark_results(tmp_path, monkeypatch, changed):
    source = tmp_path / "benchmark.py"
    source.write_text("recorded source")
    atomic_json(tmp_path / "configs/inference.json", {})
    record = {
        "manifest": {
            "inputs": {
                "feature_fingerprint": "features",
                "model_fingerprint": "models",
                "source": {"benchmark.py": digest(source)},
                "config": {},
            }
        }
    }
    records = {
        "benchmark": record,
        "feature_store": {"summary": {"fingerprint": "features"}},
        "model_comparison": {"summary": {"fingerprint": "models"}},
    }
    # Independent evidence-byte and upstream-source verification have separate tests.
    monkeypatch.setattr(workflow, "evidence", lambda root, name: (root / name, records[name]))
    monkeypatch.setattr(workflow, "require_recorded_source", lambda *args: None)
    workflow.benchmark_evidence(tmp_path)
    if changed == "source":
        source.write_text("changed source")
    elif changed == "config":
        atomic_json(tmp_path / "configs/inference.json", {"changed": True})
    else:
        record["manifest"]["inputs"][changed] = "other run"
    with pytest.raises(ValueError, match="stale|changed"):
        workflow.benchmark_evidence(tmp_path)
