"""Validate an existing 2026 submission and preserve its exact bytes and audit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from march_mania.publication.submission import release_submission


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument(
        "--expected-sha256", help="Recorded prediction-file checksum, when available"
    )
    parser.add_argument("--run-root", type=Path, default=Path("outputs/submission"))
    parser.add_argument("--s3", help="Optional private S3 prefix for the validated release")
    args = parser.parse_args()
    release_submission(
        args.submission,
        args.sample,
        args.run_root,
        expected_sha256=args.expected_sha256,
        s3=args.s3,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
