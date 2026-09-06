from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from march_mania.research import run
from march_mania.research_report import probability_metrics


def test_official_brier_and_invalid_probabilities():
    assert probability_metrics(np.array([1, 0]), np.array([0.8, 0.4]))["brier"] == pytest.approx(
        0.1
    )
    assert probability_metrics(np.array([1, 1]), np.array([0.8, 0.4]))["roc_auc"] is None
    with pytest.raises(ValueError, match="within"):
        probability_metrics(np.array([1]), np.array([1.1]))


def test_end_to_end_all_blocks_and_resume(raw, tmp_path, config):
    output = tmp_path / "run"
    result = run(raw, output, config)
    assert result["fold_tasks"] == 48
    before = {str(p): p.stat().st_mtime_ns for p in output.glob("fold_*/model.joblib")}
    resumed = run(raw, output, config)
    assert resumed["fingerprint"] == result["fingerprint"]
    assert before == {str(p): p.stat().st_mtime_ns for p in output.glob("fold_*/model.joblib")}
    predictions = pd.read_parquet(output / "predictions.parquet")
    assert len(predictions.groupby(["Gender", "Season", "block", "model"])) == 48
    assert predictions.groupby(["Gender", "Season", "block", "model"]).size().eq(28).all()
    assert not predictions.duplicated(["Gender", "Season", "block", "model", "ID"]).any()
    assert (output / "report.html").stat().st_size > 10000
    assert "Retrospective development benchmark" in (output / "report.html").read_text()
    events = [json.loads(s) for s in (output / "events.jsonl").read_text().splitlines()]
    assert sum(e["event"] == "task_reused" for e in events) == 58
    config["ridge_alpha"] = 21
    with pytest.raises(ValueError, match="changed"):
        run(raw, output, config)


def test_remote_completion_published_last_and_failure_is_explicit(tmp_path):
    from unittest.mock import Mock

    from march_mania.research import finalize_run
    from march_mania.runtime import EventLog

    log = EventLog(tmp_path / "events.jsonl")
    log.emit("test_started")
    (tmp_path / "report.html").write_text("example")
    mirror = Mock()
    mirror.upload.side_effect = RuntimeError("network interrupted")
    with pytest.raises(RuntimeError):
        finalize_run(tmp_path, {}, mirror, log)
    assert json.loads((tmp_path / "summary.json").read_text())["status"] == "upload_failed"
    assert "run_completed" not in (tmp_path / "events.jsonl").read_text()
    mirror.upload.side_effect = None
    assert finalize_run(tmp_path, {}, mirror, log)["status"] == "completed"
    assert mirror.upload.call_args.args[1] == "summary.json"
