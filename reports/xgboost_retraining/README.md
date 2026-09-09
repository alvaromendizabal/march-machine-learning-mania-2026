# Bounded XGBoost retraining and coverage audit

The eight observed follow-up submissions motivated a small retrospective study,
not a new holdout experiment. Repeating the same deterministic model on unchanged
inputs provides no new signal. This experiment changes specific assumptions in
the strongest submitted men's recipe while preserving the original production
configuration and all submitted prediction bytes.

## Coverage and temporal boundaries

The [source coverage table](../feature_store/source_coverage.csv) covers every raw
season. Men's Massey observations start in **2003**. The current research and
production pipelines start training in **2013**, well inside that coverage.
Every men's regular-season team has legal Massey and coach records in **2013–2026**;
the last available ranking publication is day 128, before the day-132 cutoff.
Individual ranking-system coverage varies. This is complete team-level consensus
coverage, not a claim that every system reports every team every year.

Each development fit uses seasons strictly before its validation year. The outer
development seasons are 2016–2019 and 2021. Final production uses 2013–2025,
excluding the canceled 2020 tournament. No 2026 tournament outcome enters a fit.
Women's models exclude all 23 Massey-derived columns; no women's ratings or
coach records are fabricated. Coach history and target-derived features use only
earlier seasons. Notebook 02 now asserts coverage for every modeled year, and the
retraining engine rejects an unsupported season or incomplete men's coverage.

## Executed comparisons

[The configuration](../../configs/xgboost_retraining.json) declares seven recipes.
All use XGBoost depth 2, learning rate 0.04, seed 2026 and two threads. The pooled
reference uses 120 trees, minimum child weight 10, L2 regularization 10 and at most
128 training-screened features. New fits change tree count, regularization,
retained capacity, or remove coaches from the men's Massey recipe.

**28 new candidate/fold tasks** and **21 verified existing controls** cover inner
2014–2015 seasons and five outer development seasons. Checkpoints include the
screen, fitted estimator, predictions, rejection reasons, training years and
checksums. Existing predictions come from the exact earlier model archive.
Training includes mirrored rows; scoring uses each physical game once. All model
selection uses strictly earlier out-of-fold seasons. Tests mutate validation
labels and require the fitted screen/model to remain unchanged.

| Fixed recipe | Men's game-weighted Brier | Mean-season Brier |
|---|---:|---:|
| Pooled, 64 features | **0.184333** | **0.184403** |
| Pooled, lighter regularization | 0.185088 | 0.185155 |
| Pooled, 240 trees | 0.185116 | 0.185166 |
| Pooled reference | 0.185134 | 0.185199 |
| Men's Massey, no coach | 0.191808 | 0.191867 |
| Men's Massey | 0.192201 | 0.192258 |
| Men's reference without Massey | 0.193306 | 0.193366 |

These are **334 men's historical games**, not the combined men's/women's 2026
Kaggle score. The broader nested candidate-selection stream in notebook 03 is a
different procedure and must not be treated as this fixed-recipe baseline.

Reducing capacity to 64 helps three of five seasons, with a game-weighted gain of
0.000801. Its exploratory mean-season bootstrap interval for the paired change
is **−0.004364 to +0.003439**. All five declared paired-comparison intervals cross
zero. They resample complete seasons, with 4,000 replicates, and are not adjusted
for multiple comparisons.

Forward-only recipe selection produces **0.185070** game-weighted Brier versus
**0.185134** for the pooled reference, a gain of only **0.000064**. Its mean-season
Brier is **0.185138**, log loss **0.545950**, ROC AUC **0.798954**, and 10-bin
calibration error **0.073055**. Calibration error is worse than the reference's
**0.058835**. This does not establish a dependable retraining improvement.

## What did Massey and coaches contribute?

In these matched men's XGBoost controls, Massey reduces game-weighted Brier by
**0.001105**. Removing coaches from that Massey recipe further reduces it by
**0.000393**. Both effects are uncertain and both recipes trail the pooled model.
They are conditional pipeline effects: changing the eligible bank can change
which correlated features survive screening.

Earlier feature ablations showed that compact Massey consensus helps histogram
boosting more clearly: mean-season improvement **0.010687**, exploratory interval
**0.002978 to 0.016580**. Compact logistic improves more modestly. Broad-bank
Massey and coach effects vary by model and season, with intervals including zero.
See the [paired family ablations](../feature_store/ablation_intervals.csv).

The submitted pooled-XGBoost winner has **no Massey inputs** by design. Neither
its seeded nor seed-free final 128-feature screen retained a coach feature.
Therefore, its strong submission score cannot be attributed to coaches or Massey.
The temperature-0.90 adjustment retains that same fitted model and feature set.

## Decision and reproduction

Keep the original production reference. The **64-feature pooled challenger** is
the strongest bounded candidate to freeze for a future evaluation, but it is not
promoted on these retrospective results. The observed temperature gain on 2026
also conflicts with its historical result. Further leaderboard-driven tuning
would not resolve this uncertainty. No new submission CSV is generated here.

Notebook 03 recomputes the comparisons and displays a Plotly interval figure with
a static GitHub fallback. Compact evidence includes [per-game predictions](predictions.csv),
[annual metrics](metrics_by_season.csv), [selection decisions](selection.csv),
[fit audits](fit_audits.json) and [input/source hashes](summary.json).

```bash
uv run --locked python -m march_mania.publication.retraining --check
# After restoring the exact feature_store/run and model_comparison/run inputs:
uv run --locked python -m march_mania.publication.retraining --run --inputs outputs/retraining_inputs
```

The versioned archive in [storage.json](storage.json) preserves the 28 fitted
estimators and complete task checkpoints, exact input matrices and their original
archive receipts, source/configuration and all comparison outputs. Matching
completed tasks are reused after checksum verification. Routine notebook review
only verifies the published evidence; retraining is an explicit opt-in.
