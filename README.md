# NCAA tournament probability forecasting

[![Research quality](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml)

Season-aware forecasting for the men's and women's NCAA tournaments: basketball-informed
features, nested temporal model selection, calibration analysis and interpretable diagnostics.

## Start here

**Current project: this repository's `main` branch. The expanded features have
already been generated and used in completed retraining.** PR #8 replaced the
stale 124-feature handoff with the executed 3,106-candidate study. The capacity
follow-up below tests whether more of those candidates should reach each fit.

**Open the notebooks and read their saved outputs. No AWS login, dataset download,
GPU or notebook execution is needed to review the project.**

| Notebook | What an employer can inspect |
|---|---|
| [00 · Data](notebooks/00_data_audit_and_preparation.ipynb) | Official-file provenance, coverage and basketball data quality |
| [01 · Validation](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb) | Prediction cutoff, whole-season splits and pre-tournament snapshots |
| [02 · Features](notebooks/02_feature_store_and_diagnostics.ipynb) | 3,106-candidate definitions, ablations, uncertainty and feature diagnostics |
| [03 · Models](notebooks/03_model_comparison_and_diagnostics.ipynb) | Executed nested comparison, calibration, ensembles, errors and interpretation |
| [04 · Benchmark](notebooks/04_locked_benchmark_and_final_submission.ipynb) | Current retrospective evaluation and tested, optional generation/validation/download |

[05 · Feature research](notebooks/05_feature_research.ipynb) is an optional appendix,
not another prerequisite. The original notebook filenames remain canonical.

## Research scope and evidence

The expanded experiment generates **3,106 candidate features**: 124 existing signals,
2,944 distribution/recency/venue/opponent/trajectory/peer hypotheses, 26 official coach-history signals, and 12 annual conference-strength signals. The main 02/03 study retains at most **128 features per model fit**, using only the applicable temporal
training population. There is no validation-selected global feature list.

Notebook 02 records candidate counts, rejection reasons, per-fold retention, stability and paired
family ablations. The explicit no-Massey ablation removes all 23 ranking-derived inputs. Coach
performance and target encodings use strictly earlier seasons; regular-season snapshots stop at
day 132. Every candidate model is retrained against notebook 02's exact feature fingerprint.

The completed study ran **1,050 feature ablation fits and 861 model candidate fits**.
Its central result is mixed: broader features improved some men's pooled models, but
did not reliably improve both populations or beat compact models.

The subsequent [capacity study](reports/feature_capacity/README.md) adds **138 fresh fits**
and reuses **30 verified 128-input fits**. It compares limits of 32, 64, 128 and 256,
including forward-only inner selection. More inputs generally hurt; smaller screens
improve the broad logistic models but do not beat the existing compact leaders.
The 128-input main-study limit and its original results remain explicitly identified.

| Current evidence | Men: mean season Brier | Women: mean season Brier |
|---|---:|---:|
| Best observed nested development stream | 0.188396 · no-Massey pooled blend | 0.144823 · separate logistic |
| Men's ranking alternative | 0.188468 · ranking logistic | Unavailable |
| Frozen logistic anchors, retrospective 2022–2025 | 0.198288 | 0.146881 |

Lower is better. The earlier 124-feature development minima were 0.188476 and 0.143867:
the men's best is essentially tied and the women's result worsens. The full-bank Massey and combined
non-Massey coach/encoding controls have uncertainty intervals that include zero. Several
other feature groups worsen performance; compact rankings help one histogram model.
The benchmark also fails to improve the previous frozen anchors. These negative results
remain visible; adding thousands of candidates is not itself evidence of a better model.

The [completion audit](docs/research_audit.md) reconciles the old and new runs, source
coverage, measured feature effects and execution gates. Notebook 03 recomputes metrics
from recorded predictions; notebook 05 pairs previous and revised predictions game by game.
Notebook 04 links its current retrospective benchmark to those exact upstream runs. The earlier
124-feature final release remains separately identified under `reports/final_predictions/`.

| What has actually completed | Evidence |
|---|---|
| Expanded feature generation and family ablations | 3,106 candidates; 1,050 fits in notebook 02 |
| Retraining on those exact features | 861 candidate fits in notebook 03 |
| Target encoding and chronological splits | Prior-season histories, nested selection, mutation tests |
| Retained-feature capacity experiment | 168 evaluated fits; 138 new and 30 inherited |
| Current retrospective benchmark | 16 fits on previously consumed 2022–2025 seasons |
| Native notebook execution and checkpoint recovery | [Original release](reports/validation/release.json) and [capacity follow-up](reports/validation/capacity.json) |

The remaining scientific question is stronger generalization, particularly for women.
It is not whether the remade notebook 02 has been trained. Repeating identical completed
fits cannot answer that question; additional data or genuinely unseen outcomes are needed.

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

The original expanded release passed **202 tests** and native execution of **all six notebooks**
(39 code cells). A second notebook pass reused all six checkpoints. An independent fresh
artifact download restored **901 model tasks with zero repeated fits and byte-identical
predictions**. [Release evidence](reports/validation/release.json) preserves that source
and those notebook bytes. The [capacity follow-up](reports/validation/capacity.json)
separately records actual native execution of all six current notebooks (**40 code
cells**) and verified reuse of all 168 capacity tasks. The current suite has **212
tests**; exact publication checks are recorded on [PR #9](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/pull/9).
The new capacity archive's S3 backup awaits a specific upload approval; the earlier
feature/model archives remain verified and available.

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

[Studio and resume instructions](docs/studio.md) cover the **Notebook research** workflow and
`python -m march_mania.publication.inference`. Current feature and model fingerprints must match before final generation. `scripts/portfolio_release.py --help` describes the independent exact-CSV audit;
it does not invent predictions or upload to Kaggle.

MIT-licensed code. Competition data remains subject to Kaggle's terms.
