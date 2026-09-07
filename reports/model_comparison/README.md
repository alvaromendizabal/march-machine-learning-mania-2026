# Nested temporal model comparison

Executed on 2026-09-07 using the verified 124-feature store. The experiment
completed 497 candidate fits and 20 outer selection contexts in 63.384 seconds,
saving 14,946 predictions across 649 physical tournament games.

| Best observed stream | Mean season Brier | Game-weighted Brier |
|---|---:|---:|
| Men: ranking logistic | 0.188476 | 0.188409 |
| Women: separate logistic | 0.143867 | 0.143867 |
| Men: separate seed baseline | 0.200158 | 0.200083 |
| Women: separate seed baseline | 0.151179 | 0.151179 |

Read the [executed notebook](../../notebooks/03_model_comparison_and_diagnostics.ipynb)
for scoreboards, reliability, season variability, paired uncertainty, blend weights,
held-out permutation diagnostics, and direct recalculation from saved predictions.

## Protocol

- Validation: 2016, 2017, 2018, 2019 and 2021. Training starts in 2013.
- Candidates: seed logistic, regularized logistic, histogram boosting, XGBoost and
  LightGBM; additional men's ranking logistic. The common-model candidate bank is
  identical across separate and pooled fits and excludes 23 Massey-derived columns.
- Feature-group and hyperparameter choices use mean season Brier on earlier OOF
  predictions. Fixed boosting length avoids outer-validation early stopping.
- Identity and bounded temperature calibration are compared with forward-only
  inner folds. The earliest outer year has only one calibration validation year.
- Convex ensemble weights use raw inner OOF probabilities and regularization
  toward equal weights. Men's ranking logistic is outside this common-feature blend.
- Every physical game remains inside one season; mirrored pairs are created only
  inside the training fold. Every fitted candidate passes a team-swap audit.
- Permutation importance uses the last outer season, five shuffles per feature,
  and the selected model held fixed. It is descriptive, not causal or a tuning rule.

## What the results establish

The ranking/logistic streams outperform the seed baselines in these development
seasons. Boosting and blending do not outperform the best observed logistic
streams. Temperature calibration is selected in 21 of 105 family/context folds;
its outer performance remains visible alongside raw probabilities.

The current men's minimum is worse than the earlier reported rich-system value
of 0.180669. That system used a different feature schema and broader training
history; its original predictions are needed for a controlled paired comparison.
The current minimum also does not beat notebook 02's best fixed-feature result;
that comparison is exploratory because notebook 02's blocks were inspected on
the same development seasons. No new final recipe has been promoted.

These are retrospective development results. Five seasons provide limited
uncertainty, the intervals are not adjusted for multiple comparisons, and the
2022–2025 benchmark has already been evaluated in prior work. Historical neural
and margin results remain under `reports/modeling/03_model_comparison`; they
have not been rerun on the current schema. No Kaggle submission occurred here.

## Reproducibility and artifacts

`run.json` contains source/configuration/input hashes, measured runtime, archive
status and checksums. `predictions.csv` supports direct independent metric checks.
`selection.csv` and `decisions.json` expose the history boundaries, selected
settings and calibration crossfits. `validation.json` records the local quality gate.
Full candidate forecasts, serialized models, feature matrices, fold manifests,
task logs/checkpoints and a standalone interactive report are in the run archive.

The test suite has 102 passing tests and 90% measured coverage. Added tests run
every current engine, perturb outer/future outcomes, verify common-feature
parity and probability symmetry, interrupt a run, and check reuse/recomputation
after checksum corruption. Python warnings are errors in tests; the data run also
executed with `PYTHONWARNINGS=error`. LightGBM's routine native split chatter is
disabled through its verbosity setting; fatal errors still raise.

Resource telemetry from restricted process namespaces is not used to claim
peak RAM or size production instances. Runtime figures are measured in this
execution environment and are not a performance guarantee for other machines.

References: [official Brier metric](https://www.kaggle.com/competitions/march-machine-learning-mania-2026),
[XGBoost CPU package](https://pypi.org/project/xgboost-cpu/3.1.3/),
[LightGBM 4.6 parameters](https://lightgbm.readthedocs.io/en/v4.6.0/Parameters.html).
