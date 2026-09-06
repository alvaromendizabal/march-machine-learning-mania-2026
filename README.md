# NCAA tournament probability forecasting

Forecasting men's and women's college basketball tournament games with chronological evaluation, calibrated probability diagnostics, and reproducible experiments.

**Current phase: rebuilt notebook 02 and measured feature ablations.** The feature store now has 80 registered matchup features, official Kaggle ingestion, and resumable season/model checkpoints. A real-data run completed 400 folds and exactly reproduced 3,894 control forecasts from notebook 05. Historical implementations remain in Git history; historical model and submission evidence remains available.

[Feature definitions and run commands](docs/feature_store.md) · [Notebook 02](notebooks/02_feature_store_and_diagnostics.ipynb) · [Notebook 05 evidence](notebooks/05_feature_research.ipynb) · [Studio](docs/studio.md)

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
| Notebook 05 strength logistic | 0.191268 | 0.144308 |
| Best observed new candidate | 0.188058 (adjusted Four Factors) | 0.143597 (dynamic Elo) |

New improvements are exploratory: their paired season intervals include zero.
The earlier men's rich system reports a stronger 0.180669. Its original forecasts
are still needed for an exact paired comparison. These multi-season development
metrics are not directly comparable with the single-season Kaggle scores above.
The current new run uses eight official CSV files; external rankings and the
official sample submission await the full authenticated Kaggle pull in Studio.

## Reproducible research

```bash
python3 scripts/bootstrap.py
.venv/bin/march-data --output data/kaggle --s3 s3://YOUR_BUCKET/data
.venv/bin/march-features --raw data/kaggle/raw --output outputs/feature_store --s3 s3://YOUR_BUCKET/feature-store
```

A locked Python 3.12 environment, fixed random seeds and CPU thread limits make the run reproducible. UTC events, task heartbeats, elapsed time and checksum-verified checkpoints make it observable and resumable. Git stores code and evidence; private S3 stores input snapshots and generated models/results. See the [Studio guide](docs/studio.md) for the provisioned project bucket and exact commands.

The rebuilt store evaluates adjusted offense/defense, opponent-adjusted Four Factors, residual form, shooting posteriors and uncertainty, tempo, dynamic Elo, program history, dated ranking consensus, and contextual interactions. The benchmark has **400 folds without external rankings**, or **420 with men's rankings**. Models remain fixed to isolate feature effects. The smaller notebook 05 benchmark remains reproducible through `march-research` using a new output directory when code or inputs change.

## Project map

| Path | Purpose |
|---|---|
| `notebooks/00_data_audit_and_preparation.ipynb` | Historical raw-data audit |
| `notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb` | Historical split and snapshot protocol |
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

The lockfile covers rebuilt notebook 02, notebook 05, ingestion and the feature benchmarks. Notebooks 00, 01, 03 and 04 retain their historical contracts and environment requirements. Migrating notebook 03's nested tuning/calibration to the new feature schema precedes a new final submission recipe.

## Development

```bash
uv sync --locked --group dev
uv run --locked python scripts/quality.py
```

The quality gate compiles, lints, checks formatting and types, then runs unit and end-to-end tests with JUnit and coverage artifacts. Raw Kaggle files, environments, generated datasets, checkpoints and model binaries are excluded from Git. Use ordinary module names and edit the canonical implementation; Git history records revisions.
