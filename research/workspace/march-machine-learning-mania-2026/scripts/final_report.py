"""Close the scored portfolio without fitting models or changing prediction bytes."""

from __future__ import annotations

import argparse
import hashlib
import html
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from matplotlib.ticker import FuncFormatter

from march_mania.publication import scoreboard
from march_mania.publication.submission import validate_submission
from march_mania.runtime import EventLog, TaskStore, atomic_json, digest, fingerprint

REPORT = "reports/final_results"
BATCHES = ["original_50", "refinement_8", "men_challengers_6", "women_challengers_6"]
LABELS = ["Original models", "Probability adjustments", "Men’s retraining", "Women’s retraining"]
WINNER = "m_pooled_xgboost_t090__w_conference_c100_t110.csv"
INK, TEAL, BLUE, GRID = "#19324A", "#008577", "#718CA3", "#E5EBF0"


def reconcile(
    old: pd.DataFrame, observed: pd.DataFrame, manifests: pd.DataFrame, provenance: dict[str, Any]
) -> pd.DataFrame:
    """Join observed scores to exact files; overlap must reproduce the prior ledger."""
    if (
        len(observed) != 20
        or observed.isna().any().any()
        or observed.filename.duplicated().any()
        or manifests.filename.duplicated().any()
        or not np.isfinite(observed[["private_brier", "public_brier"]]).all().all()
        or not observed.private_brier.between(0, 1).all()
        or not observed.private_brier.equals(observed.public_brier)
    ):
        raise ValueError("Invalid screenshot observations or manifest")
    repeated = observed.loc[observed.filename.isin(old.filename)]
    previous = repeated.merge(old, on="filename", validate="one_to_one", suffixes=("", "_old"))
    if len(previous) != 8 or any(
        not np.array_equal(previous[c], previous[c + "_old"])
        for c in ["private_brier", "public_brier"]
    ):
        raise ValueError("Repeated screenshot rows disagree with preserved scores")
    new = observed.loc[~observed.filename.isin(old.filename)]
    if len(new) != 12 or set(new.filename) != set(manifests.filename):
        raise ValueError("Exactly twelve known new submissions are required")
    new = new.merge(manifests, on="filename", validate="one_to_one")
    new["candidate_id"] = new.filename.str.removesuffix(".csv")
    new["status"] = provenance["status"]
    new["recorded_at_utc"] = provenance["recorded_at_utc"]
    new["source_image"] = provenance["source_original_filename"]
    result = pd.concat([old, new[old.columns]], ignore_index=True)
    if len(result) != 70 or result.filename.nunique() != 70 or result.sha256.nunique() != 70:
        raise ValueError("Require seventy distinct scored submissions")
    return result.sort_values(["private_brier", "filename"]).reset_index(drop=True)


def scores(root: Path) -> pd.DataFrame:
    scoreboard.review(root)
    provenance = json.loads((root / REPORT / "provenance.json").read_text())
    if (
        digest(root / provenance["source_image"]) != provenance["source_image_sha256"]
        or digest(root / REPORT / "latest_scores.csv") != provenance["scores_sha256"]
    ):
        raise ValueError("Score provenance checksum mismatch")
    manifests = []
    for folder, batch in zip(
        ["prediction_challengers", "women_challengers"], BATCHES[2:], strict=True
    ):
        frame = pd.read_csv(root / "reports" / folder / "submission_manifest.csv")
        manifests.append(frame[["filename", "rows", "bytes", "sha256"]].assign(batch=batch))
    return reconcile(
        scoreboard.scores(root),
        pd.read_csv(root / REPORT / "latest_scores.csv"),
        pd.concat(manifests, ignore_index=True),
        provenance,
    )


