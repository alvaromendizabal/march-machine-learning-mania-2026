"""Audit, archive and recover the current prediction portfolio without retraining."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd
from filelock import FileLock

from march_mania.publication import portfolio, production
from march_mania.publication.artifacts import download_input, restore_archive, safe_path
from march_mania.runtime import EventLog, digest, fingerprint


def check(root: Path) -> dict[str, Any]:
    """Verify the portable public evidence without private data or AWS credentials."""
    public = root / production.REPORT
    recipe = json.loads((public / "recipe.json").read_text())
    production.validate_recipe(recipe)
    config = json.loads((root / portfolio.CONFIG).read_text())
    expected = {
        (g, s["id"], s["route"], s["family"])
        for g, streams in config["streams"].items()
        for s in streams
    }
    actual = {(s["Gender"], s["id"], s["route"], s["family"]) for s in recipe["streams"]}
    if expected != actual:
        raise ValueError("Frozen procedures differ from the audited development catalog")
    receipts = json.loads((public / "input_receipts.json").read_text())
    for name, receipt in receipts.items():
        archive = json.loads((root / "reports" / name / "run.json").read_text())["archive"]
        if receipt["archive"] != archive:
            raise ValueError("Frozen input archive differs from current research")
        if set(receipt["sha256"]) != set(production.production_inputs.MEMBERS[name]):
            raise ValueError("Frozen input member inventory changed")
    if set(receipts) != set(production.production_inputs.MEMBERS):
        raise ValueError("Missing frozen input receipts")
    if not (public / "run.json").exists():
        return {
            "status": "frozen",
            "candidate_recipes": len(recipe["pairs"]),
            "submission_files": 0,
        }
    run = json.loads((public / "run.json").read_text())
    if fingerprint(run["inputs"]) != run["fingerprint"]:
        raise ValueError("Production fingerprint changed")
    if run["inputs"]["recipe"] != recipe or run["inputs"]["inputs"] != receipts:
        raise ValueError("Production recipe or input receipts changed")
    for name, expected_hash in run["inputs"]["source"].items():
        if digest(safe_path(root, name)) != expected_hash:
            raise ValueError("Production source changed; preserve and review its lineage")
    for name, expected_hash in run["sha256"].items():
        if digest(safe_path(public, name)) != expected_hash:
            raise ValueError("Published production artifact changed")
    summary = json.loads((public / "summary.json").read_text())
    files = pd.read_csv(public / "submission_manifest.csv")
    routes = pd.read_csv(public / "routes.csv")
    if (
        summary["status"] != "completed"
        or summary["fingerprint"] != run["fingerprint"]
        or len(files) != 50
        or files.candidate_id.nunique() != 50
        or files.sha256.nunique() != 50
        or set(files.candidate_id) != {p["id"] for p in recipe["pairs"]}
        or not files.rows.eq(summary["rows_per_file"]).all()
        or routes.rows.sum() != summary["rows_per_file"]
        or summary["training_max_season"] != 2025
        or summary["future_labels_used"]
        or summary["kaggle_submission_sent"]
    ):
        raise ValueError("Invalid production population, count or temporal contract")
    audits = json.loads((public / "fit_audits.json").read_text())
    if (
        len(audits) != len(recipe["components"]) * 2
        or {(a["component"], a["route"]) for a in audits}
        != {(c, r) for c in recipe["components"] for r in production.ROUTES}
        or sum(a["fitted"] for a in audits) != summary["fitted_models"]
        or any(a["training_max_season"] != 2025 for a in audits)
        or any(
            "seed" in c.lower()
            for a in audits
            if a["route"] == "seed_free"
            for c in a["retained_features"]
        )
    ):
        raise ValueError("Invalid fitted-model inventory")
    if (public / "archive.json").exists():
        record = json.loads((public / "archive.json").read_text())
        if record["fingerprint"] != run["fingerprint"] or record["status"] != "uploaded":
            raise ValueError("Archive belongs to a different production run")
    return summary


def verify_tasks(run: Path, key: str) -> dict[str, str]:
    summary = json.loads((run / "summary.json").read_text())
    if summary["status"] != "completed" or summary["fingerprint"] != key:
        raise ValueError("Only a completed matching production run can be preserved")
    checkpoints = list(run.glob("*/checkpoint.json"))
    expected_count = (
        summary["component_routes"] + summary["prediction_chunks"] + summary["submission_files"] + 1
    )
    if len(checkpoints) != expected_count:
        raise ValueError("Incomplete production checkpoints")
    for checkpoint in checkpoints:
        record = json.loads(checkpoint.read_text())
        if record["fingerprint"] != key or not record["outputs"]:
            raise ValueError("Incompatible production checkpoint")
        for name, expected in record["outputs"].items():
            if digest(safe_path(checkpoint.parent, name)) != expected:
                raise ValueError("A production checkpoint output changed")
    files = pd.read_csv(run / "publication/submission_manifest.csv")
    for row in files.itertuples():
        if digest(safe_path(run, str(row.path))) != row.sha256:
            raise ValueError("A final prediction file changed")
    return dict(zip(files.candidate_id, files.sha256, strict=True))


def pack(root: Path, run: Path, destination: Path) -> dict[str, Any]:
    summary = check(root)
    key = summary["fingerprint"]
    verify_tasks(run, key)
    manifest = json.loads((run / "manifest.json").read_text())
    public = json.loads((root / production.REPORT / "run.json").read_text())
    if manifest != {"fingerprint": key, "inputs": public["inputs"]}:
        raise ValueError("Archive manifest differs from public production lineage")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.resolve().is_relative_to(run.resolve()):
        raise ValueError("Archive destination cannot be inside the run")
    temporary = destination.with_suffix(".tmp")
    files = sorted(
        p
        for p in run.rglob("*")
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(run).parts)
    )
    with FileLock(str(run / ".lock"), timeout=0):
        hashes = {"run/" + str(p.relative_to(run)): digest(p) for p in files}
        try:
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, expected in hashes.items():
                    path = run / name.removeprefix("run/")
                    archive.write(path, name)
                    if digest(path) != expected:
                        raise ValueError("Run changed during archive creation")
                archive.writestr(
                    "archive_manifest.json",
                    json.dumps({"schema": 1, "run_fingerprint": key, "sha256": hashes}, indent=2),
                )
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    return {
        "fingerprint": key,
        "bytes": destination.stat().st_size,
        "sha256": digest(destination),
        "members": len(hashes),
    }


def recover(root: Path, destination: Path, archive: Path | None = None) -> Path:
    """Restore the exact published run; normal generation then reuses its checkpoints."""
    summary = check(root)
    record = json.loads((root / production.REPORT / "archive.json").read_text())
    key = summary["fingerprint"]
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / key
    with FileLock(str(destination / ".recovery.lock"), timeout=0):
        if target.exists():
            verify_tasks(target, key)
            return target
        staging = destination / ".recovery"
        log = EventLog(destination / "recovery.jsonl")
        if archive:
            restore_archive(archive, staging, record["sha256"], complete_run=True)
            restored = staging / "run"
        else:
            restored = download_input(record, staging, log, complete_run=True)
        manifest = json.loads((restored / "manifest.json").read_text())
        public = json.loads((root / production.REPORT / "run.json").read_text())
        if manifest != {"fingerprint": key, "inputs": public["inputs"]}:
            raise ValueError("Restored production lineage differs from the published run")
        verify_tasks(restored, key)
        restored.replace(target)
        shutil.rmtree(staging)
        log.emit(
            "production_restored",
            fingerprint=key,
            checkpoints=len(list(target.glob("*/checkpoint.json"))),
        )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--pack", type=Path, metavar="RUN")
    action.add_argument("--recover", action="store_true")
    parser.add_argument("--destination", type=Path, default=Path("outputs/prediction_production"))
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    if args.check:
        result = check(root)
    elif args.pack:
        if args.archive is None:
            parser.error("--pack requires --archive as the output ZIP path")
        result = pack(root, args.pack, args.archive)
    else:
        result = {"restored": str(recover(root, args.destination, args.archive))}
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
