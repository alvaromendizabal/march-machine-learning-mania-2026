"""Create and restore a checksum-verified portable research run archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from march_mania.runtime import EventLog, digest


def create(run: Path, raw: Path, destination: Path, root: Path) -> None:
    summary = json.loads((run / "summary.json").read_text())
    manifest = json.loads((run / "manifest.json").read_text())
    if summary.get("status") != "completed":
        raise ValueError("Only completed runs can be archived")
    files = {
        "run/" + str(p.relative_to(run)): p
        for p in run.rglob("*")
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(run).parts)
    }
    for prefix, base, inputs in [
        ("raw", raw, manifest["inputs"]["data"]),
        ("source", root, manifest["inputs"]["source"]),
    ]:
        for name, expected in inputs.items():
            path = base / name
            if not path.resolve().is_relative_to(base.resolve()) or digest(path) != expected:
                raise ValueError("An input no longer matches the run manifest")
            files[prefix + "/" + name] = path
    for checkpoint in run.rglob("checkpoint.json"):
        for name, expected in json.loads(checkpoint.read_text())["outputs"].items():
            if digest(checkpoint.parent / name) != expected:
                raise ValueError("A task output no longer matches its checkpoint")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name("." + destination.name + ".tmp")
    log = EventLog(destination.with_suffix(".jsonl"))
    log.emit("archive_started", files=len(files))
    hashes = {}
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for i, (name, path) in enumerate(sorted(files.items()), 1):
                data = path.read_bytes()
                hashes[name] = hashlib.sha256(data).hexdigest()
                archive.writestr(name, data)
                if i % 100 == 0 or i == len(files):
                    log.emit("archive_progress", completed=i, total=len(files))
            archive.writestr(
                "archive_manifest.json",
                json.dumps(
                    {
                        "schema": 1,
                        "created_at": datetime.now(UTC).isoformat(),
                        "run_fingerprint": manifest["fingerprint"],
                        "sha256": hashes,
                    },
                    indent=2,
                ),
            )
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    log.emit("archive_completed", bytes=destination.stat().st_size, sha256=digest(destination))


def restore(source: Path, destination: Path) -> None:
    log = EventLog(destination.parent / (destination.name + ".jsonl"))
    log.emit("restore_started")
    with zipfile.ZipFile(source) as archive:
        manifest = json.loads(archive.read("archive_manifest.json"))
        names = archive.namelist()
        if manifest.get("schema") != 1 or len(names) != len(set(names)):
            raise ValueError("Invalid archive schema or duplicate paths")
        if set(names) != {"archive_manifest.json", *manifest["sha256"]}:
            raise ValueError("Archive members do not match the manifest")
        for i, (name, expected) in enumerate(manifest["sha256"].items(), 1):
            path = destination / name
            if not path.resolve().is_relative_to(destination.resolve()):
                raise ValueError("Unsafe archive path")
            if path.exists():
                if digest(path) != expected:
                    raise ValueError("Existing destination has different contents")
                continue
            data = archive.read(name)  # ZIP CRC verification precedes the SHA-256 check.
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError("Archive SHA-256 mismatch")
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name("." + path.name + ".tmp")
            try:
                temporary.write_bytes(data)
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
            if i % 100 == 0:
                log.emit("restore_progress", completed=i, total=len(manifest["sha256"]))
    log.emit("restore_completed", files=len(manifest["sha256"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pack = sub.add_parser("create")
    pack.add_argument("--run", type=Path, required=True)
    pack.add_argument("--raw", type=Path, required=True)
    pack.add_argument("--destination", type=Path, required=True)
    unpack = sub.add_parser("restore")
    unpack.add_argument("source", type=Path)
    unpack.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "create":
        create(args.run, args.raw, args.destination, Path(__file__).resolve().parents[1])
    else:
        restore(args.source, args.destination)
    return 0


if __name__ == "__main__":
    sys.exit(main())
