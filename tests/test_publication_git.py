"""Real local Git remotes: fail closed on new code; preserve concurrent documentation."""

from __future__ import annotations

import subprocess

import nbformat
import pytest

from march_mania.publication import git as publication
from march_mania.publication.notebooks import NOTEBOOKS


def command(path, *args):
    return subprocess.run(
        ["git", *args], cwd=path, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def remote(tmp_path, monkeypatch):
    bare, root = tmp_path / "remote.git", tmp_path / "checkout"
    bare.mkdir()
    command(bare, "init", "--bare")
    command(tmp_path, "clone", str(bare), str(root))
    command(root, "config", "user.name", "Test")
    command(root, "config", "user.email", "test@example.invalid")
    command(root, "checkout", "-b", "feat/notebook-research")
    (root / "README.md").write_text("initial docs")
    (root / "notebooks").mkdir()
    for name in NOTEBOOKS:
        nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell("1 + 1", execution_count=1)])
        nbformat.write(nb, root / "notebooks" / name)
    for group in ("feature_store", "model_comparison"):
        folder = root / "reports" / group
        folder.mkdir(parents=True)
        (folder / "run.json").write_text("{}")
        (folder / "metrics.csv").write_text("score\n0.2\n")
    command(root, "add", ".")
    command(root, "commit", "-m", "initial")
    command(root, "push", "origin", "HEAD")
    source = command(root, "rev-parse", "HEAD")
    monkeypatch.setattr(publication, "lineage", lambda root: None)
    monkeypatch.setattr(
        publication,
        "evidence",
        lambda root, name: (
            root / "reports" / name,
            {"sha256": {"metrics.csv": "verified in separate evidence tests"}},
        ),
    )
    return bare, root, source


def test_publish_uses_only_allowlisted_evidence_and_preserves_docs(remote, tmp_path):
    bare, root, source = remote
    other = tmp_path / "other"
    command(tmp_path, "clone", "-b", "feat/notebook-research", str(bare), str(other))
    command(other, "config", "user.name", "Other")
    command(other, "config", "user.email", "other@example.invalid")
    (other / "README.md").write_text("concurrent docs")
    command(other, "commit", "-am", "docs")
    command(other, "push")
    (root / "reports/feature_store/metrics.csv").write_text("score\n0.19\n")
    (root / "private.csv").write_text("must never be published")
    published = publication.publish(root, "feat/notebook-research", source)
    assert command(bare, "show", published + ":README.md") == "concurrent docs"
    assert command(bare, "show", published + ":reports/feature_store/metrics.csv") == "score\n0.19"
    assert "private.csv" not in command(bare, "ls-tree", "-r", "--name-only", published)
    assert (root / "private.csv").read_text() == "must never be published"


def test_new_source_refuses_stale_output_publication(remote):
    bare, root, source = remote
    (root / "model.py").write_text("changed = True")
    command(root, "add", "model.py")
    command(root, "commit", "-m", "new source")
    command(root, "push", "origin", "HEAD")
    before = command(bare, "rev-parse", "refs/heads/feat/notebook-research")
    with pytest.raises(ValueError, match="Source changed"):
        publication.publish(root, "feat/notebook-research", source)
    assert command(bare, "rev-parse", "refs/heads/feat/notebook-research") == before
