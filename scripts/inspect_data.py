"""Extract official CSVs from a ZIP safely, without overwriting different raw inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from march_mania.features import FILES, read_official


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip", type=Path)
    parser.add_argument(
        "--destination", type=Path, default=Path("data/raw/march-machine-learning-mania-2026")
    )
    args = parser.parse_args()
    required = {f"{g}{name}.csv" for g in ("M", "W") for name in FILES}
    try:
        with zipfile.ZipFile(args.zip) as archive:
            selected = {}
            for member in archive.infolist():
                name = Path(member.filename).name
                if name in required:
                    if name in selected:
                        raise ValueError(f"Duplicate raw CSV basename: {name}")
                    selected[name] = member
            if set(selected) != required:
                raise ValueError(f"Missing official files: {sorted(required - set(selected))}")
            # Check every existing file before writing any new file.
            for name, member in selected.items():
                path = args.destination / name
                if path.exists():
                    existing = hashlib.sha256(path.read_bytes()).digest()
                    incoming = hashlib.sha256(archive.read(member)).digest()
                    if existing != incoming:
                        raise ValueError(
                            f"Raw data is immutable; different contents already at {path}"
                        )
            args.destination.mkdir(parents=True, exist_ok=True)
            for name, member in selected.items():
                path = args.destination / name
                if not path.exists():
                    temporary = path.with_suffix(".tmp")
                    with archive.open(member) as source, temporary.open("wb") as target:
                        import shutil

                        shutil.copyfileobj(source, target)
                    temporary.replace(path)
        read_official(args.destination)
        print(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "status": "data_ready",
                    "files": len(required),
                    "directory": str(args.destination),
                }
            ),
            flush=True,
        )
        return 0
    except (ValueError, OSError, zipfile.BadZipFile) as error:
        print(json.dumps({"status": "failed", "error": str(error)}), file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