def progression(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, (batch, label) in enumerate(zip(BATCHES, LABELS, strict=True)):
        part = frame.loc[frame.batch.eq(batch)]
        cumulative = frame.loc[frame.batch.isin(BATCHES[: i + 1])]
        best = cumulative.sort_values(["private_brier", "filename"]).iloc[0]
        rows.append(
            {
                "batch": batch,
                "label": label,
                "files_in_batch": len(part),
                "total_files": len(cumulative),
                "batch_best_brier": float(part.private_brier.min()),
                "best_so_far_brier": float(best.private_brier),
                "best_filename": best.filename,
            }
        )
    return pd.DataFrame(rows)


def review(root: Path, *, write: bool = False) -> dict[str, Any]:
    frame = scores(root)
    winner = frame.iloc[0]
    if winner.filename != WINNER or not np.isclose(winner.private_brier, 0.1222672, atol=1e-12):
        raise ValueError("Final winner does not match the supplied evidence")
    recipe = json.loads((root / "reports/prediction_production/recipe.json").read_text())
    stream = next(s for s in recipe["streams"] if s["id"] == "m_pooled_xgboost")
    key = stream["components"][0]["id"]
    men = [
        a
        for a in json.loads((root / "reports/prediction_production/fit_audits.json").read_text())
        if a["component"] == key
    ]
    women = [
        a
        for a in json.loads((root / "reports/women_challengers/final_fit_audits.json").read_text())
        if a["variant"] == "conference_c100"
    ]
    if (
        len(men) != 2
        or len(women) != 2
        or any(a["training_max_season"] != 2025 for a in men + women)
    ):
        raise ValueError("Missing final model route or invalid training cutoff")
    prior = frame.loc[frame.batch.isin(BATCHES[:2]), "private_brier"].min()
    original = frame.loc[frame.batch.eq(BATCHES[0]), "private_brier"].min()
    paths = [
        "scripts/final_report.py",
        "templates/final_results.html",
        REPORT + "/latest_scores.csv",
        REPORT + "/provenance.json",
        REPORT + "/score_evidence.png",
        "reports/submission_scores/summary.json",
        "reports/prediction_production/recipe.json",
        "reports/prediction_production/fit_audits.json",
        "reports/prediction_challengers/submission_manifest.csv",
        "reports/women_challengers/submission_manifest.csv",
        "reports/women_challengers/final_fit_audits.json",
    ]
    inputs = {name: digest(root / name) for name in paths}
    result = {
        "status": "completed",
        "fingerprint": fingerprint(inputs),
        "inputs": inputs,
        "scored_files": 70,
        "unscored_files": 0,
        "best_brier": float(winner.private_brier),
        "best_public_brier": float(winner.public_brier),
        "best_filename": str(winner.filename),
        "best_csv_sha256": str(winner.sha256),
        "best_csv_bytes": int(winner.bytes),
        "rows_per_file": int(winner.rows),
        "previous_best_brier": float(prior),
        "original_best_brier": float(original),
        "improvement_vs_previous": float(prior - winner.private_brier),
        "improvement_vs_original": float(original - winner.private_brier),
        "men": {"temperature": 0.9, "component": key, **recipe["components"][key], "fits": men},
        "women": {"temperature": 1.1, "C": 1.0, "feature_block": "conference", "fits": women},
        "new_model_fits": 0,
        "prior_prediction_bytes_preserved": True,
        "legacy_score_rows_preserved": 18,
        "scope": (
            "Observed late 2026 submissions selected retrospectively; "
            "not a fresh holdout or prospective leaderboard rank. "
            "The original frozen development reference is retained."
        ),
    }
    payloads = {
        "kaggle_scores.csv": frame.to_csv(index=False, float_format="%.7f"),
        "progression.csv": progression(frame).to_csv(index=False, float_format="%.7f"),
        "summary.json": json.dumps(result, indent=2, sort_keys=True) + "\n",
    }
    for name, content in payloads.items():
        path = root / REPORT / name
        if write:
            path.write_text(content)
        elif not path.is_file() or path.read_text() != content:
            raise ValueError(f"Stale final publication: {name}")
    return result


def short_label(filename: str) -> str:
    men, women = filename.removesuffix(".csv").split("__")
    m = men.removeprefix("m_").replace("pooled_xgboost", "Pooled XGB")
    m = m.replace("_lighter", " · lighter").replace("_f064", " · 64 inputs")
    m = m.replace("_trees240", " · 240 trees")
    w = women.removeprefix("w_").replace("logistic", "Women’s LR")
    w = w.replace("conference_c100", "Women’s conference LR C=1")
    w = w.replace("conference_c030", "Women’s conference LR C=0.3")
    w = w.replace("conference_c010", "Women’s conference LR C=0.1")
    for old, new in [("_t090", " · T=0.90"), ("_t100", " · T=1.00"), ("_t110", " · T=1.10")]:
        m, w = m.replace(old, new), w.replace(old, new)
    return m + "<br>" + w


def figures(root: Path) -> dict[str, go.Figure]:
    frame, history = scores(root), progression(scores(root))
    leaders = frame.head(6)
    labels = [short_label(n) for n in leaders.filename]
    colors = [TEAL] + [BLUE] * 5
    top = go.Figure(
        go.Scatter(
            x=leaders.private_brier,
            y=labels,
            mode="markers+text",
            marker={"size": 13, "color": colors},
            text=[f"{x:.7f}" for x in leaders.private_brier],
            textposition="middle right",
            customdata=leaders[["filename", "batch"]].to_numpy(),
            hovertemplate="%{customdata[0]}<br>Brier %{x:.7f}<extra></extra>",
        )
    )
    top.update_layout(title="The final six leaders", height=550, margin={"l": 350, "r": 120})
    top.update_yaxes(autorange="reversed")
    top.update_xaxes(
        title="Observed Kaggle Brier · lower is better", tickformat=".4f", range=[0.12222, 0.12292]
    )
    curve = go.Figure(
        go.Scatter(
            x=history.label,
            y=history.best_so_far_brier,
            mode="lines+markers+text",
            line={"color": TEAL, "width": 3},
            marker={"size": 11},
            text=[f"{x:.7f}" for x in history.best_so_far_brier],
            textposition="top center",
            customdata=history[["total_files", "best_filename"]].to_numpy(),
            hovertemplate=(
                "%{x}<br>%{customdata[0]} files scored<br>Best %{y:.7f}"
                "<br>%{customdata[1]}<extra></extra>"
            ),
        )
    )
    curve.update_layout(title="Small gains across four completed batches", height=430)
    curve.update_yaxes(title="Best observed Brier", tickformat=".4f", range=[0.12215, 0.12308])
    all_scores = go.Figure()
    for i, (batch, label) in enumerate(zip(BATCHES, LABELS, strict=True)):
        group = frame.loc[frame.batch.eq(batch)].sort_values("filename")
        offsets = np.linspace(-0.17, 0.17, len(group))
        all_scores.add_trace(
            go.Scatter(
                x=i + offsets,
                y=group.private_brier,
                mode="markers",
                name=label,
                marker={"size": 9, "color": [BLUE, "#6272A4", "#C48635", TEAL][i], "opacity": 0.8},
                customdata=group[["filename"]].to_numpy(),
                hovertemplate="%{customdata[0]}<br>Brier %{y:.7f}<extra></extra>",
            )
        )
    all_scores.update_layout(
        title="Every scored submission · all 70 files", height=440, showlegend=False
    )
    all_scores.update_xaxes(tickvals=list(range(4)), ticktext=LABELS)
    all_scores.update_yaxes(title="Observed Kaggle Brier", tickformat=".3f")
    for fig in [top, curve, all_scores]:
        fig.update_layout(
            template="plotly_white",
            font={"family": "Arial, sans-serif", "size": 14, "color": INK},
            title_font={"size": 23},
            paper_bgcolor="white",
            plot_bgcolor="white",
            hoverlabel={"font_size": 12},
        )
        fig.update_yaxes(gridcolor=GRID, zeroline=False)
        fig.update_xaxes(gridcolor=GRID, zeroline=False)
    return {"leaders": top, "progression": curve, "all_scores": all_scores}


def render(root: Path) -> None:
    """Plotly for interaction, matching static previews for GitHub notebook rendering."""
    figs = figures(root)
    folder = root / REPORT
    frame, history = scores(root), progression(scores(root))
    plt.rcParams.update(
        {"font.family": "DejaVu Sans", "font.size": 11, "text.color": INK, "axes.labelcolor": INK}
    )
    for name in ["leaders", "progression"]:
        fig, axis = plt.subplots(figsize=(12, 5.5), facecolor="white")
        if name == "leaders":
            top = frame.head(6)
            y = np.arange(len(top))
            axis.scatter(top.private_brier, y, s=85, c=[TEAL] + [BLUE] * 5, zorder=3)
            axis.set_yticks(y, [short_label(x).replace("<br>", "\n") for x in top.filename])
            axis.invert_yaxis()
            axis.set_xlim(0.12222, 0.12292)
            for i, value in enumerate(top.private_brier):
                axis.annotate(
                    f"{value:.7f}",
                    (value, i),
                    xytext=(11, 0),
                    textcoords="offset points",
                    va="center",
                    color=INK,
                )
            axis.set_xlabel("Observed Kaggle Brier · lower is better", labelpad=12)
            axis.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.4f}"))
            axis.grid(axis="x", color=GRID)
            axis.tick_params(axis="y", length=0, pad=14)
            fig.subplots_adjust(left=0.37, right=0.95, top=0.83, bottom=0.18)
            title = "The final six leaders"
        else:
            axis.plot(
                range(4),
                history.best_so_far_brier,
                color=TEAL,
                linewidth=2.5,
                marker="o",
                markersize=8,
            )
            axis.set_xticks(
                range(4),
                [
                    "Original\n50 files",
                    "Probability adjustments\n58 files",
                    "Men’s retraining\n64 files",
                    "Women’s retraining\n70 files",
                ],
            )
            for i, value in enumerate(history.best_so_far_brier):
                axis.annotate(
                    f"{value:.7f}",
                    (i, value),
                    xytext=(0, 13),
                    textcoords="offset points",
                    ha="center",
                    color=INK,
                )
            axis.set_ylim(0.12215, 0.12308)
            axis.set_ylabel("Best observed Brier", labelpad=12)
            axis.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:.4f}"))
            axis.grid(axis="y", color=GRID)
            fig.subplots_adjust(left=0.10, right=0.95, top=0.83, bottom=0.19)
            title = "Small gains across four completed batches"
        for spine in axis.spines.values():
            spine.set_visible(False)
        fig.text(0.055, 0.93, title, fontsize=21, weight="bold", color=INK)
        fig.text(
            0.055,
            0.875,
            "March Machine Learning Mania 2026  /  Final observed results",
            fontsize=11,
            color=BLUE,
        )
        fig.text(
            0.055,
            0.04,
            "Late submissions · retrospective selection · no prospective ranking claim",
            fontsize=10,
            color=BLUE,
        )
        fig.savefig(folder / f"{name}.png", dpi=150, facecolor="white")
        plt.close(fig)
    table = frame[["filename", "batch", "private_brier"]].to_html(
        index=False, float_format=lambda x: f"{x:.7f}", escape=True
    )
    plots = "\n".join(
        fig.to_html(
            full_html=False,
            include_plotlyjs=i == 0,
            div_id="figure_" + name,
            config={"responsive": True, "displaylogo": False},
        )
        for i, (name, fig) in enumerate(figs.items())
    )
    document = (root / "templates/final_results.html").read_text()
    (folder / "results.html").write_text(
        document.replace("WINNER_FILE", html.escape(WINNER))
        .replace("PLOTS", plots)
        .replace("TABLE", table)
    )
    atomic_json(
        folder / "figures.json",
        {
            name: digest(folder / name)
            for name in ["leaders.png", "progression.png", "results.html"]
        },
    )


