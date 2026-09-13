# Milestone 13 — evidence review

Source: the user's `milestone_13_return.zip`. The delivered evidence directory contains its
non-ZIP members verbatim. All 23 files covered by the return-integrity manifest were
verified before the next release was prepared. No missing raw records or model bytes were inferred.

## Measured results — men's later-era historical main draw

| Year | Reference Brier | Reference plus consensus | Delta |
|---|---:|---:|---:|
| 2022 | 0.2229206 | 0.2223017 | -0.0006189 |
| 2023 | 0.2083905 | 0.2084530 | +0.0000624 |
| 2024 | 0.1937255 | 0.1915872 | -0.0021383 |
| 2025 | 0.1474573 | 0.1474004 | -0.0000569 |

Mean Brier delta: **-0.0006879083**; three of four seasons improved; worst deterioration
+0.0000624355. The preserved decision is **CONSIDER_FIXED_PRODUCTION_RECIPE_TEST**.
This passes the declared exploratory replication gate; it is not automatic promotion.

Most improvement comes from 2024. Omitting 2024 leaves mean delta **-0.0002044492**.
The 2022 Brier improvement did not extend to log loss. All original metrics and diagnostics
remain in `evidence/round13`; the smaller table here is not a replacement for them.

Eight new classifiers were fitted. Preparation built five missing later-season reference
snapshots with ten regular-season rating components; these are now reusable. This kit
runs zero new rating fits by consuming those verified artifacts.

## What this does not establish

The scored submission remains the previously reported **0.1222672**. **0.1097454** remains
a research target, not a guarantee. The historical 2022–2025 labels have already been
consumed elsewhere in the project. Neither a clean temporal fit nor a passed gate turns
those seasons into an untouched test or independently validates a production model.

The submitted men's winner uses pooled XGBoost and 128 retained inputs, not the 17-input
men-only logistic reference here. The pinned public final-results record says its pooled
stream excludes Massey. Testing whether consensus transfers into that fixed production
recipe remains pending and scientifically valuable.

## Next action requested by the user

The user specifically requested **two new feature rounds**, not one halved experiment.
Both delivered rounds therefore contain four hypotheses, two families, controlled add/drop
comparisons, a duplicate-input diagnostic, ten charts and at most sixteen new classifier
fits. They use the successful 17-input reference unchanged, instead of the weaker
16-input comparison. Both are specified before either new result is seen. Round 15 does
not inherit any winner or threshold change from round 14.

This is not claimed to complete feature engineering or the production-transfer obligation.
Later independent/later-season evidence, production transfer, external player/availability
provenance, and submission generation remain separate, unexecuted work.

Repository source inspected for production context:
https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/reports/final_results/README.md
