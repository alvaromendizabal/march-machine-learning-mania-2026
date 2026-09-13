#!/usr/bin/env python3
"""Correct two presentation cells, in place, without changing the experiment.

Usage (in the existing project Python environment):
  python apply_notebook_update.py --kit ~/march_schedule_research
  python apply_notebook_update.py --kit ~/march_schedule_research --verify-only

No downloads, installs, Git writes, cache deletion, or model fits. An isolated
subprocess deliberately blocks Jinja2 while testing BOTH replacement displays.
The original notebook and package manifest are backed up before replacement.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

NOTEBOOK = "04_quality_wins_and_schedule.ipynb"
EXPECTED_SOURCE = {
    "reference/research_workflow.py": "5a556973f36908c6b2b7b683717a4580154f55d3fbeda58e9dcfc2ed8555bcd1",
    "reference/run_round02.py": "e28d267f3cfc72a2a67561135265bc1d4b33370d56016707c6e73d9b98c65fda",
    "reference/shot_features.py": "8d2f2c3bf9d556c0cd899bcb8ad6125fca1b185b04708f1b8c8012cc487f5c4c",
    "run_round04.py": "58149071dbd0cfbd157abd66b4088630723c46f9274816612527d5fa9422d151",
    "schedule_features.py": "c414f6af2a809600afa4fe55d8a4f455a726e6aaecf8333b7dff21378a0d9fc1",
    "schedule_plots.py": "280fe471d2fd8c4f0fe32dd0c95bbe9e7812a0a888d4cf86dbed1803af7b8b28",
    "schedule_workflow.py": "6a89c8950df018e2217e966792dd806c68d2dc896f6e926d0dc35fce44249b1e",
}
EXPRESSIONS = [
    "prior_metrics[['Gender','Season','recipe','brier','delta_vs_anchor']]",
    "metrics[['Gender','Season','recipe','games','train_games','brier','delta_vs_anchor','active_features']]",
]
OLD_LINES = [
    "display(" + expr + ".style.format({'brier':'{:.7f}','delta_vs_anchor':'{:+.7f}'}))"
    for expr in EXPRESSIONS
]
NEW_LINES = [
    "display(" + expr + ".assign(brier=lambda table: table['brier'].map('{:.7f}'.format), "
    "delta_vs_anchor=lambda table: table['delta_vs_anchor'].map('{:+.7f}'.format)))"
    for expr in EXPRESSIONS
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_file(path: Path) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Missing or symlinked file: {path}. Nothing needs deleting.")
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError(f"File exceeds the bounded update size: {path}")
    return path.read_bytes()


def repair_document(document: dict) -> tuple[dict, list[int]]:
    """Change only the two known display expressions; preserve other cell sources.

    Execution outputs/counts are cleared only when an actual correction is made.
    The untouched original, including its traceback, is saved separately on disk.
    """
    if document.get("nbformat") != 4 or not isinstance(document.get("cells"), list):
        raise ValueError("Expected a version-4 Jupyter notebook")
    result = copy.deepcopy(document)
    changed: list[int] = []
    for old, new in zip(OLD_LINES, NEW_LINES):
        old_hits, new_hits = [], []
        for index, cell in enumerate(result["cells"]):
            if cell.get("cell_type") != "code":
                continue
            source = cell.get("source", [])
            text = source if isinstance(source, str) else "".join(source)
            old_hits.extend([index] * text.count(old))
            new_hits.extend([index] * text.count(new))
        if len(old_hits) + len(new_hits) != 1:
            raise ValueError("A display cell was changed or duplicated unexpectedly. Original preserved; do not reset.")
        if old_hits:
            index = old_hits[0]
            cell = result["cells"][index]
            src = cell["source"]
            text = src if isinstance(src, str) else "".join(src)
            text = text.replace(old, new, 1)
            cell["source"] = text if isinstance(src, str) else text.splitlines(keepends=True)
            changed.append(index)
    if changed:
        for cell in result["cells"]:
            if cell.get("cell_type") == "code":
                cell["outputs"] = []
                cell["execution_count"] = None
    return result, sorted(set(changed))


def render_check() -> dict:
    """Reproduce the old failure and verify the replacements in a fresh process."""
    program = r'''
import importlib.abc
import json
import sys
class NoJinja(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "jinja2" or fullname.startswith("jinja2."):
            raise ModuleNotFoundError("Jinja2 deliberately unavailable in regression test", name="jinja2")
sys.meta_path.insert(0, NoJinja())
for name in list(sys.modules):
    if name == "jinja2" or name.startswith("jinja2."):
        del sys.modules[name]
import pandas as pd
payload = json.loads(sys.stdin.read())
frame = pd.DataFrame({"Gender":["M","W"],"Season":[2018,2018],"recipe":["anchor","anchor_quality"],
    "games":[63,63],"train_games":[315,315],"brier":[.17320192076291752,.17220192076291752],
    "delta_vs_anchor":[0.,-.001],"active_features":[16,19]})
original = frame.copy(deep=True)
rendered = []
def display(table):
    h = table._repr_html_()
    if not isinstance(h, str) or '<table' not in h:
        raise AssertionError("Plain DataFrame HTML did not render")
    if '<table' not in table.to_html(index=False):
        raise AssertionError("Standalone HTML table did not render")
    rendered.append(table)
namespace = {"prior_metrics":frame,"metrics":frame,"display":display}
failures = 0
for expression in payload["old"]:
    try:
        exec(expression, namespace)
    except (AttributeError, ImportError) as error:
        if 'jinja2' not in str(error).lower():
            raise
        failures += 1
    else:
        raise AssertionError("Old formatting failure was not reproduced")
for expression in payload["new"]:
    exec(expression, namespace)
pd.testing.assert_frame_equal(frame, original, check_exact=True)
if len(rendered) != 2 or failures != 2:
    raise AssertionError("Both display locations must be tested")
for table in rendered:
    if list(table.brier) != ['0.1732019','0.1722019'] or list(table.delta_vs_anchor) != ['+0.0000000','-0.0010000']:
        raise AssertionError("Display precision or delta sign changed")
print(json.dumps({"status":"PASS","jinja2_blocked":True,"old_failures_reproduced":failures,
    "corrected_displays_rendered":len(rendered),"numeric_data_unchanged":True,"models_fitted":0,
    "pandas_version":pd.__version__}))
'''
    result = subprocess.run(
        [sys.executable, "-c", program], input=json.dumps({"old": OLD_LINES, "new": NEW_LINES}),
        text=True, capture_output=True, timeout=45, check=False,
    )
    if result.returncode:
        raise RuntimeError("Display regression check failed BEFORE updating files:\n" + result.stderr[-4000:])
    return json.loads(result.stdout.strip().splitlines()[-1])


def atomic_write(path: Path, data: bytes) -> None:
    fd, name = tempfile.mkstemp(prefix=".notebook_update_", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            os.chmod(temp, path.stat().st_mode & 0o777)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def apply(kit: Path, *, verify_only: bool = False) -> dict:
    import fcntl  # SageMaker Linux, matching the existing experiment supervisor.
    kit = kit.expanduser().absolute()
    if not kit.is_dir() or kit.is_symlink():
        raise ValueError(f"Existing kit not found, or symlinked: {kit}")
    for rel in ("reference", "reports"):
        if (kit / rel).is_symlink():
            raise ValueError(f"Symlinked folder is not supported: {kit / rel}")
    reports = kit / "reports"
    reports.mkdir(exist_ok=True)
    lock_path = reports / "execution.lock"
    if lock_path.is_symlink():
        raise ValueError("Symlinked execution lock")
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("An experiment stage is running. Do not update its notebook concurrently.") from error
        actual_source = {}
        for name, expected in EXPECTED_SOURCE.items():
            actual_source[name] = hashlib.sha256(checked_file(kit / name)).hexdigest()
            if actual_source[name] != expected:
                raise ValueError(f"Computational source differs from the supplied kit: {name}. Original preserved.")
        target = kit / NOTEBOOK
        original = checked_file(target)
        document = json.loads(original)
        corrected, changed = repair_document(document)
        if verify_only and changed:
            raise ValueError("The two display corrections have not both been applied yet.")
        manifest_path = kit / "MANIFEST.json"
        manifest_original = checked_file(manifest_path)
        manifest = json.loads(manifest_original)
        if not isinstance(manifest.get("files"), dict) or NOTEBOOK not in manifest["files"]:
            raise ValueError("Unexpected package manifest; do not overwrite it manually")
        print("Checking both displays with Jinja2 deliberately blocked; no model fitting.", flush=True)
        checked = render_check()
        backup = None
        if changed:
            data = (json.dumps(corrected, indent=1, ensure_ascii=False) + "\n").encode()
            parent = reports / "notebook_backups"
            if parent.is_symlink():
                raise ValueError("Symlinked notebook backup directory")
            parent.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup = parent / (stamp + "_" + hashlib.sha256(original).hexdigest()[:12])
            backup.mkdir()
            for name, blob in ((NOTEBOOK, original), ("MANIFEST.json", manifest_original)):
                with (backup / name).open("xb") as handle:
                    handle.write(blob)
                if (backup / name).read_bytes() != blob:
                    raise RuntimeError("Backup verification failed; original notebook has not been updated")
            if target.read_bytes() != original or manifest_path.read_bytes() != manifest_original:
                raise RuntimeError("Notebook/manifest changed during checks. Close the notebook before updating.")
            atomic_write(target, data)
            manifest["files"][NOTEBOOK] = digest(target)
            atomic_write(manifest_path, (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
        after_source = {name: digest(kit / name) for name in EXPECTED_SOURCE}
        if after_source != actual_source:
            raise RuntimeError("Computational files changed concurrently; stop before running research.")
        receipt = {
            "status": "PASS_NOTEBOOK_UPDATE" if changed else "PASS_ALREADY_UPDATED",
            "utc": datetime.now(timezone.utc).isoformat(),
            "notebook": str(target), "changed_code_cells": changed,
            "number_of_display_cells_corrected": len(changed),
            "backup_directory": str(backup) if backup else None,
            "before_sha256": hashlib.sha256(original).hexdigest(), "after_sha256": digest(target),
            "computational_source_sha256": actual_source, "computational_source_unchanged": True,
            "cache_identity_inputs_changed": False, "environment_modified": False,
            "cached_models_or_predictions_modified": False, "models_fitted": 0,
            "github_updated": False, "aws_resources_modified": False, "render_check": checked,
            "next_step": "Reopen the canonical notebook, restart its kernel, and run all cells once.",
        }
        if not verify_only:
            name = reports / "notebook_display_update.json"
            if name.is_symlink():
                raise ValueError("Symlinked update receipt")
            atomic_write(name, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
        print(json.dumps(receipt, indent=2), flush=True)
        return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path, default=Path.home() / "march_schedule_research")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        apply(args.kit, verify_only=args.verify_only)
    except Exception as error:
        print(f"STOP: {type(error).__name__}: {error}", file=sys.stderr)
        print("Do not delete data, change the environment, or bypass a checksum check.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
