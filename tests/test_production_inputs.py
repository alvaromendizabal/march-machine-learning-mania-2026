"""Selective immutable-archive recovery without downloading a giant unused member."""

from __future__ import annotations

import base64
import hashlib
import io
import json

import pytest

from march_mania.publication.production_inputs import RangeReader, restore_members, verify_object
from march_mania.runtime import EventLog


def archive_bytes(bad=False):
    import zipfile

    stream = io.BytesIO()
    contents = {"run/input.csv": b"a,b\n1,2\n", "run/unused.bin": b"x" * 1000000}
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}
    if bad:
        hashes["run/input.csv"] = "0" * 64
    with zipfile.ZipFile(stream, "w") as archive:
        for name, data in contents.items():
            archive.writestr(name, data)
        archive.writestr("archive_manifest.json", json.dumps({"schema": 1, "sha256": hashes}))
    return stream.getvalue()


def test_selected_member_recovery_and_reuse(tmp_path):
    data = archive_bytes()
    reader = RangeReader(len(data), lambda a, b: data[a : b + 1])
    record = {"sha256": hashlib.sha256(data).hexdigest()}
    log = EventLog(tmp_path / "events.jsonl")
    first = restore_members(reader, record, ["run/input.csv"], tmp_path, log)
    second = restore_members(reader, record, ["run/input.csv"], tmp_path, log)
    assert first == second
    assert (tmp_path / "run/input.csv").read_bytes() == b"a,b\n1,2\n"
    assert not (tmp_path / "run/unused.bin").exists()
    assert reader.transferred < 10000
    assert '"event": "input_reused"' in log.path.read_text()


def test_corrupt_member_never_receives_a_receipt(tmp_path):
    data = archive_bytes(bad=True)
    reader = RangeReader(len(data), lambda a, b: data[a : b + 1])
    with pytest.raises(ValueError, match="checksum"):
        restore_members(
            reader, {}, ["run/input.csv"], tmp_path, EventLog(tmp_path / "events.jsonl")
        )
    assert not (tmp_path / "receipt.json").exists()
    assert not (tmp_path / "run/input.csv").exists()
    assert not list(tmp_path.rglob("*.tmp"))


def test_truncated_range_and_invalid_seek_fail():
    reader = RangeReader(10, lambda a, b: b"bad")
    with pytest.raises(ValueError, match="Truncated"):
        reader.read(10)
    with pytest.raises(ValueError, match="Negative"):
        reader.seek(-1)
    with pytest.raises(ValueError, match="origin"):
        reader.seek(0, 3)


@pytest.mark.parametrize("key", ["VersionId", "ContentLength", "ChecksumType", "ChecksumSHA256"])
def test_s3_object_identity_is_not_just_a_filename(key):
    record = {"version_id": "v1", "bytes": 42, "sha256": "ab" * 32}
    metadata = {
        "VersionId": "v1",
        "ContentLength": 42,
        "ChecksumType": "FULL_OBJECT",
        "ChecksumSHA256": base64.b64encode(bytes.fromhex(record["sha256"])).decode(),
    }
    verify_object(record, metadata)
    metadata[key] = 43 if key == "ContentLength" else "wrong"
    with pytest.raises(ValueError):
        verify_object(record, metadata)
