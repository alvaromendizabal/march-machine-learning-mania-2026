# Research protocol — women's schedule-record signal

## Measured basis, not a promised score

Source: the user-supplied `milestone_04_return.zip` and its exact `metrics.csv`, `ablations.csv`, `summary.json` and `manifest.json`, copied unchanged into `evidence/`.

Women, 2018, 63 main-draw games: fixed reference Brier 0.15365012520859095; reference plus the four record features 0.15223873876123450; delta −0.0014113864473564441. Adding quality-win features to that record recipe gives 0.15259847166393523: +0.00035973290270072122 worse than record alone. The men's record-alone delta was −0.00005249896226278139, close to zero. These exploratory results justify targeted replication, not promotion or broad retraining.

The existing submitted result 0.1222672 and target 0.1097454 are context only. The local 2018 comparisons concern different games from the 2026 leaderboard. Their deltas cannot be subtracted from the submitted score. No new leaderboard result is available.

## Current hypothesis

For women's NCAA tournament forecasts, schedule-adjusted regular-season achievement adds information to the frozen 16-input reference beyond seed, scoring strength, schedule mean strength and basic shooting summaries.

The mechanism is plausible because results against a schedule and opponent-adjusted efficiency describe different aspects of achievement and ability. NCAA's own selection-criteria explanation separates results-based metrics, including expected wins against a schedule, from other ratings. This supports the concept, not these particular heuristic constants or a prediction-quality claim.

Primary domain source, checked for this milestone:

- NCAA, *Explaining NCAA Tournament Selection Criteria*: https://www.ncaa.org/breaking-down-the-ncaa-division-i-mens-and-womens-basketball-committees-selection-criteria/

Primary methodological sources:

- scikit-learn, *Common pitfalls — data leakage*: https://scikit-learn.org/1.5/common_pitfalls.html
- scikit-learn, *Cross-validation: evaluating estimator performance*: https://scikit-learn.org/stable/modules/cross_validation.html

## Frozen representation

For regular-season game g, team i, and opponent j, let s_j be the cached pre-tournament strength, q be the 75th percentile of that season's active-team strengths, and h_g ∈ {−1,0,+1} encode away, neutral and home. The unchanged reference expectation is:

`p_ref(g) = sigmoid((q − s_j + 3 h_g) / 10)`.

Let y_g be the actual regular-season win indicator. This is not a calibrated forecast or an official NCAA bubble-team baseline. It uses the complete legal regular season and is descriptive at the pre-tournament snapshot, not a pregame backtest of each regular-season matchup.

| Team statistic | Exact unchanged definition |
|---|---|
| `reference_surplus` | sum(y_g − p_ref(g)) |
| `reference_surplus_nonhome` | sum((y_g − p_ref(g)) for away/neutral games) / (nonhome games + 5) |
| `reference_upset_credit` | sum(y_g × (1 − p_ref(g))²) / (games + 5) |
| `reference_bad_loss_cost` | sum((1 − y_g) × p_ref(g)²) / (games + 5) |

Each matchup input is the corresponding team-1 statistic minus team-2 statistic. No new feature definitions, normalizations, thresholds or heuristics are introduced in milestone 05. The source is copied byte-for-byte from the completed study and checked against its manifest.

Quality-win features and the unsuccessful shooting additions are excluded from every new recipe. The original baseline's basic shooting controls remain unchanged.

## Availability and leakage contract

Regular-season rows are restricted to the relevant season and day ≤132. Cached seed-based baseline features refer to predictions after the announced field. No same-season NCAA outcomes enter feature construction. Each tournament classifier uses years 2013 through validation-year-minus-one. Main draw only; no First Four. No 2020–2026 targets are used.

DataFrames for features do not accept tournament labels. Reference RMS scaling and constant checks fit only on training rows. Physical games are mirrored; each orientation receives half weight so each game's total weight is one. Complementary probabilities and feature sign reversal are tested.

