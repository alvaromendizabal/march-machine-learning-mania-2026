# NCAA tournament probability forecasting

Season-aware forecasting for the men's and women's NCAA tournaments: basketball-informed
features, nested temporal model selection, calibrated probabilities and interpretable diagnostics.

## Start here

**Open the notebooks and read their saved outputs. No AWS login, dataset download,
GPU or notebook execution is needed to review the project.**

| Notebook | What an employer can inspect |
|---|---|
| [00 · Data](notebooks/00_data_audit_and_preparation.ipynb) | Official-file provenance, coverage and basketball data quality |
| [01 · Validation](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb) | Prediction cutoff, whole-season splits and pre-tournament snapshots |
| [02 · Features](notebooks/02_feature_store_and_diagnostics.ipynb) | 124-feature definitions, ablations, uncertainty and feature diagnostics |
| [03 · Models](notebooks/03_model_comparison_and_diagnostics.ipynb) | Executed nested comparison, calibration, ensembles, errors and interpretation |
| [04 · Benchmark and submissions](notebooks/04_locked_benchmark_and_final_submission.ipynb) | Earlier benchmark evidence, its limitations, submission manifests and audit contract |

[05 · Feature research](notebooks/05_feature_research.ipynb) is an optional research appendix,
not another prerequisite. The original notebook filenames remain canonical.

## Current model evidence

The completed current-schema experiment contains **497 candidate fits**, **20 nested selection
contexts**, **14,946 saved prediction rows** and **649 distinct validation games**. Men and women
are evaluated separately and with a shared-feature pooled alternative. The executed families
are logistic regression, histogram boosting, XGBoost and LightGBM.

| Stream | Game-weighted Brier ↓ | Mean season Brier ↓ |
|---|---:|---:|
| Men's ranking logistic | 0.188409 | 0.188476 |
| Men's pooled common blend | 0.190840 | 0.190919 |
| Women's separate logistic | 0.143867 | 0.143867 |
| Women's pooled common blend | 0.146494 | 0.146494 |

These are **retrospective development results** for 2016–2019 and 2021, not Kaggle leaderboard
scores or a newly untouched test. Model selection and calibration use earlier-season predictions
inside each outer fold. The tables distinguish game-weighted Brier from equal-season averaging.
Notebook 03 recomputes both from saved predictions and reports log loss, ROC AUC, average precision,
calibration, season-clustered uncertainty and held-out permutation diagnostics.

The [official competition metric](https://www.kaggle.com/competitions/march-machine-learning-mania-2026)
is Brier score. Our local tournament evaluation includes play-ins; the official 2026 scored set does
not. The metric formula matches, but the game populations must not be conflated.

The [earlier submission log](reports/submission_portfolio/kaggle_scores.csv) records a challenger
score of **0.1299012** and a later temperature-refinement score of **0.1281386**. These records are
not independently authenticated Kaggle receipts. The latter is post-result sensitivity analysis,
not confirmatory validation. Historical neural models, the consumed 2022–2025 benchmark and the
original final model card describe the **earlier feature schema**, not current-schema retraining.

## Engineering that can be inspected

Reusable Python lives in `src/march_mania`; notebooks explain the results rather than holding
hidden training state. Tests cover temporal boundaries, game uniqueness, symmetry, probability
validity, checkpoint corruption, failure recovery and notebook publication. Meaningful warnings
are not hidden; tests treat warnings as errors, and publication rejects emitted warning/error outputs.

Runs emit UTC timestamps, total and task elapsed time, progress and 15-second heartbeats.
Completed model tasks are content-verified and reused. A failed estimator restarts that fit,
not earlier successful fits. Notebook execution similarly reuses **whole completed notebooks**;
a failed notebook restarts from its first cell because its old kernel state is not trustworthy.
Canonical notebooks are replaced atomically only after successful execution. Changed code,
configuration, evidence or environments invalidate the relevant publication cache.

Private S3 archives preserve completed experiments independently of Studio's persistent volume.
The feature and model archive references and checksums are in their `reports/*/run.json` records.
CI preserves JUnit, coverage, UTC logs, notebook checkpoints and the exact source under validation.
No trained model binaries, raw competition data or credentials belong in Git.

## Maintainer commands

The existing Studio checkout can be updated with `python3 scripts/update.py` from its project
folder. It preserves edited notebooks, fast-forwards `main`, installs the lock and runs checks.

For a fresh reproduction environment:

```bash
uv sync --locked --group dev
uv run --locked python -m ipykernel install --user --name march-mania
uv run --locked python scripts/quality.py
uv run --locked python scripts/notebook.py --execute --publish
```

[Studio and resume instructions](docs/studio.md) cover data, feature/model execution and optional
S3 replication. The notebook command executes all six canonical notebooks and resumes verified
completed ones on repeat runs.

`scripts/portfolio_release.py --help` explains how to audit and package an **existing real CSV**
against the official Stage 2 template, preserving its exact bytes and optional recorded checksum.
It does not generate probabilities, invent missing predictions, retune models or submit to Kaggle.
Notebook 04 makes file availability explicit. The original competitive deadline was March 19,
2026 at 16:00 UTC; later releases are retrospective.

MIT-licensed code. Competition data remains subject to Kaggle's terms.
