"""Assemble an employer review without credentials, private data, or private fitting.

Default mode requires only Python 3.12 and Node. Optional notebook generation uses
the locked development environment and a real Jupyter kernel. The explicitly
synthetic temporal example performs three actual numerical fits on authored data.
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
from model_delivery_demo import run_demo as run_delivery_demo
from owner_replay import REPLAY, load_replay, render_replay_panel
from qualification_frontier import (
    FRONTIER,
    load_frontier,
    render_frontier_panel,
    summarize_frontier,
)
from reliability_demo import demonstrate
from source_readiness import SOURCE_READINESS, load_source_readiness, render_source_panel
from temporal_model_demo import DEFAULT_OUTPUT, calibration_svg, run_demo

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "portfolio/acquisition_progress.json"
SCORE = ROOT / "reports/champion_result/kaggle_record.json"
NOTEBOOK = ROOT / "portfolio/engineering_review.ipynb"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_snapshot() -> dict:
    return validate_snapshot(json.loads(SOURCE.read_text()))


def render_delivery_panel(receipt: dict) -> str:
    """Keep serving-contract evidence separate from training and private research."""
    require(
        receipt["status"] == "PASS" and receipt["scope"] == "SYNTHETIC_ONLY",
        "Synthetic delivery receipt missing",
    )
    require(
        receipt["new_model_fits"] == 0 and receipt["exact_prediction_parity"] is True,
        "Delivery must reuse frozen models without fitting",
    )
    return (
        "<section id='model-delivery' class='delivery-panel' aria-labelledby='delivery-title'>"
        "<div class='eyebrow'>Model delivery · fresh-process evidence</div>"
        "<h2 id='delivery-title'>A saved model is a contract, not just a file.</h2>"
        "<p>Reload three frozen teaching models in isolated Python processes with no trainer "
        "module, labels, network or private inputs. Validate the expected digest, exact schema, "
        "feature order, finite values and prediction clocks before inference.</p>"
        "<div class='grid'><article><span>Frozen artifacts loaded</span><strong>"
        f"{receipt['model_count']}</strong><span>No new model fits</span></article>"
        "<article><span>Byte-exact prediction parity</span><strong>"
        f"{receipt['predictions_checked']}</strong>"
        "<span>All three synthetic evaluation seasons</span>"
        "</article><article><span>Maximum probability difference</span><strong>"
        f"{receipt['maximum_absolute_probability_difference']:.1f}</strong>"
        "<span>Measured against frozen responses</span></article></div>"
        "<p><code>python tools/model_delivery_demo.py demo "
        "--out-dir outputs/model-delivery</code></p>"
        "<p>This is a tested local inference interface, not a deployed service, production SLA "
        "or claim about the private competition model. Altered artifacts, leaked outcomes and "
        "invalid clocks are rejected before producing a response.</p></section>"
    )


def render_temporal_panel(evaluation: dict) -> str:
    """Render actual synthetic learning separately from private owner aggregates."""
    require(evaluation["evidence_scope"] == "SYNTHETIC_ONLY", "Synthetic scope missing")
    require(evaluation["owner_research_fits"] == 0, "Synthetic work is not owner research")
    metrics = evaluation["pooled_game_weighted"]
    rows = "".join(
        f"<tr><th scope='row'>{fold['evaluation_season']}</th>"
        f"<td>{', '.join(map(str, fold['training_seasons']))}</td>"
        f"<td>{fold['physical_training_games']}</td>"
        f"<td>{fold['physical_evaluation_games']}</td>"
        f"<td>{evaluation['per_season'][str(fold['evaluation_season'])]['brier']:.6f}</td>"
        "</tr>"
        for fold in evaluation["folds"]
    )
    return (
        "<section id='temporal-model' class='temporal-panel' aria-labelledby='temporal-title'>"
        "<div class='eyebrow'>Runnable learning system · synthetic only</div>"
        "<h2 id='temporal-title'>A model that really trains. A boundary you can test.</h2>"
        "<p>Fit a regularized logistic model on earlier fictional seasons, freeze its "
        "predictions, then score later seasons. Scaling sees training rows only; late "
        "observations and unavailable labels are rejected. This compact teaching "
        "implementation is independent of the private competition system.</p>"
        "<div class='grid'><article><span>Actual synthetic fits</span>"
        f"<strong>{evaluation['synthetic_model_fits']}</strong>"
        "<span>Zero owner research fits; no private data</span></article>"
        "<article><span>Synthetic out-of-season games</span>"
        f"<strong>{metrics['physical_games']}</strong>"
        "<span>One forecast per physical game</span></article>"
        "<article><span>Synthetic Brier / log loss</span>"
        f"<strong class='metric-pair'>{metrics['brier']:.4f} / {metrics['log_loss']:.4f}</strong>"
        "<span>Teaching diagnostics, not NCAA results</span></article></div>"
        "<div class='replay-table' tabindex='0' role='region' "
        "aria-label='Synthetic temporal folds'>"
        "<table><caption>Expanding windows; fixed teaching settings, no evaluation tuning</caption>"
        "<thead><tr><th scope='col'>Forecast season</th><th scope='col'>Training seasons</th>"
        "<th scope='col'>Training games</th><th scope='col'>Evaluation games</th>"
        "<th scope='col'>Synthetic Brier</th></tr></thead><tbody>"
        + rows
        + "</tbody></table></div><figure class='reliability-figure'>"
        + calibration_svg(evaluation).decode()
        + "<figcaption>Five fixed probability bins; the small authored sample is not "
        "evidence of prospective calibration or competitive advantage.</figcaption></figure>"
        "<p>The public artifacts include the complete fictional inputs, predictions, "
        "fitted coefficients, training-only scalers and exact content manifest. "
        "The existing unfitted rating example remains a separate baseline.</p>"
        "<p><code>python tools/temporal_model_demo.py --check</code></p></section>"
    )


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
        "owner_replay": render_replay_panel(report["owner_replay"]),
        "latest_date": html.escape(report["owner_replay"]["reviewed_on"]),
        "current_date": html.escape(report["source_readiness"]["reviewed_on"]),
        "source_readiness": render_source_panel(report["source_readiness"]),
        "temporal_model": render_temporal_panel(report["synthetic_temporal_model"]),
        "model_delivery": render_delivery_panel(report["synthetic_model_delivery"]),
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
    replay = load_replay()
    source_readiness = load_source_readiness()
    temporal_model = run_demo(DEFAULT_OUTPUT, check=True)
    delivery = run_delivery_demo(output / "model-delivery")
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
            "Actual synthetic training, time splits and inference contracts",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tools",
                "-p",
                "test_temporal_model_demo.py",
            ],
        ),
        (
            "V019 custody and V020 source-diagnostic eligibility boundaries",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tools",
                "-p",
                "test_source_readiness.py",
            ],
        ),
        (
            "Frozen artifact loading, isolated inference and fail-closed contracts",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tools",
                "-p",
                "test_model_delivery_demo.py",
            ],
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
            "Owner replay, model selection and storage accounting",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "tools",
                "-p",
                "test_owner_replay.py",
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
        "owner_replay": replay,
        "source_readiness": source_readiness,
        "scored_result": score,
        "synthetic_reliability": reliability,
        "synthetic_temporal_model": temporal_model,
        "synthetic_model_delivery": delivery,
        "checks": checks,
        "source_hashes": {
            "acquisition_progress.json": sha(SOURCE),
            "execution_history.json": sha(HISTORY),
            "qualification_frontier.json": sha(FRONTIER),
            "owner_replay.json": sha(REPLAY),
            "kaggle_record.json": sha(SCORE),
            "source_readiness.json": sha(SOURCE_READINESS),
            "tools/source_readiness.py": sha(ROOT / "tools/source_readiness.py"),
            "tools/temporal_model_demo.py": sha(ROOT / "tools/temporal_model_demo.py"),
            "tools/model_delivery_demo.py": sha(ROOT / "tools/model_delivery_demo.py"),
            "src/march_mania/public_reference.py": sha(
                ROOT / "src/march_mania/public_reference.py"
            ),
            "examples/temporal_model_demo/evaluation.json": sha(DEFAULT_OUTPUT / "evaluation.json"),
            "examples/temporal_model_demo/manifest.json": sha(DEFAULT_OUTPUT / "manifest.json"),
        },
        "network_requests": 0,
        "private_model_fits": 0,
        "synthetic_example_model_fits": 3,
        "fit_count_scope": "Three example folds; contract-test fits are separate synthetic tests.",
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
        dated owner-execution aggregates, and independently authored synthetic examples.
        This notebook executes three actual synthetic model fits and the recovery contract.
        No owner research fit is created; private recipes and source banks stay private.

        ## Current source audit: integrity is necessary, not sufficient

        V019 verified all 67 registered source bodies and remains an immutable **PARTIAL**
        historical record. V020 then completed two narrowly registered diagnostics: the failed
        payload is a 2,283-record CSV; the Parquet contains 1,629 season-2027 candidate rows,
        with every game JSON URL null. Those format observations are not proof of source,
        basketball identity, physical-game alignment or historical feature availability.
        Seven tiny archive text members remain semantically uninspected. The original
        67 object / 3,573 request debts and zero new historical feature admissions are unchanged.

        These public aggregate checks do not reread the private bodies or manufacture clocks.
        """),
        code("""
        from pathlib import Path
        import sys, json, io, base64, hashlib
        root = Path.cwd()
        if not (root / 'tools').is_dir():
            root = root.parent
        sys.path.insert(0, str(root / 'tools'))
        from review_project import load_snapshot
        from evidence_history import load_history, summarize_history
        from qualification_frontier import load_frontier, summarize_frontier
        from reliability_demo import demonstrate
        from source_readiness import load_source_readiness
        import pandas as pd
        import matplotlib.pyplot as plt
        import plotly.graph_objects as go
        from IPython.display import display
        d = load_snapshot()
        history = summarize_history(load_history())
        frontier = summarize_frontier(load_frontier(), d)
        source = load_source_readiness()
        source_audit = source['source_audit']
        followup = source['latest_followup']
        print('Historical source audit:', source['execution'], source['status'])
        print('Latest follow-up:', followup['execution'], followup['status'])
        display(pd.DataFrame([{
            'Complete body verification': source_audit['complete_bodies_verified'],
            'Registered locations': source_audit['registered_locations'],
            'Unresolved requests': source_audit['unresolved_requests'],
            'New historical features': source_audit['historical_features_admitted'],
            'New owner fits': source_audit['new_private_model_fits']}]))
        source_categories = ['JSON traversed', 'ZIP inspected', 'Parquet schema only',
                             'Prior content analysis reused', 'Payload interpretation failed']
        source_counts = [source_audit['json_interpretations'], source_audit['zip_interpretations'],
                         source_audit['parquet_schema_only'],
                         source_audit['reused_interpretations'],
                         source_audit['payload_uninterpreted']]
        colors = ['#1c5ba8', '#1c5ba8', '#bf7b20', '#7389a1', '#b6484d']
        assert sum(source_counts) == 67
        source_plot = go.Figure(go.Bar(y=source_categories, x=source_counts, orientation='h',
                                       marker_color=colors, text=source_counts,
                                       textposition='outside'))
        source_plot.update_layout(title='V019: integrity passed; semantic admission still blocked',
                                  width=960, height=460, template='plotly_white',
                                  xaxis_title='Registered object locations',
                                  xaxis_range=[0, 45], margin=dict(l=240))
        static, ax = plt.subplots(figsize=(10, 4.8), layout='constrained')
        ax.barh(source_categories, source_counts, color=colors)
        for index, count in enumerate(source_counts):
            ax.text(count + .4, index, str(count), va='center')
        ax.set(xlim=(0, 45), xlabel='Registered object locations',
               title='V019: integrity passed; semantic admission still blocked')
        image = io.BytesIO()
        static.savefig(image, format='png', dpi=120)
        plt.close(static)
        display({'application/vnd.plotly.v1+json': json.loads(source_plot.to_json()),
                 'image/png': base64.b64encode(image.getvalue()).decode()}, raw=True)
        print('ZIP inspection includes 7 tiny text members not semantically interpreted.')
        print('V020 CSV records:', followup['csv']['records'])
        print('V020 Parquet rows:', followup['parquet']['rows'])
        print('These are records, not independently verified unique basketball games.')
        print('V020 new historical features:', followup['new_historical_features'])
        print('Actual billing:', source['resources']['aws_cost'])
        print('V018 completed frozen replay, 925 games; all later labels exposed:')
        display(pd.DataFrame(source['matched_replay']['aggregate_scores']).set_index('arm'))
        print('218 feature-bearing games; 707 unchanged control fallbacks; no promotion.')
        print('Both candidates passed 0/5 screens; every paired interval includes zero.')
        print('Aggregate source SHA-256:', hashlib.sha256(
            (root / 'portfolio/source_readiness.json').read_bytes()).hexdigest())
        """),
        md("""
        ## Actual learning on an inspectable, fictional temporal fixture

        The public model really fits coefficients: train-only symmetric scaling followed by
        L2-regularized logistic regression. The configuration is fixed before evaluation:
        250 gradient steps, learning rate 0.12, penalty 0.04, no early stopping or search.
        Expanding training windows use only earlier seasons and labels available before fitting.
        Three later seasons contribute 66 physical games each, for 198 synthetic forecasts.

        Mirrored representations receive half weight, retain one physical-game unit and enforce
        team-order symmetry. The latest observation must have been published by the forecast
        cutoff, at least one hour before the game. Outcome fields cannot enter inference.
        This is a separate teaching implementation, not a public version of the private recipe.

        The following cell **executes all three fits**, freezes predictions before scoring and
        displays actual results. Dates are authored fixture clocks, not historical source proof.
        Synthetic scores are not NCAA performance, a new submission or prospective validation.
        """),
        code("""
        from temporal_model_demo import run_demo
        learned = run_demo()
        assert learned['evidence_scope'] == 'SYNTHETIC_ONLY'
        assert learned['synthetic_model_fits'] == 3 and learned['owner_research_fits'] == 0
        assert learned['network_requests'] == learned['private_artifacts_read'] == 0
        display(pd.DataFrame(learned['folds'])[[
            'evaluation_season', 'training_seasons', 'physical_training_games',
            'physical_evaluation_games', 'train_evaluation_ID_intersection',
            'training_labels_available_before_fit', 'scaler_fit_on_training_only']])
        display(pd.DataFrame(learned['per_season']).T)
        display(pd.DataFrame([learned['pooled_game_weighted']])
                .rename(index={0: 'Synthetic pooled'}))
        bins = [item for item in learned['reliability']['bins'] if item['count']]
        x = [item['mean_prediction'] for item in bins]
        y = [item['observed_frequency'] for item in bins]
        counts = [item['count'] for item in bins]
        calibration = go.Figure()
        calibration.add_scatter(x=[0, 1], y=[0, 1], mode='lines', name='Reference diagonal',
                                line=dict(color='#7389a1', dash='dash'))
        calibration.add_scatter(x=x, y=y, mode='lines+markers', name='Synthetic reliability',
                                text=[f'n={count}' for count in counts],
                                line=dict(color='#008477'), marker_size=10)
        calibration.update_layout(title='Synthetic only: does confidence match frequency?',
                                   width=960, height=500, template='plotly_white',
                                   xaxis_title='Mean forecast probability',
                                   yaxis_title='Observed frequency',
                                   xaxis_range=[0, 1], yaxis_range=[0, 1])
        static, ax = plt.subplots(figsize=(10, 5.2), layout='constrained')
        ax.plot([0, 1], [0, 1], '--', color='#7389a1', label='Reference diagonal')
        ax.plot(x, y, '-o', color='#008477', label='Synthetic reliability')
        for px, py, count in zip(x, y, counts):
            ax.annotate(f'n={count}', (px, py), xytext=(8, 8), textcoords='offset points')
        ax.set(xlim=(0, 1), ylim=(0, 1), xlabel='Mean forecast probability',
               ylabel='Observed frequency',
               title='Synthetic only: does confidence match frequency?')
        ax.legend(loc='lower right')
        image = io.BytesIO()
        static.savefig(image, format='png', dpi=120)
        plt.close(static)
        display({'application/vnd.plotly.v1+json': json.loads(calibration.to_json()),
                 'image/png': base64.b64encode(image.getvalue()).decode()}, raw=True)
        print('Small authored sample, five fixed bins; not a calibration guarantee.')
        print('Synthetic prediction SHA-256:', learned['forecast_pin_before_scoring']['sha256'])
        print('Generator SHA-256:', hashlib.sha256(
            (root / 'tools/temporal_model_demo.py').read_bytes()).hexdigest())
        """),
        md("""
        ## Deliver the frozen artifact without importing the trainer

        Training and inference have different contracts. This cell loads the already committed
        public synthetic artifacts in three isolated Python processes and compares the complete
        response bytes with frozen expectations. No new fit occurs. Requests contain features,
        identities and clocks, never outcome labels. The pure loader validates the externally
        supplied SHA, exact schema, finite bounds, feature order and training-cutoff metadata.

        The interface is local and testable, not a deployed API or production-availability claim.
        The same inference module is used by the command line; there is no notebook-only path.
        """),
        code("""
        from model_delivery_demo import run_demo as run_delivery_demo
        delivery = run_delivery_demo()
        assert delivery['status'] == 'PASS' and delivery['scope'] == 'SYNTHETIC_ONLY'
        assert delivery['model_count'] == 3 and delivery['predictions_checked'] == 198
        assert delivery['exact_prediction_parity'] is True
        assert delivery['maximum_absolute_probability_difference'] == 0.0
        assert delivery['new_model_fits'] == delivery['network_requests'] == 0
        assert delivery['private_inputs_read'] == 0
        assert delivery['inference_loaded_training_module'] is False
        display(pd.DataFrame([{key: delivery[key] for key in (
            'model_count', 'predictions_checked', 'exact_prediction_parity',
            'maximum_absolute_probability_difference', 'new_model_fits',
            'network_requests', 'inference_loaded_training_module')}]))
        print('Fresh-process test:', delivery['fresh_process_test'])
        print('Inference module SHA-256:', hashlib.sha256(
            (root / 'src/march_mania/public_reference.py').read_bytes()).hexdigest())
        """),
        md("""
        ## Historical owner replay: the accepted control still wins development

        The October 30 V351 run (Pacific time) reused 302 fitted operations and completed
        the 925-game matched research replay without new fits. The overall run remains PARTIAL
        because owned market-source reconciliation is incomplete. Each challenger worsens
        development Brier; lower Brier in the exposed later window cannot justify promotion.

        Public aggregate checks cannot recreate paired uncertainty or source-level authentication
        without the withheld per-game evidence. Generic arm labels protect private recipes.
        The earlier source-qualification panels below retain their October 26 scope; they are
        not relabeled as a fresh census by this later replay.
        """),
        code("""
        from owner_replay import load_replay
        replay = load_replay()
        display(pd.DataFrame(replay['scorecards']).set_index('arm'))
        execution = replay['execution_accounting']
        print('Owner execution:', replay['execution'], replay['status'])
        print('Fits reused:', execution['research_fits_reused'] + execution['science_fits_reused'])
        print('New fits:', execution['new_model_fits'])
        print('Selected:', replay['decision']['selected_arm'])
        print('Complete broader project data:', replay['coverage']['broader_project_data_complete'])
        assert replay['cohort']['total_games'] == 925
        assert replay['cohort']['prediction_rows'] == 3700
        ledger = replay['execution_ledger']
        display(pd.DataFrame(ledger['records'])[['execution', 'status', 'evidence_level']])
        print('Recent twelve owner runs:', ledger['counts'])
        print('Latest addition:', ledger['latest_delta'])
        print('Complete all-time totals:', ledger['all_time_totals'])
        print('Completed workstreams counted separately:', ledger['latest_completed_workstreams'])
        """),
        md("""
        ## Historical systems comparison: consolidation cost stays visible

        The same 302 fitted operations and accepted scientific result were preserved.
        End-to-end elapsed time grew 35.98%, from 533.10 to 724.91 seconds.
        The odds phase improved 60.45%, from 201.17 to 79.57 seconds, with authenticated
        warm price reuse in 0.107 seconds. Consolidation took 582.02 seconds, including
        423.68 seconds of diagnostics. Actual allocated release was 243,220,480 bytes;
        final free space was 2,647,855,104 bytes, a net increase of only 1,417,216 bytes.

        All eight current diagnostics were authenticated. The complete scoped metadata census
        has 650,791 records: 587,969 regular files, 55,580 directories, 7,231 symlinks and
        11 explicit exceptions. It includes 1,583 immediate home entries before later moves,
        including 591 ZIPs and 450 PYZs. This is not a final post-action clean-layout claim.
        Sixty-seven historical roots moved with compatibility aliases; 204 were preserved,
        including 100 lease failures. The 472 notebook/HTML moves are cumulative prior work.
        The 29,590 duplicate candidate groups have a 4,972,310,528-byte upper bound, not
        qualified reclaimable space. Features, mutable roles and restoration contracts
        remain protected.

        These are sequential observations, not a controlled benchmark. Provider latency and
        background load were uncontrolled. Source GETs fell to 71, while downloaded bytes grew
        because all 71 remaining blockers were inspected. None closed. The cumulative product
        ledger's 3,482 current-endpoint rows are V350 work; V351 added zero quote rows and zero
        training admissions. Zero supported core rows do not prove empty provider payloads.
        Forced resource probes fell from 61,773 to 196; unchanged product requeues were zero.

        That dated twelve-run ledger has zero SUCCESS, eight PARTIAL and four STOPPED outcomes.
        Three completed workstreams do not create an overall success. Older V48 aggregate
        categories overlap; missing intervening history keeps current all-time totals unknown.
        V352 later added another PARTIAL. This historical chart is not the V020 source follow-up,
        a new run count or evidence that the current source debt has closed.
        """),
        code("""
        import io, base64
        import matplotlib.pyplot as plt
        import plotly.graph_objects as go
        from owner_replay import comparison_rows
        measured = pd.DataFrame(comparison_rows(replay))
        display(measured)
        display(pd.DataFrame([replay['storage']]).T.rename(columns={0: 'Observed'}))
        display(pd.DataFrame(replay['source_recovery']['products']))
        organization = replay['organization']
        display(pd.DataFrame([{
            'Cumulative notebook moves': organization['physically_moved'],
            'Historical roots moved now': organization['physical_historical_roots_moved'],
            'Root migration blockers': organization['root_migration_blockers'],
            'Protected index links': organization['protected_index_links'],
            'Private references': organization['private_references_without_browse_links'],
            'Files in home census': organization['census_files'],
            'Root entries in home census': organization['census_root_entries'],
            'Selected project roots': organization['selected_project_root_entries']}]))
        labels = ['Elapsed time', 'Odds duration', 'Odds GET responses',
                  'Odds HTTP attempts', 'Odds body bytes', 'Review return bytes']
        relative = (100 * measured['after'] / measured['before']).tolist()
        before_label = replay['comparison']['baseline']['execution'].upper()
        after_label = replay['execution'].upper()
        comparison = go.Figure()
        comparison.add_bar(y=labels, x=[100] * len(labels), name=before_label + ' reference',
                           orientation='h', marker_color='#d4deea')
        comparison.add_bar(y=labels, x=relative, name=after_label + ' observed', orientation='h',
                           marker_color='#008477')
        comparison.update_layout(title='Observed work relative to ' + before_label + ' (=100%)',
                                 barmode='group', width=960, height=500,
                                 template='plotly_white',
                                 xaxis_type='log',
                                 xaxis_title='Percent of prior observation (log scale)')
        static, ax = plt.subplots(figsize=(10, 5.2), layout='constrained')
        yy = list(range(len(labels)))
        ax.barh([v + .18 for v in yy], [100] * len(yy), height=.34,
                label=before_label + ' reference', color='#d4deea')
        ax.barh([v - .18 for v in yy], relative, height=.34,
                label=after_label + ' observed', color='#008477')
        ax.set_xscale('log')
        ax.set(yticks=yy, yticklabels=labels, xlabel='Percent of prior observation (log scale)',
               title='Observed work relative to ' + before_label
                     + ' (=100%); not a controlled benchmark')
        ax.legend(loc='lower right')
        image = io.BytesIO()
        static.savefig(image, format='png', dpi=120)
        plt.close(static)
        display({'application/vnd.plotly.v1+json': json.loads(comparison.to_json()),
                 'image/png': base64.b64encode(image.getvalue()).decode()}, raw=True)
        assert replay['systems']['negative_cache_hits'] == 2
        assert replay['source_recovery']['new_historical_selection_records'] == 0
        assert replay['storage']['unique_scientific_bytes_discarded'] == 0
        """),
        md("""
        ## Numerical coverage has an explicit denominator

        The recovered overlay contains 133 of 221 originally missing numerical records;
        88 remained at the October 26 acquisition snapshot. Numerical recovery does not establish
        historical timing: strict historical
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
        Late and unknown timestamps never become eligible. This recovery example does not fit
        a model; the three actual synthetic fits above remain a separate public demonstration.
        """),
        code("""
        result = demonstrate()
        display(pd.DataFrame([result]))
        assert result['warm_computed'] == 0 and result['corruption_rejected']
        assert result['qualification_counts'] == {
            'ELIGIBLE': 2, 'LATE_SOURCE': 1, 'UNKNOWN_TIMING': 1}
        print('ENGINEERING_REVIEW_COMPLETE — zero owner fits; three synthetic example fits')
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
        sum("application/vnd.plotly.v1+json" in o.get("data", {}) for o in outputs) == 6,
        "Persisted interactive figure missing",
    )
    require(sum("image/png" in o.get("data", {}) for o in outputs) == 6, "Static fallback missing")
    NOTEBOOK.write_text(nb.writes(book))
    return {
        "status": "PASS",
        "actual_kernel_execution": True,
        "code_cells": sum(cell.cell_type == "code" for cell in book.cells),
        "plotly_outputs": 6,
        "png_fallbacks": 6,
        "synthetic_model_fits": 3,
        "owner_research_fits": 0,
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
