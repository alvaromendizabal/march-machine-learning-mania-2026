# NCAA tournament probability forecasting

Season-aware forecasting for the men's and women's NCAA tournaments: basketball-informed
features, nested temporal model selection, calibration analysis and interpretable diagnostics.

## Start here

**Open the notebooks and read their saved outputs. No AWS login, dataset download,
GPU or notebook execution is needed to review the project.**

| Notebook | What an employer can inspect |
|---|---|
| [00 · Data](notebooks/00_data_audit_and_preparation.ipynb) | Official-file provenance, coverage and basketball data quality |
| [01 · Validation](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb) | Prediction cutoff, whole-season splits and pre-tournament snapshots |
| [02 · Features](notebooks/02_feature_store_and_diagnostics.ipynb) | 124-feature definitions, ablations, uncertainty and feature diagnostics |
| [03 · Models](notebooks/03_model_comparison_and_diagnostics.ipynb) | Executed nested comparison, calibration, ensembles, errors and interpretation |
| [04 · Final predictions](notebooks/04_locked_benchmark_and_final_submission.ipynb) | Actual final fits, retrospective benchmark, complete prediction CSV and verified recovery |

[05 · Feature research](notebooks/05_feature_research.ipynb) is an optional appendix,
not another prerequisite. The original notebook filenames remain canonical.

## Executed results

The current-schema development experiment contains **497 candidate fits**, **20 nested selection
contexts**, **14,946 prediction rows** and **649 distinct validation games**. Logistic regression,
histogram boosting, XGBoost and LightGBM are compared in separate and shared-feature pooled settings.

| Evidence and population | Men's game-weighted Brier ↓ | Women's game-weighted Brier ↓ |
|---|---:|---:|
| Nested development · 2016–2019 and 2021 | 0.188409 | 0.143867 |
| Frozen seeded recipe · consumed 2022–2025 benchmark | 0.198014 | 0.138599 |

These are **retrospective results on different season populations**, not Kaggle scores or a new
untouched holdout. Nested development selects and calibrates from earlier seasons inside each outer
fold. The final recipe uses men's ranking logistic and women's dynamic-Elo logistic, with feature
blocks and regularization frozen from 2016–2019/2021 forecasts. Identity calibration is retained;
no temperature or recipe is tuned on the displayed 2022–2025 benchmark. Notebook 04 reports 268
benchmark games per tournament, log loss, ROC AUC, average precision, calibration and seed-free
sensitivity. Notebook 03 also reports season-clustered uncertainty and permutation diagnostics.

**132,133 real 2026 matchup probabilities** are generated and audited against the official Stage 2
template. Four final estimators train through 2025: men's and women's models, each with seeded and
seed-free routes. No 2026 tournament outcomes enter fitting. The seed-free model removes every
seed-dependent input rather than inventing missing seeds; its tournament validation does not
establish performance on teams that did not qualify.

The [official competition metric](https://www.kaggle.com/competitions/march-machine-learning-mania-2026)
is Brier score. Our local tournament evaluation includes play-ins; the official 2026 scored set does
not. The formula matches, but the game populations must not be conflated. Historical neural/margin
models and [earlier submission records](reports/submission_portfolio/) retain their original lineage.
Recorded scores there are not independently authenticated Kaggle receipts.

## Prediction file and durability

The [successful final-prediction run](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/runs/34083821689)
passed 152 tests, fitted 20 estimators (16 historical evaluation fits and four final fits), and generated
the CSV. A fresh local directory restored **53 tasks from private S3 with zero repeated fits** and
identical submission bytes. The [validation artifact](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/runs/34083821689/artifacts/10004608823)
contains `final/submission.csv`, reports and execution evidence. Its 90-day retention is separate
from the durable versioned private S3 copy documented in [Studio instructions](docs/studio.md).

**Generation is complete; a new Kaggle upload has not been sent.** Submission SHA-256:
`1be5445fadc1c47531bbede2a5892327524a2aaa667663f0628d13b8057facb4`.
The original competitive deadline was March 19, 2026 at 16:00 UTC; later releases are retrospective.

## Engineering that can be inspected

Reusable Python lives in `src/march_mania`; notebooks explain the results rather than holding
hidden training state. Tests cover temporal boundaries, game uniqueness, symmetry, probability
validity, checkpoint corruption, interruption recovery, published metric integrity and notebook
publication. Tests treat meaningful warnings as errors; publication rejects warning/error outputs.

Runs emit UTC timestamps, task/total elapsed time, progress and 15-second task heartbeats.
Completed estimators and forecast batches are content-verified and reused. A failed estimator
restarts that fit, not earlier successful fits. Notebook execution reuses **whole completed
notebooks**; an interrupted notebook restarts from its first cell. Canonical notebooks are replaced
atomically after successful execution. Changed inputs invalidate the relevant checkpoints.

Private S3 preserves inputs, fitted estimators, forecasts and exact source independently of Studio
or GitHub runners. Git stores code, executed notebooks and compact public evidence, not raw data,
trained binaries or credentials. The final workflow uses narrowly scoped, short-lived AWS credentials.

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

[Studio and resume instructions](docs/studio.md) cover the **Final predictions** workflow and
`python -m march_mania.publication.inference`. Neither requires repeating the completed model
comparison. `scripts/portfolio_release.py --help` describes the independent exact-CSV audit;
it does not invent predictions or upload to Kaggle.

MIT-licensed code. Competition data remains subject to Kaggle's terms.
