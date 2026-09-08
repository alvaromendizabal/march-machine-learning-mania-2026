"""Execute canonical review notebooks with verified resume and atomic publication."""

from __future__ import annotations

import copy
import os
import re
import sys
import time
from importlib.metadata import distributions
from pathlib import Path
from typing import Any

import nbformat
from filelock import FileLock
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

from march_mania.runtime import EventLog, Mirror, TaskStore, atomic_json, digest, fingerprint

NOTEBOOKS = (
    "00_data_audit_and_preparation.ipynb",
    "01_split_protocol_and_pre_tournament_snapshots.ipynb",
    "02_feature_store_and_diagnostics.ipynb",
    "03_model_comparison_and_diagnostics.ipynb",
    "04_locked_benchmark_and_final_submission.ipynb",
    "05_feature_research.ipynb",
)


def definition(notebook: Any) -> dict[str, Any]:
    """Ignore execution-only state, not source, attachments, or execution-control tags."""
    result = copy.deepcopy(dict(notebook))
    result["metadata"] = {
        key: value
        for key, value in result.get("metadata", {}).items()
        if key not in {"language_info", "widgets"}
    }
    for cell in result["cells"]:
        cell.pop("execution_count", None)
        cell.pop("outputs", None)
        cell.get("metadata", {}).pop("execution", None)
    return result


def dependency_hashes(root: Path) -> dict[str, str]:
    """Conservatively fingerprint code and evidence, including available local runs.

    Log files, fitted binaries and the publication cache are not notebook inputs.
    Actual table bytes are hashed; a stale manifest cannot conceal changed data.
    """
    folders = [
        root / name for name in ("src", "scripts", "configs", "reports", "data", "submissions")
    ]
    folders.extend(
        root / "outputs" / name
        for name in (
            "data_review",
            "feature_store",
            "model_comparison",
            "benchmark",
            "research",
            "final_predictions",
        )
    )
    paths = [root / name for name in ("pyproject.toml", "uv.lock", ".python-version")]
    suffixes = {".py", ".csv", ".parquet", ".json", ".yaml", ".yml", ".md"}
    for folder in folders:
        paths.extend(
            path
            for path in folder.rglob("*")
            if path.is_file()
            and path.suffix in suffixes
            and not any(part in {"logs", "__pycache__"} for part in path.parts)
        )
    return {
        str(path.relative_to(root)): digest(path) for path in sorted(set(paths)) if path.is_file()
    }


def validate_execution(notebook: Any) -> None:
    """Reject skipped code, error outputs and emitted Python warnings before publication."""
    nbformat.validate(notebook)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type != "code" or not cell.source.strip():
            continue
        if type(cell.execution_count) is not int or cell.execution_count < 1:
            raise ValueError(f"Code cell {index} was not executed")
        for output in cell.outputs:
            if output.output_type == "error":
                raise ValueError(f"Code cell {index} contains an error")
            if output.output_type == "stream" and re.search(
                r"\b[A-Za-z]*Warning:", output.get("text", "")
            ):
                raise ValueError(
                    f"Code cell {index} emitted a warning; resolve it before publishing"
                )


