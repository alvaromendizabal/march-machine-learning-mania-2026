"""Render approved portfolio aggregates only. No model or training-data access."""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "reports/current_research/milestone.json"
NB = ROOT / "portfolio/current_research.ipynb"
RECEIPT = ROOT / "reports/current_research/publication.json"
FIGURES = ["scored", "women_screen_history", "women_robustness",
           "women_robustness_years", "women_robustness_repeats", "women_objective_ablation"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(data):
    if data["schema"] != 1:
        raise ValueError("Unknown case-study schema")
    scored, w = data["scored"], data["women"]
    if scored["status"] != "COMPLETE" or scored["submission_ref"] != "56447505":
        raise ValueError("Scored identity changed")
    if scored["incumbent"] != .1094899:
        raise ValueError("No new scored release is supported by this milestone")
    if len(scored["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in scored["sha256"]):
        raise ValueError("Invalid scored-file checksum")
    if w["new_submissions"] != 0 or w["kaggle_score"] is not None:
        raise ValueError("Historical results must not be turned into a Kaggle score")
    if w["decision"] != "CANDIDATE_BUILD_REVIEW" or len(w["checks"]) != 7 or not all(w["checks"].values()):
        raise ValueError("Robustness decision or gates changed")
    if [x["year"] for x in w["years"]] != [2023, 2024, 2025]:
        raise ValueError("Assessment years changed")
    if sum(x["games"] for x in w["years"]) != 189 or len(w["repeats"]) != 3:
        raise ValueError("Incomplete population or repeat evidence")
    for key in ["core", "binary", "margin"]:
        values = [x[key] for x in w["years"]] + [w[key]]
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in values):
            raise ValueError("Invalid Brier")
        if abs(sum(x[key] * x["games"] for x in w["years"]) / 189 - w[key]) > 1e-12:
            raise ValueError("Pooled metric differs from seasonal aggregation")
    if w["new_tree_fits"] != 234 or w["regression_tests"] != 78:
        raise ValueError("Completed-run accounting changed")
    if len(data["screen"]["years"]) != 8 or len(data["screen"]["gain"]) != 8:
        raise ValueError("Incomplete earlier screen")
    if not all(math.isfinite(x) for x in data["screen"]["gain"]):
        raise ValueError("Invalid screening gain")
    return data


def load():
    return validate(json.loads(DATA.read_text()))


def chart(name, title, labels, series, ylabel, reference=None):
    """Nonblocking inline Plotly output and independently rendered static fallback."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import plotly.graph_objects as go
    from IPython.display import display

    labels = [str(x) for x in labels]
    fig = go.Figure()
    png, ax = plt.subplots(figsize=(10, 5.3), layout="constrained")
    x = np.arange(len(labels))
    width = .78 / len(series)
    for i, (label, values) in enumerate(series.items()):
        fig.add_bar(name=label, x=labels, y=values)
        ax.bar(x + (i - (len(series) - 1) / 2) * width, values, width, label=label)
    if reference is not None:
        fig.add_hline(y=reference, line_dash="dot")
        ax.axhline(reference, linestyle=":", label="Published benchmark")
    fig.update_layout(title=title, width=960, height=530, barmode="group",
                      yaxis_title=ylabel, font_size=13, xaxis_type="category",
                      margin=dict(l=80, r=30, t=90, b=100),
                      legend=dict(orientation="h", y=-.23))
    ax.set_xticks(x, labels)
    ax.set_title(title, pad=18)
    ax.set_ylabel(ylabel)
    ax.ticklabel_format(axis="y", useOffset=False, style="plain")
    if len(series) > 1 or reference is not None:
        ax.legend(loc="upper center", bbox_to_anchor=(.5, -.12), ncol=3, frameon=False)
    stream = io.BytesIO()
    png.savefig(stream, format="png", dpi=130)
    plt.close(png)
    image = stream.getvalue()
    destination = ROOT / "reports/current_research/figures" / (name + ".png")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(image)
    display({"application/vnd.plotly.v1+json": json.loads(fig.to_json()),
             "image/png": base64.b64encode(image).decode()}, raw=True)


def build(kernel):
    import nbformat as nbf
    from nbclient import NotebookClient
    md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    cells = [
        md("# NCAA forecasting | ML engineering case study\n"
           "**Alvaro Mendizabal · achieved 2026 release and ongoing private research**\n\n"
           "This notebook presents approved aggregate evidence. It does not contain or invoke "
           "the training system, model parameters, private data or submission code. All displayed "
           "outputs are saved for review without cloud access."),
        code("from pathlib import Path\nimport sys\nroot = Path.cwd()\n"
             "if not (root / 'portfolio').is_dir():\n    root = root.parent\n"
             "sys.path.insert(0, str(root / 'portfolio'))\n"
             "from current_research import load, chart\nimport pandas as pd\n"
             "from IPython.display import display\ne = load()\ns = e['scored']\nw = e['women']\n"
             "display(pd.DataFrame([{'Evidence': 'Scored late release', 'Brier': s['incumbent'], 'Setting': s['setting']}, {'Evidence': 'Women research candidate', 'Brier': w['margin'], 'Setting': w['setting']}]))"),
        md("## 1. An achieved score, not an inferred one\n"
           "Submission **56447505** is recorded COMPLETE at **0.1094899 Brier**, compared with "
           "the published winning benchmark of **0.1097454**. The numerical difference is "
           "**0.0002555**, approximately **0.23% lower Brier**. This post-competition result "
           "is not an original first-place finish or evidence of a guaranteed future advantage. "
           "Brier measures squared probability error; historical and Kaggle populations remain separate."),
        code("chart('scored', 'Recorded late-submission progression', ['Previous release', 'Current release'], {'Brier': [s['predecessor'], s['incumbent']]}, 'Brier (lower is better)', s['published_benchmark'])\n"
             "print('Improvement over predecessor:', round(s['predecessor']-s['incumbent'], 7))\n"
             "print('Below published benchmark:', round(s['published_benchmark']-s['incumbent'], 7))"),
        md("## 2. Research judgment before additional complexity\n"
           "Full feature expansion, residual dimensionality reduction, chronological subset "
           "selection and error corrections did not automatically improve the compact reference. "
           "Those rejected directions are retained in earlier evidence. A controlled change to "
           "learning score margins produced useful complementary forecasts and then an improved "
           "scored men's release. The next question was whether that mechanism transfers to women.\n\n"
           "The earlier women's screen improved six of eight historical years. It justified a fuller "
           "ensemble check, not an immediate submission."),
        code("chart('women_screen_history', 'Earlier women’s screen — six of eight years improved', e['screen']['years'], {'Brier reduction': e['screen']['gain']}, 'Reference minus candidate Brier; positive is better')"),
        md("## 3. Does the women's candidate survive fuller training?\n"
           "The same historical 2023–2025 games compare a frozen reference, a matched win/loss "
           "control, and the margin-based ensemble. Whole-season inner omissions and three fixed "
           "random repeats assess training stability. Every outer assessment year is excluded "
           "from fitting, early stopping and calibration. The scored men's probabilities remain "
           "untouched; this experiment makes no Kaggle submission."),
        code("display(pd.DataFrame([{'Core': w['core'], 'Binary control': w['binary'], 'Margin candidate': w['margin'], 'Gain over core': w['core']-w['margin'], 'Gain over binary': w['binary']-w['margin']}]))\n"
             "chart('women_robustness', 'Women’s historical robustness — 189 games', ['Frozen reference', 'Binary control', 'Margin candidate'], {'Brier': [w['core'],w['binary'],w['margin']]}, 'Brier (lower is better)')"),
        code("years = pd.DataFrame(w['years'])\ndisplay(years)\n"
             "chart('women_robustness_years', 'Does improvement persist across assessment years?', years.year.tolist(), {'Binary control': (years.core-years.binary).tolist(), 'Margin candidate': (years.core-years.margin).tolist()}, 'Core minus candidate Brier; positive is better')"),
        md("The margin candidate improves the reference in all three years. That does not imply "
           "it always beats the matched binary control: the binary control is better in 2025. "
           "The pooled target advantage is **0.0006872**, while the overall gain against the core "
           "is **0.0009077**. Both comparisons matter."),
        code("chart('women_objective_ablation', 'Margin target versus matched binary control', years.year.tolist(), {'Margin advantage': (years.binary-years.margin).tolist()}, 'Binary minus margin Brier; positive favors margin')"),
        code("repeat = pd.DataFrame(w['repeats'])\nrepeat['gain'] = w['core']-repeat.brier\ndisplay(repeat)\n"
             "chart('women_robustness_repeats', 'All three predeclared repeats retained', repeat['repeat'].tolist(), {'Brier reduction': repeat.gain.tolist()}, 'Core minus candidate Brier')"),
        md("## 4. Decision and uncertainty\n"
           "All seven predeclared robustness criteria passed. The completed run performed "
           "**234 model fits**, passed **78 regression tests**, and took **53.43 seconds overall**. "
           "Its decision is **CANDIDATE_BUILD_REVIEW**, not a new scored release.\n\n"
           "These development years have been reused, and the proposal was selected following "
           "earlier experiments. Inner held-out predictions guide both early stopping and "
           "calibration. Three random repeats do not create three independent tournaments. "
           "Conditional uncertainty summaries do not correct for the entire adaptive research "
           "history. No 2027 improvement can be inferred from the observed late score."),
        code("display(pd.DataFrame([{'Gate': k, 'Passed': v} for k,v in w['checks'].items()]))\n"
             "print('Women decision:', w['decision'])\nprint('Women Kaggle score:', w['kaggle_score'])\n"
             "print('Model fits performed by this report:', 0)"),
        md("## 5. Engineering, ownership and the 2027 boundary\n"
           "The private pipeline preserves source/data/checkpoint identities, protects previously "
           "scored predictions, validates schema and probabilities, reuses completed work, and "
           "packages failures for diagnosis. The public report exposes outcomes and professional "
           "reasoning—not the evolving training implementation or detailed future recipe.\n\n"
           "Existing public source and licenses remain accessible; this publication does not erase "
           "history or retract earlier grants. Going forward, detailed implementation stays in "
           "the owner's workspace. Attribution to the compact reference's public author is retained.\n\n"
           "For 2027, preserve the current baseline, audit season-specific assumptions, record "
           "timestamped pregame snapshots and forecasts, and freeze evaluation and selection rules "
           "before future outcomes arrive. The next competition's actual rules must be reviewed "
           "when available; no schedule or external-data permission is assumed. See the "
           "employer walkthrough and 2027 readiness note for the high-level plan."),
        code("print('REPORT_COMPLETE — approved aggregates; no training or submission')")
    ]
    nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name":kernel,"display_name":"Python 3","language":"python"}})
    NotebookClient(nb, timeout=90, kernel_name=kernel, resources={"metadata":{"path":str(ROOT)}}).execute()
    NB.write_text(nbf.writes(nb))
    result = inspect()
    RECEIPT.write_text(json.dumps(result, indent=2)+"\n")
    return result


def inspect():
    import nbformat
    nb = nbformat.read(NB, as_version=4)
    nbformat.validate(nb)
    code = [c for c in nb.cells if c.cell_type == "code"]
    if [c.execution_count for c in code] != list(range(1,len(code)+1)):
        raise ValueError("Unresolved notebook cell")
    outputs = [o for c in code for o in c.get("outputs",[])]
    if any(o.output_type == "error" for o in outputs):
        raise ValueError("Notebook has errors")
    plots = [o.data["application/vnd.plotly.v1+json"] for o in outputs if "application/vnd.plotly.v1+json" in o.get("data",{})]
    pngs = sum("image/png" in o.get("data",{}) for o in outputs)
    if len(plots) != 6 or pngs != 6 or "REPORT_COMPLETE" not in str(nb.cells[-1].outputs):
        raise ValueError("Missing inline evidence or sentinel")
    if any(x["layout"].get("width",0)<900 or x["layout"].get("height",0)<450 for x in plots):
        raise ValueError("Unreadable figure")
    if NB.stat().st_size > 2*1024*1024:
        raise ValueError("Oversized report")
    return {"status":"PASS","scope":"Executed aggregate case study, no training", "milestone_sha256":digest(DATA), "builder_sha256":digest(__file__), "notebook_sha256":digest(NB), "executed_code_cells":len(code),"plotly_outputs":len(plots),"png_fallbacks":pngs,"model_fits":0,"figures":{n:digest(ROOT/"reports/current_research/figures"/(n+".png")) for n in FIGURES}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",action="store_true")
    parser.add_argument("--check",action="store_true")
    parser.add_argument("--kernel",default="python3")
    args=parser.parse_args()
    load()
    if args.build:
        print(json.dumps(build(args.kernel),indent=2))
    elif args.check:
        actual=inspect()
        if actual != json.loads(RECEIPT.read_text()):
            raise ValueError("Report receipt mismatch")
        print(json.dumps(actual,indent=2))
    else:
        parser.error("Select --build or --check")


if __name__ == "__main__":
    main()
