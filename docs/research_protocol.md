# Feature research protocol

This document records the compact notebook 05 protocol. Its first real-data run is complete; verified scores and hashes are in `reports/research`. The next phase rebuilds canonical notebook 02 using the [feature-store contract](feature_store.md). Historical implementations remain in Git history.

## Evidence audit: 2026-09-06

Audit base: `cf005b42910f217a34f87017e6647d1b74f46ab8`.

| Evidence | What the repository establishes |
|---|---|
| Best recorded observed Kaggle score | 0.1281386; temperature refinement performed after results were available |
| Original challenger | 0.1299012 |
| Development-frozen blend | 0.1318165 |
| Original primary | 0.1421117 |
| User recalls approximately 0.121 | Not found in the checked repository records; retain as unverified pending the submission record |
| Existing candidate feature counts | 408–1,070 per candidate set; final selection capped at 120 |
| Original tests | Three reshaping tests passed before changes |
| Source of metric facts | `reports/submission_portfolio/kaggle_scores.csv`, `reports/modeling/03_model_comparison/winner_summary.csv` |

The original men's best development macro-season Brier is 0.180669 and women's is 0.148684, on 2016–2019 and 2021. These are different populations from the single-year Kaggle score. They must not be compared as equivalent metrics.

## Why investigate feature quality

The original feature store already includes Elo variants, opponent-adjusted ratings, efficiency, recent form, ranking summaries, coach/program priors, and many correlated alternatives. Several original matchup formulas, such as `(offense_A - defense_B) - (offense_B - defense_A)`, reduce to linear combinations of team differences. They may help a constrained nonlinear learner, but add no independent linear basis when the component differences already exist.

The new research module explicitly tests cross-team products, such as `offense_A * allowed_B - offense_B * allowed_A`, plus strength normalized by combined margin volatility. They are hypotheses about matchup effects, not established improvements or probability estimates.

| Candidate | Question |
|---|---|
| Seed | How strong is the simple tournament-seed baseline? |
| Strength | Do home-adjusted ridge ratings and schedule strength improve it? |
| Efficiency | Do shooting, turnover, rebounding, free-throw and three-point rates help? |
| Recent | Does time-weighted adjusted strength add information? |
| Matchup | Do genuinely nonlinear cross-team interactions help? |
| Full | Does combining recent form and matchup features retain their benefit? |

Two fixed model recipes (regularized logistic and shallow histogram boosting) run separately for men and women. The default protocol contains 120 fold tasks: 2 genders × 5 seasons × 6 feature sets × 2 model families. This compact challenger does not replace the larger historical system, its tuned XGBoost/LightGBM models, or its production submission routing.

## Temporal boundaries and evaluation

- Development evaluation: 2016, 2017, 2018, 2019, 2021. Train from 2013 through the preceding season, with at least three prior seasons.
- Use only official regular-season games through DayNum 132 for each team's snapshot. NCAA outcomes enter only as labels. All features use the final pre-tournament snapshot, including for later tournament rounds.
- Include play-in games by default, matching the broad historical NCAA-label universe; `include_play_in=false` restricts to DayNum >= 136. The 2026 leaderboard description reported 126 scored games, so never imply identical scoring populations without checking the specific competition stage.
- Fit imputation and scaling inside each training fold. Mirror physical games only after selecting the training fold. Score each validation game once in lower-TeamID orientation and enforce complementary reversed probabilities.
- Existing 2022–2025 locked benchmark results and 2026 outcomes have already been examined. The new runner excludes them and labels all work retrospective development research. They cannot become an untouched holdout again.
- Primary comparison: macro mean season Brier. Also report game-weighted Brier, combined men/women metrics by season, log loss, ROC AUC, average precision, fixed-0.5 precision/recall/F1, reliability bins and ECE.
- Paired ablations resample whole seasons with 4,000 bootstrap draws. Negative deltas favor the added block. Few seasons and multiple comparisons limit the evidence; intervals are diagnostic, not a selection guarantee.
- No automatic promotion, tuning on validation outcomes, or validation-fitted calibrator. Fixed recipes need no hyperparameter search. Future tuning, calibration and ensembles require inner chronological OOF predictions.

## Next research priorities

1. Reproduce this benchmark on the official files, reconcile the recalled 0.121 submission, and compare new and historical forecasts on identical IDs/seasons.
2. Test historical external power ratings, especially women's coverage, with explicit release timestamps and licenses. Current-only ratings cannot be backfilled into historical folds.
3. Test timestamped player availability, minutes concentration, returning production and injuries. Preserve the pre-tournament publication snapshot; later injury knowledge leaks.
4. Add external features to the existing feature store only after paired ablations establish a benefit. Keep genuine interactions that survive regularization and multiple-season checks.
5. Evaluate tuned XGBoost/LightGBM, margin regression and calibrated blends on nested chronological folds. Diagnose correlated errors before adding neural models or extra compute.
6. Freeze the resulting recipe before the next prospective tournament. A post-competition score can support a reproduction study, but cannot earn a new medal in a closed competition.

## Sources

- [Official 2026 competition and Brier evaluation](https://www.kaggle.com/competitions/march-machine-learning-mania-2026)
- [Winning team's repository and published score](https://github.com/harrisonhoran/kaggle-march-mania-2026-1st-place)
- [Second-place solution: efficiency, Elo and ranking features](https://www.kaggle.com/competitions/march-machine-learning-mania-2026/writeups/2nd-place-solution-for-the-march-machine-learning)

The winning score is useful context, not a transferable threshold or evidence that this project would medal. No winner code or external datasets were copied into this repository.
