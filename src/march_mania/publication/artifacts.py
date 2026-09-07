"""Restore trusted input archives and completed tasks without long-lived credentials."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from march_mania.runtime import EventLog, Mirror, atomic_json, digest


def safe_path(root: Path, name: str) -> Path:
    path = root / name
    if not name or "\\" in name or Path(name).is_absolute() or ".." in Path(name).parts:
        raise ValueError("Unsafe artifact path")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Artifact escapes its destination")
    return path


def verified_write(path: Path, contents: bytes, expected: str) -> None:
    if hashlib.sha256(contents).hexdigest() != expected:
        raise ValueError("Artifact SHA-256 mismatch")
    if path.exists() and digest(path) == expected:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def restore_archive(archive: Path, destination: Path, expected: str) -> None:
    """Trust the recorded whole-file checksum before reading any archive members."""
    if digest(archive) != expected:
        raise ValueError("Input archive differs from its recorded SHA-256")
    with zipfile.ZipFile(archive) as source:
        manifest = json.loads(source.read("archive_manifest.json"))
        names = source.namelist()
        hashes = manifest["sha256"]
        if manifest.get("schema") != 1 or len(names) != len(set(names)):
            raise ValueError("Invalid input archive schema")
        if set(names) != {*hashes, "archive_manifest.json"}:
            raise ValueError("Input archive inventory mismatch")
        # Only tabular inputs and provenance are needed; do not deserialize old estimators.
        selected = [name for name in hashes if name.startswith(("run/", "raw/"))]
        for name in selected:
            if Path(name).suffix not in {".parquet", ".csv", ".json"}:
                continue
            path = safe_path(destination, name)
            if path.exists() and digest(path) == hashes[name]:
                continue
            verified_write(path, source.read(name), hashes[name])
        atomic_json(destination / "archive.json", {"sha256": expected, "manifest": manifest})


def download_input(record: dict[str, Any], target: Path, log: EventLog) -> Path:
    """Download through the AWS role chain; never write credentials to artifacts."""
    uri = record.get("uri", record.get("s3_uri"))
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path.strip("/"):
        raise ValueError("Recorded archive must use an explicit S3 object")
    target.mkdir(parents=True, exist_ok=True)
    archive = target / "archive.zip"
    if not archive.exists() or digest(archive) != record["sha256"]:
        temporary = target / ".archive.zip.tmp"
        mirror = Mirror(f"s3://{parsed.netloc}/inputs")
        extra = {"VersionId": record["version_id"]} if record.get("version_id") else {}
        try:
            log.emit("input_download_started", object=parsed.path.lstrip("/"))
            mirror.client.download_file(
                parsed.netloc, parsed.path.lstrip("/"), str(temporary), ExtraArgs=extra
            )
            if digest(temporary) != record["sha256"]:
                raise ValueError("Downloaded input archive checksum mismatch")
            temporary.replace(archive)
        finally:
            temporary.unlink(missing_ok=True)
    restore_archive(archive, target, record["sha256"])
    log.emit("input_verified", sha256=record["sha256"], bytes=archive.stat().st_size)
    return target / "run"


def restore_tasks(mirror: Mirror, destination: Path, run_key: str, log: EventLog) -> int:
    """Restore only remotely committed tasks, verifying outputs before checkpoint commit.

    Partial uploads without a checkpoint are ignored. Existing valid local tasks are
    retained. Network/permission errors are not mistaken for an empty remote run.
    """
    prefix = mirror.prefix + "/"
    count = 0
    paginator = mirror.client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=mirror.bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            relative = item["Key"][len(prefix) :]
            if not relative.endswith("/checkpoint.json"):
                continue
            checkpoint = safe_path(destination, relative)
            if len(Path(relative).parts) != 2:
                raise ValueError("Unexpected checkpoint nesting")
            response = mirror.client.get_object(Bucket=mirror.bucket, Key=item["Key"])
            content = response["Body"].read()
            if hashlib.sha256(content).hexdigest() != response.get("Metadata", {}).get("sha256"):
                raise ValueError("Remote checkpoint checksum mismatch")
            record = json.loads(content)
            if record["fingerprint"] != run_key or not record.get("outputs"):
                raise ValueError("Remote checkpoint has incompatible inputs")
            for name, expected in record["outputs"].items():
                path = safe_path(checkpoint.parent, name)
                if path.exists() and digest(path) == expected:
                    continue
                object_key = prefix + str(path.relative_to(destination))
                value = mirror.client.get_object(Bucket=mirror.bucket, Key=object_key)
                verified_write(path, value["Body"].read(), expected)
            verified_write(checkpoint, content, hashlib.sha256(content).hexdigest())
            count += 1
            log.emit("task_restored", task=checkpoint.parent.name)
    return count
