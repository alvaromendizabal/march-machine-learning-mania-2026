# research-grade Feature Store Protocol

## Boundaries

- Split contract: `84d6ab4fc44e59286e1a8bad08df1b89d5881c7be88055c716665d0c29e1937b`
- Feature contract: `4827ee3f980360d679466b754a283164cf55d32f3839aaf669baf3364f96aa21`
- Target season: 2026
- Feature cutoff: DayNum 132
- Same-season NCAA outcomes are prohibited from team features.
- Program, coach, and seed priors use tournament outcomes from strictly earlier seasons only.

## Stores

- `data/processed/team_feature_store_v1.parquet`
- `data/processed/historical_matchup_feature_store_v1.parquet`
- `data/processed/stage2_matchup_feature_store_v1.parquet`

## Architecture support

- Men's separate model: common + men's-only features
- Women's separate model: common features without fake Massey values
- Pooled challenger: common features + explicit gender context
- Partial pooling: prediction-level blend selected from nested OOF only
- Seed-aware and seed-free routes have distinct candidate manifests

## Feature governance

- No feature is selected in notebook 02.
- Imputation, scaling, feature selection, hyperparameter tuning, calibration, and blending
  must be fit inside inner-training folds in notebook 03.
- Locked 2022–2025 outcomes cannot influence the recipe.
- Full, clean-possession, robust, recent, and EWM variants remain separate candidates.
- Correlation and drift findings are diagnostics, not automatic deletion rules.

## Next stage

Notebook 03 must generate nested out-of-fold predictions for the complete model ladder:
constant, seed logistic, corrected Elo+seed logistic, elastic-net logistic, XGBoost,
LightGBM, direct classification, point-margin regression, calibrated models, and
constrained gender-specific/pooled ensembles.
