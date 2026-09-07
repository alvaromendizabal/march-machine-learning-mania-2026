# Notebook 02: feature store and temporal evidence

Notebook 02 reviews a tested, importable feature pipeline. Its current contract
contains **124 candidate matchup features**: 95 basketball/history features,
20 Massey features, and 9 target-history features. Without Massey, 101 candidates
remain eligible. Exact fitted columns depend on training availability and are
recorded per model. Feature count is not evidence of forecasting quality.

## Publication-safe Massey features

`MMasseyOrdinals.csv` contains rankings from multiple systems. It does not contain
all of the underlying efficiency statistics used by those systems. Raw system
names are identifiers, not basketball measurements to target-encode blindly.

For each season and requested cutoff:

1. Filter `RankingDayNum` to the cutoff or earlier, with a 14-day staleness limit.
2. Select each system's latest published edition. A team missing from that
   edition stays missing; an older edition is not mixed into the current one.
3. Normalize each edition separately: `1 - (rank - 1) / max(max_rank - 1, 1)`.
   The denominator comes from that legal edition only, never a future/full-season
   table. This normalization assumes the edition's observed maximum represents
   its ranking universe; changing coverage remains a documented limitation.
4. Aggregate systems with equal weights. No system is selected or weighted using
   the validation labels. A future learned consensus requires inner temporal CV.
5. Calculate changes using only systems shared between both as-of snapshots.

| Family | Candidate features | Interpretation |
|---|---|---|
| Rank level (13) | Median, mean, SD, quartiles, IQR, top-25/top-50 fractions, system count, coverage fraction, mean/max age, clipped consensus logit | Strength, disagreement, coverage and nonlinear strength |
| Rank trends (7) | 7/30/60-day momentum, short-vs-monthly acceleration, monthly change SD, matched-system fraction, dispersion change | Movement and whether movement is broadly shared |
| Rank target history (3) | Smoothed win rate, uncertainty, log support for fixed consensus deciles | Earlier tournaments' performance for that ranking band |

A single system has undefined between-system SD, not zero disagreement. Missing
or stale rankings remain missing. Women do not receive invented Massey values.
Day 132 is the declared Selection Sunday/pre-tournament snapshot; models for
an earlier forecast date would need a different cutoff and seed availability
contract. Historical publication dates are an as-of assumption; the downloaded
file's revision history cannot prove what a vendor published in real time.

## Forward-only target encoding

Every row belonging to season Y uses **only seasons before Y**. This applies to
training rows as well as validation and submission rows. No current-season
NCAA outcomes enter the encoding, including earlier rounds of that tournament.

The eligible history is restricted to seasons represented in the configured
feature store (currently beginning in 2013), and then to the preceding five
calendar seasons. Each physical game contributes one win for its winner and one
loss for its loser, exactly once, separately for each gender. Model mirroring
happens later and cannot double these history counts.

Categories are team ID, numeric tournament seed, and a fixed rank-consensus
decile. Historical observations retain **their own season's** seed and ranking
category. Rankings are never joined from a team's current season onto past
outcomes. Unseeded submission teams have missing seed history; a new team with
no tournament history receives the fixed prior for its team encoding.

For category c, history game g in season s has weight
`w = 0.5 ** ((Y - 1 - s) / 3)`. Let W be weighted wins and N weighted appearances.
We use `alpha = W + 10`, `beta = N - W + 10`, and expose:

- Mean: `alpha / (alpha + beta)`.
- Uncertainty: `sqrt(alpha * beta / ((alpha + beta)^2 * (alpha + beta + 1)))`.
- Support: `log1p(N)`.

The Beta(10,10) prior, three-season half life and five-season window are fixed
research choices, not fitted on the evaluation seasons. The 0.5 prior is justified
by counting both perspectives of every game. Decay gives pseudo-counts, so the
uncertainty feature is a regularization diagnostic, not a calibrated confidence
interval. NCAA survival and roster turnover can make team history misleading;
its value must be established by ablation.

This is an expanding, season-held-out encoding rather than random-fold target
encoding. Scikit-learn's default target-encoder splitting does not enforce this
season boundary. If smoothing, buckets or system weights are tuned later, their
selection belongs inside notebook 03's **inner chronological folds**.

## Remaining basketball features

The 75 non-Massey basketball features retain seed/strength controls, ridge
opponent-adjusted offense and defense, opponent-adjusted Four Factors, residual
form and downside, contextual road/strong-opponent results, Bayesian shooting
means and uncertainty, overtime-adjusted pace, Elo and margin Elo, earlier
program history, and antisymmetric matchup interactions. See
`advanced_features.py` and `feature_registry.csv` for the exact names.

Every model feature changes sign when the teams swap. Imputation and scaling
are fitted inside each model's training fold. Columns wholly absent or zero
throughout its training fold are excluded and recorded, without looking at
validation outcomes. No ID, season, or label is passed as a numerical predictor.

## What actually reaches the model?

