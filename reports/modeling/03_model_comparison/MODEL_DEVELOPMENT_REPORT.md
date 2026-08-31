# Model Development and Comparison Report

## Validation design

- Matched held-out seasons: [2016, 2017, 2018, 2019, 2021]
- Entire tournament seasons are held out.
- Training seasons always precede validation seasons.
- Inner folds select preprocessing, features, parameters, training length, and calibration.
- The 2022–2025 benchmark and 2026 Stage 2 data were not opened.

## Model families

Logistic regression, XGBoost, LightGBM, PyTorch, and TensorFlow were compared in separate and pooled architectures. Point-margin models and constrained ensembles were also evaluated.

## Recommended development selections

### Men's tournament

- Architecture: separate_gender
- Model: Rich elastic-net logistic
- Mean held-out season Brier: 0.186799
- ROC AUC: 0.794481
- Average precision: 0.770103
- F1 at 0.50: 0.707317

### Women's tournament

- Architecture: pooled_common
- Model: Seed logistic
- Mean held-out season Brier: 0.152978
- ROC AUC: 0.858562
- Average precision: 0.853805
- F1 at 0.50: 0.771160

## Interpretation of “winner”

The numerical winner has the lowest mean season-level Brier score. The recommended winner applies the one-standard-error rule and may choose a simpler model when its performance is statistically indistinguishable from the lowest score.

## Feature ablation

Ablation retrains reference models after cumulative feature blocks are added. It measures whether ratings, efficiency, schedule, history, rankings, and matchup interactions improve held-out seasons rather than merely fitting the training sample.

## Next boundary

The replacement notebook `04` may evaluate the frozen recipe on 2022–2025 once. No model or feature decision may be changed after those outcomes are viewed without creating a new explicitly documented experiment.
