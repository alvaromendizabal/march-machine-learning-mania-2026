from __future__ import annotations

import json
import time
from unittest.mock import Mock

import pytest

from march_mania.runtime import EventLog, TaskStore, atomic_json, digest


def test_resume_skips_valid_work_and_recomputes_corrupt_output(tmp_path):
    log = EventLog(tmp_path / "events.jsonl")
    store = TaskStore(tmp_path, "identity", log, heartbeat_seconds=0.01)
    work = Mock()

    def produce(target):
        path = target / "result.json"
        atomic_json(path, {"value": 7})
        return [path]

    work.side_effect = produce
    target = store.task("model", work)
    before = digest(target / "checkpoint.json")
    store.task("model", work)
    assert work.call_count == 1
    assert digest(target / "checkpoint.json") == before
    (target / "result.json").write_text("corrupt")
    store.task("model", work)
    assert work.call_count == 2
    assert json.loads((target / "result.json").read_text()) == {"value": 7}


def test_failure_has_no_completion_and_successful_tasks_survive(tmp_path):
    store = TaskStore(tmp_path, "identity", EventLog(tmp_path / "events.jsonl"), 0.01)

    def failing(target):
        atomic_json(target / "partial.json", {"state": "partial"})
        raise RuntimeError("interrupted computation")

    with pytest.raises(RuntimeError):
        store.task("work", failing)
    assert not (tmp_path / "work/checkpoint.json").exists()
    events = [json.loads(s) for s in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert events[-1]["event"] == "task_failed"
    assert all("timestamp" in e and "elapsed_seconds" in e for e in events)


def test_heartbeat_is_independent_of_worker(tmp_path):
    store = TaskStore(tmp_path, "identity", EventLog(tmp_path / "events.jsonl"), 0.01)

    def work(target):
        time.sleep(0.045)
        atomic_json(target / "out.json", {})
        return [target / "out.json"]

    store.task("work", work)
    events = [json.loads(s) for s in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert any(e["event"] == "heartbeat" and e["task_elapsed_seconds"] > 0 for e in events)


def test_failed_s3_replication_retries_without_retraining(tmp_path):
    mirror = Mock()
    mirror.upload.side_effect = RuntimeError("upload failed")
    store = TaskStore(tmp_path, "identity", EventLog(tmp_path / "events.jsonl"), mirror=mirror)
    work = Mock()

    def produce(target):
        atomic_json(target / "out.json", {"value": 3})
        return [target / "out.json"]

    work.side_effect = produce
    with pytest.raises(RuntimeError, match="upload failed"):
        store.task("work", work)
    mirror.upload.side_effect = None
    store.task("work", work)
    assert work.call_count == 1
    assert mirror.upload.call_count >= 3


def test_changed_inputs_rejected(tmp_path):
    def work(target):
        atomic_json(target / "out.json", {})
        return [target / "out.json"]

    TaskStore(tmp_path, "first", EventLog(tmp_path / "events.jsonl")).task("work", work)
    with pytest.raises(ValueError, match="inputs changed"):
        TaskStore(tmp_path, "second", EventLog(tmp_path / "events.jsonl")).task("work", work)


def test_concurrent_task_is_rejected(tmp_path):
    from filelock import FileLock, Timeout

    target = tmp_path / "work"
    target.mkdir()
    with FileLock(str(target / ".lock")):
        with pytest.raises(Timeout):
            TaskStore(tmp_path, "x", EventLog(tmp_path / "events.jsonl")).task("work", Mock())
