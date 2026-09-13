"""Fresh-checkout restoration must precede current-input checks, never new fitting."""

import json
from types import SimpleNamespace

import pytest

from march_mania.publication import followups
from march_mania.runtime import atomic_json


def setup_study(tmp_path, monkeypatch):
    key = "a" * 64
    record = {
        "summary": {"fingerprint": key, "status": "completed"},
        "manifest": {"fingerprint": key, "inputs": {"data": "verified"}},
    }
    archive = {
        "status": "uploaded",
        "uri": "s3://fixture/experiment.zip",
        "version_id": "recorded-version",
        "sha256": "b" * 64,
    }
    atomic_json(tmp_path / "reports/validation/ranking_systems.json", {"archive": archive})
    calls = []

    def review(root):
        calls.append("review")
        return root, record

    def run(root):
        calls.append("run")
        path = root / "outputs/ranking_systems" / key
        assert json.loads((path / "summary.json").read_text()) == record["summary"]
        return path

    def download(value, target, log, complete_run):
        calls.append("download")
        assert value == archive and complete_run
        atomic_json(target / "run/manifest.json", record["manifest"])
        atomic_json(target / "run/summary.json", record["summary"])
        return target / "run"

    monkeypatch.setitem(
        followups.STUDIES, "ranking_systems", SimpleNamespace(review=review, run=run)
    )
    monkeypatch.setattr(followups, "download_input", download)
    return key, record, calls


def test_fresh_recovery_uses_declared_version_and_existing_run_avoids_download(
    tmp_path, monkeypatch
):
    key, _, calls = setup_study(tmp_path, monkeypatch)
    expected = tmp_path / "outputs/ranking_systems" / key
    assert followups.study_stage(tmp_path, "ranking_systems") == expected
    assert calls == ["review", "download", "run"]
    calls.clear()
    assert followups.study_stage(tmp_path, "ranking_systems") == expected
    assert calls == ["review", "run"]


def test_changed_source_delegates_fresh_computation_without_old_archive(tmp_path, monkeypatch):
    _, _, calls = setup_study(tmp_path, monkeypatch)

    def stale(root):
        raise ValueError("Stale source")

    monkeypatch.setattr(followups.STUDIES["ranking_systems"], "review", stale)
    monkeypatch.setattr(followups.STUDIES["ranking_systems"], "run", lambda root: root / "new-run")
    assert followups.study_stage(tmp_path, "ranking_systems") == tmp_path / "new-run"
    assert calls == []


def test_wrong_archive_lineage_never_becomes_current(tmp_path, monkeypatch):
    key, record, calls = setup_study(tmp_path, monkeypatch)

    def wrong(value, target, log, complete_run):
        atomic_json(target / "run/manifest.json", {"fingerprint": "c" * 64})
        atomic_json(target / "run/summary.json", record["summary"])
        return target / "run"

    monkeypatch.setattr(followups, "download_input", wrong)
    with pytest.raises(ValueError, match="lineage"):
        followups.study_stage(tmp_path, "ranking_systems")
    assert calls == ["review"]
    assert not (tmp_path / "outputs/ranking_systems" / key).exists()


def test_unversioned_archive_and_unknown_study_fail(tmp_path, monkeypatch):
    _, _, calls = setup_study(tmp_path, monkeypatch)
    atomic_json(
        tmp_path / "reports/validation/ranking_systems.json", {"archive": {"status": "uploaded"}}
    )
    with pytest.raises(ValueError, match="versioned"):
        followups.study_stage(tmp_path, "ranking_systems")
    with pytest.raises(ValueError, match="Unknown"):
        followups.study_stage(tmp_path, "unregistered")
    assert calls == ["review"]
