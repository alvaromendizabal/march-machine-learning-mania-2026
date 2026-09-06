"""Matched-season metrics and a standalone interactive research report."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

from march_mania.runtime import atomic_json


def probability_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float | None]:
    if len(y) == 0 or len(y) != len(p) or not np.isin(y, [0, 1]).all():
        raise ValueError("Expected aligned nonempty binary labels")
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Probabilities must be finite and within [0, 1]")
    bucket = np.minimum((p * 10).astype(int), 9)
    ece = sum(
        np.mean(bucket == b) * abs(np.mean(y[bucket == b]) - np.mean(p[bucket == b]))
        for b in range(10)
        if np.any(bucket == b)
    )
    return {
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "roc_auc": float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None,
        "average_precision": float(average_precision_score(y, p)) if y.sum() else None,
        "precision_at_05": float(precision_score(y, p >= 0.5, zero_division=0)),
        "recall_at_05": float(recall_score(y, p >= 0.5, zero_division=0)),
        "f1_at_05": float(f1_score(y, p >= 0.5, zero_division=0)),
        "ece_10_bins": float(ece),
    }


def paired_season_intervals(
    predictions: pd.DataFrame, seed: int, comparisons: list[tuple[str, str]] | None = None
) -> pd.DataFrame:
    """Paired loss deltas, resampling entire seasons rather than dependent games."""
    comparisons = (
        comparisons
        if comparisons is not None
        else [
            ("strength", "seed"),
            ("efficiency", "strength"),
            ("recent", "efficiency"),
            ("matchup", "efficiency"),
            ("full", "recent"),
            ("full", "matchup"),
        ]
    )
    rng = np.random.default_rng(seed)
    records = []
    for (gender, model), group in predictions.groupby(["Gender", "model"]):
        for candidate, baseline in comparisons:
            if candidate not in set(group.block) or baseline not in set(group.block):
                continue
            keys = ["Gender", "Season", "ID"]
            left = group.loc[group.block == candidate, keys + ["y", "p"]]
            right = group.loc[group.block == baseline, keys + ["y", "p"]]
            paired = left.merge(right, on=keys, suffixes=("_a", "_b"), validate="one_to_one")
            if len(paired) != len(left) or len(paired) != len(right):
                raise ValueError("Ablation rows do not match")
            if not paired.y_a.equals(paired.y_b):
                raise ValueError("Ablation labels do not match")
            paired["delta"] = (paired.y_a - paired.p_a) ** 2 - (paired.y_b - paired.p_b) ** 2
            deltas = paired.groupby("Season").delta.mean().to_numpy()
            if not len(deltas):
                continue
            samples = rng.choice(deltas, size=(4000, len(deltas)), replace=True).mean(axis=1)
            records.append(
                {
                    "Gender": gender,
                    "model": model,
                    "candidate": candidate,
                    "baseline": baseline,
                    "season_count": len(deltas),
                    "brier_delta": float(deltas.mean()),
                    "ci_low": float(np.quantile(samples, 0.025)),
                    "ci_high": float(np.quantile(samples, 0.975)),
                }
            )
    return pd.DataFrame(records)


def write_report(
    predictions: pd.DataFrame,
    output: Path,
    seed: int,
    comparisons: list[tuple[str, str]] | None = None,
) -> None:
    records = []
    for keys, group in predictions.groupby(["Gender", "Season", "block", "model"]):
        records.append(
            {
                **dict(zip(["Gender", "Season", "block", "model"], keys, strict=True)),
                "games": len(group),
                **probability_metrics(group.y.to_numpy(), group.p.to_numpy()),
            }
        )
    metrics = pd.DataFrame(records)
    metrics.to_csv(output / "metrics_by_season.csv", index=False)
    summary = (
        metrics.groupby(["Gender", "block", "model"])
        .agg(
            macro_season_brier=("brier", "mean"),
            seasons=("Season", "nunique"),
            games=("games", "sum"),
        )
        .reset_index()
    )
    weighted = []
    for keys, group in predictions.groupby(["Gender", "block", "model"]):
        weighted.append(
            {
                **dict(zip(["Gender", "block", "model"], keys, strict=True)),
                **probability_metrics(group.y.to_numpy(), group.p.to_numpy()),
            }
        )
    summary = summary.merge(pd.DataFrame(weighted), on=["Gender", "block", "model"])
    summary.to_csv(output / "leaderboard.csv", index=False)
    combined = []
    for keys, group in predictions.groupby(["Season", "block", "model"]):
        combined.append(
            {
                **dict(zip(["Season", "block", "model"], keys, strict=True)),
                "games": len(group),
                **probability_metrics(group.y.to_numpy(), group.p.to_numpy()),
            }
        )
    pd.DataFrame(combined).to_csv(output / "combined_metrics_by_season.csv", index=False)
    intervals = paired_season_intervals(predictions, seed, comparisons)
    intervals.to_csv(output / "ablation_intervals.csv", index=False)
    curves = []
    for keys, group in predictions.groupby(["Gender", "block", "model"]):
        bins = group.assign(bin=np.minimum((group.p * 10).astype(int), 9))
        curve = (
            bins.groupby("bin")
            .agg(predicted=("p", "mean"), observed=("y", "mean"), games=("y", "size"))
            .reset_index()
        )
        for key, value in zip(["Gender", "block", "model"], keys, strict=True):
            curve[key] = value
        curves.append(curve)
    reliability = pd.concat(curves, ignore_index=True)
    reliability.to_csv(output / "reliability.csv", index=False)
    atomic_json(
        output / "interpretation.json",
        {
            "status": "retrospective development research; no automatic model promotion",
            "selection_metric": "macro mean season Brier",
            "official_metric": "game-weighted Brier (mean squared probability error)",
            "uncertainty": "paired season bootstrap; few seasons imply unstable intervals",
            "threshold_metrics": "0.5 threshold; positive class is lower TeamID winning",
            "calibration": "diagnostic only; no calibrator fitted on validation outcomes",
            "historical_limit": "2022-2026 excluded; development years were previously explored",
        },
    )
    figures = [
        px.bar(
            summary.loc[~summary.block.str.startswith("without_")],
            x="block",
            y="macro_season_brier",
            color="model",
            facet_col="Gender",
            barmode="group",
            title="Matched-season feature comparison",
        ),
        px.line(
            metrics.loc[~metrics.block.str.startswith("without_")],
            x="Season",
            y="brier",
            color="block",
            line_dash="model",
            facet_col="Gender",
            markers=True,
            title="Performance across tournament seasons",
        ),
        px.scatter(
            intervals,
            x="brier_delta",
            y="candidate",
            color="model",
            facet_col="Gender",
            symbol="baseline",
            error_x=intervals.ci_high - intervals.brier_delta,
            error_x_minus=intervals.brier_delta - intervals.ci_low,
            title="Paired ablations · lower than zero favors the added features",
            hover_data=["baseline", "season_count"],
        ),
        px.line(
            reliability.loc[reliability.block.isin(["seed", "full"])],
            x="predicted",
            y="observed",
            color="block",
            line_dash="model",
            facet_col="Gender",
            markers=True,
            title="Reliability · seed and full models",
            hover_data=["games"],
        ),
    ]
    figures[-1].add_trace(
        go.Scatter(
            x=[0, 1],
            y=[0, 1],
            mode="lines",
            line={"color": "#667085", "dash": "dot"},
            name="Perfect calibration",
        ),
        row="all",
        col="all",
        exclude_empty_subplots=True,
    )
    for fig in figures:
        fig.update_layout(
            template="plotly_white",
            font={"family": "Arial", "size": 13},
            paper_bgcolor="white",
            height=460,
            margin={"t": 85, "l": 65, "r": 35},
        )
    sections = "\n".join(
        f"<section>{fig.to_html(full_html=False, include_plotlyjs=i == 0)}</section>"
        for i, fig in enumerate(figures)
    )
    html = (
        """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>March Mania · Feature Research</title><style>
