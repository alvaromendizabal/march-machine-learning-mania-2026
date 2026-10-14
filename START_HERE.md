# Start here

**A short review path for ML engineers, data scientists and hiring teams.**

I built this project around two questions: are the probabilities useful, and can the evidence behind them be trusted? Start with an executable demonstration, then inspect the research evidence and implementation at the depth you need.

## Three-minute review

1. **Explore:** [Tournament Lab](https://alvaro-tournament-lab.tartmacaw2.chatgpt.site) propagates fictional team strengths through an eight-team bracket. The calculations are exact under the demo's declared assumptions.
2. **Understand the contribution:** [Engineering case study](docs/employer_walkthrough.md) connects source qualification, forecast construction, evaluation repairs and recoverable execution.
3. **Check the evidence:** [Evidence map](docs/evidence_map.md) identifies the proof and limitation behind each headline result.

## Ten-minute technical review

From the repository root, with Python 3.12:

```bash
python tools/reproduce_public.py --check
python portfolio/reproduce_release.py --check
python tools/summarize_execution.py --check
python -m unittest discover -s tools -p 'test_public_reproduction.py'
```

The [synthetic evaluation lab](docs/public_reproduction.md) runs a complete public example with timestamped observations, identity-only prediction requests and separate scoring labels. Inspect its source and try a failing input. The other commands verify aggregate result and execution records. All three use the standard library and require no credentials or downloads.

| Question | Start with |
|---|---|
| How is outcome leakage prevented? | [Synthetic reproduction](docs/public_reproduction.md), [split notebook](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb) |
| What did the author contribute? | [Case study](docs/employer_walkthrough.md), [method attribution](docs/benchmark_comparison.md#method-lineage-and-additional-work) |
| What was actually delivered? | [Scored receipt](reports/verified_result/submission_receipt.json), [latest source audit](portfolio/latest_execution.json) |
| What can I reproduce? | [Reproduction matrix](docs/reproduction_matrix.md), [disclosure](portfolio/DISCLOSURE.md) |
| How are failures handled? | [Runtime code](src/march_mania/runtime.py), [runtime tests](tests/test_runtime.py), [publication gate](tools/check_publication.py) |

## Browser demo locally

```bash
python -m http.server 8000
```

Open **http://localhost:8000/public-demo/**. The static demo needs no build step. Check its engine and actual UI handlers with `node tools/test_public_demo_engine.mjs` and `node tools/test_public_demo.mjs`. [Demo guide](docs/public_demo.md)

## Full framework review

Python **3.12.13** and the project dependencies are locked in `uv.lock`:

```bash
uv sync --locked --group dev
uv run --locked python scripts/quality.py
uv run --locked python -m ipykernel install --user --name march-mania
uv run --locked python scripts/notebook.py --execute --publish
```

Default review mode reads published aggregate evidence. Submission generation is default-off. Public framework outputs and private forecasts retain separate lineages.

| Notebook | Review question |
|---|---|
| [00 — Data audit](notebooks/00_data_audit_and_preparation.ipynb) | Are tables and physical game identities coherent? |
| [01 — Splits and snapshots](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb) | What was available at the prediction cutoff? |
| [02 — Feature store](notebooks/02_feature_store_and_diagnostics.ipynb) | How are features and provenance organized? |
| [03 — Model comparison](notebooks/03_model_comparison_and_diagnostics.ipynb) | How are model families compared? |
| [04 — Historical benchmark](notebooks/04_locked_benchmark_and_final_submission.ipynb) | What does the consumed benchmark establish? |
| [05 — Feature research](notebooks/05_feature_research.ipynb) | How are hypotheses, ablations and failures recorded? |

These six notebooks document public-framework lineages. [Verified result](portfolio/verified_result.ipynb) documents the separate receipted retrospective submission. Historical research notebooks preserve dated experiments; they do not supersede [current evidence](docs/current_research.md).

## Read the results correctly

The latest inspected return is v170, a source audit with no new submission. The public scored case study has a recorded Brier of 0.1067095; that is not a claim about the best private experiment. Brier is mean squared probability error, not accuracy. Historical outcomes were inspected, and the example's synthetic scores establish no NCAA performance. Prospective evaluation requires a forecast frozen before future outcomes. [Evaluation disclosure](portfolio/DISCLOSURE.md)
