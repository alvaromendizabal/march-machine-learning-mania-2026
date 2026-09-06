from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("archive", Path("scripts/archive.py"))
assert spec is not None and spec.loader is not None
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


def test_archive_roundtrip_resume_and_conflict(tmp_path):
    run, raw, source = [tmp_path / name for name in ["run", "raw", "source"]]
    for directory in [run, raw, source]:
        directory.mkdir()
    (run / "summary.json").write_text(json.dumps({"status": "completed"}))
    (run / "result.csv").write_text("brier\n0.2\n")
    (raw / "games.csv").write_text("inputs")
    (source / "model.py").write_text("source")

    def checksum(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    (run / "manifest.json").write_text(
        json.dumps(
            {
                "fingerprint": "test",
                "inputs": {
                    "data": {"games.csv": checksum(raw / "games.csv")},
                    "source": {"model.py": checksum(source / "model.py")},
                },
            }
        )
    )
    bundle = tmp_path / "run.zip"
    archive.create(run, raw, bundle, source)
    target = tmp_path / "restored"
    archive.restore(bundle, target)
    before = (target / "run/result.csv").stat().st_mtime_ns
    archive.restore(bundle, target)
    assert (target / "run/result.csv").stat().st_mtime_ns == before
    (target / "run/result.csv").write_text("changed")
    with pytest.raises(ValueError, match="different"):
        archive.restore(bundle, target)


def test_archive_rejects_traversal_and_corruption(tmp_path):
    for name, checksum, error in [("../outside", "0", "Unsafe"), ("run/test", "0", "SHA-256")]:
        bundle = tmp_path / "invalid.zip"
        with zipfile.ZipFile(bundle, "w") as writer:
            writer.writestr(name, "test")
            writer.writestr(
                "archive_manifest.json", json.dumps({"schema": 1, "sha256": {name: checksum}})
            )
        with pytest.raises(ValueError, match=error):
            archive.restore(bundle, tmp_path / "destination")
    assert not (tmp_path / "outside").exists()
