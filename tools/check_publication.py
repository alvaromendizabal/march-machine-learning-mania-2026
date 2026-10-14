"""Check newly published Git blobs for accidental private material.

Run before committing with ``python tools/check_publication.py --staged``.
CI can review an exact commit with ``--base BASE_SHA --head HEAD_SHA``.
The check reads Git objects, not the working tree, and never prints matched values.
It is a focused publication guard, not a claim that all private material or
credentials can be recognized automatically. Existing public recipes are not
classified as private merely because they contain modeling parameters.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

PRIVATE_SUFFIXES = (
    ".pyz",
    ".zip",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".csv.gz",
    ".json.gz",
    ".parquet",
    ".feather",
    ".arrow",
    ".pkl",
    ".pickle",
    ".joblib",
    ".cbm",
    ".pt",
    ".pth",
    ".h5",
    ".keras",
    ".onnx",
    ".npy",
    ".npz",
)
PRIVATE_NAMES = {
    "kaggle.json",
    "credentials.json",
    "credentials",
    "id_rsa",
    "id_ed25519",
    "restored_v155_sha_verified.csv",
    "injury_23_status_weight_and_team_rebuild.json",
    "target_23_injury_and_bpr_source_inventory.json",
    "v19_10stage_closure_and_stop_decision.json",
    "v19_stages_missing_original_sources_and_models.json",
}
PRIVATE_PARTS = {
    "private_backups",
    "raw_supplemental",
    "owner_returns",
    "private_artifacts",
}
PRIVATE_COLUMN_NAMES = {
    "ownedv155p",
    "kalshititleratio",
    "originalkalshibothinformative",
}
SECRET_PATTERNS = (
    re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}"),
    re.compile(r"KGAT_[A-Za-z0-9_-]{25,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"[?&](?:X-Amz-Signature|X-Goog-Signature)=[a-fA-F0-9]{32,}"),
)


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def synthetic_example(path: str, rows: list[dict]) -> bool:
    """Only explicitly scoped authored examples may contain prediction pairs."""
    if not path.startswith(("examples/", "tests/fixtures/")) or not rows:
        return False
    for row in rows:
        lowered = {str(key).lower(): value for key, value in row.items()}
        if lowered.get("scope") != "SYNTHETIC_ONLY":
            return False
        if not str(lowered.get("id", "")).startswith("synthetic_"):
            return False
    return True


def data_reasons(path: str, rows: list[dict]) -> list[str]:
    reasons = []
    fields = {str(key).lower() for row in rows for key in row}
    if fields & PRIVATE_COLUMN_NAMES:
        reasons.append("private source/prediction columns")
    prediction_rows = [row for row in rows if {"id", "pred"} <= {str(key).lower() for key in row}]
    if prediction_rows and not synthetic_example(path, prediction_rows):
        reasons.append("row-level submission probabilities")
    return reasons


def inspect_blob(path: str, content: bytes, *, symlink: bool = False) -> list[str]:
    """Return descriptions only; never return a credential or a private value."""
    relative = PurePosixPath(path)
    name, lower = relative.name.lower(), path.lower()
    reasons = []
    if symlink:
        reasons.append("symlink requires separate publication review")
    if lower.endswith(PRIVATE_SUFFIXES):
        reasons.append("private archive, data, or model artifact extension")
    if name in PRIVATE_NAMES or name == ".env" or name.startswith(".env."):
        reasons.append("private artifact or credential filename")
    if set(relative.parts) & PRIVATE_PARTS:
        reasons.append("private artifact directory")
    if name.startswith("march_") and ("_return_" in name or name.endswith(".pyz")):
        reasons.append("owner execution artifact filename")
    # Images and other existing public binary assets have no text content to scan.
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return reasons
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        reasons.append("credential-like material or signed download URL")
    suffix = relative.suffix.lower()
    if suffix == ".csv":
        try:
            reasons.extend(data_reasons(path, list(csv.DictReader(io.StringIO(text)))))
        except csv.Error:
            reasons.append("unreadable CSV publication")
    elif suffix in {".json", ".jsonl", ".ipynb"}:
        try:
            objects = (
                [json.loads(line) for line in text.splitlines() if line.strip()]
                if suffix == ".jsonl"
                else [json.loads(text)]
            )
        except json.JSONDecodeError:
            reasons.append("unreadable structured publication")
        else:
            rows = []
            while objects:
                obj = objects.pop()
                if isinstance(obj, dict):
                    rows.append(obj)
                    objects.extend(obj.values())
                elif isinstance(obj, list):
                    objects.extend(obj)
            reasons.extend(data_reasons(path, rows))
    return sorted(set(reasons))


def review(root: Path, *, base: str | None = None, head: str = "HEAD") -> dict:
    """Review additions/modifications only; do not reinterpret public history."""
    if base is None:
        changed = git(root, "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMRT")
        source = "index"
    else:
        # Resolve refs first so command-line values cannot become Git options.
        base = git(root, "rev-parse", "--verify", f"{base}^{{commit}}").decode().strip()
        head = git(root, "rev-parse", "--verify", f"{head}^{{commit}}").decode().strip()
        changed = git(root, "diff", "--name-only", "-z", "--diff-filter=ACMRT", base, head)
        source = head
    paths = [value.decode("utf-8") for value in changed.split(b"\0") if value]
    findings = []
    for path in paths:
        if base is None:
            metadata = git(root, "ls-files", "--stage", "--", path).split(b" ", 1)[0]
            content = git(root, "show", f":{path}")
        else:
            metadata = git(root, "ls-tree", head, "--", path).split(b" ", 1)[0]
            content = git(root, "show", f"{head}:{path}")
        for reason in inspect_blob(path, content, symlink=metadata == b"120000"):
            findings.append({"path": path, "reason": reason})
    return {
        "status": "FAIL" if findings else "PASS",
        "scope": "changed Git blobs only; focused private-artifact and credential checks",
        "source": source,
        "files_checked": len(paths),
        "findings": findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true")
    mode.add_argument("--base", help="Compare this commit with --head")
    parser.add_argument("--head", default="HEAD", help="Exact proposed commit (default HEAD)")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        result = review(root, base=args.base, head=args.head)
    except (subprocess.CalledProcessError, UnicodeDecodeError) as exc:
        # Git diagnostics can contain operational locators, so keep failure output narrow.
        print(json.dumps({"status": "FAIL", "reason": f"Git review failed: {type(exc).__name__}"}))
        return 1
    print(json.dumps(result, indent=2))
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
