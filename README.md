# NCAA tournament probability forecasting

Forecasting men's and women's college basketball tournament games with chronological evaluation, calibrated probability diagnostics, and reproducible experiments.

**Current phase: feature research and AWS Studio migration.** The original modeling notebooks and results are preserved. A compact, tested research pipeline now compares feature families, saves resumable fold checkpoints, and produces a standalone interactive report.

[Studio setup and commands](docs/studio.md) · [Research protocol and evidence audit](docs/research_protocol.md) · [Research notebook](notebooks/05_feature_research.ipynb)

## Results and their limits

| Recorded submission | Observed Brier ↓ | Evidence |
|---|---:|---|
| Original challenger | 0.1299012 | Repository score log |
| Development-frozen blend | 0.1318165 | Repository score log |
| Original primary | 0.1421117 | Repository score log |
| Best recorded temperature refinement | 0.1281386 | Post-result exploratory refinement |

These are repository-recorded scores, not independently authenticated Kaggle standings. The recalled approximately 0.121 result has not yet been located. Post-result refinements are not untouched validation and do not establish a medal. New feature research has no measured real-data improvement yet.

## Reproducible research

```bash
python3 scripts/bootstrap.py
.venv/bin/python scripts/inspect_data.py march-machine-learning-mania-2026.zip
.venv/bin/march-research --preflight
.venv/bin/march-research --output outputs/research --s3 s3://YOUR_BUCKET/research
```

A locked Python 3.12 environment, fixed random seeds and CPU thread limits make the run reproducible. UTC events, task heartbeats, elapsed time and checksum-verified checkpoints make it observable and resumable. Git stores code and evidence; private S3 stores input snapshots and generated models/results. See the [Studio guide](docs/studio.md) for the provisioned project bucket and exact commands.

The feature ladder evaluates seeds, opponent-adjusted strength, schedule quality, efficiency, recent form and nonlinear matchup interactions. The default protocol runs **120 matched fold tasks**. Models are intentionally fixed while testing the feature hypotheses. Brier is the primary probability metric, supported by log loss, discrimination, calibration and paired season uncertainty.

## Project map

| Path | Purpose |
|---|---|
| `notebooks/00_data_audit_and_preparation.ipynb` | Historical raw-data audit |
| `notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb` | Historical split and snapshot protocol |
| `notebooks/02_feature_store_and_diagnostics.ipynb` | Original rich feature store |
| `notebooks/03_model_comparison_and_diagnostics.ipynb` | Original nested model comparison |
| `notebooks/04_locked_benchmark_and_final_submission.ipynb` | Historical benchmark and submission |
| `notebooks/05_feature_research.ipynb` | Auditable feature research and results review |
| `src/march_mania/` | Reusable preparation, features, experiment runtime and reporting |
| `configs/research.json` | Explicit research boundaries and runtime configuration |
| `tests/` | Structural, temporal, probability, failure, resume and restore tests |
| `reports/` | Historical results and documented validation evidence |
| `docs/` | Research rationale and operational instructions |

The original environment exports document the older notebooks. The new lockfile covers the research runner and notebook 05; it does not claim to migrate every optional legacy model framework.

## Development

```bash
uv sync --locked --group dev
uv run --locked python scripts/quality.py
```

The quality gate compiles, lints, checks formatting and types, then runs unit and end-to-end tests with JUnit and coverage artifacts. Raw Kaggle files, environments, generated datasets, checkpoints and model binaries are excluded from Git. Use ordinary module names and edit the canonical implementation; Git history records revisions.