def package(root: Path, archives: list[Path]) -> dict[str, Any]:
    summary, frame = review(root), scores(root)
    receipts = [
        json.loads((root / folder / name).read_text())
        for folder, name in [
            ("reports/submission_scores", "collection.json"),
            ("reports/prediction_challengers", "summary.json"),
            ("reports/women_challengers", "generation.json"),
        ]
    ]
    if len(archives) != 3 or any(
        digest(p) != r["sha256"] for p, r in zip(archives, receipts, strict=True)
    ):
        raise ValueError("Use the three exact preserved submission archives")
    inputs = {
        "scores": summary["fingerprint"],
        "archives": [r["sha256"] for r in receipts],
        "readme": digest(root / REPORT / "README.md"),
    }
    key = fingerprint(inputs)
    run = root / "outputs/final_results" / key
    log = EventLog(run / "events.jsonl")
    store = TaskStore(run, key, log, 15)

    def work(target: Path) -> list[Path]:
        contents: dict[str, bytes] = {}
        for archive in archives:
            with zipfile.ZipFile(archive) as z:
                if len(z.namelist()) != len(set(z.namelist())):
                    raise ValueError("Duplicate ZIP members")
                for name in z.namelist():
                    if name.startswith("m_") and name.endswith(".csv"):
                        if name in contents:
                            raise ValueError("Duplicate prediction filename")
                        contents[name] = z.read(name)
        if set(contents) != set(frame.filename):
            raise ValueError("Missing or extra submission bytes")
        baseline = None
        with zipfile.ZipFile(target / "final_submissions.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for index, row in enumerate(frame.itertuples()):
                data = contents[str(row.filename)]
                if len(data) != row.bytes or hashlib.sha256(data).hexdigest() != row.sha256:
                    raise ValueError("Submission differs from its original manifest")
                actual = pd.read_csv(io.BytesIO(data), float_precision="round_trip")
                baseline = actual if baseline is None else baseline
                validate_submission(actual, baseline)
                if len(actual) != 132133:
                    raise ValueError("Incomplete official submission")
                member = zipfile.ZipInfo(str(row.filename), date_time=(2026, 9, 9, 0, 0, 0))
                member.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(member, data)
                log.emit("submission_preserved", completed=index + 1, total=70)
            for name in ["kaggle_scores.csv", "summary.json", "provenance.json", "README.md"]:
                member = zipfile.ZipInfo(name, date_time=(2026, 9, 9, 0, 0, 0))
                member.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(member, (root / REPORT / name).read_bytes())
        (target / WINNER).write_bytes(contents[WINNER])
        with zipfile.ZipFile(target / "final_submissions.zip") as z:
            for row in frame.itertuples():
                if hashlib.sha256(z.read(str(row.filename))).hexdigest() != row.sha256:
                    raise ValueError("Packaged bytes differ")
        return [target / "final_submissions.zip", target / WINNER]

    saved = store.task("package", work)
    output = root / "submissions"
    output.mkdir(exist_ok=True)
    for name in ["final_submissions.zip", WINNER]:
        (output / name).write_bytes((saved / name).read_bytes())
    result = {
        "status": "verified",
        "fingerprint": key,
        "inputs": inputs,
        "files": 70,
        "new_model_fits": 0,
        "prediction_bytes_unchanged": True,
        "sha256": digest(saved / "final_submissions.zip"),
        "bytes": (saved / "final_submissions.zip").stat().st_size,
    }
    atomic_json(root / REPORT / "collection.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--archives", type=Path, nargs=3)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = review(root, write=args.write)
    if args.render:
        render(root)
    if args.check:
        for name, sha in json.loads((root / REPORT / "figures.json").read_text()).items():
            if digest(root / REPORT / name) != sha:
                raise ValueError("Figure or interactive report checksum mismatch")
    if args.archives:
        package(root, args.archives)
    print(
        json.dumps(
            {k: result[k] for k in ["status", "scored_files", "best_brier", "best_filename"]}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
