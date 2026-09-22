"""Reproduce the curated research report from committed aggregates; never train."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'reports/current_research/evidence.json'
NOTEBOOK = ROOT / 'portfolio/current_research.ipynb'
RECEIPT = ROOT / 'reports/current_research/publication.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_data(data):
    if data['schema'] != 1:
        raise ValueError('Unsupported evidence schema')
    r = data['robustness']
    if r['new_kaggle_score'] is not None or r['submissions'] != 0:
        raise ValueError('Historical evidence must not become a Kaggle score')
    if r['decision'] != 'CANDIDATE_BUILD_REVIEW' or not all(r['checks'].values()):
        raise ValueError('Recorded decision changed')
    rows = r['rows']
    if [x['year'] for x in rows] != [2023, 2024, 2025]:
        raise ValueError('Assessment seasons changed')
    if sum(x['games'] for x in rows) != 189 or len(r['seeds']) != 3:
        raise ValueError('Incomplete evidence')
    for key in ['core', 'binary', 'margin']:
        values = [x[key] for x in rows] + [r['pooled'][key]]
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in values):
            raise ValueError('Invalid Brier')
        weighted = sum(x[key] * x['games'] for x in rows) / 189
        if abs(weighted - r['pooled'][key]) > 1e-12:
            raise ValueError('Season aggregation disagrees')
    if [x['seed'] for x in r['seeds']] != data['method']['seeds']:
        raise ValueError('Seed selection changed')
    if data['method']['margin_weight'] != .25:
        raise ValueError('Frozen blend changed')
    if r['new_tree_fits'] != sum(data['method']['inner_fold_counts']) * 3 * 2:
        raise ValueError('Fit accounting disagrees')
    for x in data['screen']['rows']:
        if not all(math.isfinite(x[k]) and 0 <= x[k] <= 1 for k in ['core', 'candidate']):
            raise ValueError('Invalid screen metric')
    for x in data['sources']:
        if len(x['sha256']) != 64 or any(c not in '0123456789abcdef' for c in x['sha256']):
            raise ValueError('Invalid source checksum')
    return data


def load_evidence():
    return validate_data(json.loads(EVIDENCE.read_text()))


def chart(name, title, labels, series, ylabel, reference=None):
    """One Plotly MIME output with a matching PNG fallback, no browser or server."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    import plotly.graph_objects as go
    from IPython.display import display
    fig = go.Figure()
    mpl, ax = plt.subplots(figsize=(10, 5.2), layout='constrained')
    x = np.arange(len(labels)); width = .78 / len(series)
    for i, (label, values) in enumerate(series.items()):
        fig.add_bar(name=label, x=labels, y=values)
        ax.bar(x + (i - (len(series) - 1) / 2) * width, values, width, label=label)
    if reference is not None:
        fig.add_hline(y=reference, line_dash='dot')
        ax.axhline(reference, linestyle=':', label='Published benchmark')
    fig.update_layout(title=title, width=960, height=520, barmode='group',
                      yaxis_title=ylabel, font_size=13,
                      margin=dict(l=75, r=25, t=85, b=90),
                      legend=dict(orientation='h', y=-.23))
    ax.set_xticks(x, labels); ax.set_ylabel(ylabel); ax.set_title(title, pad=18)
    ax.ticklabel_format(axis='y', style='plain', useOffset=False)
    if len(series) > 1 or reference is not None:
        ax.legend(loc='upper center', bbox_to_anchor=(.5, -.12), ncol=3, frameon=False)
    stream = io.BytesIO(); mpl.savefig(stream, format='png', dpi=130); plt.close(mpl)
    image = stream.getvalue()
    dest = ROOT / 'reports/current_research/figures' / f'{name}.png'
    dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(image)
    display({'application/vnd.plotly.v1+json': json.loads(fig.to_json()),
             'image/png': base64.b64encode(image).decode()}, raw=True)


