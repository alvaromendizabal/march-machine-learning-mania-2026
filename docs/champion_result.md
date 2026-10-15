# 0.1034347 · Kaggle-scored NCAA forecasting

**Alvaro Mendizabal · March Machine Learning Mania 2026 · Submission 57122407**

| Recorded result | Value |
|---|---:|
| Kaggle public Brier | **0.1034347** |
| Kaggle private Brier | **0.1034347** |
| Forecast population | 132,133 within-division matchup probabilities |
| Men's / women's candidate rows | 66,430 / 65,703 |
| Evaluation context | Late, retrospective 2026 submission |

This is the project's featured scored result—not an unsubmitted offline estimate. The normalized [result record](../reports/champion_result/kaggle_record.json) preserves the submission identifier, both displayed scores and the full forecast's SHA-256 without exposing its probabilities or trained models.

## What the number means

Brier is the mean squared error of probabilities on the applicable scored games; lower is better. The full candidate row count includes possible matchups and is **not** the number of played games scored. A Brier of 0.1034347 is not 89.7% accuracy.

The result was obtained retrospectively after 2026 outcomes were available. It is not an official competition win, a claim of untouched validation, a prospective 2027 result or evidence of betting profitability. These are scope distinctions; they do not make the Kaggle score less real.

## Evidence and provenance

The retained owner audit records explicitly associate v155, submission 57122407 and both displayed scores of 0.1034347. The owner reconfirmed that association for this release. The source-lineage records preserve the original forecast digest. The JSON is a normalized publication record of that evidence, **not a newly fetched raw Kaggle API response**. No new submission or live account query occurred during this portfolio update.

Earlier published results and their receipts remain in the [historical case study](benchmark_comparison.md). They are preserved as history, not presented as the project's current best result.

## Separate, reproducible public demonstration

The [Duke × Michigan lab](public_demo.md) uses authored public ratings and an eight-team bracket. Its exact probability engine, path attribution, sensitivity calculations and exports are reproducible offline. It does not load or regenerate the private scored forecast. [Model card](model_card.md) · [Technical review](../START_HERE.md)
