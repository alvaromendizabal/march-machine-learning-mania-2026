"""Restore selected production inputs from checksum-verified immutable S3 archives.

Read only the required ZIP members rather than storing the multi-gigabyte feature
archive and its complete submission matrix. Every object is version-pinned and
must expose S3's full-object SHA-256 before any member is accepted.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import time
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from filelock import FileLock

from march_mania.publication.artifacts import safe_path
from march_mania.runtime import EventLog, Mirror, atomic_json, digest

MEMBERS = {
    "feature_store": [
        "run/features.parquet",
        "run/teams.parquet",
        "run/manifest.json",
        "run/summary.json",
        "raw/SampleSubmissionStage2.csv",
    ],
    "model_comparison": [
        "run/candidate_predictions.parquet",
        "run/manifest.json",
        "run/summary.json",
    ],
}


def verify_object(record: dict[str, Any], metadata: dict[str, Any]) -> None:
    if (
        metadata.get("VersionId") != record["version_id"]
        or int(metadata.get("ContentLength", -1)) != record["bytes"]
        or metadata.get("ChecksumType") != "FULL_OBJECT"
        or metadata.get("ChecksumSHA256")
        != base64.b64encode(bytes.fromhex(record["sha256"])).decode()
    ):
        raise ValueError("Archive version, size or full-object SHA-256 differs from the release")


class RangeReader(io.RawIOBase):
    """A bounded, seekable ZIP input backed by validated byte-range reads."""

    def __init__(self, size: int, fetch: Callable[[int, int], bytes]):
        self.size, self.fetch, self.position, self.transferred = size, fetch, 0, 0

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence not in {0, 1, 2}:
            raise ValueError("Invalid seek origin")
        position = (0 if whence == 0 else self.position if whence == 1 else self.size) + offset
        if position < 0:
            raise ValueError("Negative archive seek")
        self.position = position
        return position

    def read(self, size: int = -1) -> bytes:
        count = (
            max(0, self.size - self.position)
            if size < 0
            else min(size, max(0, self.size - self.position))
        )
        if not count:
            return b""
        data = self.fetch(self.position, self.position + count - 1)
        if len(data) != count:
            raise ValueError("Truncated archive byte range")
        self.position += count
        self.transferred += count
        return data


def open_remote(record: dict[str, Any], url: str | None = None) -> RangeReader:
    if url:
        remote, original = urlparse(url), urlparse(record["uri"])
        if (
            remote.scheme != "https"
            or remote.hostname
            not in {
                original.netloc + ".s3.us-west-2.amazonaws.com",
                original.netloc + ".s3.amazonaws.com",
            }
            or unquote(remote.path) != original.path
            or parse_qs(remote.query).get("versionId") != [record["version_id"]]
        ):
            raise ValueError("Use the exact version-pinned S3 archive URL")
        headers = {"x-amz-checksum-mode": "ENABLED"}
        # GET headers verify the object without retaining its entire body. The
        # streaming response is always closed, including on a validation failure.
        with urllib.request.urlopen(
            urllib.request.Request(url, headers=headers), timeout=60
        ) as response:
            verify_object(
                record,
                {
                    "VersionId": response.headers.get("x-amz-version-id"),
                    "ContentLength": response.headers.get("Content-Length"),
                    "ChecksumType": response.headers.get("x-amz-checksum-type"),
                    "ChecksumSHA256": response.headers.get("x-amz-checksum-sha256"),
                },
            )

        def fetch(start: int, end: int) -> bytes:
            request = urllib.request.Request(
                url, headers={**headers, "Range": f"bytes={start}-{end}"}
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                if (
                    response.status != 206
                    or response.headers.get("x-amz-version-id") != record["version_id"]
                    or response.headers.get("Content-Range")
                    != f"bytes {start}-{end}/{record['bytes']}"
                ):
                    raise ValueError("Server returned a different archive range/version")
                return response.read(end - start + 2)
    else:
        uri = record["uri"]
        mirror = Mirror(uri.rsplit("/", 1)[0])
        key = uri.split("/", 3)[3]
        params = {"Bucket": mirror.bucket, "Key": key, "VersionId": record["version_id"]}
        verify_object(record, mirror.client.head_object(**params, ChecksumMode="ENABLED"))

        def fetch(start: int, end: int) -> bytes:
            response = mirror.client.get_object(**params, Range=f"bytes={start}-{end}")
            try:
                if (
                    response.get("VersionId") != record["version_id"]
                    or response.get("ContentRange") != f"bytes {start}-{end}/{record['bytes']}"
                ):
                    raise ValueError("S3 returned a different archive range/version")
                return response["Body"].read()
            finally:
                response["Body"].close()

    return RangeReader(record["bytes"], fetch)


def restore_members(
    reader: RangeReader,
    record: dict[str, Any],
    members: list[str],
    target: Path,
    log: EventLog,
) -> dict[str, Any]:
    hashes = {}
    with zipfile.ZipFile(reader) as archive:
        manifest = json.loads(archive.read("archive_manifest.json"))
        names = archive.namelist()
        if (
            manifest.get("schema") != 1
            or len(names) != len(set(names))
            or set(names) != {*manifest["sha256"], "archive_manifest.json"}
        ):
            raise ValueError("Invalid archive inventory")
        for name in members:
            path = safe_path(target, name)
            expected = manifest["sha256"][name]
            hashes[name] = expected
            if path.is_file() and digest(path) == expected:
                log.emit("input_reused", member=name)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            hasher, last = hashlib.sha256(), time.monotonic()
            try:
                with archive.open(name) as source, temporary.open("wb") as destination:
                    while block := source.read(4 * 1024 * 1024):
                        destination.write(block)
                        hasher.update(block)
                        if time.monotonic() - last >= 15:
                            log.emit(
                                "input_download_progress", member=name, bytes=destination.tell()
                            )
                            last = time.monotonic()
                if hasher.hexdigest() != expected:
                    raise ValueError("Restored archive member checksum mismatch")
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
            log.emit("input_verified", member=name, sha256=expected, bytes=path.stat().st_size)
    receipt = {
        "archive": record,
        "sha256": hashes,
        "verification": "S3 FULL_OBJECT SHA-256 and every selected member SHA-256",
    }
    atomic_json(target / "receipt.json", receipt)
    return receipt


def restore(root: Path, destination: Path, urls: dict[str, str] | None = None) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with FileLock(str(destination / ".lock"), timeout=0):
        _restore(root, destination, urls)


def _restore(root: Path, destination: Path, urls: dict[str, str] | None) -> None:
    log = EventLog(destination / "events.jsonl")
    for name, members in MEMBERS.items():
        record = json.loads((root / "reports" / name / "run.json").read_text())["archive"]
        reader = open_remote(record, (urls or {}).get(name))
        restore_members(reader, record, members, destination / name, log)
        log.emit(
            "archive_inputs_ready",
            name=name,
            bytes_transferred=reader.transferred,
            archive_bytes=reader.size,
        )


def verify(root: Path, destination: Path) -> dict[str, Any]:
    result = {}
    for name, members in MEMBERS.items():
        record = json.loads((root / "reports" / name / "run.json").read_text())["archive"]
        receipt = json.loads((destination / name / "receipt.json").read_text())
        if receipt["archive"] != record or set(receipt["sha256"]) != set(members):
            raise ValueError("Production inputs belong to a different archive")
        if any(digest(safe_path(destination / name, p)) != h for p, h in receipt["sha256"].items()):
            raise ValueError("Production input bytes changed")
        result[name] = receipt
    return result
