# Current retrospective benchmark

This completed run evaluates the exact expanded feature and model artifacts from
notebooks 02 and 03. It contains **16 annual fits**, **536 physical games** and 1,072
prediction rows across 2022–2025. Seeded and seed-free routes score identical games.

| Population and route | Brier | Log loss | ROC AUC | Calibration error (10 bins) |
|---|---:|---:|---:|---:|
| Men, seeded | 0.198288 | 0.579068 | 0.751196 | 0.048059 |
| Men, seed-free | 0.197639 | 0.578065 | 0.754443 | 0.053146 |
| Women, seeded | 0.146881 | 0.438468 | 0.871468 | 0.066548 |
| Women, seed-free | 0.148550 | 0.441682 | 0.870848 | 0.082929 |

Game-weighted and mean-season Brier coincide because each route has 67 games per
season. This includes play-ins and differs from Kaggle's scored population.

The declared men's ranking-logistic and women's logistic families use identity
calibration. Block and penalty are frozen from pre-2022 OOF predictions before
loading benchmark outcomes: rankings/C=0.3 for men; conference/C=0.3 for women. Each
year is fitted on strictly earlier seasons. The seed-free recipe removes all
seed-dependent columns with the same penalty. `recipe.json` and `fit_audits.json`
expose exact features, training cutoffs and fitted dimensions.

**These years were already consumed in prior work.** This is a retrospective
check, not an untouched holdout or a new model-selection opportunity. The previous
124-feature seeded benchmark scored 0.198014 for men and 0.138599 for women. The
revised anchor improves neither score; the women regress materially. This result
is retained without tuning against these outcomes or overwriting the old release.
A strong development conference score did not establish benchmark superiority.

`run.json` binds this evidence to both upstream fingerprints and exact source,
configuration, environment and input checksums. All 33 tasks are checkpointed.
The archive preserves estimators and development forecasts. Notebook 04 independently
recomputes scores from `benchmark_predictions.csv`.

No 2026 labels enter the benchmark, no 2026 estimator is fitted, and no submission
CSV or Kaggle upload is produced. Notebook 04's separate, tested export control stays
default-off for a maintainer who later chooses to generate a file.
