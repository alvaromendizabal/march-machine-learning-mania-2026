"""Validate the research notebook and optionally execute it in its Jupyter kernel."""

from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

from march_mania.runtime import EventLog


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    log = EventLog(root / "outputs/validation/notebooks.jsonl")
    stop = threading.Event()

    def heartbeat() -> None:
        while not stop.wait(15):
            log.emit("heartbeat", task="notebook_execution")

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        for name in ["02_feature_store_and_diagnostics.ipynb", "05_feature_research.ipynb"]:
            started = time.monotonic()
            log.emit("notebook_started", notebook=name)
            notebook = nbformat.read(root / "notebooks" / name, as_version=4)
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
                output = root / "outputs/validation" / name
                output.parent.mkdir(parents=True, exist_ok=True)
                nbformat.write(notebook, output)
            log.emit(
                "notebook_completed", notebook=name, task_elapsed_seconds=time.monotonic() - started
            )
    finally:
        stop.set()
        thread.join()
    return 0


if __name__ == "__main__":
    sys.exit(main())
