"""Matched model scoreboards, calibration and paired season uncertainty."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from march_mania.research_report import probability_metrics


def paired_intervals(predictions: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    records = []
    for gender, population in predictions.groupby("Gender"):
        reference = population.loc[(population.block == gender) & (population.model == "seed_raw")]
        for (route, model), group in population.groupby(["block", "model"]):
            matched = group.merge(
                reference,
                on=["Gender", "Season", "ID"],
                suffixes=("_a", "_b"),
                validate="one_to_one",
            )
            if (
                len(matched) != len(group)
                or len(matched) != len(reference)
                or not matched.y_a.equals(matched.y_b)
            ):
                raise ValueError("Unmatched predictions or labels")
            loss = matched.assign(
                delta=(matched.y_a - matched.p_a) ** 2 - (matched.y_b - matched.p_b) ** 2
            )
            means = loss.groupby("Season").delta.mean().to_numpy()
            samples = rng.choice(means, size=(4000, len(means)), replace=True).mean(axis=1)
            records.append(
                {
                    "Gender": gender,
                    "block": route,
                    "model": model,
                    "brier_delta": float(means.mean()),
                    "ci_low": float(np.quantile(samples, 0.025)),
                    "ci_high": float(np.quantile(samples, 0.975)),
                    "seasons": len(means),
                    "baseline": "separate seed_raw",
                }
            )
    return pd.DataFrame(records)


def write_model_report(
    predictions: pd.DataFrame, decisions: list[dict[str, Any]], output: Path, seed: int
) -> None:
    keys = ["Gender", "Season", "block", "model"]
    if predictions.duplicated(keys + ["ID"]).any():
        raise ValueError("Duplicate scored physical games")
    records = []
    for values, group in predictions.groupby(keys):
        records.append(
            {
                **dict(zip(keys, values, strict=True)),
                "games": len(group),
                **probability_metrics(group.y.to_numpy(), group.p.to_numpy()),
            }
        )
    metrics = pd.DataFrame(records)
    metrics.to_csv(output / "metrics_by_season.csv", index=False)
    score = (
        metrics.groupby(["Gender", "block", "model"])
        .agg(
            macro_season_brier=("brier", "mean"),
            season_brier_sd=("brier", "std"),
            seasons=("Season", "nunique"),
            games=("games", "sum"),
        )
        .reset_index()
    )
    weighted, curves = [], []
    for values, group in predictions.groupby(["Gender", "block", "model"]):
        context = dict(zip(["Gender", "block", "model"], values, strict=True))
        weighted.append({**context, **probability_metrics(group.y.to_numpy(), group.p.to_numpy())})
        bins = group.assign(bin=np.minimum((group.p * 10).astype(int), 9))
        curve = (
            bins.groupby("bin")
            .agg(predicted=("p", "mean"), observed=("y", "mean"), games=("y", "size"))
            .reset_index()
        )
        for key, value in context.items():
            curve[key] = value
        curves.append(curve)
    score = score.merge(pd.DataFrame(weighted), on=["Gender", "block", "model"])
    score.to_csv(output / "leaderboard.csv", index=False)
    reliability = pd.concat(curves, ignore_index=True)
    reliability.to_csv(output / "reliability.csv", index=False)
    intervals = paired_intervals(predictions, seed)
    intervals.to_csv(output / "paired_intervals.csv", index=False)
    selection: list[dict[str, Any]] = []
    weights: list[dict[str, Any]] = []
    for context in decisions:
        for family, choice in context["decisions"].items():
            identity = {k: context[k] for k in ["Gender", "route", "Season"]}
            if family == "blend":
                weights.extend(
                    {**identity, "family": name, "weight": weight}
                    for name, weight in choice["weights"].items()
                )
            else:
                selection.append(
                    {
                        **identity,
                        "family": family,
                        "candidate": choice["candidate"],
                        "calibration": choice["method"],
                        "temperature": choice["temperature"],
                        "history_last_season": max(choice["history_seasons"]),
                        "history_seasons": len(choice["history_seasons"]),
                    }
                )
    pd.DataFrame(selection).to_csv(output / "selection.csv", index=False)
    pd.DataFrame(weights).to_csv(output / "ensemble_weights.csv", index=False)
    errors = predictions.assign(squared_error=(predictions.y - predictions.p) ** 2)
    errors = errors.loc[errors.model == "blend"].sort_values("squared_error", ascending=False)
    errors.head(30).to_csv(output / "largest_errors.csv", index=False)
    presentation = score.loc[
        score.model.str.endswith("_calibrated") | (score.model == "blend")
    ].copy()
    presentation["architecture"] = np.where(
        presentation.block == "pooled_common", "Pooled common", "Separate"
    )
    season_chart = metrics.loc[
        metrics.model.isin(
            [
                "seed_raw",
                "logistic_calibrated",
                "xgboost_calibrated",
                "lightgbm_calibrated",
                "blend",
            ]
        )
        & (metrics.block != "pooled_common")
    ]
    reliability_chart = reliability.loc[
        reliability.model.isin(["seed_raw", "blend"]) & (reliability.block != "pooled_common")
    ]
    figures = [
        px.bar(
            presentation,
            x="model",
            y="macro_season_brier",
            color="architecture",
            facet_col="Gender",
            barmode="group",
            title="Nested model comparison · mean season Brier ↓",
        ),
        px.line(
            season_chart,
            x="Season",
            y="brier",
            color="model",
            facet_col="Gender",
            markers=True,
            title="Season stability · separate models",
        ),
        px.line(
            reliability_chart,
            x="predicted",
            y="observed",
            color="model",
            facet_col="Gender",
            markers=True,
            hover_data=["games"],
            title="Reliability · earlier OOF training, outer-season scoring",
        ),
    ]
    figures[-1].add_trace(
        go.Scatter(
            x=[0, 1], y=[0, 1], mode="lines", name="Ideal", line={"dash": "dot", "color": "#607080"}
        ),
        row="all",
        col="all",
        exclude_empty_subplots=True,
    )
    for figure in figures:
        figure.update_layout(
            template="plotly_white",
            height=480,
            font={"family": "Arial", "size": 13},
            margin={"t": 85, "b": 110},
        )
    sections = "\n".join(
        f"<section>{figure.to_html(full_html=False, include_plotlyjs=i == 0)}</section>"
        for i, figure in enumerate(figures)
    )
    html = (
        """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>March Mania · Model Comparison</title><style>
