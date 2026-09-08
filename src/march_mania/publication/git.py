"""Publish verified notebook outputs without overwriting concurrent source changes."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import nbformat

from march_mania.publication.notebooks import NOTEBOOKS, validate_execution
from march_mania.publication.workflow import evidence, lineage


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=True
    ).stdout.strip()


def publish(root: Path, branch: str, expected: str) -> str:
    """Allow documentation-only advances; reject any change to computational inputs."""
    if branch != "feat/notebook-research" or len(expected) != 40:
        raise ValueError("An explicit research branch and source commit are required")
    lineage(root)
    files: list[Path] = []
    for name in NOTEBOOKS:
        path = root / "notebooks" / name
        validate_execution(nbformat.read(path, as_version=4))
        files.append(path)
    for name in ("feature_store", "model_comparison"):
        folder, record = evidence(root, name)
        files.extend(folder / filename for filename in ["run.json", *record["sha256"]])
    git(root, "fetch", "origin", branch)
    remote = git(root, "rev-parse", "FETCH_HEAD")
    changed = git(root, "diff", "--name-only", expected, remote).splitlines()
    if any(
        not (p.startswith("docs/") or p in {"README.md", ".github/workflows/ci.yml"})
        for p in changed
    ):
        raise ValueError(
            "Source changed while executing; preserved outputs must not replace newer research"
        )
    git(root, "merge-base", "--is-ancestor", expected, remote)
    with tempfile.TemporaryDirectory(prefix="march-publication-") as directory:
        work = Path(directory) / "tree"
        git(root, "worktree", "add", "--detach", str(work), remote)
        try:
            for path in files:
                relative = path.relative_to(root)
                target = work / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
            git(work, "add", "--", *(str(p.relative_to(root)) for p in files))
            if not git(work, "diff", "--cached", "--name-only"):
                return remote
            git(
                work,
                "-c",
                "user.name=Alvaro Mendizabal",
                "-c",
                "user.email=108156083+alvaromendizabal@users.noreply.github.com",
                "commit",
                "-m",
                "research: publish executed feature search and temporal model evidence",
                "-m",
                f"Validated source {expected}; "
                f"workflow {os.environ.get('GITHUB_RUN_ID', 'local')}. "
                "Preserves concurrent documentation and never force-pushes.",
            )
            commit = git(work, "rev-parse", "HEAD")
            git(work, "push", "origin", f"HEAD:{branch}")
            return commit
        finally:
            git(root, "worktree", "remove", "--force", str(work))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    print(publish(Path.cwd(), "feat/notebook-research", args.source))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
