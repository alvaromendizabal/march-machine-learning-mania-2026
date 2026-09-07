"""Audit and durably package an existing prediction file against Kaggle's template.

This module never invents probabilities, promotes a model, or submits to Kaggle.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from march_mania.runtime import EventLog, Mirror, TaskStore, atomic_json, digest, fingerprint


def validate_submission(predictions: pd.DataFrame, sample: pd.DataFrame) -> dict[str, Any]:
    for name, frame in (("predictions", predictions), ("sample", sample)):
        if list(frame.columns) != ["ID", "Pred"] or frame.empty:
            raise ValueError(f"{name}: expected nonempty ID,Pred columns in that order")
        if frame.ID.isna().any() or frame.ID.duplicated().any():
            raise ValueError(f"{name}: missing or duplicate matchup IDs")
        if not frame.ID.map(lambda value: isinstance(value, str)).all():
            raise ValueError(f"{name}: matchup IDs must be strings")
        parsed = frame.ID.str.extract(r"^(2026)_(\d{4})_(\d{4})$")
        if parsed.isna().any().any() or not (parsed[1] < parsed[2]).all():
            raise ValueError(f"{name}: expected 2026 lower-TeamID-first matchups")
    if predictions.ID.tolist() != sample.ID.tolist():
        raise ValueError("Predictions must match every template ID exactly, in template order")
    if not pd.api.types.is_numeric_dtype(predictions.Pred) or pd.api.types.is_bool_dtype(
        predictions.Pred
    ):
        raise ValueError("Probabilities must be numeric, not strings or booleans")
    probabilities = predictions.Pred.to_numpy(dtype=float)
    if (
        not np.isfinite(probabilities).all()
        or not ((0 <= probabilities) & (probabilities <= 1)).all()
    ):
        raise ValueError("Probabilities must be finite and between zero and one")
    return {
        "rows": len(predictions),
        "minimum_probability": float(probabilities.min()),
        "maximum_probability": float(probabilities.max()),
        "exact_zero_or_one": int(((probabilities == 0) | (probabilities == 1)).sum()),
        "template_order_verified": True,
        "prediction_meaning": "Probability that the lower-TeamID team wins",
    }


def release_submission(
    submission: Path,
    sample: Path,
    run_root: Path,
    *,
    expected_sha256: str | None = None,
    s3: str | None = None,
) -> Path:
    """Commit a checksum-verified release; resume re-verifies files and S3 replication."""
    input_hash = digest(submission)
    if expected_sha256 is not None and input_hash != expected_sha256:
        raise ValueError("Submission checksum differs from the recorded model manifest")
    inputs = {
        "submission_sha256": input_hash,
        "sample_sha256": digest(sample),
        "implementation_sha256": digest(Path(__file__)),
    }
    key = fingerprint(inputs)
    root = run_root / key
    log = EventLog(root / "events.jsonl")
    store = TaskStore(root, key, log, mirror=Mirror(f"{s3.rstrip('/')}/{key}") if s3 else None)

    def work(target: Path) -> list[Path]:
        # Preserve exact CSV bytes; a pandas round trip would change the recorded hash.
        output = target / "submission.csv"
        temporary = target / f".{uuid.uuid4().hex}.tmp"
        try:
            with submission.open("rb") as source, temporary.open("wb") as destination:
                while chunk := source.read(1024 * 1024):
                    destination.write(chunk)
                destination.flush()
                os.fsync(destination.fileno())
            if digest(temporary) != input_hash:
                raise ValueError("Submission changed while packaging")
            audit = validate_submission(pd.read_csv(temporary), pd.read_csv(sample))
            if digest(sample) != inputs["sample_sha256"]:
                raise ValueError("Template changed while validating")
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
        audit.update(
            {
                "status": "validated",
                "inputs": inputs,
                "kaggle_submission_sent": False,
                "competition_status": "Deadline: 2026-03-19T16:00:00Z; retrospective release",
            }
        )
        atomic_json(target / "audit.json", audit)
        return [output, target / "audit.json"]

    target = store.task("release", work)
    atomic_json(run_root / "latest.json", {"fingerprint": key, "directory": key})
    log.emit("run_completed", submission=str(target / "submission.csv"))
    return target


def verify_text_evidence(path: Path, expected_sha256: str) -> str:
    """Verify recorded bytes, permitting only Git's documented CRLF-to-LF conversion."""
    import hashlib

    contents = path.read_bytes()
    if hashlib.sha256(contents).hexdigest() == expected_sha256:
        return "exact recorded bytes"
    windows_bytes = contents.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    if hashlib.sha256(windows_bytes).hexdigest() == expected_sha256:
        return "recorded Windows bytes; Git-normalized line endings"
    raise ValueError(f"Historical evidence checksum mismatch: {path.name}")
