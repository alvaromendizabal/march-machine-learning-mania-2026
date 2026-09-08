"""Bounded-memory, resumable construction of wide official-template feature matrices."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from march_mania.advanced_features import pair_features
from march_mania.runtime import TaskStore


def write_submission_features(
    teams: pd.DataFrame,
    pairs: pd.DataFrame,
    sample: pd.DataFrame,
    output: Path,
    store: TaskStore,
    chunk_size: int = 512,
) -> None:
    """Persist validated chunks, then atomically assemble Parquet without a full wide dataframe."""
    if chunk_size < 1 or pairs.empty or len(pairs) != len(sample):
        raise ValueError("Positive chunk size and aligned nonempty template required")
    if sample.ID.duplicated().any():
        raise ValueError("Duplicate template ID")
    paths = []
    for start in range(0, len(pairs), chunk_size):
        chunk = pairs.iloc[start : start + chunk_size]
        expected = sample.ID.iloc[start : start + chunk_size].tolist()

        def build(
            target: Path, chunk: pd.DataFrame = chunk, expected: list = expected
        ) -> list[Path]:
            identities = chunk[["Gender", "Season"]].drop_duplicates()
            selected = teams.merge(identities, on=["Gender", "Season"], validate="many_to_one")
            frame = pair_features(selected, chunk)
            if frame.ID.tolist() != expected:
                raise ValueError("Submission feature chunk order changed")
            frame["route"] = np.where(frame.diff_seed.notna(), "seeded", "unseeded")
            path = target / "features.parquet"
            frame.to_parquet(path, index=False)
            return [path]

        target = store.task(f"submission_{chunk_size}_{start:06d}", build)
        paths.append(target / "features.parquet")
        store.log.emit(
            "submission_feature_progress",
            completed=min(start + chunk_size, len(pairs)),
            total=len(pairs),
        )
    temporary = output.with_suffix(".parquet.tmp")
    writer = None
    try:
        for path in paths:
            table = pq.read_table(path)
            if writer is None:
                writer = pq.ParquetWriter(temporary, table.schema, compression="zstd")
            writer.write_table(table)
        if writer is not None:
            writer.close()
            writer = None
        ids = pd.read_parquet(temporary, columns=["ID"])
        if ids.ID.tolist() != sample.ID.tolist():
            raise ValueError("Assembled submission feature identity mismatch")
        os.replace(temporary, output)
    finally:
        if writer is not None:
            writer.close()
        temporary.unlink(missing_ok=True)
