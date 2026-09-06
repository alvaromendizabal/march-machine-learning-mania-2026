"""Create an isolated, locked project environment without changing Studio packages."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

UV_VERSION = "0.11.33"


def command(argv: list[str], root: Path) -> None:
    started = time.monotonic()
    stopped = threading.Event()

    def event(status: str) -> None:
        print(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "event": status,
                    "command": argv,
                    "elapsed_seconds": round(time.monotonic() - started, 2),
                }
            ),
            flush=True,
        )

    def heartbeat() -> None:
        while not stopped.wait(15):
            event("heartbeat")

    event("started")
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        subprocess.run(argv, cwd=root, check=True, timeout=900)
        event("completed")
    finally:
        stopped.set()
        thread.join()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    executable = root / ".tools" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    uv = root / ".tools" / ("Scripts/uv.exe" if os.name == "nt" else "bin/uv")
    started = time.monotonic()
    try:
        if not executable.exists():
            command([sys.executable, "-m", "venv", str(root / ".tools")], root)
        command([str(executable), "-m", "pip", "install", f"uv=={UV_VERSION}"], root)
        command([str(uv), "sync", "--locked", "--group", "dev", "--python", "3.12.13"], root)
        command(
            [
                str(uv),
                "run",
                "--locked",
                "python",
                "-m",
                "ipykernel",
                "install",
                "--user",
                "--name",
                "march-mania",
                "--display-name",
                "Python (March Mania)",
            ],
            root,
        )
        command([str(uv), "run", "--locked", "python", "scripts/quality.py"], root)
        print(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "event": "bootstrap_completed",
                    "total_seconds": round(time.monotonic() - started, 2),
                }
            ),
            flush=True,
        )
        return 0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "event": "bootstrap_failed",
                    "returncode": getattr(error, "returncode", 1),
                }
            ),
            flush=True,
        )
        return getattr(error, "returncode", 1)


if __name__ == "__main__":
    sys.exit(main())
