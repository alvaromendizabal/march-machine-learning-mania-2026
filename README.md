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
| [02 · Features](notebooks/02_feature_store_and_diagnostics.ipynb) | 3,090-candidate definitions, ablations, uncertainty and feature diagnostics |
| [03 · Models](notebooks/03_model_comparison_and_diagnostics.ipynb) | Executed nested comparison, calibration, ensembles, errors and interpretation |
| [04 · Final predictions](notebooks/04_locked_benchmark_and_final_submission.ipynb) | Actual final fits, retrospective benchmark, complete prediction CSV and verified recovery |

[05 · Feature research](notebooks/05_feature_research.ipynb) is an optional appendix,
not another prerequisite. The original notebook filenames remain canonical.

## Research scope and evidence

The expanded experiment generates **3,090 candidate features**: 124 existing signals,
2,944 distribution/recency/venue/opponent/trajectory/peer hypotheses, and 22 official coach-history
signals. At most **128 features are retained per model fit**, using only the applicable temporal
training population. There is no validation-selected global feature list.

Notebook 02 records candidate counts, rejection reasons, per-fold retention, stability and paired
family ablations. The explicit no-Massey ablation removes all 23 ranking-derived inputs. Coach
performance and target encodings use strictly earlier seasons; regular-season snapshots stop at
day 132. Every candidate model is retrained against notebook 02's exact feature fingerprint.

**Use the completed run records and saved notebook outputs for measured results.**
The expanded source must not be credited with old 124-feature scores. Notebook 03 recomputes metrics
from recorded predictions; notebook 05 pairs previous and revised predictions game by game.
The earlier final release in notebook 04 is a separately identified historical baseline until a
new final generation is explicitly requested through its opt-in cell.

The [official competition metric](https://www.kaggle.com/competitions/march-machine-learning-mania-2026)
is Brier score. Game-weighted Brier and mean-season Brier are reported separately. Development
seasons are 2016–2019 and 2021. The 2022–2025 benchmark was previously consumed and is **not an untouched
holdout**. Local evaluation includes play-ins and is not identical to Kaggle's scored population.
The original competition deadline was March 19, 2026; this is a retrospective portfolio project.

## User-controlled prediction generation

Notebook 04 exposes a default-off `GENERATE_SUBMISSION` control that checks current feature/model
lineage, fits the frozen recipe, generates and validates `submission.csv`, and displays a download
control. It never submits or uploads to Kaggle. No premade submission is required to review the
project. Historic final-fit artifacts retain their original fingerprint and are not relabeled
as results from the expanded feature experiment.

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
`python -m march_mania.publication.inference`. Current feature and model fingerprints must match before final generation. `scripts/portfolio_release.py --help` describes the independent exact-CSV audit;
it does not invent predictions or upload to Kaggle.

MIT-licensed code. Competition data remains subject to Kaggle's terms.