body{margin:0;background:#eff3f8;color:#14243b;font:16px/1.6 Arial}
main{max-width:1240px;margin:auto;padding:36px 24px}h1{font-size:40px;line-height:1.15}
section{background:white;border-radius:14px;border:1px solid #dbe3ed;padding:16px;margin:24px 0}
.note{background:#e2eef0;border-left:4px solid #147d86;padding:18px}
p{max-width:960px}</style><main>
<p>NCAA PROBABILITY FORECASTING / MODEL LAB</p><h1>Do stronger learners improve the forecast?</h1>
<p>Every model predicts the same five tournament seasons. Hyperparameters, candidate features,
probability calibration and convex blend weights use earlier out-of-fold games only.</p>
<div class="note"><b>Retrospective development evidence.</b> These seasons have been explored
before. Results establish no new untouched holdout or Kaggle standing. The official metric
is game-weighted Brier; model selection uses equal season weights. Smaller is better.</div>
"""
        + sections
        + """<p>Common models share the same feature universe across separate and pooled fits.
Men's rank_logistic is an additional ranking-feature comparison. Five seasons provide limited
uncertainty information. Average precision summarizes the precision-recall curve;
precision/recall/F1 use threshold 0.5 and lower TeamID winning as the positive class.</p>
<p>Underlying CSVs contain complete metrics, choices, reliability-bin counts, blend weights,
largest errors and paired season-bootstrap intervals. Neural framework results from the
historical feature schema are retained separately; this run evaluates the four current
tabular learner families.</p></main></html>"""
    )
    (output / "report.html").write_text(html, encoding="utf-8")
