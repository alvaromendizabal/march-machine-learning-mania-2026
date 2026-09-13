"""Preserve local notebook edits, fast-forward main, and verify the new environment."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from bootstrap import command


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def update(root: Path) -> dict[str, str | None]:
    """Stop on divergence/non-notebook edits; never pop or delete the preserved stash."""
    if git(root, "branch", "--show-current") != "main":
        raise ValueError("Update requires main; preserve branch work before switching")
    if git(root, "ls-files", "--others", "--exclude-standard"):
        raise ValueError("Untracked files require review before the repository update")
    modified = set(git(root, "diff", "--name-only", "HEAD").splitlines())
    if any(not p.startswith("notebooks/") or not p.endswith(".ipynb") for p in modified):
        raise ValueError("Non-notebook edits require review before the repository update")
    # Fetch before changing the working tree; network failure leaves notebook work in place.
    command(["git", "fetch", "origin", "main"], root)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"], cwd=root, check=True
    )
    stash = None
    if modified:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        command(
            [
                "git",
                "stash",
                "push",
                "-m",
                f"Studio notebook work {stamp}",
                "--",
                *sorted(modified),
            ],
            root,
        )
        stash = git(root, "rev-parse", "refs/stash")
        print(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "event": "notebooks_preserved",
                    "stash_commit": stash,
                }
            ),
            flush=True,
        )
    command(["git", "merge", "--ff-only", "origin/main"], root)
    return {"commit": git(root, "rev-parse", "HEAD"), "notebook_stash": stash}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        result = update(root)
        command([sys.executable, "scripts/bootstrap.py"], root)
        print(
            json.dumps(
                {"timestamp": datetime.now(UTC).isoformat(), "event": "update_completed", **result}
            ),
            flush=True,
        )
        return 0
    except (ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "event": "update_stopped",
                    "reason": str(error),
                }
            ),
            flush=True,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
