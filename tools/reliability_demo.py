"""An independently authored, synthetic checkpoint and timing demonstration.

This small public example exercises reliable execution without distributing the
private acquisition adapters or forecasting recipes. It performs no network I/O
and fits no model. Hashes detect accidental corruption; they are not signatures.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

SCOPE = "SYNTHETIC_ONLY"
CUTOFF = "2025-03-01T12:00:00+00:00"
OBSERVATIONS = (
    {
        "id": "synthetic_alpha",
        "available_at": "2025-02-28T10:00:00+00:00",
        "value": 12,
        "scope": SCOPE,
    },
    {
        "id": "synthetic_beta",
        "available_at": "2025-03-01T13:00:00+00:00",
        "value": 7,
        "scope": SCOPE,
    },
    {"id": "synthetic_gamma", "available_at": None, "value": 4, "scope": SCOPE},
    {
        "id": "synthetic_delta",
        "available_at": "2025-03-01T11:00:00+00:00",
        "value": 9,
        "scope": SCOPE,
    },
)


class IntegrityError(ValueError):
    """Committed data no longer agrees with its recorded content or inputs."""


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def commit(path: Path, value: object) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(canonical(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_input(observation: dict, cutoff: str) -> None:
    if set(observation) != {"id", "available_at", "value", "scope"}:
        raise ValueError("Unknown observation fields")
    if observation["scope"] != SCOPE:
        raise ValueError("Only explicitly synthetic observations are supported")
    identity = observation["id"]
    if not isinstance(identity, str) or not identity.startswith("synthetic_"):
        raise ValueError("Invalid synthetic identity")
    if not identity.replace("_", "").isalnum() or type(observation["value"]) is not int:
        raise ValueError("Invalid identity or value")
    if datetime.fromisoformat(cutoff).tzinfo is None:
        raise ValueError("Cutoff requires a timezone")
    stamp = observation["available_at"]
    if stamp is not None and datetime.fromisoformat(stamp).tzinfo is None:
        raise ValueError("Availability requires a timezone")


def qualify(observation: dict, cutoff: str) -> dict:
    validate_input(observation, cutoff)
    stamp = observation["available_at"]
    if stamp is None:
        status = "UNKNOWN_TIMING"
    else:
        eligible = datetime.fromisoformat(stamp) <= datetime.fromisoformat(cutoff)
        status = "ELIGIBLE" if eligible else "LATE_SOURCE"
    return {
        "id": observation["id"],
        "scope": SCOPE,
        "status": status,
        "value": observation["value"],
    }


def reuse(path: Path, input_digest: str, observation: dict) -> dict:
    if path.is_symlink():
        raise IntegrityError("Checkpoint cannot be a symlink")
    try:
        saved = json.loads(path.read_text())
        if set(saved) != {"unit", "unit_sha256"}:
            raise ValueError("Envelope schema changed")
        unit = saved["unit"]
        if set(unit) != {"schema", "input_sha256", "result"}:
            raise ValueError("Unit schema changed")
        if unit["schema"] != 1 or saved["unit_sha256"] != digest(unit):
            raise ValueError("Content digest changed")
        if unit["input_sha256"] != input_digest:
            raise ValueError("Input identity changed")
        result = unit["result"]
        if set(result) != {"id", "scope", "status", "value"}:
            raise ValueError("Result schema changed")
        if (result["id"], result["scope"], result["value"]) != (
            observation["id"],
            SCOPE,
            observation["value"],
        ):
            raise ValueError("Result identity changed")
        if result["status"] not in {"ELIGIBLE", "LATE_SOURCE", "UNKNOWN_TIMING"}:
            raise ValueError("Unknown status")
        return result
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise IntegrityError("Checkpoint content or input identity failed verification") from exc


def run(directory: Path, *, stop_after=None, observations=OBSERVATIONS, cutoff=CUTOFF) -> dict:
    """Compute uncached units only; verify and load committed results on resume."""
    directory = Path(directory)
    if directory.is_symlink():
        raise IntegrityError("Checkpoint directory cannot be a symlink")
    directory.mkdir(parents=True, exist_ok=True)
    if stop_after is not None and (type(stop_after) is not int or stop_after < 1):
        raise ValueError("stop_after must be a positive integer")
    observations = tuple(observations)
    for row in observations:
        validate_input(row, cutoff)
    if len({row["id"] for row in observations}) != len(observations):
        raise ValueError("Duplicate source identity")
    lock = directory / "run.lock"
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise IntegrityError("Another invocation owns this checkpoint directory") from exc
    os.close(descriptor)
    computed, reused, results = 0, 0, []
    try:
        for observation in observations:
            path = directory / (observation["id"] + ".json")
            input_digest = digest({"observation": observation, "cutoff": cutoff})
            if path.exists() or path.is_symlink():
                result = reuse(path, input_digest, observation)
                reused += 1
            else:
                result = qualify(observation, cutoff)
                unit = {"schema": 1, "input_sha256": input_digest, "result": result}
                commit(path, {"unit": unit, "unit_sha256": digest(unit)})
                computed += 1
            results.append(result)
            if (
                stop_after is not None
                and computed >= stop_after
                and len(results) < len(observations)
            ):
                break
        report = {
            "schema": 1,
            "scope": SCOPE,
            "status": "COMPLETE" if len(results) == len(observations) else "INTERRUPTED",
            "planned": len(observations),
            "completed": len(results),
            "computed_this_invocation": computed,
            "reused_this_invocation": reused,
            "results": results,
            "network_requests": 0,
            "model_fits": 0,
        }
        commit(directory / "manifest.json", report)
        return report
    finally:
        lock.unlink()


def demonstrate() -> dict:
    with tempfile.TemporaryDirectory(prefix="tournament-review-") as temporary:
        root = Path(temporary)
        early = run(root / "resumed", stop_after=1)
        resumed = run(root / "resumed")
        warm = run(root / "resumed")
        cold = run(root / "cold")
        assert early["status"] == "INTERRUPTED" and early["completed"] == 1
        assert resumed["results"] == cold["results"]
        assert resumed["computed_this_invocation"] == 3 and resumed["reused_this_invocation"] == 1
        assert warm["computed_this_invocation"] == 0 and warm["reused_this_invocation"] == 4
        damaged = root / "resumed" / "synthetic_alpha.json"
        saved = json.loads(damaged.read_text())
        saved["unit"]["result"]["value"] += 1
        damaged.write_bytes(canonical(saved))
        try:
            run(root / "resumed")
        except IntegrityError:
            pass
        else:
            raise AssertionError("Corruption was accepted")
        return {
            "scope": SCOPE,
            "status": "PASS",
            "interrupted_completed": 1,
            "resume_computed": 3,
            "resume_reused": 1,
            "warm_computed": 0,
            "warm_reused": 4,
            "cold_and_resumed_results_identical": True,
            "corruption_rejected": True,
            "qualification_counts": {
                status: sum(row["status"] == status for row in cold["results"])
                for status in ("ELIGIBLE", "LATE_SOURCE", "UNKNOWN_TIMING")
            },
            "network_requests": 0,
            "model_fits": 0,
        }


if __name__ == "__main__":
    print(json.dumps(demonstrate(), indent=2))
