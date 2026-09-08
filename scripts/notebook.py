"""Validate, execute, resume and publish the canonical review notebooks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nbformat

from march_mania.publication.notebooks import NOTEBOOKS, execute_notebooks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--publish", action="store_true", help="Publish verified executed outputs")
    parser.add_argument(
        "--timeout", type=int, default=120, help="Per-cell seconds; use 1800 for training"
    )
    parser.add_argument("--s3", help="Optional private S3 prefix for notebook checkpoints")
    args = parser.parse_args()
    if (args.publish or args.s3) and not args.execute:
        parser.error("--publish and --s3 require --execute")
    root = Path(__file__).resolve().parents[1]
    if args.execute:
        execute_notebooks(root, publish=args.publish, s3=args.s3, timeout=args.timeout)
    else:
        for name in NOTEBOOKS:
            notebook = nbformat.read(root / "notebooks" / name, as_version=4)
            nbformat.validate(notebook)
            for index, cell in enumerate(notebook.cells):
                if cell.cell_type == "code":
                    compile(cell.source, f"{name}:cell-{index}", "exec")
    return 0


if __name__ == "__main__":
    sys.exit(main())
