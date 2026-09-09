"""Delivery preserves fitted probabilities and rejects stale or incomplete releases."""

from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from march_mania.runtime import atomic_json, digest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("delivery", ROOT / "scripts/deliver_predictions.py")
assert SPEC is not None and SPEC.loader is not None
delivery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delivery)


@pytest.fixture
def completed(tmp_path, monkeypatch):
    public = tmp_path / "reports/prediction_production"
    public.mkdir(parents=True)
    run = tmp_path / "run"
    rows = []
    for index in range(50):
        name = delivery.REFERENCE if index == 0 else f"candidate_{index:02}"
        path = run / f"csv_{name}/submission.csv"
        path.parent.mkdir(parents=True)
        path.write_bytes(f"ID,Pred\n2026_1101_1102,{0.01 + index / 100:.8f}\n".encode())
        rows.append(
            {
                "candidate_id": name,
                "path": str(path.relative_to(run)),
                "sha256": digest(path),
                "bytes": path.stat().st_size,
                "rows": 1,
            }
        )
    pd.DataFrame(rows).to_csv(public / "submission_manifest.csv", index=False)
    atomic_json(public / "recipe.json", {"reference": delivery.REFERENCE})
    monkeypatch.setattr(
        delivery.production_release,
        "check",
        lambda root: {"fingerprint": "a" * 64, "status": "completed", "submission_files": 50},
    )
    monkeypatch.setattr(
        delivery.production_release,
        "verify_tasks",
        lambda path, key: {row["candidate_id"]: row["sha256"] for row in rows},
    )
    return tmp_path, run, rows


def test_review_is_offline_and_does_not_create_predictions(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Review must not restore, train or export")

    monkeypatch.setattr(delivery.production_release, "recover", forbidden)
    monkeypatch.setattr(delivery.production_inputs, "restore", forbidden)
    monkeypatch.setattr(delivery.production, "run", forbidden)
    monkeypatch.setattr(delivery, "package", forbidden)
    summary = delivery.deliver(ROOT)
    assert summary["submission_files"] == 50
    assert summary["fitted_models"] == 33


def test_all_fifty_bytes_and_reference_are_preserved_and_resumed(completed, monkeypatch):
    root, run, rows = completed
    result = delivery.package(root, run)
    with zipfile.ZipFile(root / result["download_archive"]) as archive:
        assert len(archive.namelist()) == 52
        for row in rows:
            assert (
                archive.read(f"{row['candidate_id']}/submission.csv")
                == (run / row["path"]).read_bytes()
            )
    assert digest(root / result["reference_file"]) == rows[0]["sha256"]
    before = digest(root / result["download_archive"])
    # A reusable task must not open a new ZIP, even if the convenience copy is absent.
    monkeypatch.setattr(delivery.zipfile, "ZipFile", lambda *a, **kw: pytest.fail("repack"))
    (root / result["download_archive"]).unlink()
    assert delivery.package(root, run) == result
    assert digest(root / result["download_archive"]) == before
    events = [
        json.loads(line)
        for p in (root / "outputs").rglob("events.jsonl")
        for line in p.read_text().splitlines()
    ]
    assert any(e["event"] == "task_reused" for e in events)


@pytest.mark.parametrize("change", ["file", "manifest", "unsafe_path"])
def test_changed_or_unsafe_csv_cannot_be_delivered(completed, change):
    root, run, rows = completed
    if change == "file":
        (run / rows[0]["path"]).write_text("ID,Pred\n2026_1101_1102,0.999\n")
    else:
        manifest = root / "reports/prediction_production/submission_manifest.csv"
        frame = pd.read_csv(manifest)
        if change == "manifest":
            frame.loc[0, "sha256"] = "0" * 64
        else:
            frame.loc[0, "path"] = "../outside.csv"
        frame.to_csv(manifest, index=False)
    with pytest.raises(ValueError):
        delivery.package(root, run)
    assert not (root / "submissions").exists()


def test_restore_never_calls_training(completed, monkeypatch):
    root, run, _ = completed
    archive = root / "download.zip"
    calls = []

    def recover(r, destination, source):
        calls.append((r, destination, source))
        return run

    monkeypatch.setattr(delivery.production_release, "recover", recover)
    monkeypatch.setattr(delivery.production, "run", lambda *a: pytest.fail("training called"))
    result = delivery.deliver(root, "restore", archive)
    assert calls == [(root, root / "outputs/prediction_production", archive)]
    assert result["reference_candidate"] == delivery.REFERENCE


def test_generate_prepares_verified_inputs_before_resumable_execution(completed, monkeypatch):
    root, run, _ = completed
    calls = []
    monkeypatch.setattr(delivery.production_inputs, "restore", lambda *a: calls.append("inputs"))

    def generate(*args):
        assert calls == ["inputs"]
        calls.append("generate")
        return run

    monkeypatch.setattr(delivery.production, "run", generate)
    assert delivery.deliver(root, "generate")["submission_files"] == 50
    assert calls == ["inputs", "generate"]


@pytest.mark.parametrize("action,archive", [("submit", None), ("review", Path("x.zip"))])
def test_invalid_actions_fail_before_side_effects(action, archive):
    with pytest.raises(ValueError):
        delivery.deliver(ROOT, action, archive)
