"""Compact public research tables; complete per-fit audits stay in verified archives."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def public_bytes(source: Path, *, feature_audit: bool = False) -> bytes:
    """Retain full-block fitted features, never drop the archived rejection audit.

    Read the potentially large private candidate audit in bounded chunks. The
    public table is a labelled selection view, not a substitute for the complete
    audit. A byte limit prevents accidentally committing private-scale exports.
    """
    if feature_audit:
        keys = ["Gender", "Season", "block", "model", "feature"]
        selected = []
        with pd.read_csv(source, chunksize=10_000, dtype={"fitted": "boolean"}) as reader:
            for chunk in reader:
                if not {*keys, "fitted"}.issubset(chunk) or chunk.fitted.isna().any():
                    raise ValueError("Incomplete feature usage schema")
                selected.append(chunk.loc[(chunk.block == "full") & chunk.fitted])
        if not selected:
            raise ValueError("Empty feature usage audit")
        table = pd.concat(selected, ignore_index=True).sort_values(keys)
        if table.empty or table.duplicated(keys).any():
            raise ValueError("Full-block feature usage must be nonempty and unique")
        result = table.to_csv(index=False, lineterminator="\n").encode()
    else:
        if source.stat().st_size > 8 * 1024 * 1024:
            raise ValueError("Public report exceeds 8 MiB; retain complete data in its archive")
        result = source.read_bytes()
    if len(result) > 8 * 1024 * 1024:
        raise ValueError("Public report exceeds 8 MiB; retain complete data in its archive")
    return result
