# A short guide to the research

**Question:** does broader basketball feature engineering improve NCAA tournament
win probabilities enough to justify the added complexity?

**Finding:** compact team-strength and consensus-ranking representations remain
the supported choice. The project investigated 3,946 candidate definitions,
including controlled family ablations, feature-capacity comparisons and individual
ranking-system representations. Apparent gains were not consistently stable under
earlier-season selection. The contribution is a reproducible decision supported by
positive and negative evidence, with explicit limits on forecasting claims.

## Two-minute review

| Inspect | What it demonstrates |
|---|---|
| [Feature research, notebook 02](../notebooks/02_feature_store_and_diagnostics.ipynb) | Basketball hypotheses, temporal screening, family ablations, capacity limits and the decision to stop expanding the feature bank |
| [Model comparison, notebook 03](../notebooks/03_model_comparison_and_diagnostics.ipynb) | Season-based evaluation of logistic regression, histogram boosting, XGBoost and LightGBM; calibration and error diagnostics |
| [Benchmark and production, notebook 04](../notebooks/04_locked_benchmark_and_final_submission.ipynb) | The consumed 2022–2025 benchmark, frozen final recipe, fifty completed files and verifiable recovery |
| [Quality workflow](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml) | Tests, type checking, release audits, native notebook execution and checkpoint reuse on each proposed revision |

The notebooks include saved outputs and figures. A reviewer needs no AWS account,
private data or GPU. For the full method, begin with [data provenance in 00](../notebooks/00_data_audit_and_preparation.ipynb)
and [information boundaries in 01](../notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb).
Notebook 05 is an optional research appendix.

## Trace the reference prediction file

The declared reference is `m_rank_logistic__w_logistic`. Its lineage is inspectable
without downloading the private model archive:

1. [Input receipts](../reports/prediction_production/input_receipts.json) identify the
   current feature and model archives by immutable version and checksum, including
   the team snapshots and official Stage 2 template used for prediction.
2. [The frozen recipe](../reports/prediction_production/recipe.json) selects components
   using only explored 2016–2019 and 2021 development predictions. The men's reference
   uses `rank_logistic_1`, component `c_a6748f16757a948ce51c`, at weight 1.
3. [Fit audits](../reports/prediction_production/fit_audits.json) record final training
   through 2025. That men's component retains 17 seeded inputs and 16 seed-free
   inputs; the latter removes `diff_seed`. Screening and fitting use training data.
4. [The file manifest](../reports/prediction_production/submission_manifest.csv)
   identifies `csv_m_rank_logistic__w_logistic/submission.csv`: 132,133 rows,
   4,635,537 bytes, SHA-256
   `a4b4e17f1e6f3f2c938e83949872fd463eb3af1fea3ebeea524bc6d745bd51ed`.
5. [Independent model replay](../reports/prediction_production/saved_model_verification.json)
   reproduced every saved probability across 33 estimators and 259 chunks.
   [Fresh S3 recovery](../reports/prediction_production/s3_recovery.json) reused all
   344 checkpoints with zero new fits and fifty byte-identical CSVs.

The complete batch contains 6,606,650 probabilities across fifty distinct files.
Shared components are fitted once and reused across the ten-by-five procedure
combinations. Models, source snapshots and checkpoint inventories remain in the
versioned private archive; small audit evidence remains in Git.

## What the evidence supports

- Temporal feature construction, training-only selection and physical-game checks
  constrain leakage. Team-order symmetry and exact template validation constrain
  prediction errors. These are tested properties, not a claim that all bias is absent.
- The official game-weighted Brier score and mean-season Brier answer different
  aggregation questions and are reported separately. No favorable metric is
  substituted silently for the evaluation contract.
- The pre-2022 development years were explored; 2022–2025 was already consumed.
  Neither is a fresh holdout. Final fitting excludes 2026 outcomes, but generating
  the files retrospectively is not evidence of prospective competition performance.
- The 127,577 template pairs requiring seed-free features lack matched tournament
  OOF validation. Full template coverage does not establish accuracy for nonqualifiers.
- Fifty files are a delivery and sensitivity-analysis result. They are not fifty
  independent findings, accepted Kaggle uploads or a new promoted winner.

A future tournament under a frozen protocol would provide a new test of forecasting
improvement. More columns or retrospective leaderboard comparisons cannot provide it.

## Reproduce or retrieve

Follow the [locked setup](../README.md#reproduce-or-generate-predictions) and
[Studio instructions](studio.md). The public production audit needs no private data:

```bash
uv run --locked python -m march_mania.publication.production_release --check
```

With authorized access to the existing private bucket, notebook 04's
`RESTORE_PRODUCTION` control retrieves the completed files without training.
The equivalent terminal command is:

```bash
uv run --locked python -m march_mania.publication.production_release --recover
```

The notebook also exposes a separate, default-off production execution control.
The [production report](../reports/prediction_production/README.md) documents exact
recipes, input restoration, model verification and the archive. The
[completion plan](completion_plan.md) distinguishes completed delivery gates from
future research extensions.

The completed batch can also be downloaded as one checksum-verified ZIP from notebook 04. [Delivery evidence](../reports/prediction_production/delivery.json) records all fifty exact CSVs, the guarded zero-fit generation replay and the immutable S3 download version.
