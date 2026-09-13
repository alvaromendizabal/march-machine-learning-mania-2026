# Research plan — quality wins and reference-team record

## Evidence received, not a new experiment

Source: `evidence/smoke_metrics.csv` from the user's `milestone_02_return.zip`.

| 2019 recipe | Men Brier | Change | Women Brier | Change |
|---|---:|---:|---:|---:|
| Reference | 0.1732019 | 0 | 0.1462544 | 0 |
| Shooting residuals | 0.1825130 | +0.0093111 | 0.1502530 | +0.0039986 |
| Adjusted shooting profiles | 0.1742004 | +0.0009984 | 0.1464528 | +0.0001984 |
| Both | 0.1836240 | +0.0104221 | 0.1521537 | +0.0058993 |

Each population contains 63 validation games. Eight classifier fits completed. The game-weighted combined reference Brier is 0.1597281670; residual, profile, and combined additions worsen it by +0.0066548158, +0.0005984309, and +0.0081607042 respectively. These are historical diagnostic results, not new Kaggle submissions.

The former `clearly_unproductive_smoke` flag only triggered when **every** challenger worsened by more than 0.01. Its false value is not positive feature evidence. The direction of all six observed comparisons supports pausing automatic expansion, with more deterioration associated with residuals than profiles in this test. Causal reasons are not established by aggregate metrics. The new notebook replays the saved predictions to locate the loss, without fitting again or using individual outcomes for overrides.

**Decision:** do not promote the shooting additions. Preserve the negative evidence. Pause notebook 03. This is a prioritization decision, not proof that all shooting representations are exhausted.

## External research versus our design

### Source 1: direct leading-solution evidence

Harrison Horan's first-place 2026 write-up reports a 0.1097454 Brier score and includes seed differences, a custom efficiency rating, and quality-win differences in its compact representation. Its opponent-quality points reward wins over highly seeded teams; its full definition also distinguishes secondary-tournament participation. This motivates testing the quality-win concept, not assuming it independently caused the winning score.

Source: https://www.kaggle.com/competitions/march-machine-learning-mania-2026/writeups/march-machine-learning-mania-2026-1st-place-solut

### Source 2: NCAA's account of opponent and venue effects

The NCAA distinguishes a results-based team-value component from opponent/location-adjusted net efficiency. It values wins differently according to opponent quality and game location. That supports separating the quality of accomplishments from an average efficiency measure.

Source: https://www.ncaa.org/media-center-how-do-net-rankings-work-in-ncaa-tournament-selection/

### Source 3: NCAA's description of reference-team records

The NCAA describes Wins Above Bubble as a comparison between actual wins and the wins a typical bubble team would be expected to achieve against the same schedule. It is a resume measure, not simply another efficiency rating.

Source: https://www.ncaa.org/championships/march-madness/selections-101/division-i-womens-basketball-championship/

### Existing project context

The reviewed `context_features.py` already has an elite-opponent win posterior, elite-opponent exposure, road/neutral margins and conference context. The new work is not the first attempt at quality-of-opposition features. It tests explicit seed-weighted win accomplishments and a nonlinear reference-team record against a fixed control; the definitions differ from those previously inspected.

Source: https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/src/march_mania/context_features.py

**Our additions below are hypotheses.** They are not NET, official WAB, an exact reproduction of the winner, or proven gains. No external dataset is downloaded. We exclude the secondary-tournament tier because its publication timing is not verified for every historical snapshot. We do not copy a potentially non-temporal validation or calibration scheme from a leaderboard solution.

## Prediction time and data boundaries

The forecast snapshot is after the NCAA field and seed announcement, using regular-season games with `DayNum <= 132`. Seeds are selection information available then, not information available before those regular-season games. Current-season seeds must never be used to claim an earlier pre-game backtest.

All features use regular-season results, already-built pre-tournament strengths, and the announced field. Historical tournament labels are passed separately. Model training is 2013–2017 and evaluation is 2018, main draw only. Saved 2019 predictions are replayed for diagnosis. No 2022–2026 tournament targets enter modeling/evaluation.

Team strengths describe the entire legal pre-tournament season. They may include the regular-season games summarized by the resume; this is not a leave-one-game-out forecast. The definition and its limitation are intentional, not hidden. The reference distribution uses all active teams in the same population/season, never only the eventual tournament field.

## Seven implemented features

For a regular-season game, let `w` be win=1/loss=0, `h` be +1 home, 0 neutral, −1 away, `r_j` the cached opponent strength, and `n` the team's game count.

### Family A — quality wins (3 team features, then Team1 minus Team2)

Define opponent quality points `q=6` for seeds 1–4, `q=4` for other NCAA seeds, and `q=0.25` for opponents outside the NCAA field.

