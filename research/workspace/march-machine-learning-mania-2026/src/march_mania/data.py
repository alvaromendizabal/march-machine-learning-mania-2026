"""Download the official Kaggle competition into an immutable, resumable snapshot."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

from filelock import FileLock

from march_mania.features import read_official
from march_mania.runtime import EventLog, Mirror, TaskStore, atomic_json, digest, fingerprint

COMPETITION = "march-machine-learning-mania-2026"


def authenticate() -> Any:
    """Use Kaggle's existing runtime credentials; never print or copy credential values."""
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            from kaggle.api.kaggle_api_extended import KaggleApi

            api = KaggleApi()
            api.authenticate()
        return api
    except (Exception, SystemExit):
        raise RuntimeError(
            "Kaggle authentication failed. Use the existing Studio credentials or run "
            ".venv/bin/kaggle auth login in Studio."
        ) from None


def list_files(api: Any) -> list[dict[str, Any]]:
    """Exhaust every page; freeze file names, sizes and release timestamps."""
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    token = None
    while True:
        try:
            response = api.competition_list_files(COMPETITION, page_token=token, page_size=200)
        except Exception:
            raise RuntimeError(
                "Kaggle file listing failed. Verify runtime authentication "
                "and competition data access."
            ) from None
        for item in response.files:
            name = str(item.name)
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name or not path.name:
                raise ValueError("Unsafe competition file path")
            size = getattr(item, "total_bytes", getattr(item, "totalBytes", None))
            created = getattr(item, "creation_date", getattr(item, "creationDate", None))
            if size is None or int(size) < 0:
                raise ValueError("Missing competition file size")
            records.append({"name": name, "bytes": int(size), "created_at": str(created)})
        token = response.next_page_token
        if not token:
            break
        if token in seen:
            raise ValueError("Repeated Kaggle pagination token")
        seen.add(token)
    names = [PurePosixPath(r["name"]).name for r in records]
    if not records or len(names) != len(set(names)):
        raise ValueError("Empty competition or duplicate file basenames")
    return sorted(records, key=lambda r: r["name"])


def unpack_file(download: Path, name: str, expected_bytes: int, target: Path) -> Path:
    """Handle CSV or ZIP responses, validating CRC, names and uncompressed size."""
    expected_name = PurePosixPath(name).name
    candidates = [
        p for p in download.rglob("*") if p.is_file() and not p.name.endswith(".kaggle-partial")
    ]
    direct = download / name
    temporary = target / ("." + expected_name + ".tmp")
    output = target / expected_name
    try:
        if direct.is_file() and not zipfile.is_zipfile(direct):
            shutil.copyfile(direct, temporary)
        else:
            archives = [p for p in candidates if zipfile.is_zipfile(p)]
            if len(archives) != 1:
                raise ValueError("Expected one downloaded file or ZIP")
            with zipfile.ZipFile(archives[0]) as archive:
                entries = [i for i in archive.infolist() if not i.is_dir()]
                if len(entries) != 1 or PurePosixPath(entries[0].filename).name != expected_name:
                    raise ValueError("Archive does not match the requested file")
                if entries[0].file_size != expected_bytes:
                    raise ValueError("Archive size differs from the frozen Kaggle listing")
                # The destination is constructed locally; ZIP paths are never extracted.
                with archive.open(entries[0]) as source, temporary.open("wb") as destination:
                    shutil.copyfileobj(source, destination)
        if temporary.stat().st_size != expected_bytes:
            raise ValueError("Downloaded size differs from the frozen Kaggle listing")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return output


def run(output: Path, mirror_uri: str | None = None, api: Any = None) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    with FileLock(str(output / ".run.lock"), timeout=0):
        log = EventLog(output / "events.jsonl")
        log.emit("download_started", competition=COMPETITION)
        manifest = output / "manifest.json"
        if manifest.exists():
            record = json.loads(manifest.read_text())
            if (
                record["competition"] != COMPETITION
                or fingerprint(record["files"]) != record["fingerprint"]
            ):
                raise ValueError("Invalid download manifest")
            files = record["files"]
        else:
            api = api if api is not None else authenticate()
            files = list_files(api)
            record = {
                "competition": COMPETITION,
                "files": files,
                "fingerprint": fingerprint(files),
                "retrieved_at": datetime.now(UTC).isoformat(),
                "source": "Kaggle competition API",
                "client_version": "2.2.4",
            }
            atomic_json(manifest, record)
        run_hash = record["fingerprint"]
        mirror = Mirror(mirror_uri.rstrip("/") + "/" + run_hash) if mirror_uri else None
        store = TaskStore(output, run_hash, log, 15, mirror)
        raw = output / "raw"
        raw.mkdir(exist_ok=True)
        hashes = {}
        for completed, item in enumerate(files, 1):
            name = PurePosixPath(item["name"]).name

            def download(target: Path, item: dict[str, Any] = item) -> list[Path]:
                nonlocal api
                api = api if api is not None else authenticate()
                staging = target / "download"
                staging.mkdir(exist_ok=True)
                try:
                    # Kaggle's client owns ETag-aware HTTP-range resumption and retries.
                    api.competition_download_file(
                        COMPETITION, item["name"], path=str(staging), force=False, quiet=True
                    )
                except Exception:
                    raise RuntimeError(
                        "Kaggle download interrupted; rerun the same command to resume."
                    ) from None
                path = unpack_file(staging, item["name"], item["bytes"], target)
                return [path]

            target = store.task("file_" + fingerprint(item)[:16], download)
            source, destination = target / name, raw / name
            expected = digest(source)
            if destination.exists() and digest(destination) != expected:
                raise ValueError(
                    f"Existing raw file changed: {name}; choose a new snapshot directory"
                )
            if not destination.exists():
                temporary = destination.with_name("." + name + ".tmp")
                shutil.copyfile(source, temporary)
                temporary.replace(destination)
            hashes[name] = expected
            if mirror:
                mirror.upload(destination, "raw/" + name)
            log.emit(
                "download_progress",
                file=name,
                completed=completed,
                total=len(files),
                bytes=item["bytes"],
            )
        read_official(raw)
        atomic_json(output / "data_manifest.json", {**record, "sha256": hashes})
        log.emit("data_validated", files=len(files), raw_directory=str(raw))
        summary = {
            "status": "completed",
            "fingerprint": run_hash,
            "files": len(files),
            "raw_directory": str(raw),
            "remote_run_uri": mirror_uri.rstrip("/") + "/" + run_hash if mirror_uri else None,
        }
        # Shared finalizer publishes the completion marker after durable artifacts.
        from march_mania.research import finalize_run

        return finalize_run(output, summary, mirror, log)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/kaggle"))
    parser.add_argument("--s3")
    args = parser.parse_args()
    try:
        run(args.output, args.s3)
        return 0
    except Exception as error:
        EventLog(args.output / "events.jsonl").emit(
            "download_failed", error_type=type(error).__name__, error=str(error)
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
