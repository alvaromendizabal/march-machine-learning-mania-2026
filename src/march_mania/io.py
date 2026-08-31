from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

import pandas as pd


def discover_csv_files(data_dir: str | Path) -> list[Path]:
    data_dir = Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(
            f"Raw data directory does not exist: {data_dir}\n"
            "Run scripts\\download_data.cmd first, or place the Kaggle CSV files there."
        )
    files = sorted(data_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    return files


def load_csv_tables(data_dir: str | Path) -> tuple[dict[str, pd.DataFrame], list[Path]]:
    """Load every CSV in a competition directory, keyed by file stem."""
    csv_files = discover_csv_files(data_dir)
    tables: dict[str, pd.DataFrame] = {}
    for path in csv_files:
        tables[path.stem] = pd.read_csv(path, low_memory=False)
    return tables, csv_files


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def build_inventory(tables: Mapping[str, pd.DataFrame], csv_files: list[Path]) -> pd.DataFrame:
    file_by_stem = {path.stem: path for path in csv_files}
    records = []
    for name, frame in sorted(tables.items()):
        path = file_by_stem[name]
        records.append(
            {
                "Table": name,
                "FileName": path.name,
                "Rows": len(frame),
                "Columns": frame.shape[1],
                "SizeMB": round(path.stat().st_size / 1024**2, 3),
                "Sha256": sha256_file(path),
                "ColumnNames": " | ".join(map(str, frame.columns)),
            }
        )
    return pd.DataFrame(records)


def write_manifest(inventory: pd.DataFrame, output_path: str | Path) -> None:
    records = inventory.to_dict(orient="records")
    Path(output_path).write_text(json.dumps(records, indent=2), encoding="utf-8")
