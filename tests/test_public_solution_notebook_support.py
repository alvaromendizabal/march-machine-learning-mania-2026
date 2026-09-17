from __future__ import annotations

import plotly.graph_objects as go

import march_mania.public_solutions.notebook_support as notebook_support


def test_plotly_figure_writes_standalone_and_emits_html(
    tmp_path,
    monkeypatch,
):
    rendered = []

    monkeypatch.setattr(
        notebook_support,
        "display",
        rendered.append,
    )

    figure = go.Figure(
        go.Scatter(
            x=[1, 2],
            y=[3, 4],
        )
    )

    artifact = tmp_path / "figures" / "example.html"

    notebook_support.plotly_figure(
        figure,
        artifact,
        height=480,
    )

    assert artifact.is_file()

    assert "plotly" in artifact.read_text(encoding="utf-8").lower()

    assert len(rendered) == 1

    assert "plotly" in rendered[0].data.lower()
