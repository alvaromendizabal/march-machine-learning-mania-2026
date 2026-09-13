"""Review, restore or generate the frozen prediction release and prepare downloads."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any

import pandas as pd

from march_mania.publication import production, production_inputs, production_release
from march_mania.publication.artifacts import safe_path, verified_write
from march_mania.runtime import EventLog, TaskStore, atomic_json, digest, fingerprint

REFERENCE = "m_rank_logistic__w_logistic"


def package(root: Path, run: Path) -> dict[str, Any]:
    """Preserve the fifty recorded CSV byte sequences in one resumable download."""
    public = root / production.REPORT
    summary = production_release.check(root)
    hashes = production_release.verify_tasks(run, summary["fingerprint"])
    files = pd.read_csv(public / "submission_manifest.csv")
    candidates = files.candidate_id.tolist()
    if len(set(candidates)) != len(candidates) or any(
        not isinstance(name, str) or re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name) is None
        for name in candidates
    ):
        raise ValueError("Candidate IDs must be unique, safe lowercase filenames")
    downloads = files.copy()
    downloads["source_path"] = downloads["path"]
    downloads["path"] = downloads.candidate_id + ".csv"
    manifest_bytes = downloads.to_csv(index=False, lineterminator="\n").encode("utf-8")
    expected = dict(zip(files.candidate_id, files.sha256, strict=True))
    if hashes != expected or REFERENCE not in hashes:
        raise ValueError("Restored files differ from the public prediction release")
    inputs = {
        "production_fingerprint": summary["fingerprint"],
        "script_sha256": digest(Path(__file__)),
        "manifest_sha256": digest(public / "submission_manifest.csv"),
        "recipe_sha256": digest(public / "recipe.json"),
        "files": hashes,
        "download_layout": "flat-candidate-csv-v1",
    }
    folder = root / "outputs/prediction_delivery" / fingerprint(inputs)
    log = EventLog(folder / "events.jsonl")
    store = TaskStore(folder, fingerprint(inputs), log, heartbeat_seconds=15)

    def work(target: Path) -> list[Path]:
        destination = target / "prediction_portfolio.zip"
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            for row in files.itertuples():
                path = safe_path(run, str(row.path))
                contents = path.read_bytes()
                if digest(path) != row.sha256 or len(contents) != row.bytes:
                    raise ValueError("A prediction file changed while preparing downloads")
                archive.writestr(f"{row.candidate_id}.csv", contents)
            archive.writestr("submission_manifest.csv", manifest_bytes)
            archive.write(public / "recipe.json", "recipe.json")
        with zipfile.ZipFile(destination) as archive:
            if archive.testzip() is not None:
                raise ValueError("Prediction download archive failed its CRC check")
            import hashlib

            for name, expected_hash in hashes.items():
                if hashlib.sha256(archive.read(f"{name}.csv")).hexdigest() != expected_hash:
                    raise ValueError("Prediction download differs from its fitted-model output")
        atomic_json(target / "receipt.json", {"inputs": inputs, "sha256": digest(destination)})
        return [destination, target / "receipt.json"]

    output = store.task("package", work)
    # Publish only fully verified completed outputs, preserving every CSV byte.
    bundle = root / "submissions/prediction_portfolio.zip"
    verified_write(bundle, (output / bundle.name).read_bytes(), digest(output / bundle.name))
    row = files.set_index("candidate_id").loc[REFERENCE]
    reference = root / "submissions/submission.csv"
    verified_write(reference, safe_path(run, str(row.path)).read_bytes(), str(row.sha256))
    result = {
        **summary,
        "reference_candidate": REFERENCE,
        "reference_file": str(reference.relative_to(root)),
        "reference_sha256": str(row.sha256),
        "download_archive": str(bundle.relative_to(root)),
        "download_sha256": digest(bundle),
        "download_layout": "flat-candidate-csv-v1",
    }
    atomic_json(folder / "summary.json", result)
    log.emit("delivery_completed", submission_files=len(files), reference_candidate=REFERENCE)
    return result


def deliver(root: Path, action: str = "review", archive: Path | None = None) -> dict[str, Any]:
    """Review is offline; restore performs zero fits; generate reuses valid checkpoints."""
    if action not in {"review", "restore", "generate"}:
        raise ValueError("Choose review, restore or generate")
    if archive is not None and action != "restore":
        raise ValueError("An explicit archive is supported only for restore")
    summary = production_release.check(root)
    if action == "review":
        return summary
    destination = root / "outputs/prediction_production"
    if action == "restore":
        run = production_release.recover(root, destination, archive)
    else:
        inputs = root / "outputs/production_inputs"
        try:
            production_inputs.verify(root, inputs)
        except FileNotFoundError:
            production_inputs.restore(root, inputs)
        run = production.run(root, inputs, destination)
    return package(root, run)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=["review", "restore", "generate"], default="review")
    parser.add_argument("--archive", type=Path, help="Optional exact archive already downloaded")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(deliver(root, args.action, args.archive), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
