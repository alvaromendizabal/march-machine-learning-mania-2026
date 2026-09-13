from __future__ import annotations

import hashlib
from unittest.mock import Mock, patch

import pytest

from march_mania.runtime import EventLog, Mirror


def make_mirror(key="project/data.json", content=b"valid", metadata=True):
    mirror = object.__new__(Mirror)
    mirror.bucket, mirror.prefix = "bucket", "project"
    mirror.client = Mock()
    mirror.client.get_paginator.return_value.paginate.return_value = [{"Contents": [{"Key": key}]}]
    mirror.client.head_object.return_value = {
        "Metadata": {"sha256": hashlib.sha256(content).hexdigest()} if metadata else {}
    }

    def download(bucket, key, filename):
        from pathlib import Path

        Path(filename).write_bytes(content)

    mirror.client.download_file.side_effect = download
    return mirror


def test_restore_checks_bytes_and_preserves_existing_directory(tmp_path):
    mirror = make_mirror()
    destination = tmp_path / "restored"
    mirror.restore(destination)
    assert (destination / "data.json").read_bytes() == b"valid"
    with pytest.raises(ValueError, match="empty"):
        mirror.restore(destination)


@pytest.mark.parametrize("key", ["project/../outside", "project//absolute"])
def test_restore_rejects_unsafe_keys(tmp_path, key):
    with pytest.raises(ValueError, match="Unsafe"):
        make_mirror(key).restore(tmp_path / "restored")


def test_restore_rejects_corrupt_download(tmp_path):
    mirror = make_mirror()
    mirror.client.head_object.return_value = {"Metadata": {"sha256": "wrong"}}
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        mirror.restore(tmp_path / "restored")
    assert not (tmp_path / "restored/data.json").exists()


def test_restore_rejects_unverified_objects(tmp_path):
    with pytest.raises(ValueError, match="Missing SHA256"):
        make_mirror(metadata=False).restore(tmp_path / "restored")


def test_restore_empty_prefix_is_explicit(tmp_path):
    mirror = make_mirror()
    mirror.client.get_paginator.return_value.paginate.return_value = []
    with pytest.raises(FileNotFoundError):
        mirror.restore(tmp_path / "restored")


def test_upload_includes_content_checksum(tmp_path):
    path = tmp_path / "data.json"
    path.write_bytes(b"valid")
    mirror = make_mirror()
    mirror.upload(path, "work/result.json")
    mirror.client.upload_file.assert_called_once_with(
        str(path),
        "bucket",
        "project/work/result.json",
        ExtraArgs={"Metadata": {"sha256": hashlib.sha256(b"valid").hexdigest()}},
    )


@pytest.mark.parametrize("uri", ["https://bucket/prefix", "s3://bucket", "s3://bucket/p?x=1"])
def test_remote_prefix_is_required(uri):
    with pytest.raises(ValueError):
        Mirror(uri)


def test_unavailable_memory_telemetry_cannot_break_work(tmp_path):
    import json

    import psutil

    with patch("march_mania.runtime.psutil.Process", side_effect=psutil.AccessDenied()):
        log = EventLog(tmp_path / "events.jsonl")
        log.emit("still_running")
    record = json.loads(log.path.read_text())
    assert record["rss_mb"] is None
    assert record["memory_status"] == "AccessDenied"