def _execute_notebooks(
    root: Path,
    *,
    names: tuple[str, ...] = NOTEBOOKS,
    publish: bool = False,
    kernel_name: str = "march-mania",
    heartbeat_seconds: float = 15,
    timeout: int = 120,
    s3: str | None = None,
    client_factory: Any = NotebookClient,
) -> dict[str, Any]:
    """Resume whole completed notebooks, never individual cells without kernel state.

    A failed notebook retains its diagnostic output but cannot replace a published
    notebook or receive a successful checkpoint. TaskStore retries incomplete S3
    replication on resume without repeating successful notebook execution.
    """
    if not names or len(set(names)) != len(names) or any(name not in NOTEBOOKS for name in names):
        raise ValueError("Select unique canonical notebook filenames")
    if timeout <= 0:
        raise ValueError("A positive per-cell timeout is required")
    root = root.resolve()
    destination = root / "outputs/validation"
    log = EventLog(destination / "notebooks.jsonl")
    environment = {
        "python": sys.version,
        "kernel": KernelSpecManager().get_kernel_spec(kernel_name).to_dict(),
        "packages": sorted(
            (item.metadata["Name"], item.version)
            for item in distributions()
            if item.metadata["Name"]
        ),
    }
    records: list[dict[str, Any]] = []
    started = log.started
    log.emit("run_started", notebooks=len(names), publish=publish)
    try:
        for position, name in enumerate(names, start=1):
            records.append(
                _execute_one(
                    root,
                    name,
                    position,
                    log,
                    environment,
                    publish=publish,
                    kernel_name=kernel_name,
                    heartbeat_seconds=heartbeat_seconds,
                    timeout=timeout,
                    s3=s3,
                    client_factory=client_factory,
                )
            )
            atomic_json(
                destination / "notebook_execution.json", {"status": "running", "notebooks": records}
            )
            log.emit("notebook_completed", notebook=name, completed=position, total=len(names))
    except BaseException as error:
        atomic_json(
            destination / "notebook_execution.json",
            {
                "status": "failed",
                "notebooks": records,
                "error_type": type(error).__name__,
                "error": str(error),
                "elapsed_seconds": time.monotonic() - started,
            },
        )
        log.emit("run_failed", error_type=type(error).__name__, error=str(error))
        raise
    result = {
        "status": "completed",
        "notebooks": records,
        "elapsed_seconds": time.monotonic() - started,
    }
    atomic_json(destination / "notebook_execution.json", result)
    log.emit("run_completed", notebooks=len(records))
    return result


def _execute_one(
    root: Path,
    name: str,
    position: int,
    log: EventLog,
    environment: dict[str, Any],
    *,
    publish: bool,
    kernel_name: str,
    heartbeat_seconds: float,
    timeout: int,
    s3: str | None,
    client_factory: Any,
) -> dict[str, Any]:
    destination = root / "outputs/validation"
    source = root / "notebooks" / name
    notebook = nbformat.read(source, as_version=4)
    nbformat.validate(notebook)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            compile(cell.source, f"{name}:cell-{index}", "exec")
    inputs = {
        "notebook": definition(notebook),
        "dependencies": dependency_hashes(root),
        "environment": environment,
        "execution_mode": os.environ.get("MARCH_NOTEBOOK_MODE", "review"),
    }
    key = fingerprint(inputs)
    cache = destination / "notebook_runs" / key
    mirror = Mirror(f"{s3.rstrip('/')}/{key}") if s3 else None
    store = TaskStore(cache, key, log, heartbeat_seconds, mirror)
    cell_started: dict[int, float] = {}

    def on_start(cell: Any, cell_index: int) -> None:
        cell_started[cell_index] = time.monotonic()
        log.emit("cell_started", notebook=name, cell=cell_index, position=position)

    def on_end(cell: Any, cell_index: int, execute_reply: Any) -> None:
        status = execute_reply.get("content", {}).get("status", "unknown")
        log.emit(
            "cell_finished",
            notebook=name,
            cell=cell_index,
            status=status,
            cell_elapsed_seconds=time.monotonic() - cell_started[cell_index],
        )

    def work(target: Path) -> list[Path]:
        output = target / name
        atomic_json(target / "inputs.json", inputs)
        try:
            client_factory(
                notebook,
                timeout=timeout,
                kernel_name=kernel_name,
                allow_errors=False,
                force_raise_errors=True,
                resources={"metadata": {"path": str(root)}},
                on_cell_execute=on_start,
                on_cell_executed=on_end,
            ).execute()
            validate_execution(notebook)
        finally:
            # Preserve diagnostic cell state on failure, but do not publish it.
            atomic_json(output, dict(notebook))
        return [output, target / "inputs.json"]

    target = store.task(Path(name).stem, work)
    completed = nbformat.read(target / name, as_version=4)
    validate_execution(completed)
    if definition(completed) != definition(notebook):
        raise ValueError("Executed notebook source differs from the requested source")
    atomic_json(destination / name, dict(completed))
    if publish:
        atomic_json(source, dict(completed))
    return {
        "notebook": name,
        "fingerprint": key,
        "sha256": digest(destination / name),
        "status": "completed",
        "code_cells": sum(c.cell_type == "code" for c in completed.cells),
    }


def execute_notebooks(root: Path, **kwargs: Any) -> dict[str, Any]:
    """Serialize notebook publication so concurrent runs cannot race on canonical files."""
    destination = root / "outputs/validation"
    destination.mkdir(parents=True, exist_ok=True)
    with FileLock(str(destination / "publication.lock"), timeout=0):
        return _execute_notebooks(root, **kwargs)
