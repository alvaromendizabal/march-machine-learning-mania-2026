"""Assemble a public employer review without private data, credentials, or fitting.

Default mode requires only Python 3.12 and Node. Optional notebook generation uses
the locked development environment and a real Jupyter kernel.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path
from string import Template
from textwrap import dedent

from reliability_demo import demonstrate

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "portfolio/acquisition_progress.json"
SCORE = ROOT / "reports/champion_result/kaggle_record.json"
NOTEBOOK = ROOT / "portfolio/engineering_review.ipynb"
FIELDS = {
    "schema_version",
    "evidence_type",
    "reviewed_on",
    "review_timezone",
    "execution",
    "status",
    "scope",
    "provenance",
    "box_scores",
    "team_seasons",
    "venue",
    "execution_counters",
    "interpretation",
}
BOX_FIELDS = {
    "original_missing",
    "previous_recovered",
    "recovered",
    "new_recovered",
    "remaining",
    "unresolved",
    "unverified",
    "quarantined",
    "strict_historical_admissions",
    "by_season",
}
VENUE_FIELDS = {
    "planned_units",
    "completed_units",
    "unique_new_captures",
    "source_errors",
    "qualified_editions",
    "qualified_home_pods",
    "dated_court_assignments",
    "women_rows_required",
    "women_rows_qualified",
    "women_rows_unknown",
    "men_rows_carried",
    "measure",
}


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_snapshot(d: dict) -> dict:
    """Enforce a narrow public schema and explicit, internally consistent denominators."""
    require(set(d) == FIELDS, "Unexpected snapshot fields")
    require(d["schema_version"] == 1, "Unknown snapshot schema")
    require(d["evidence_type"] == "OWNER_EXECUTION_AGGREGATES", "Unknown evidence class")
    require(d["status"] in {"SUCCESS", "PARTIAL", "FAILED", "STOPPED"}, "Unknown execution status")
    b, v, t = (d[k] for k in ("box_scores", "venue", "team_seasons"))
    c, i, p = (d[k] for k in ("execution_counters", "interpretation", "provenance"))
    require(set(b) == BOX_FIELDS and set(v) == VENUE_FIELDS, "Unexpected source fields")
    require(set(t) == {"total", "complete", "affected", "measure"}, "Unexpected history fields")
    require(
        set(c)
        == {
            "elapsed_seconds",
            "source_elapsed_seconds",
            "source_http_requests",
            "venue_http_requests",
            "new_model_fits",
            "new_submissions",
            "champion_changed",
            "all_aggregate_caps_disabled",
        },
        "Unexpected execution fields",
    )
    require(
        set(i)
        == {
            "acquisition_milestone_completed",
            "full_model_study_completed",
            "prospective_validation_claimed",
            "next_data_work",
        },
        "Unexpected interpretation fields",
    )
    require(
        set(p)
        == {
            "source",
            "manifest_members_verified",
            "manifest_checks",
            "raw_source_data_public",
            "public_checks",
        },
        "Unexpected provenance fields",
    )
    for group in (b, v, t):
        for key, value in group.items():
            if key not in {"by_season", "measure"}:
                require(type(value) is int and value >= 0, "Invalid count: " + key)
    require(b["recovered"] + b["remaining"] == b["original_missing"], "Box denominator changed")
    require(b["previous_recovered"] + b["new_recovered"] == b["recovered"], "Delta disagrees")
    require(
        sum(b[k] for k in ("unresolved", "unverified", "quarantined")) == b["remaining"],
        "Residual states do not partition the gap",
    )
    require(b["strict_historical_admissions"] <= b["recovered"], "Admissions exceed recovery")
    seasons = b["by_season"]
    require(len({r["season"] for r in seasons}) == len(seasons), "Duplicate season")
    for row in seasons:
        require(
            set(row) == {"season", "original_missing", "recovered", "remaining"},
            "Unexpected season fields",
        )
        require(all(type(x) is int and x >= 0 for x in row.values()), "Invalid season counts")
        require(
            row["recovered"] + row["remaining"] == row["original_missing"],
            "Season denominator changed",
        )
    for key in ("original_missing", "recovered", "remaining"):
        require(sum(row[key] for row in seasons) == b[key], "Season totals disagree")
    require(t["complete"] + t["affected"] == t["total"], "History denominator changed")
    require(
        v["women_rows_qualified"] + v["women_rows_unknown"] == v["women_rows_required"],
        "Women's representation denominator changed",
    )
    require(v["completed_units"] <= v["planned_units"], "Units exceed the plan")
    require(v["source_errors"] <= v["completed_units"], "Errors exceed attempts")
    require(v["qualified_home_pods"] <= v["dated_court_assignments"], "Home facts exceed courts")
    require(
        c["new_model_fits"] == c["new_submissions"] == 0 and c["champion_changed"] is False,
        "This acquisition snapshot cannot claim a new model or score",
    )
    require(
        i["full_model_study_completed"] is False and i["prospective_validation_claimed"] is False,
        "Unsupported scientific completion claim",
    )
    require(p["raw_source_data_public"] is False, "Raw disclosure is outside this public schema")
    for key in ("elapsed_seconds", "source_elapsed_seconds"):
        require(
            type(c[key]) in (float, int) and math.isfinite(c[key]) and c[key] >= 0,
            "Invalid duration",
        )
    for key in ("source_http_requests", "venue_http_requests", "new_model_fits", "new_submissions"):
        require(type(c[key]) is int and c[key] >= 0, "Invalid execution count")
    return d


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
    }
    return Template((ROOT / "tools/review_template.html").read_text()).substitute(values)


def run_review(output: Path) -> dict:
    require(
        output.resolve().is_relative_to((ROOT / "outputs").resolve()),
        "Review output must stay under outputs/",
    )
    output.mkdir(parents=True, exist_ok=True)
    d = load_snapshot()
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
        "scored_result": score,
        "synthetic_reliability": reliability,
        "checks": checks,
        "source_hashes": {
            "acquisition_progress.json": sha(SOURCE),
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
        from reliability_demo import demonstrate
        import pandas as pd
        from IPython.display import display
        d = load_snapshot()
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

        All 72 venue units were attempted and 62 new source bodies were captured. Source processing
        recorded 27 errors; only six of 583 required women's representation rows qualified.
        The 602 men's rows are carried controls. This is useful partial progress with an execution
        defect, not a completed model study.
        """),
        code("""
        measures = ['completed_units', 'unique_new_captures', 'source_errors',
                    'women_rows_qualified', 'women_rows_unknown']
        display(pd.DataFrame([{'Measure': k, 'Count': d['venue'][k]} for k in measures]))
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
        sum("application/vnd.plotly.v1+json" in o.get("data", {}) for o in outputs) == 1,
        "Persisted interactive figure missing",
    )
    require(sum("image/png" in o.get("data", {}) for o in outputs) == 1, "Static fallback missing")
    NOTEBOOK.write_text(nb.writes(book))
    return {
        "status": "PASS",
        "actual_kernel_execution": True,
        "code_cells": 4,
        "plotly_outputs": 1,
        "png_fallbacks": 1,
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
