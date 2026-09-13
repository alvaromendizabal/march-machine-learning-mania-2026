from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    raw: Path
    interim: Path
    processed: Path
    reports: Path
    submissions: Path


def find_project_root(start: str | Path | None = None) -> Path:
    """Find the project root by walking upward to pyproject.toml or .git."""
    current = Path(start or Path.cwd()).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
            return candidate
    raise FileNotFoundError(
        "Could not find the project root. Start Jupyter from the repository root."
    )


def get_project_paths(root: str | Path | None = None) -> ProjectPaths:
    project_root = Path(root).resolve() if root else find_project_root()
    paths = ProjectPaths(
        root=project_root,
        raw=project_root / "data" / "raw" / "march-machine-learning-mania-2026",
        interim=project_root / "data" / "interim",
        processed=project_root / "data" / "processed",
        reports=project_root / "reports" / "data_quality",
        submissions=project_root / "submissions",
    )
    for path in (paths.interim, paths.processed, paths.reports, paths.submissions):
        path.mkdir(parents=True, exist_ok=True)
    return paths
