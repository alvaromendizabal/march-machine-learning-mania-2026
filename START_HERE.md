# Start here

## Three-minute review

I built this project around two questions: **are the probabilities useful, and can the evidence behind them be trusted?** The delivered research forecast received **0.1067095 Brier**, numerically **2.77% below the official winning score**. It was submitted after outcomes were inspected, so this is a retrospective comparison, not an official placement or prospective result.

1. **Interact:** [Tournament Lab](https://alvaro-tournament-lab.tartmacaw2.chatgpt.site) lets you change fictional ratings, inspect exact bracket probabilities and export calculations. It is a public synthetic demonstration, separate from the private forecast.
2. **Verify:** read the [measured result and timing](docs/benchmark_comparison.md) and the [executed result notebook](portfolio/verified_result.ipynb).
3. **Inspect the work:** [employer walkthrough](docs/employer_walkthrough.md), [architecture](docs/architecture.md), [validation matrix](docs/reproduction_matrix.md) and [disclosure](portfolio/DISCLOSURE.md).

## Two lightweight ways to run it

The aggregate result audit uses Python 3.12's standard library:

```bash
python portfolio/reproduce_release.py --check
python tools/summarize_execution.py --check
```

These commands verify the published score evidence and the sanitized latest-inspected execution receipt. The score audit recomputes comparison arithmetic. No credentials or external data are needed. It does not fit the private model or recover withheld predictions. [Aggregate input](portfolio/release_evidence.json) · [Audit output](reports/verified_result/reproduction.json)

The browser demo has no installation or backend. From the repository root:

```bash
python -m http.server 8000
```

Open **http://localhost:8000/public-demo/**. Run its independent engine and actual UI-handler checks with Node:

```bash
node tools/test_public_demo_engine.mjs
node tools/test_public_demo.mjs
```

The [demo guide](docs/public_demo.md) explains the probability formula, synthetic scoring sample and limits.

## Full public framework review

The framework uses Python **3.12.13** with dependencies locked in `uv.lock`:

```bash
uv sync --locked --group dev
uv run --locked python scripts/quality.py
uv run --locked python -m ipykernel install --user --name march-mania
uv run --locked python scripts/notebook.py --execute --publish
```

Default review mode reads published aggregate evidence; it does not initiate private training or submit to Kaggle. The Research quality workflow exercises this review. Public framework outputs and private submitted forecasts retain distinct lineage.

| Notebook | Review question |
|---|---|
| [00 — Data audit](notebooks/00_data_audit_and_preparation.ipynb) | Are tables and physical game identities coherent? |
| [01 — Splits and snapshots](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb) | What is available at the prediction cutoff? |
| [02 — Feature store](notebooks/02_feature_store_and_diagnostics.ipynb) | How are features and provenance organized? |
| [03 — Model comparison](notebooks/03_model_comparison_and_diagnostics.ipynb) | How are model families compared? |
| [04 — Historical benchmark](notebooks/04_locked_benchmark_and_final_submission.ipynb) | What does the consumed benchmark establish? |
| [05 — Feature research](notebooks/05_feature_research.ipynb) | How are hypotheses, ablations and failures recorded? |

These six notebooks document historical public-framework lineages. The latest confirmed submission is documented separately in [verified_result.ipynb](portfolio/verified_result.ipynb).

## Read the evidence correctly

- Brier is mean squared probability error; lower is better. A 2.77% reduction is not 2.77 percentage points of accuracy.
- The 126-game retrospective audit and 566-game men's historical bank are different populations.
- Submission acceptance does not certify historical promotion, unseen-season performance or complete source timing.
- The demo's eight fictional teams and authored outcomes provide no evidence about the 2026 forecast.
- Latest inspected execution return **v128, October 10**, is **SOURCE_PARTIAL** with zero fits, inferences, candidates or submissions. It changes source status, not the confirmed score.

[Current state](docs/current_research.md) · [2027 work still required](docs/2027_readiness.md)
