"""Assemble a public employer review without private data, credentials, or fitting.

Default mode requires only Python 3.12 and Node. Optional notebook generation uses
the locked development environment and a real Jupyter kernel.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from string import Template
from textwrap import dedent

from evidence_contracts import require, validate_snapshot
from evidence_history import HISTORY, load_history, render_history_panel, summarize_history
from qualification_frontier import (
    FRONTIER,
    load_frontier,
    render_frontier_panel,
    summarize_frontier,
)
from reliability_demo import demonstrate

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "portfolio/acquisition_progress.json"
SCORE = ROOT / "reports/champion_result/kaggle_record.json"
NOTEBOOK = ROOT / "portfolio/engineering_review.ipynb"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_snapshot() -> dict:
    return validate_snapshot(json.loads(SOURCE.read_text()))


def render_report(report: dict) -> str:
    d, r, score = report["acquisition"], report["synthetic_reliability"], report["scored_result"]
    b, v = d["box_scores"], d["venue"]
    rows = "".join(
        f"<tr><td>{html.escape(x['name'])}</td>"
        f"<td class='{x['status'].lower()}'>{x['status']}</td>"
        f"<td>{x['elapsed_seconds']:.2f}s</td></tr>"
        for x in report["checks"]
    )
    values = {
        "status": html.escape(report["status"]),
        "date": html.escape(d["reviewed_on"]),
        "brier": f"{score['public_brier']:.7f}",
        "recovered": b["recovered"],
        "original": b["original_missing"],
        "remaining": b["remaining"],
        "qualified": v["women_rows_qualified"],
        "required": v["women_rows_required"],
        "unknown": v["women_rows_unknown"],
        "resume_computed": r["resume_computed"],
        "resume_reused": r["resume_reused"],
        "warm_computed": r["warm_computed"],
        "rows": rows,
        "history": render_history_panel(report["execution_history"]),
        "frontier": render_frontier_panel(report["qualification_frontier"]),
    }
    return Template((ROOT / "tools/review_template.html").read_text()).substitute(values)


def run_review(output: Path) -> dict:
    require(
        output.resolve().is_relative_to((ROOT / "outputs").resolve()),
        "Review output must stay under outputs/",
    )
    output.mkdir(parents=True, exist_ok=True)
    d = load_snapshot()
    history = summarize_history(load_history())
    frontier = summarize_frontier(load_frontier(), d)
    score = json.loads(SCORE.read_text())
    require(
        score["record_kind"] == "NORMALIZED_HISTORICAL_KAGGLE_RESULT"
        and score["evaluation_context"] == "LATE_RETROSPECTIVE_2026",
        "Scored evidence context changed",
    )
    reliability = demonstrate()
    commands = [
        (
            "Synthetic forecast and scoring",
            [sys.executable, "tools/reproduce_public.py", "--check"],
        ),
        (
            "Historical receipt arithmetic",
            [sys.executable, "portfolio/reproduce_release.py", "--check"],
        ),
        (
            "Recovery and timing failure contracts",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tools",
                "-p",
                "test_reliability_demo.py",
            ],
        ),
        (
            "Current aggregate boundaries",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tools",
                "-p",
                "test_review_project.py",
            ],
        ),
        (
            "Execution history and progress accounting",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tools",
                "-p",
                "test_evidence_history.py",
            ],
        ),
        (
            "Qualification frontier and parent binding",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tools",
                "-p",
                "test_qualification_frontier.py",
            ],
        ),
        (
            "Qualification explorer controls",
            [shutil.which("node") or "node", "tools/test_qualification_frontier.mjs"],
        ),
        (
            "Exact bracket engine",
            [shutil.which("node") or "node", "tools/test_public_demo_engine.mjs"],
        ),
        ("Actual demo handlers", [shutil.which("node") or "node", "tools/test_public_demo.mjs"]),
        ("Deterministic offline package", [sys.executable, "tools/package_public_demo.py"]),
    ]
    checks = []
    for index, (name, command) in enumerate(commands):
        started = time.monotonic()
        try:
            result = subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True, timeout=120, check=False
            )
            status = "PASS" if result.returncode == 0 else "FAIL"
            log = result.stdout + result.stderr
        except (OSError, subprocess.TimeoutExpired) as exc:
            status, log = "FAIL", type(exc).__name__
        (output / f"check_{index + 1}.txt").write_text(log)
        checks.append(
            {"name": name, "status": status, "elapsed_seconds": time.monotonic() - started}
        )
    report = {
        "schema_version": 1,
        "status": "PASS" if all(c["status"] == "PASS" for c in checks) else "FAIL",
        "acquisition": d,
        "execution_history": history,
        "qualification_frontier": frontier,
        "scored_result": score,
        "synthetic_reliability": reliability,
        "checks": checks,
        "source_hashes": {
            "acquisition_progress.json": sha(SOURCE),
            "execution_history.json": sha(HISTORY),
            "qualification_frontier.json": sha(FRONTIER),
            "kaggle_record.json": sha(SCORE),
        },
        "network_requests": 0,
        "private_model_fits": 0,
    }
    (output / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "index.html").write_text(render_report(report))
    return report


def build_notebook(kernel: str) -> dict:
    import nbformat as nb
    from nbclient import NotebookClient

    def md(text):
        return nb.v4.new_markdown_cell(dedent(text).strip())

    def code(text):
        return nb.v4.new_code_cell(dedent(text).strip())

    cells = [
        md("""
        # Engineering evidence behind a probability forecast

        **Alvaro Mendizabal · source qualification · reproducible evaluation · reliable execution**

        Three evidence classes remain distinct: an inherited retrospective scored result,
        current owner-execution aggregates, and an independently authored synthetic reliability
        example. This notebook executes public checks; private recipes and source banks
        stay private.
        """),
        code("""
        from pathlib import Path
        import sys, json
        root = Path.cwd()
        if not (root / 'tools').is_dir():
            root = root.parent
        sys.path.insert(0, str(root / 'tools'))
        from review_project import load_snapshot
        from evidence_history import load_history, summarize_history
        from qualification_frontier import load_frontier, summarize_frontier
        from reliability_demo import demonstrate
        import pandas as pd
        from IPython.display import display
        d = load_snapshot()
        history = summarize_history(load_history())
        frontier = summarize_frontier(load_frontier(), d)
        display(pd.DataFrame(d['box_scores']['by_season']))
        print('Execution status:', d['status'])
        print('Strict historical admissions:', d['box_scores']['strict_historical_admissions'])
        """),
        md("""
        ## Numerical coverage has an explicit denominator

        The recovered overlay contains 133 of 221 originally missing numerical records;
        88 remain. Numerical recovery does not establish historical timing: strict historical
        admission remains zero. These are audited owner-run aggregates, not a public re-acquisition.
        """),
        code("""
        import io, base64
        import matplotlib.pyplot as plt
        import plotly.graph_objects as go
        rows = d['box_scores']['by_season']
        x = [str(r['season']) for r in rows]
        recovered = [r['recovered'] for r in rows]
        missing = [r['remaining'] for r in rows]
        fig = go.Figure()
        fig.add_bar(x=x, y=recovered, name='Numerical candidates', marker_color='#1c5ba8')
        fig.add_bar(x=x, y=missing, name='Missing', marker_color='#bdc8d8')
        fig.update_layout(title='Women detailed-result gap', barmode='stack', width=960,
                          height=480, template='plotly_white', yaxis_title='Games')
        static, ax = plt.subplots(figsize=(10, 5), layout='constrained')
        ax.bar(x, recovered, label='Numerical candidates', color='#1c5ba8')
        ax.bar(x, missing, bottom=recovered, label='Missing', color='#bdc8d8')
        ax.set(title='Women detailed-result gap', ylabel='Games')
        ax.legend()
        image = io.BytesIO()
        static.savefig(image, format='png', dpi=120)
        plt.close(static)
        display({'application/vnd.plotly.v1+json': json.loads(fig.to_json()),
                 'image/png': base64.b64encode(image.getvalue()).decode()}, raw=True)
        """),
        md("""
        ## Acquisition and qualification are separate milestones

        The versioned history preserves a partial execution, its reconciliation and the next
        expanded acquisition. Each transition distinguishes additions, verified reuse and
        reparsing. The chart keeps the unknown population visible.
        Acquisition SUCCESS does not establish a completed model study or historical eligibility.
        The men's rows remain carried controls, separate from new women's qualifications.
        """),
        code("""
        measures = ['completed_units', 'unique_new_captures', 'source_errors',
                    'women_rows_qualified', 'women_rows_unknown']
        display(pd.DataFrame([{'Measure': k, 'Count': d['venue'][k]} for k in measures]))
        observed = history['observations']
        labels = [r['execution'] for r in observed]
        known = [r['women_qualified'] for r in observed]
        unknown = [r['women_unknown'] for r in observed]
        progress = go.Figure()
        progress.add_bar(x=labels, y=known, name='Qualified', marker_color='#008477')
        progress.add_bar(x=labels, y=unknown, name='Unknown', marker_color='#c8d6e4')
        progress.update_layout(title='Women venue qualification: fixed 583-row population',
                               barmode='stack', width=960, height=440,
                               template='plotly_white', yaxis_title='Representation rows')
        static, ax = plt.subplots(figsize=(10, 4.6), layout='constrained')
        ax.bar(labels, known, label='Qualified', color='#008477')
        ax.bar(labels, unknown, bottom=known, label='Unknown', color='#c8d6e4')
        ax.set(title='Women venue qualification: fixed 583-row population',
               ylabel='Representation rows')
        ax.legend()
        image = io.BytesIO()
        static.savefig(image, format='png', dpi=120)
        plt.close(static)
        display({'application/vnd.plotly.v1+json': json.loads(progress.to_json()),
                 'image/png': base64.b64encode(image.getvalue()).decode()}, raw=True)
        display(pd.DataFrame([history['latest_change']]))
        """),
        md("""
        ## The remaining gap has a shape

        The frontier partitions each frozen edition into disjoint qualification states and
        binds the exact current aggregate snapshot. Court-qualified rows lacking home context
        need different evidence from rows without a qualified court. Counts describe played-game
        representation rows, not distinct arenas or promised acquisitions.

        Classification follows the original court-first contract. A row without a qualified court
        may still have a standalone home witness: both dimensions unqualified does not mean no
        source facts exist. The public validator checks accounting, not private provider bodies.
        """),
        code("""
        frame = pd.DataFrame(frontier['editions']).set_index('season')
        display(frame)
        groups = [('qualified', 'Qualified', '#008477'),
                  ('missing_home_only', 'Court qualified; home unresolved', '#bf7b20'),
                  ('missing_court_only', 'Home qualified; court unresolved', '#7264b5'),
                  ('missing_both', 'Court and context unqualified', '#d4deea')]
        frontier_plot = go.Figure()
        static, ax = plt.subplots(figsize=(10, 5.2), layout='constrained')
        bottom = [0] * len(frame)
        labels = [str(year) for year in frame.index]
        for key, label, color in groups:
            values = frame[key].tolist()
            frontier_plot.add_bar(x=labels, y=values, name=label, marker_color=color)
            ax.bar(labels, values, bottom=bottom, label=label, color=color)
            bottom = [a + b for a, b in zip(bottom, values)]
        frontier_plot.update_layout(title='What still blocks women venue qualification?',
                                    barmode='stack', width=960, height=500,
                                    template='plotly_white', yaxis_title='Representation rows')
        ax.set(title='What still blocks women venue qualification?',
               ylabel='Representation rows', xlabel='Tournament edition')
        ax.legend(fontsize=8, loc='upper left', bbox_to_anchor=(0, 1.23), ncol=2)
        image = io.BytesIO()
        static.savefig(image, format='png', dpi=120)
        plt.close(static)
        display({'application/vnd.plotly.v1+json': json.loads(frontier_plot.to_json()),
                 'image/png': base64.b64encode(image.getvalue()).decode()}, raw=True)
        print('Bound snapshot SHA-256:', frontier['snapshot_sha256'])
        print('Complete editions:', frontier['completed_editions'], 'of', len(frame))
        """),
        md("""
        ## Execute the recovery contract

        The authored example commits one unit, stops deliberately, resumes the remaining three,
        then reuses all four without recomputing qualification. It rejects altered checkpoint
        content. Tests separately spy on actual qualification calls: cold four, stop one,
        resume three, warm zero. Input fingerprints and digests are still verified on reuse.
        Late and unknown timestamps never become eligible. No network or model fitting occurs.
        """),
        code("""
        result = demonstrate()
        display(pd.DataFrame([result]))
        assert result['warm_computed'] == 0 and result['corruption_rejected']
        assert result['qualification_counts'] == {
            'ELIGIBLE': 2, 'LATE_SOURCE': 1, 'UNKNOWN_TIMING': 1}
        print('ENGINEERING_REVIEW_COMPLETE — public evidence; zero model fits')
        """),
    ]
    book = nb.v4.new_notebook(
        cells=cells,
        metadata={"kernelspec": {"name": kernel, "display_name": "Python 3", "language": "python"}},
    )
    NotebookClient(
        book, timeout=120, kernel_name=kernel, resources={"metadata": {"path": str(ROOT)}}
    ).execute()
    nb.validate(book)
    outputs = [o for c in book.cells for o in c.get("outputs", [])]
    require(not any(o.output_type == "error" for o in outputs), "Notebook execution failed")
    require("ENGINEERING_REVIEW_COMPLETE" in str(book.cells[-1].outputs), "Notebook incomplete")
    require(
        sum("application/vnd.plotly.v1+json" in o.get("data", {}) for o in outputs) == 3,
        "Persisted interactive figure missing",
    )
    require(sum("image/png" in o.get("data", {}) for o in outputs) == 3, "Static fallback missing")
    NOTEBOOK.write_text(nb.writes(book))
    return {
        "status": "PASS",
        "actual_kernel_execution": True,
        "code_cells": 5,
        "plotly_outputs": 3,
        "png_fallbacks": 3,
        "model_fits": 0,
        "notebook_sha256": sha(NOTEBOOK),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Run the same full public review")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/review")
    parser.add_argument("--build-notebook", action="store_true")
    parser.add_argument("--kernel", default="march-portfolio")
    args = parser.parse_args()
    if args.build_notebook:
        print(json.dumps(build_notebook(args.kernel), indent=2))
        return 0
    report = run_review(args.output)
    print(
        json.dumps(
            {
                "status": report["status"],
                "checks": report["checks"],
                "report": str(args.output / "index.html"),
            },
            indent=2,
        )
    )
    return int(report["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
