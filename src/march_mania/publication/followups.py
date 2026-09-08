"""Restore completed notebook-02 follow-ups before delegating to their verified runners."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from filelock import FileLock

from march_mania.publication import capacity, ranking_systems
from march_mania.publication.artifacts import download_input, safe_path
from march_mania.runtime import EventLog

STUDIES: dict[str, Any] = {"feature_capacity": capacity, "ranking_systems": ranking_systems}


def study_stage(root: Path, name: str) -> Path:
    """Only restore the version tied to current public source, config and feature lineage.

    Existing runs retain their per-task recovery behavior. The study runner still
    verifies the actual raw data, matrix and environment before reusing any fit.
    An archive is an input to those checks, never permission to bypass them.
    """
    if name not in STUDIES:
        raise ValueError("Unknown notebook feature follow-up")
    study = STUDIES[name]
    try:
        _, record = study.review(root)
    except FileNotFoundError:
        return study.run(root)
    except ValueError as error:
        # Train mode may intentionally change a protocol. Never restore an old
        # archive for changed source/config; let the runner create a new identity.
        if str(error).startswith("Stale "):
            return study.run(root)
        raise
    key = record["summary"]["fingerprint"]
    if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
        raise ValueError("Invalid follow-up fingerprint")
    base = root / "outputs" / name
    base.mkdir(parents=True, exist_ok=True)
    destination = safe_path(base, key)
    with FileLock(str(base / ".restore.lock"), timeout=0):
        if not destination.exists():
            receipt_name = "capacity" if name == "feature_capacity" else name
            receipt = json.loads((root / "reports/validation" / f"{receipt_name}.json").read_text())
            archive = receipt["archive"]
            if archive.get("status") != "uploaded" or not archive.get("version_id"):
                raise ValueError("A verified versioned archive is required for fresh recovery")
            log = EventLog(base / "recovery.jsonl")
            restored = download_input(
                archive, root / "outputs/followup_inputs" / name / key, log, complete_run=True
            )
            manifest = json.loads((restored / "manifest.json").read_text())
            summary = json.loads((restored / "summary.json").read_text())
            if manifest != record["manifest"] or summary != record["summary"]:
                raise ValueError("Restored follow-up differs from the declared research lineage")
            restored.replace(destination)
            log.emit("followup_restored", study=name, fingerprint=key)
    return study.run(root)
