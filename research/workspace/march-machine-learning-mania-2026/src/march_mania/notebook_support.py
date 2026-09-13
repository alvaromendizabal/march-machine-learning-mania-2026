"""Consistent evidence loading and tables for the canonical review notebooks."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
from IPython.display import HTML, display

from march_mania.runtime import digest


def review_source(
    root: Path,
    name: str,
    feature_count: int | None = None,
) -> tuple[Path | None, dict, str]:
    local, recorded = root / "outputs" / name, root / "reports" / name
    if (local / "latest.json").exists():
        pointer = json.loads((local / "latest.json").read_text())
        folder = pointer["directory"]
        if folder != pointer["fingerprint"] or not re.fullmatch(r"[a-f0-9]{64}", folder):
            raise ValueError("Invalid completed-run pointer")
        local = local / folder
    if (local / "summary.json").exists():
        summary = json.loads((local / "summary.json").read_text())
        if summary.get("status") == "completed" and (
            feature_count is None or summary.get("feature_count") == feature_count
        ):
            return local, summary, "completed local run"
    if (recorded / "run.json").exists():
        evidence = json.loads((recorded / "run.json").read_text())
        if feature_count is not None and evidence["summary"].get("feature_count") != feature_count:
            return None, {}, "no completed evidence for the current feature contract"
        for filename, expected in evidence["sha256"].items():
            path = recorded / filename
            if not path.resolve().is_relative_to(recorded.resolve()) or digest(path) != expected:
                raise ValueError(f"Recorded evidence checksum mismatch: {filename}")
        return recorded, evidence["summary"], "recorded Git evidence (checksums verified)"
    return None, {}, "not run"


def table(frame: pd.DataFrame, formats: dict | None = None) -> None:
    formatters = {
        name: (lambda value, template=template: template.format(value))
        for name, template in (formats or {}).items()
    }
    display(
        HTML(
            frame.to_html(
                index=False,
                border=0,
                classes="research-table",
                float_format=lambda value: f"{value:.6f}",
                formatters=formatters,
            )
        )
    )


def style() -> None:
    display(
        HTML("""<style>
.research-table{border-collapse:collapse;font:13px/1.5 Arial;width:100%}
.research-table th{background:#14243b;color:white;text-align:left;padding:10px}
.research-table td{padding:8px 10px;border-bottom:1px solid #e1e7ef}
.research-table tr:nth-child(even){background:#f1f6f8}
</style>""")
    )
