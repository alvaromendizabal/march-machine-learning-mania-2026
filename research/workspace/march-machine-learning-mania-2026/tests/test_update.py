from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path("scripts").resolve()))
spec = importlib.util.spec_from_file_location("studio_update", "scripts/update.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def git(root, *args):
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def repository(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    git(origin, "init", "-b", "main")
    git(origin, "config", "user.name", "Test")
    git(origin, "config", "user.email", "test@example.com")
    (origin / "notebooks").mkdir()
    (origin / "notebooks/05.ipynb").write_text("old upstream")
    git(origin, "add", ".")
    git(origin, "commit", "-m", "initial")
    clone = tmp_path / "studio"
    git(tmp_path, "clone", str(origin), str(clone))
    git(clone, "config", "user.name", "Test")
    git(clone, "config", "user.email", "test@example.com")
    (origin / "notebooks/05.ipynb").write_text("new upstream")
    git(origin, "commit", "-am", "update")
    return origin, clone


def test_dirty_notebook_survives_update_and_stash_is_not_applied(tmp_path):
    origin, clone = repository(tmp_path)
    (clone / "notebooks/05.ipynb").write_text("valuable executed notebook")
    result = module.update(clone)
    assert result["commit"] == git(origin, "rev-parse", "HEAD")
    assert (clone / "notebooks/05.ipynb").read_text() == "new upstream"
    assert (
        git(clone, "show", result["notebook_stash"] + ":notebooks/05.ipynb")
        == "valuable executed notebook"
    )
    assert module.update(clone)["notebook_stash"] is None


def test_fetch_failure_leaves_notebook_untouched(tmp_path):
    _, clone = repository(tmp_path)
    (clone / "notebooks/05.ipynb").write_text("my notebook")
    git(clone, "remote", "set-url", "origin", str(tmp_path / "missing"))
    with pytest.raises(subprocess.CalledProcessError):
        module.update(clone)
    assert (clone / "notebooks/05.ipynb").read_text() == "my notebook"


def test_divergence_and_non_notebook_work_are_never_discarded(tmp_path):
    _, clone = repository(tmp_path)
    (clone / "notes.txt").write_text("work")
    with pytest.raises(ValueError, match="Untracked"):
        module.update(clone)
    git(clone, "add", ".")
    git(clone, "commit", "-m", "local work")
    (clone / "notes.txt").write_text("more work")
    with pytest.raises(ValueError, match="Non-notebook"):
        module.update(clone)
    git(clone, "commit", "-am", "more work")
    with pytest.raises(subprocess.CalledProcessError):
        module.update(clone)
    assert (clone / "notes.txt").read_text() == "more work"
