# Start here

## Five-minute review

This project combines a **Kaggle-confirmed 0.1067095 late-submission Brier score** with source reconstruction, temporal evaluation, and reproducible research engineering. The score is numerically **2.77% below the official winning reference**, with the post-competition setting stated explicitly.

1. Read the [result and comparison](docs/benchmark_comparison.md): exact scores, matched evaluation, timing, and attribution.
2. Open the [executed result notebook](portfolio/verified_result.ipynb): inspect the comparisons and public evidence without running a cloud job.
3. Read the [employer walkthrough](docs/employer_walkthrough.md): responsibilities, engineering decisions, and transferable skills.
4. Inspect the [architecture](docs/architecture.md), [reproduction matrix](docs/reproduction_matrix.md), and [disclosure boundary](portfolio/DISCLOSURE.md).
5. Run the public evidence check below.

## Lightweight public audit

From the repository root, with Python 3.12:

```bash
python portfolio/reproduce_release.py --check
```

This requires no credentials or external data. It verifies published receipt fields and hashes and recomputes comparison arithmetic. It does not refit the private submitted model or recover withheld predictions. The [aggregate input](portfolio/release_evidence.json) and [audit output](reports/verified_result/reproduction.json) make that scope explicit.

## Full public framework review

The public framework has a Python 3.12.13 environment locked in uv.lock. Install with uv sync --locked --group dev. Run uv run --locked python scripts/quality.py for compilation, lint, formatting, types, and tests. Register the march-mania kernel with uv run --locked python -m ipykernel install --user --name march-mania, then execute uv run --locked python scripts/notebook.py --execute --publish in its default review mode. The GitHub Research quality workflow exercises these commands on the proposed change.

Review mode reads published aggregate evidence; it does not initiate private training or submit to Kaggle. Training is a separately controlled AWS workflow. Public framework outputs and private submitted forecasts have distinct lineage.

| Notebook | Review question |
|---|---|
| [00 — Data audit](notebooks/00_data_audit_and_preparation.ipynb) | Are tables and physical game identities coherent? |
| [01 — Splits and snapshots](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb) | What information is available at a prediction cutoff? |
| [02 — Feature store](notebooks/02_feature_store_and_diagnostics.ipynb) | How are features and provenance organized? |
| [03 — Model comparison](notebooks/03_model_comparison_and_diagnostics.ipynb) | How are distinct model families compared? |
| [04 — Historical benchmark](notebooks/04_locked_benchmark_and_final_submission.ipynb) | What does the consumed historical benchmark establish? |
| [05 — Feature research](notebooks/05_feature_research.ipynb) | How are hypotheses, ablations, and failures recorded? |

These six notebooks document the public framework's historical lineages. The latest confirmed submission is documented in [verified_result.ipynb](portfolio/verified_result.ipynb), rather than relabeling old experiments as current results.

## Read the evidence correctly

- Brier is mean squared probability error; lower is better.
- The official winner and this project's late result have different information-time settings. No original competition rank is claimed.
- The 126-game retrospective audit and 566-game men's historical bank are different populations.
- A confirmed upload does not certify historical promotion, unseen-season performance, or complete source vintage.
- Source coverage is reported separately from evidence that a source improved the score.
- v99 is a pending original-source pilot at this snapshot; its local tests are not an AWS research result.

Public materials omit private weights, prediction rows, fitted models, and supplemental raw archives. [Current state](docs/current_research.md) · [2027 work still required](docs/2027_readiness.md)