| Feature | Formula | Hypothesis |
|---|---|---|
| `quality_points_won` | sum(w × q) | Repeated wins over strong opponents add information beyond overall win rate. |
| `quality_points_won_nonhome` | sum(w × q × 1[h<=0]) | Away/neutral accomplishments may distinguish teams with similar totals. |
| `quality_bad_losses` | losses to non-field opponents / (n+5) | Costly losses may reveal a different aspect of a resume. |

These are team-season summaries. Missing seeds for individual opponents mean outside the announced field only after the complete field/data hashes have been verified. A missing or invalid entire field is an error. We retain point sums rather than trying several normalizations after seeing validation outcomes.

### Family B — custom reference-team record (4 team features, then differences)

Define `r_ref` as the 75th percentile of the cached strengths of all active teams. Define a heuristic reference expectation:

```text
p_ref = logistic((r_ref − r_j + 3 × h) / 10)
```

`3` home-margin points, `10` logistic scale points, and the 75th percentile are fixed design assumptions. They are **not** estimated from the 2018 tournament, claimed to match a proprietary system, or asserted to be calibrated. A later changed-constant experiment must be separately preregistered and cannot overwrite this evidence.

| Feature | Formula | Hypothesis |
|---|---|---|
| `reference_surplus` | sum(w − p_ref) | Contextualizes actual wins by the difficulty of the schedule. |
| `reference_surplus_nonhome` | sum((w − p_ref) × 1[h<=0]) / (nonhome games+5) | Isolates away/neutral achievement with small-sample shrinkage. |
| `reference_upset_credit` | sum(w × (1−p_ref)^2) / (n+5) | Nonlinear reward for wins difficult for the reference. |
| `reference_bad_loss_cost` | sum((1−w) × p_ref^2) / (n+5) | Nonlinear penalty for losses easy for the reference. |

The squared terms avoid inserting an exactly redundant decomposition of reference surplus as win-credit minus loss-cost. Correlations may still be high; training-only overlap is reported explicitly. This is a record-strength hypothesis, not a new classifier or rating-model contest.

## Controlled experiment

The 16-input anchor and fitting implementation are frozen copies from milestone 02. Model settings are logistic regression C=0.1, no intercept, maximum 2,000 iterations, paired orientations with total physical-game weight 1, and RMS scaling fitted only on training observations. No normalization, feature selection, probability calibration or hyperparameter search uses validation data.

| Recipe | Inputs | Classifier fits (men + women) |
|---|---:|---:|
| Anchor | 16 | 2 |
| Anchor + quality | 19 | 2 |
| Anchor + record | 20 | 2 |
| Anchor + both | 23 | 2 |

Only training-constant columns may be removed. No capacity-based replacement selection is applied. Add-alone and add-to-other effects are both recorded. Classifier re-estimation after changing input sets is necessary; the measured effect is conditional on this fitting recipe, not a causal basketball effect.

The default 2018 smoke has eight new classifier fits and zero new rating fits. Twelve new feature snapshots derive from the already completed 2013–2018 snapshots; the two 2019 snapshots support prior-error replay. No blanket full-bank regeneration or old S3 archive download occurs.

## Decision rules and next bounded rounds

1. **Technical failure:** stop, diagnose the actual exception, preserve valid checkpoints. Do not increase limits or rerun unchanged failures.
2. **All additions worsen Brier:** do not promote. Record the result and inspect whether the intended information was redundant, unsupported or badly represented. A negative result is a methodological conclusion, not proof of universal uselessness.
3. **Tiny apparent gains:** consider inconclusive, especially within one season. Do not adjust feature constants until the planned replication establishes a reason.
4. **Delta <= −0.001 in a population:** candidate for unchanged replication, not promotion. Examine conditional family effects and loss concentration as well.
5. **Replication:** retain the formulas and model settings across other earlier-year folds; report mean-season and game-weighted Brier, worst-fold regression, count of improving seasons, and descriptive season uncertainty. Do not call previously used folds untouched.
6. **Transfer:** only after a stable result, test the surviving representation against a fixed stronger production recipe and the exact submission pathway. The present study is not a reproduction of the 0.1222672 submission.

Feature research remains open. The next distinct research families are: date-aware opponent-adjusted form; ranking levels, gaps, disagreement and coverage; opponent-specific rebounding/turnover mechanisms not already captured; and player availability/roster continuity only with verified historical as-of sources and permission. These are backlog items, not implemented or validated claims in this package.

## Durable artifacts and privacy

Each feature snapshot and classifier fit is atomically saved with content hashes. Inputs, frozen reference code, environment, and upstream evidence are bound into a run fingerprint. Saved predictions are replayed and checked before reuse. The report archive is published only after preservation checks.

Models are JSON coefficients, not executable pickle objects. Source modules shipped under `reference/` are exact frozen copies; AWS repository modules and edited notebooks are never imported. No Git writes, cloud API calls or submissions are implemented. The private per-game diagnosis stays outside the return ZIP.

**No new Kaggle score is claimed.** The submitted score remains 0.1222672 and the historical goal remains 0.1097454. Achieving that target is a research objective, not a guarantee.