Current-season relative strengths in descriptive regular-season features are not a claim that those strengths were available before each regular-season game. Do not relabel this as a chronological regular-season prediction system.

## Why a replication round rather than more new columns

The supplied report finally identifies a specific measured improvement in the current two-family study. Changing formulas now would make a repeated gain or loss harder to interpret. The next scientific question is whether this representation carries across seasons and which components are responsible. This is still feature engineering and feature validation; it is not a move to model search, ensembling, or a declaration that other realistic features have been exhausted.

Women-only focus avoids spending on a direction that barely affected men in the observed test. It does not establish permanent gender-specific causality or exhaust the men's avenue.

## Stage A — five new fits

Women only; compare the frozen baseline (16 inputs) and baseline+record (20 inputs). Fit logistic C=0.1 with all other controls unchanged. New years: 2016, 2017, 2019. The existing 2018 baseline+record fits and 2019 baseline fit are verified and replayed rather than trained again.

Total comparisons: eight. New classifiers: five. Base rating snapshots reused: seven. Prior schedule snapshots reused: six. New schedule snapshots: one for 2019 with identical formulas. New rating fits: zero.

2018 is discovery/selection, not replication. 2016, 2017 and 2019 have been used elsewhere in the project; they are additional exploratory checks, not fresh holdouts. 2019 legitimately includes 2018 in its training history. Training sets overlap, and teams recur; no independence assertion is made.

## Compute gate

Across the three additional seasons only, run component ablations when mean delta ≤−0.0005, at least two seasons improve, and worst delta ≤+0.003. Thresholds are fixed before these comparisons are run. They are a pragmatic spending gate, not proof of a reliable effect or an automatic feature-selection criterion.

Failure pauses expansion of this exact bundle. It does not prove that all schedule-based features are useless. Preserve even a negative result.

## Stage B — at most 16 new fits, only after the gate

Remove exactly one record feature at a time while keeping all 16 reference columns and the other three record columns unchanged. Repeat across 2016–2019: four variants × four seasons. Do not re-screen replacements into the model.

Report `Brier(drop feature) − Brier(full record family)`: positive suggests the feature helps conditionally under this recipe; negative suggests removing it helped. Correlated inputs may have shared or substitutable information, so neither coefficient magnitude nor a drop-one effect proves causation. All ablations are exploratory. No automatic winning subset, parameter tuning, promotion or submission.

Record per-season changes, mean changes excluding 2018, training-only redundancy and coefficient signs. Report the 2018 observation separately. A leave-one-season-out sensitivity table is descriptive; four consumed seasons with overlapping training sets do not justify a reliable population confidence interval. Do not manufacture narrow game-i.i.d. confidence intervals from repeated teams.

## Decision after the report

A repeated complete-family gain plus consistent component effects would justify freezing a representation for a bounded transfer test against the stronger, fixed women's production recipe. It would not establish that the combined 2026 submission improves or that the target score is surpassed. Calibration/modeling contributions remain separate questions; current evidence does not identify the whole leaderboard gap as a feature problem.

If the gain fails to replicate, inspect fixed-model errors, redundancy and support before proposing a change. Do not tune repeatedly to the same seasons. Possible later domain investigations include opponent-adjusted time trends, rebounding/turnover matchup mechanisms, ranking disagreement where actually available, and pre-tournament roster/availability evidence with reliable historical timestamps and permitted access. They are a research backlog, not tested or implemented gains from this notebook.

## Reproducibility and restrictions

Read-only repository, raw data and upstream caches. Known notebook edits remain preserved and unexecuted. Strict recorded environment/source/data comparisons stop on mismatches rather than silently refitting. One supervisor lock, 15-second heartbeats, stage ceilings, atomic checkpoint receipts, and model/prediction replay checks. JSON coefficients are data; no untrusted pickle loading. The return ZIP excludes raw rows, model artifacts and per-game predictions.

No AWS resource changes, paid-job submissions, network downloads, Git commits or pushes occur in these scripts. Passing local synthetic tests is not evidence of predictive performance on the real data.