`feature_usage.csv` records gender, validation season, block, model, requested
feature, whether it was fitted, training/validation coverage and the standardized
logistic coefficient. `model.joblib` and `fold.json` retain the exact fitted
column order. Tests compare the saved feature list with the estimator's actual
input dimension. Coefficients show conditional association, not causation or
proof of added predictive value. Tree models are assessed with the same family
ablations; an empty coefficient cell does not mean a feature was unused.

`encoding_audit.csv` records each target season's history boundaries, physical
game count, category count, cold starts, missing categories and smoothing
settings. `coverage.csv` and `diagnostics.csv` expose source coverage and missing
values. Notebook 02 displays these audits before the performance plots.

## Measured experiment and limits

All additions and drop-one comparisons use expanding training seasons and the
same 2016–2019/2021 development games. The fixed recipes are logistic regression
and histogram gradient boosting. There are 600 folds without Massey, or 660
when the men's Massey families are available. The official Brier score is
reported both pooled by game and averaged by season; the latter is a diagnostic
for year-to-year robustness, not a substitute for the official aggregation.

Log loss, ROC AUC, average precision, calibration error, reliability diagrams,
and threshold metrics accompany Brier. Paired season bootstrap intervals are
exploratory: five seasons and repeated feature searches do not establish medal
performance. Outcomes from 2022 onward do not tune these experiments. Notebook
03 retains its old feature contract until its explicit model-stage migration.

## Run and resume

Use the fail-fast update sequence in [studio.md](studio.md). Then, in a Bash
subshell that stops on a failed step:

```bash
(
  set -e
  .venv/bin/march-data --output data/kaggle \
    --s3 s3://sagemaker-march-mania-560403859723-us-west-2/data
  .venv/bin/march-features --raw data/kaggle/raw \
    --run-root outputs/feature_store --require-massey \
    --s3 s3://sagemaker-march-mania-560403859723-us-west-2/feature-store
)
```

Normal Kaggle credentials stay inside Studio. If needed, use
`.venv/bin/kaggle auth login` there and rerun the block. Download all official
competition files; `--require-massey` stops before modeling if the file or legal
validation-season ranking coverage is absent.

The feature command chooses `outputs/feature_store/<fingerprint>/`. Repeat it to
reuse SHA-256-verified tasks; changed code/data/configuration/environment creates
another version automatically. `latest.json` points only to a completed run.
An unfinished estimator restarts its fold, while completed folds are reused.
The deliberate `--output` option still supports an exact immutable run directory.

Logs contain UTC timestamps, elapsed time, task timings, progress and a 15-second
heartbeat during long tasks. Source/input hashes and locked versions identify
each run. S3 stores inputs, model/checkpoint artifacts and a completion marker.
The notebook shows the resolved report directory; open `report.html` inside it.
Use [archive.py](../scripts/archive.py) for an independently verifiable run archive.

Official sample IDs retain their original row order in `submission_features.parquet`
when the sample exists. This is a feature artifact, not a completed Kaggle
submission. Final probabilities, calibration and submission validation follow
model selection. The 2026 event is closed; new work is retrospective research.

## References

- [Kaggle competition data](https://www.kaggle.com/competitions/march-machine-learning-mania-2026/data)
- [Scikit-learn target encoding](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html)
- [Scikit-learn temporal cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-of-time-series-data)


## Additional context candidates

The earlier 104 features remain. The 20 additional hypotheses are tested as
three family additions to the strength baseline and as drop-one ablations:

| Family | Definition | Reason to test |
|---|---|---|
| Ball control (10) | Assists/field goals; assists/turnovers; steals/shared possessions; blocks/opponent two-point attempts; fouls/shared possessions; each for the team and its opponents | Passing, pressure, rim protection and foul burden beyond the existing Four Factors |
| Schedule context (6) | Neutral and road scoring margins shrunk by five zero-margin pseudo-games; Beta(2.5,2.5) win rate against top-quartile adjusted-strength opponents; elite-game fraction; games in the last 14 days; reported overtime fraction | Schedule composition, venue robustness and workload |
| Scoring shape (4) | Pythagorean win expectation with fixed exponent 11.5; minimum adjusted offense/defense; absolute offense/defense gap; 10th-percentile scoring margin | Nonlinear strength, balance and downside performance |

These are season summaries at DayNum 132, not pre-game predictions for the
regular-season games used in their construction. The Pythagorean exponent,
priors and thresholds are frozen before evaluation. All resulting matchup
features are team-1 minus team-2 and reverse sign under a swap. Missing extra box
columns or zero denominators remain missing and are recorded by the fitted-input
audit. No player injury, roster, minutes, tracking or betting inputs are invented.

The raw audit identifies a reported-overtime anomaly: the men's 2019 file marks
13 of 5,463 regular games as overtime (0.24%), compared with approximately 6% in
adjacent seasons. This is a source-quality finding, not proof of the true count.
Overtime fraction and overtime-normalized pace therefore carry this limitation;
the new candidates remain exploratory and are not promoted into a final recipe
automatically. The audit's ordinary tables make the discrepancy visible.
