"""Observable, atomic, content-verified research tasks and optional S3 replication."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import threading
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import psutil
from filelock import FileLock


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


class EventLog:
    """One JSON record per event; UTC wall time plus monotonic elapsed time."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.started = time.monotonic()
        self.lock = threading.Lock()

    def emit(self, event: str, **details: Any) -> None:
        try:
            rss = round(psutil.Process().memory_info().rss / 2**20, 1)
            memory_status = "available"
        except (psutil.Error, OSError) as error:
            # Restricted process namespaces can deny telemetry; model work remains valid.
            rss = None
            memory_status = type(error).__name__
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event": event,
            "elapsed_seconds": round(time.monotonic() - self.started, 3),
            "rss_mb": rss,
            "memory_status": memory_status,
            **details,
        }
        line = json.dumps(record, sort_keys=True, allow_nan=False)
        with self.lock:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
                stream.flush()
            print(line, flush=True)


class Mirror:
    """Replicate only explicitly selected artifacts; credentials use the AWS role chain."""

    def __init__(self, uri: str):
        import boto3
        from botocore.config import Config

        parsed = urlparse(uri)
        if parsed.scheme != "s3" or not parsed.netloc or parsed.query or parsed.fragment:
            raise ValueError("Expected s3://bucket/project-prefix")
        self.bucket = parsed.netloc
        self.prefix = parsed.path.strip("/")
        if not self.prefix:
            raise ValueError("An explicit project prefix is required")
        self.client = boto3.Session().client(
            "s3",
            config=Config(
                retries={"mode": "standard", "total_max_attempts": 4},
                connect_timeout=10,
                read_timeout=60,
            ),
        )

    def upload(self, path: Path, key: str) -> None:
        self.client.upload_file(
            str(path),
            self.bucket,
            f"{self.prefix}/{key}",
            ExtraArgs={"Metadata": {"sha256": digest(path)}},
        )

    def restore(self, destination: Path) -> None:
        """Restore into an empty run directory, rejecting path traversal and corrupt bytes."""
        if destination.exists() and any(destination.iterdir()):
            raise ValueError(
                "Restore destination must be empty; existing runs are never overwritten"
            )
        prefix = self.prefix + "/"
        paginator = self.client.get_paginator("list_objects_v2")
        count = 0
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                relative = item["Key"][len(prefix) :]
                if not relative or relative.endswith("/"):
                    continue
                path = destination / relative
                if not path.resolve().is_relative_to(destination.resolve()):
                    raise ValueError("Unsafe object key")
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
                try:
                    metadata = self.client.head_object(Bucket=self.bucket, Key=item["Key"])
                    expected = metadata.get("Metadata", {}).get("sha256")
                    if not expected:
                        raise ValueError(f"Missing SHA256 metadata for {relative}")
                    self.client.download_file(self.bucket, item["Key"], str(temporary))
                    if digest(temporary) != expected:
                        raise ValueError(f"SHA256 mismatch for {relative}")
                    temporary.replace(path)
                    count += 1
                finally:
                    temporary.unlink(missing_ok=True)
        if not count:
            raise FileNotFoundError("No artifacts found at the requested S3 prefix")


class TaskStore:
    """Checkpoints commit last, after every output exists and its hash is recorded."""

    def __init__(
        self,
        root: Path,
        run_fingerprint: str,
        log: EventLog,
        heartbeat_seconds: float = 15,
        mirror: Mirror | None = None,
    ):
        if heartbeat_seconds <= 0:
            raise ValueError("Heartbeat interval must be positive")
        self.root, self.run_fingerprint, self.log = root, run_fingerprint, log
        self.heartbeat_seconds, self.mirror = heartbeat_seconds, mirror
        self.root.mkdir(parents=True, exist_ok=True)

    def task(self, name: str, work: Callable[[Path], list[Path]]) -> Path:
        if not name or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in name):
            raise ValueError("Task names must be lowercase identifiers")
        target = self.root / name
        target.mkdir(exist_ok=True)
        checkpoint = target / "checkpoint.json"
        with FileLock(str(target / ".lock"), timeout=0):
            if checkpoint.exists():
                record = json.loads(checkpoint.read_text())
                if record["fingerprint"] != self.run_fingerprint:
                    raise ValueError("Run inputs changed; choose a new run directory")
                valid = record.get("outputs") and all(
                    (target / p).is_file() and digest(target / p) == sha
                    for p, sha in record["outputs"].items()
                )
                if valid:
                    self.log.emit("task_reused", task=name)
                    self._replicate(target, record)
                    return target
                self.log.emit("checkpoint_invalid", task=name)
            stop = threading.Event()
            started = time.monotonic()

            def heartbeat() -> None:
                while not stop.wait(self.heartbeat_seconds):
                    self.log.emit(
                        "heartbeat",
                        task=name,
                        task_elapsed_seconds=round(time.monotonic() - started, 3),
                    )

            thread = threading.Thread(target=heartbeat, daemon=True)
            self.log.emit("task_started", task=name)
            thread.start()
            try:
                outputs = work(target)
                if not outputs or any(not p.is_file() for p in outputs):
                    raise ValueError("Task did not produce its declared outputs")
                record = {
                    "fingerprint": self.run_fingerprint,
                    "completed_at": datetime.now(UTC).isoformat(),
                    "elapsed_seconds": time.monotonic() - started,
                    "outputs": {str(p.relative_to(target)): digest(p) for p in outputs},
                }
                atomic_json(checkpoint, record)
                self._replicate(target, record)
                self.log.emit(
                    "task_completed",
                    task=name,
                    task_elapsed_seconds=round(time.monotonic() - started, 3),
                )
            except BaseException as error:
                self.log.emit(
                    "task_failed",
                    task=name,
                    error_type=type(error).__name__,
                    error=str(error),
                    task_elapsed_seconds=time.monotonic() - started,
                )
                raise
            finally:
                stop.set()
                thread.join()
        return target

    def _replicate(self, target: Path, record: dict[str, Any]) -> None:
        if self.mirror:
            for relative in [*record["outputs"], "checkpoint.json"]:
                path = target / relative
                self.mirror.upload(path, str(path.relative_to(self.root)))
            self.mirror.upload(self.log.path, "events.jsonl")
            self.log.emit("task_uploaded", task=target.name)


def runtime_identity() -> dict[str, str]:
    from importlib.metadata import version

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        **{
            name: version(name)
            for name in ["numpy", "pandas", "scipy", "scikit-learn", "pyarrow", "joblib"]
        },
    }
