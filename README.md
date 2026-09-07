# NCAA tournament probability forecasting

Forecasting men's and women's college basketball tournament games with chronological evaluation, calibrated probability diagnostics, and reproducible experiments.

**Current phase: one coherent 00 → 01 → 02 workflow, with measured feature evidence.**
The official Kaggle download is verified: 35 CSV files, 181 MB, recorded on
2026-09-07. The current run builds 124 features and 9,200 team snapshots, evaluates
660 folds, and exactly reproduces 18,878 comparable earlier forecasts.

[Start with notebook 00](notebooks/00_data_audit_and_preparation.ipynb) ·
[Split protocol](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb) ·
[Feature evidence](notebooks/02_feature_store_and_diagnostics.ipynb) ·
[Studio commands](docs/studio.md)

## Results and their limits

| Recorded submission | Observed Brier ↓ | Evidence |
|---|---:|---|
| Original challenger | 0.1299012 | Repository score log |
| Development-frozen blend | 0.1318165 | Repository score log |
| Original primary | 0.1421117 | Repository score log |
| Best recorded temperature refinement | 0.1281386 | Post-result exploratory refinement |

These are repository-recorded scores, not independently authenticated Kaggle standings. The recalled approximately 0.121 result has not yet been located. Post-result refinements are not untouched validation and do not establish a medal.

| Development candidate | Men: mean season Brier ↓ | Women: mean season Brier ↓ |
|---|---:|---:|
| Strength logistic | 0.191268 | 0.144308 |
| Best observed current candidate | 0.187602 (Massey rankings) | 0.143597 (dynamic Elo) |
| New ball-control family | 0.190589 | 0.145600 |
| New schedule context | 0.191737 | 0.147245 |
| New scoring shape | 0.193138 | 0.145602 |

Twenty additional features preserve the earlier 104. They test passing,
defensive activity, foul rates, schedule context and nonlinear scoring summaries.
The men's ball-control family modestly improves the strength baseline, but its
paired season-bootstrap interval includes zero. None of the new families beats
the strongest current candidate. The full logistic model performs worse, so
feature count is not used as a measure of quality. No new final recipe is promoted.

These are exploratory five-season development results. The earlier men's rich
system reports 0.180669; its original predictions are still needed for an exact
paired comparison. Single-season Kaggle scores are not directly comparable with
these averages. The previously consumed 2022–2025 benchmark is not relabeled as
untouched validation. See the [full evidence](reports/feature_store/README.md).

## Reproducible research

```bash
(
  set -e
  python3 scripts/bootstrap.py
  .venv/bin/march-data --output data/kaggle --s3 s3://YOUR_BUCKET/data
  .venv/bin/march-audit --raw data/kaggle/raw --run-root outputs/data_review --s3 s3://YOUR_BUCKET/data-review
  .venv/bin/march-features --raw data/kaggle/raw --run-root outputs/feature_store --require-massey --s3 s3://YOUR_BUCKET/feature-store
)
```

A locked Python 3.12 environment, fixed random seeds and CPU thread limits make the run reproducible. UTC events, task heartbeats, elapsed time and checksum-verified checkpoints make it observable and resumable. Git stores code and evidence; private S3 stores input snapshots and generated models/results. See the [Studio guide](docs/studio.md) for the provisioned project bucket and exact commands.

The rebuilt store evaluates adjusted offense/defense, opponent-adjusted Four Factors, residual form, shooting posteriors and uncertainty, tempo, dynamic Elo, program history, publication-cohort ranking consensus and trends, forward-only team/seed/rank target encoding, and contextual interactions. Exact estimator inputs and encoding history boundaries are audited per fold. The benchmark has **600 folds without external rankings**, or **660 with men's rankings**. Models remain fixed to isolate feature effects. The smaller notebook 05 benchmark remains reproducible through `march-research` using a new output directory when code or inputs change.

## Project map

| Path | Purpose |
|---|---|
| `notebooks/00_data_audit_and_preparation.ipynb` | Current raw-data provenance, coverage and basketball exploration |
| `notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb` | Current temporal split and snapshot evidence |
| `notebooks/02_feature_store_and_diagnostics.ipynb` | Rebuilt feature store, measured ablations and source coverage |
| `notebooks/03_model_comparison_and_diagnostics.ipynb` | Original nested model comparison |
| `notebooks/04_locked_benchmark_and_final_submission.ipynb` | Historical benchmark and submission |
| `notebooks/05_feature_research.ipynb` | Auditable feature research and results review |
| `src/march_mania/` | Reusable preparation, features, experiment runtime and reporting |
| `configs/research.json` | Explicit research boundaries and runtime configuration |
| `configs/feature_store.json` | Rebuilt store's snapshot range and development evaluation |
| `tests/` | Structural, temporal, probability, failure, resume and restore tests |
| `reports/` | Historical results and documented validation evidence |
| `docs/` | Research rationale and operational instructions |

The lockfile covers notebooks 00, 01, 02 and 05, ingestion, data review and the feature benchmarks. Notebooks 03 and 04 retain their historical contracts and environment requirements. Migrating notebook 03's nested tuning/calibration to the new feature schema precedes a new final submission recipe.

## Development

```bash
uv sync --locked --group dev
uv run --locked python scripts/quality.py
```

The quality gate compiles, lints, checks formatting and types, then runs unit and end-to-end tests with JUnit and coverage artifacts. Raw Kaggle files, environments, generated datasets, checkpoints and model binaries are excluded from Git. Use ordinary module names and edit the canonical implementation; Git history records revisions.
