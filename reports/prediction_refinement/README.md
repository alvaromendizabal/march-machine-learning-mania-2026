# Observed Kaggle scores and bounded adjustments

All **50 original candidates** show **Complete (after deadline)** in the owner's
screenshots. Public and private Brier scores match to seven displayed decimals.
[observed_scores.csv](observed_scores.csv) maps every score and filename to the
original production checksum. [Screenshot provenance](../prediction_production/kaggle_scores.json)
preserves the source hashes and recording time. Exact submission IDs and submission
times were not supplied. Repeated rows across screenshots were deduplicated.

| Original candidate | Observed Kaggle Brier |
| --- | ---: |
| `m_pooled_xgboost__w_logistic` | **0.1229419** |
| `m_pooled_hist__w_logistic` | 0.1241702 |
| `m_pooled_blend__w_logistic` | 0.1246834 |
| `m_rank_logistic__w_logistic` (original reference) | 0.1257070 |

Women's logistic regression has the lowest combined score for every men's stream.
These are observed late scores. They do not represent a previously unseen test set
for any hypothesis chosen after this observation.

## Executed follow-up

Eight adjustments keep women's logistic probabilities unchanged. Men's pooled
XGBoost is mixed with ranked logistic regression or pooled histogram boosting using
25%, 50% and 75% XGBoost weights. Two confidence controls use temperature 0.90
(sharper) and 1.10 (softer). The [configuration](../../configs/prediction_refinement.json)
freezes all eight definitions. No model is refitted and the original production
recipe remains unchanged.

[historical_catalog.csv](historical_catalog.csv) and
[metrics_by_season.csv](metrics_by_season.csv) evaluate the transformations on
649 aligned historical games from 2016–2019 and 2021. Base procedures were selected
using earlier seasons. These development years were already explored. Historical
procedure scores do not directly validate the final fitted estimators.

| Adjustment | Historical Brier | Improved seasons vs anchor |
| --- | ---: | ---: |
| Pooled XGBoost anchor | 0.167220 | — |
| 50% pooled XGBoost + 50% ranked logistic | **0.166321** | 3 / 5 |
| 75% pooled XGBoost + 25% ranked logistic | 0.166542 | **4 / 5** |
| Pooled XGBoost, temperature 1.10 | 0.167057 | 4 / 5 |

Pooled-histogram mixtures and temperature 0.90 do not improve aggregate historical
Brier. All eight now have [recorded Kaggle scores](../submission_scores/README.md).
Temperature 0.90 is the best observed late score, **0.1225463**, despite worsening
historical Brier. This disagreement limits claims about future generalization.
The original reference is preserved. The complete 58-file collection includes
all original and adjusted predictions with their exact bytes and score history.

## Reproduce and download

[Notebook 04](../../notebooks/04_locked_benchmark_and_final_submission.ipynb) shows
the complete score matrix and historical comparison. Its separate default-off
`GENERATE_REFINEMENT` control verifies the source ZIP, generates the eight named
CSVs, and displays a ZIP download. Run `RESTORE_PRODUCTION` first when the original
download is absent. This requires no new training.

```bash
uv run --locked python -m march_mania.publication.refinement --check
uv run --locked python scripts/deliver_predictions.py --action restore
uv run --locked python -m march_mania.publication.refinement --generate
```

The new download is `submissions/prediction_refinement.zip`.
[generation.json](generation.json) records actual generation;
[submission_manifest.csv](submission_manifest.csv) records all eight hashes and
their original production lineage. The archive includes the exact adjustment
recipe. [storage.json](storage.json) pins the private AWS versions of the ZIP and
score ledger, with verified full-object SHA-256, byte lengths and expected owner.
Generation checks ID order, finite probabilities, unchanged women's rows,
distinct output files, and ZIP member checksums. Repeating it reuses verified
completed outputs. Extract the ZIP and submit chosen model CSVs individually.
The manifest and recipe are not predictions to upload. No code here sends a Kaggle
submission.