body{margin:0;background:#edf1f7;color:#14243b;font:16px/1.6 Arial,sans-serif}
main{max-width:1280px;margin:auto;padding:40px 24px}h1{font-size:42px;line-height:1.15}
.kicker{color:#126a75;text-transform:uppercase;letter-spacing:.15em;font-size:12px;font-weight:bold}
section{background:white;border:1px solid #dde3ec;border-radius:14px;padding:14px;margin:22px 0}
.note{background:#e4eef1;border-left:4px solid #126a75;padding:18px 22px;border-radius:6px}
p{max-width:960px}footer{font-size:13px;color:#526175;margin:24px 0}
</style><main><div class="kicker">NCAA probability forecasting / research lab</div>
<h1>Which features earn their place?</h1>
<p>Identical chronological folds. Separate men's and women's models. Every forecast saved,
with paired comparisons and visible uncertainty.</p>
<div class="note"><strong>Retrospective development benchmark.</strong> Lower Brier is better.
These results do not establish a Kaggle medal or a new untouched holdout score.
All models use fixed recipes; selecting a winner here requires subsequent
independent validation.</div>
"""
        + sections
        + """<footer>Probability target: lower TeamID wins. Brier and log loss measure
probability quality; ROC AUC measures ranking. Calibration bins include game counts.
Confidence intervals resample whole seasons and remain uncertain with few seasons.
The CSV and Parquet files alongside this report contain the underlying results.
</footer></main></html>"""
    )
    (output / "report.html").write_text(html, encoding="utf-8")
