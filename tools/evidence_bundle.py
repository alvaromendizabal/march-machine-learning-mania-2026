"""Build or independently verify a finite, closed public CI evidence bundle.

Verification is standard-library-only and never executes archived source. Build
collects this repository's already-produced outputs; it does not run notebooks.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from march_mania.publication.evidence_bundle import (  # noqa: E402
    MAX_BUNDLE_BYTES,
    RUNTIME_PATHS,
    VALIDATION,
    EvidenceBundleError,
    build_public_bundle,
    canonical,
    git_tree,
    read_zip,
    require,
    safe_name,
    strict_json,
    verify_public_bundle,
)


def regular_bytes(path: Path) -> bytes:
    require(not path.is_symlink() and stat.S_ISREG(path.stat().st_mode), "regular retained body")
    return path.read_bytes()


def build(root: Path, job: str, destination: Path) -> dict:
    """Collect actual public job outputs, then independently close and inspect them."""
    require(os.environ.get("GITHUB_JOB") == job, "actual CI job matches requested role")
    directory = root / VALIDATION
    require(directory.is_dir() and not directory.is_symlink(), "actual validation output directory")
    payloads = {}
    for path in sorted(directory.rglob("*")):
        require(not path.is_symlink(), "no symlink in validation collection")
        if path.is_dir():
            continue
        name = safe_name(path.relative_to(root).as_posix())
        payloads[name] = regular_bytes(path)
    for name in RUNTIME_PATHS:
        payloads[name] = regular_bytes(root / name)
    source, modes, comment = read_zip(payloads[VALIDATION + "source.zip"], source=True)
    identity = {
        "repository": os.environ.get("GITHUB_REPOSITORY"),
        "source_commit": comment.decode("ascii"),
        "source_tree": git_tree(source, modes),
        "reviewed_head_commit": os.environ.get("REVIEWED_HEAD_SHA"),
        "workflow_run_id": int(os.environ.get("GITHUB_RUN_ID", "0")),
        "run_attempt": int(os.environ.get("GITHUB_RUN_ATTEMPT", "0")),
        "workflow_name": os.environ.get("GITHUB_WORKFLOW"),
        "workflow_path": ".github/workflows/ci.yml",
        "event": os.environ.get("GITHUB_EVENT_NAME"),
        "job": job,
    }
    raw, binding = build_public_bundle(payloads, identity)
    result = verify_public_bundle(raw, binding)
    require(len(raw) < MAX_BUNDLE_BYTES, "finite public bundle size")
    # Never blend a new run with an old directory or silently replace evidence.
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "evidence_bundle.zip").write_bytes(raw)
    (destination / "external_binding.json").write_bytes(canonical(binding))
    (destination / "verification.json").write_bytes(canonical(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser(
        "build", help="Seal this actual GitHub job's existing public outputs"
    )
    create.add_argument("--job", choices=("quality", "notebook-publication"), required=True)
    create.add_argument("--out-dir", type=Path)
    verify = commands.add_parser(
        "verify", help="Inspect bytes using an independently obtained binding"
    )
    verify.add_argument("--bundle", type=Path, required=True)
    verify.add_argument("--binding", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            destination = args.out_dir or ROOT / "outputs/evidence" / args.job
            result = build(ROOT, args.job, destination)
        else:
            binding = strict_json(regular_bytes(args.binding))
            result = verify_public_bundle(regular_bytes(args.bundle), binding)
    except (EvidenceBundleError, OSError, ValueError, TypeError) as error:
        # Do not erase source/diagnostic files or turn a failed bundle into PASS.
        print(
            json.dumps(
                {"status": "FAIL", "error_type": type(error).__name__, "contract": str(error)}
            )
        )
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
