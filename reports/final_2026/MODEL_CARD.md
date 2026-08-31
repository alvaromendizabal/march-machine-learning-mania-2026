# NCAA Tournament Forecasting Model Card

## Purpose

Forecast every possible 2026 men's and women's tournament matchup as the probability that the lower-TeamID team wins.

## Information boundary

- Team features are frozen at or before Selection Sunday (DayNum 132).
- Tournament seasons are held out as indivisible evaluation groups.
- Model development ended in 2021.
- The locked 2022–2025 benchmark was consumed once under blueprint `fe018aa50049709a74f9fdcc43d8bbdc7c6510d0091f47a57ecc2467e6c888d7`.
- Benchmark outcomes did not reopen feature engineering, hyperparameter selection, calibration-method selection, or model-family selection.

## Development comparison

Notebook 03 compared logistic regression, histogram boosting, XGBoost, LightGBM, PyTorch, TensorFlow, point-margin models, pooled models, separate models, constrained ensembles, and partial pooling under matched nested expanding-window validation.

### Development selections

- Men's primary: separate_gender / Rich elastic-net logistic
- Men's challenger: pooled_common / Histogram boosting
- Women's primary: pooled_common / Seed logistic
- Women's challenger: pooled_common / XGBoost classifier
- Development blend weights: {'M': 0.17, 'W': 0.37}

### Neural-model development audit

| Gender   | Architecture    | Model          | ModelDisplay   |   MacroSeasonBrier |   GameWeightedBrier |   ROCAUC |   AveragePrecision |    AUCPR |   Precision |   Recall |       F1 |   CalibrationSlope |       ECE |
|:---------|:----------------|:---------------|:---------------|-------------------:|--------------------:|---------:|-------------------:|---------:|------------:|---------:|---------:|-------------------:|----------:|
| M        | separate_gender | torch_mlp      | PyTorch MLP    |           0.191687 |            0.191573 | 0.781746 |           0.742532 | 0.740958 |    0.651429 | 0.74026  | 0.693009 |           0.833712 | 0.0589802 |
| M        | pooled_common   | tensorflow_mlp | TensorFlow MLP |           0.192525 |            0.192445 | 0.775613 |           0.752112 | 0.75092  |    0.633721 | 0.707792 | 0.668712 |           0.87902  | 0.0617636 |
| M        | separate_gender | tensorflow_mlp | TensorFlow MLP |           0.193766 |            0.193633 | 0.777633 |           0.745992 | 0.744763 |    0.639344 | 0.75974  | 0.694362 |           0.828178 | 0.0762264 |
| M        | pooled_common   | torch_mlp      | PyTorch MLP    |           0.196165 |            0.196025 | 0.768975 |           0.747767 | 0.746595 |    0.615385 | 0.727273 | 0.666667 |           0.778591 | 0.0763115 |
| W        | separate_gender | tensorflow_mlp | TensorFlow MLP |           0.156218 |            0.156218 | 0.859147 |           0.848255 | 0.847599 |    0.759259 | 0.783439 | 0.77116  |           0.728836 | 0.050587  |
| W        | pooled_common   | tensorflow_mlp | TensorFlow MLP |           0.160189 |            0.160189 | 0.851891 |           0.8496   | 0.84895  |    0.732919 | 0.751592 | 0.742138 |           0.772397 | 0.0713541 |
| W        | separate_gender | torch_mlp      | PyTorch MLP    |           0.161518 |            0.161518 | 0.850318 |           0.826685 | 0.825583 |    0.75     | 0.802548 | 0.775385 |           0.584242 | 0.0711151 |
| W        | pooled_common   | torch_mlp      | PyTorch MLP    |           0.161834 |            0.161834 | 0.85048  |           0.844068 | 0.843327 |    0.736527 | 0.783439 | 0.759259 |           0.699852 | 0.0722855 |

The neural systems were evaluated as bounded tabular MLP challengers. They were not promoted because their matched held-out-season Brier scores did not beat the frozen primary or performance-challenger streams.

## Locked benchmark

| Gender   | Role              | Architecture     | ModelDisplay              |   MacroSeasonBrier |   GameWeightedBrier |   ROCAUC |   AveragePrecision |    AUCPR |   Precision |   Recall |       F1 |   CalibrationSlope |       ECE |
|:---------|:------------------|:-----------------|:--------------------------|-------------------:|--------------------:|---------:|-------------------:|---------:|------------:|---------:|---------:|-------------------:|----------:|
| M        | primary           | separate_gender  | Rich elastic-net logistic |           0.193297 |            0.193297 | 0.761677 |           0.792653 | 0.791388 |    0.73125  | 0.75974  | 0.745223 |           0.867049 | 0.0858222 |
| M        | development_blend | prediction_blend | Development-frozen blend  |           0.198565 |            0.198565 | 0.750114 |           0.785043 | 0.783848 |    0.707317 | 0.753247 | 0.72956  |           0.749573 | 0.0714114 |
| M        | challenger        | pooled_common    | Histogram boosting        |           0.201104 |            0.201104 | 0.745557 |           0.781603 | 0.780251 |    0.709877 | 0.746753 | 0.727848 |           0.69972  | 0.0770342 |
| W        | challenger        | pooled_common    | XGBoost classifier        |           0.142382 |            0.142382 | 0.881902 |           0.85424  | 0.853226 |    0.769231 | 0.756303 | 0.762712 |           1.38216  | 0.0457626 |
| W        | development_blend | prediction_blend | Development-frozen blend  |           0.14359  |            0.14359  | 0.883143 |           0.853936 | 0.852976 |    0.780702 | 0.747899 | 0.763948 |           1.58181  | 0.0665352 |
| W        | primary           | pooled_common    | Seed logistic             |           0.152802 |            0.152802 | 0.866336 |           0.834296 | 0.836571 |    0.754386 | 0.722689 | 0.738197 |           1.61033  | 0.0926958 |

## Final production routes

- Seed-aware rows use the development-frozen primary and challenger streams for the appropriate tournament.
- Seed-free hypothetical rows use a gender-specific elastic-net fallback.
- The default submission is the primary stream.
- Challenger and development-blend submissions are retained as transparent sensitivity products.

## Probability controls

- Algebraic matchup reversal is averaged at prediction time.
- Calibration methods are selected from development-only OOF predictions.
- Probability shrinkage and clipping are selected before the benchmark.
- Final calibration parameters are refit using out-of-sample predictions through 2025 without changing the calibration family.

## Limitations

- Tournament outcomes are sparse and season-to-season variance is material.
- Player injuries, roster continuity, betting-market information, and proprietary team ratings are not guaranteed to be present.
- Women's detailed box-score history begins later than men's and has documented early coverage gaps.
- Threshold metrics such as precision, recall, and F1 are secondary; the target is a calibrated probability and Brier score is primary.

## Reproducibility

- Recipe SHA-256: `92a52d4e16ca29b847ba14a37032417713256c7101388f63ca263203adeb12ac`
- Blueprint SHA-256: `fe018aa50049709a74f9fdcc43d8bbdc7c6510d0091f47a57ecc2467e6c888d7`
- Historical feature store SHA-256: `93dc3472ee3d47eb64604dddcdde884d8392adc415c4e5f314ee1f6ad4a36711`
- Stage 2 feature store SHA-256: `d4710a2d24c818a92418b21c8e4403a325e63fcdcf8b82aa86dcc22ba2281452`
- Primary submission SHA-256: `f19d0fa1c2e5f6f9ad80a346dffa40adeda6a95d45c5f5696ac92acaa0012e5e`
