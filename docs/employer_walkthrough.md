# NCAA forecasting: an employer walkthrough

**Final observed result: 0.1222672 Brier.** The completed portfolio contains 70
scored submissions, 3,946 feature hypotheses, executed notebooks and reproducible
model artifacts. The best late submission combines pooled XGBoost for men with
conference logistic regression for women.

## A two-minute review

| Open | What to look for |
|---|---|
| [Final results](../reports/final_results/README.md) | Observed Brier, exact winning model, all 70 scores and the distinction between retrospective selection and forecasting claims |
| [Notebook 02](../notebooks/02_feature_store_and_diagnostics.ipynb) | Domain hypotheses, legal feature timing, controlled ablations and evidence against unlimited feature expansion |
| [Notebook 03](../notebooks/03_model_comparison_and_diagnostics.ipynb) | Matched season comparisons, calibration, model-selection boundaries and negative findings |
| [Notebook 04](../notebooks/04_locked_benchmark_and_final_submission.ipynb) | Polished Plotly results, the completed score ledger and default-off recovery/generation controls |
| [Quality workflow](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml) | Tests, type checks, release integrity and native notebook execution on the proposed revision |

The saved outputs require no setup to inspect. Data provenance and split design
are in notebooks 00–01; notebook 05 is an optional appendix.

## Trace the winning prediction

1. [Official input receipts](../reports/prediction_production/input_receipts.json)
   identify the immutable feature matrix, team snapshots and Stage 2 template.
2. The men’s component is `c_7808f53a9ebd1b6bf13a`, pooled `xgboost_full_2`:
   120 depth-2 trees, 128 training-screened inputs, fitted on 1,575 games through 2025.
   [The original recipe](../reports/prediction_production/recipe.json) and
   [fit audits](../reports/prediction_production/fit_audits.json) preserve its identity.
3. Women’s `conference_c100` is logistic regression with C=1.0, fitted on 772
   women’s games through 2025. Its [two route audits](../reports/women_challengers/final_fit_audits.json)
   record 16 seeded and 15 seed-free retained inputs.
4. Temperatures 0.90 for men and 1.10 for women produce
   `m_pooled_xgboost_t090__w_conference_c100_t110.csv`: 132,133 rows,
   SHA-256 `b7704da76ea2b48839e1fdfaa32d593cf0cc23171d3b67e13987f152342bc92e`.
5. [Screenshot provenance](../reports/final_results/provenance.json) joins that
   exact file to the displayed private/public Brier of 0.1222672.
   [The final collection](../reports/final_results/collection.json) verifies all
   70 original CSVs without fitting or changing their bytes.

## What the work demonstrates

Temporal snapshots, target encodings and coach histories respect information
availability. Feature screening uses only the training fold. Whole-season
validation avoids treating related games as independently shuffled observations.
Brier, log loss, ranking metrics and calibration diagnostics remain separate.
Model reload checks, team-swap symmetry, ID validation, content hashes and
checkpoint reuse cover both statistical and engineering failure modes.

Compact feature groups remain competitive with much wider banks. Massey helps
some men’s models, but broader inputs, extra trees and coach additions do not
consistently improve earlier-season selection. The project preserves those negative
results instead of presenting only a favorable final score.

## Limits that matter

The final submissions were late and selected retrospectively. The explored
2016–2019/2021 development seasons and previously consumed 2022–2025 benchmark
are not new holdouts. No 2026 outcome enters fitting, but 2026 score feedback informed
later hypotheses. The final observed winner is distinct from the unchanged frozen
development reference. Seed-free template coverage lacks matched tournament validation.

All bounded release work is complete. Timestamped external player information or
a future tournament under a frozen protocol would be a new project extension.