def build(kernel='python3'):
    import nbformat as nbf
    from nbclient import NotebookClient
    md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    cells = [
        md('# NCAA tournament forecasting\n## From feature expansion to margin supervision\n'
           '**Alvaro Mendizabal · September 2026 research release**\n\n'
           'This executed notebook replays aggregate evidence from completed AWS experiments. '
           'It performs no model fitting, downloads, cloud calls, or submissions. '
           'The scored incumbent and the unsubmitted research challenger are different systems.'),
        code("from pathlib import Path\nimport sys\nroot = Path.cwd()\n"
             "if not (root / 'portfolio').is_dir():\n    root = root.parent\n"
             "sys.path.insert(0, str(root / 'portfolio'))\n"
             "from current_research import load_evidence, chart\n"
             "import pandas as pd\nfrom IPython.display import display\n"
             "e = load_evidence()\nr = e['robustness']\n"
             "display(pd.DataFrame([{'Evidence': 'Observed late Kaggle submission', 'Brier': e['scored']['incumbent'], 'Status': 'Scored'}, {'Evidence': 'Historical margin blend: men, 189 games', 'Brier': r['pooled']['margin'], 'Status': 'Unsubmitted; build review only'}]))"),
        md('## 1. What has actually been scored?\n'
           'The two-feature men’s incumbent achieved **0.1098691** in a late submission. '
           'The first-place author reports **0.1097454** over 126 games. This is a numerical '
           'reference, not a claim of original placement or exact score-scope equivalence. '
           'The margin challenger has no Kaggle score. These numbers must not be mixed with historical Brier.'),
        code("s = e['scored']\n"
             "display(pd.DataFrame([{'Incumbent improvement': s['previous']-s['incumbent'], 'Numerical gap to benchmark': s['incumbent']-s['published_benchmark']}]))\n"
             "chart('scored', 'Observed late submissions — not historical validation', ['Previous core', 'Two-feature incumbent'], {'Brier': [s['previous'], s['incumbent']]}, 'Brier (lower is better)', s['published_benchmark'])"),
        md('## 2. Why change the training target?\n'
           'Adding a full auxiliary feature bundle, compressing residual variation, selecting small '
           'subsets chronologically, and correcting frozen-core errors did not produce a promotable '
           'system. Instead of repeating those searches, the next controlled comparison changed '
           'the supervised target from signed win/loss to signed point margin.\n\n'
           'The compact core uses **seed difference and Harry-rating difference**. The auxiliary '
           'model uses those plus **31 existing basketball feature differences**. Both targets use '
           'the same 33 features, XGBoost squared error, depth-three trees, regularization and '
           'sigmoid calibration. Only the target changes. A one-point and a 25-point win no longer '
           'provide identical supervision. This mechanism was tested; it is not assumed to be superior.'),
        code("screen = pd.DataFrame(e['screen']['rows'])\n"
             "screen['gain'] = screen['core'] - screen['candidate']\n"
             "display(screen[['experiment','core','candidate','gain','decision']])\n"
             "chart('screen', 'Eight-season men’s research: gains relative to the same screening core', ['Full bundle','Residual PCA','Nested subsets','Feature correction','Margin blend'], {'Brier reduction': screen['gain'].tolist()}, 'Core minus candidate Brier; positive is better')"),
        md('These five summaries concern the same 503-game men’s screen, but reused development '
           'years and sequentially chosen hypotheses. They are not independent trials. The women’s '
           'subset experiment was rejected after four years; its incomplete result is not combined '
           'with this eight-year chart. Negative results narrowed the next question rather than being hidden.'),
        md('## 3. Does the exact candidate survive a fuller ensemble?\n'
           'For each outer year, train only on earlier seasons. Leave out each earlier season '
           'in turn, repeat for three fixed seeds, calibrate on inner held-out scores, and average '
           'the forecasts. Both margin and binary targets are run as a matched control.\n\n'
           '**Frozen prediction rule:** 0.75 × retained core probability + 0.25 × auxiliary '
           'probability. No weight search, favorable-seed selection, core retraining, or changes '
           'to women’s predictions. The three years contain 63 main-bracket games each.'),
        code("pooled = r['pooled']\n"
             "display(pd.DataFrame([{'core': pooled['core'], 'binary blend': pooled['binary'], 'margin blend': pooled['margin'], 'gain vs core': pooled['core']-pooled['margin'], 'gain vs matched binary': pooled['binary']-pooled['margin']}]))\n"
             "chart('pooled', 'Historical men’s Brier — 2023–2025, 189 games', ['Frozen core','25% binary blend','25% margin blend'], {'Brier': [pooled['core'],pooled['binary'],pooled['margin']]}, 'Brier (lower is better)')"),
        code("years = pd.DataFrame(r['rows'])\n"
             "display(years)\n"
             "chart('years', 'Does improvement persist across assessment years?', years['year'].astype(str).tolist(), {'Binary blend': (years['core']-years['binary']).tolist(), 'Margin blend': (years['core']-years['margin']).tolist()}, 'Core minus blend Brier; positive is better')"),
        md('The margin blend improves on the core in all three years. It beats the matched binary '
           'blend in **two of three**, not all three: the binary blend is better in 2025. The pooled '
           'objective advantage is approximately **0.0004168 Brier**. This distinction prevents '
           'claiming more than the controlled comparison supports.'),
        code("seed = pd.DataFrame(r['seeds'])\n"
             "seed['gain'] = pooled['core'] - seed['brier']\n"
             "display(seed)\n"
             "chart('seeds', 'Seed stability — all three predeclared seeds retained', seed['seed'].astype(str).tolist(), {'Brier reduction': seed['gain'].tolist()}, 'Core minus margin-blend Brier')"),
        code("chart('ablation', 'Margin target versus matched binary target', years['year'].astype(str).tolist(), {'Margin advantage': (years['binary']-years['margin']).tolist()}, 'Binary-blend minus margin-blend Brier')"),
        md('## 4. Decision, uncertainty and cost\n'
           'The recorded decision is **CANDIDATE_BUILD_REVIEW**, not production promotion. '
           'The run completed 360 tree fits in about 76 seconds overall and passed 61 regression '
           'tests. Source and checkpoint receipts were preserved; no feature rebuild or submission '
           'was performed. Publication itself adds no training.\n\n'
           'The outer years were excluded from fitting, but have already been used repeatedly '
           'during project development. The earlier margin screen selected this proposal on '
           'overlapping years. Three random seeds do not supply three independent outcome sets. '
           'Inner held-out scores are used for both early stopping and calibration. Conditional '
           'season-bootstrap results are not selection-adjusted evidence of a future win.'),
        code("display(pd.DataFrame([{'Check': k, 'Passed': v} for k,v in r['checks'].items()]))\n"
             "print('Decision:', r['decision'])\n"
             "print('Candidate Kaggle score:', r['new_kaggle_score'])\n"
             "print('New model fits performed by this report:', 0)"),
        md('## 5. Reproducibility and the next boundary\n'
           'Committed aggregate evidence includes source-return SHA-256 values, the scored '
           'candidate identity, run ID, policy, per-year and per-seed metrics. The report validates '
           'arithmetic before rendering. Raw competition records, per-game predictions, fitted '
           'models, credentials, machine-specific paths and environments are intentionally absent.\n\n'
           'Re-executing this notebook reproduces the published tables and plots, **not** model '
           'training. The broader source repository and AWS retain their distinct purposes. '
           'The next modeling milestone is one frozen 2026 candidate build with schema, probability, '
           'row-identity and protected-women checks, followed by separately authorized scoring.\n\n'
           'See `reports/current_research/evidence.json` and `docs/current_research.md` for provenance '
           'and the source-to-publication boundary. The first-place mechanism is attributed to '
           'Harrison Horan’s public writeup; this margin extension is not an exact winning-solution reproduction.'),
        code("print('REPORT_COMPLETE — aggregate evidence only; no training or submission')")
    ]
    nb = nbf.v4.new_notebook(cells=cells, metadata={'kernelspec':{'name':kernel,'display_name':'Python 3','language':'python'}})
    NotebookClient(nb, timeout=90, kernel_name=kernel, resources={'metadata':{'path':str(ROOT)}}).execute()
    NOTEBOOK.write_text(nbf.writes(nb))
    receipt = inspect_notebook()
    RECEIPT.write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def inspect_notebook():
    import nbformat
    nb = nbformat.read(NOTEBOOK, as_version=4); nbformat.validate(nb)
    count = 0; plots = 0; png = 0
    for cell in nb.cells:
        if cell.cell_type != 'code':
            continue
        count += 1
        if cell.execution_count != count:
            raise ValueError('Unresolved or inconsistent execution')
        for out in cell.outputs:
            if out.output_type == 'error':
                raise ValueError('Notebook contains an error')
            data = out.get('data', {})
            if 'application/vnd.plotly.v1+json' in data:
                layout = data['application/vnd.plotly.v1+json']['layout']
                if layout.get('width', 0) < 900 or layout.get('height', 0) < 450:
                    raise ValueError('Unreadable figure dimensions')
                plots += 1
            png += int('image/png' in data)
    if plots != 6 or png != 6 or 'REPORT_COMPLETE' not in str(nb.cells[-1].outputs):
        raise ValueError('Missing inline evidence or final sentinel')
    if NOTEBOOK.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('Publication notebook too large')
    return {'status':'PASS','scope':'Executed aggregate report, not model training',
            'evidence_sha256':digest(EVIDENCE),'notebook_sha256':digest(NOTEBOOK),
            'builder_sha256':digest(__file__),
            'executed_code_cells':count,'plotly_outputs':plots,'embedded_png_fallbacks':png,
            'report_model_fits':0,'figure_sha256':{p.name:digest(p) for p in sorted((ROOT/'reports/current_research/figures').glob('*.png'))}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--kernel', default='python3')
    args = parser.parse_args(); load_evidence()
    if args.build:
        print(json.dumps(build(args.kernel), indent=2))
    elif args.check:
        actual = inspect_notebook(); expected = json.loads(RECEIPT.read_text())
        if actual != expected:
            raise ValueError('Published report receipt differs')
        print(json.dumps(actual, indent=2))
    else:
        parser.error('Choose --build or --check')


if __name__ == '__main__':
    main()
