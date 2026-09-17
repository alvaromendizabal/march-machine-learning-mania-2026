"""Notebook display helpers for public-solution research only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from IPython.display import HTML, display


def plotly_figure(
    figure: Any,
    artifact_path: Path,
    *,
    height: int = 560,
    width: str = "100%",
    config: dict[str, Any] | None = None,
) -> None:
    """Render Plotly as ordinary HTML plus a standalone fallback."""
    artifact_path = artifact_path.resolve()
    artifact_path.parent.mkdir(parents=True, exist_ok=True)

    plot_config: dict[str, Any] = {
        "displaylogo": False,
        "responsive": True,
        "scrollZoom": False,
    }

    if config:
        plot_config.update(config)

    figure.update_layout(height=height)

    figure.write_html(
        artifact_path,
        full_html=True,
        include_plotlyjs=True,
        auto_open=False,
        config=plot_config,
    )

    inline_html = figure.to_html(
        full_html=False,
        include_plotlyjs=True,
        config=plot_config,
        default_width=width,
        default_height=f"{height}px",
    )

    display(HTML(inline_html))

    print(
        "PLOTLY_HTML_RENDER_COMPLETE",
        artifact_path,
    )
