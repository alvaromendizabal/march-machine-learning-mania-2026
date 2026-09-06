"""Validate the research notebook and optionally execute it in its Jupyter kernel."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    notebook = nbformat.read(root / "notebooks/05_feature_research.ipynb", as_version=4)
    nbformat.validate(notebook)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            compile(cell.source, f"notebook-cell-{index}", "exec")
    if args.execute:
        NotebookClient(
            notebook,
            timeout=120,
            kernel_name="march-mania",
            resources={"metadata": {"path": str(root)}},
        ).execute()
        output = root / "outputs/validation/05_feature_research.ipynb"
        output.parent.mkdir(parents=True, exist_ok=True)
        nbformat.write(notebook, output)
    print("Research notebook validation passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
