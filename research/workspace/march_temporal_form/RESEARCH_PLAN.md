# Investigation 06 — Frozen-early-rating temporal form

## Observed evidence, not a new hypothesis claim

The attached milestone 05 report found that the unchanged women's record family improved only one of three additional seasons. Their mean delta was +0.00023875434741482682, with worst deterioration +0.0013377036159965827. Five new classifiers and three baseline replays produced this conclusion; no rating models were refitted. The gated 16 drop-one fits were skipped. Including the discovery season makes the four-season mean slightly negative, −0.00017378085127799092, but that is not evidence of replication because the 2018 observation selected the family.

**Decision:** preserve the finding, do not promote or expand the record representation as implemented, and investigate a different mechanism. This does not prove every schedule-strength representation or every classifier would fail.

Source: exact `summary.json`, `gate.json`, and `replication_metrics.csv` extracted from the user's `milestone_05_return.zip`, included under `evidence/`.

## Hypothesis and domain rationale

A team may enter the tournament with a different offensive or defensive level from the one represented by its full-season average. Later raw margins are difficult to interpret without pace, opponent strength, and game location. At the same time, ratings fitted to the whole season partly absorb the very later games whose residuals are being used to measure recent change.

**Hypothesis:** compact, opponent/site-adjusted later-game surprises measured against a genuinely earlier frozen model add information beyond the unchanged full-season reference. Separating offensive from defensive change may be more useful than adding another aggregate win rate.

This is a new temporal representation in this local research sequence, not a claim to invent time-aware basketball ratings. The published project already contains recent efficiency, residual and trajectory features. In `advanced_features.efficiency_ratings`, the earlier residual uses an adjustment fitted on the same selected season's games; the recency-weighted rating also uses those games with different weights. That is not automatically tournament leakage—all were pre-tournament. The new difference here is that the expectation model is fitted only through day 100, while its diagnostic residual observations start strictly afterward.

### Primary-source context

1. Ken Pomeroy, *Ratings Glossary* (2012): adjusted offense and defense are neutral-opponent efficiency concepts expressed per 100 possessions. Used here to motivate separate offense/defense and pace-normalized measurement, not to claim KenPom's exact methodology is reproduced. https://kenpom.com/blog/ratings-glossary/
2. Ken Pomeroy, *Ratings methodology update* (2016): additive adjusted efficiency margin makes differences easier to interpret; his methodology discussion distinguishes opponent effects and team strength. This motivates the simple additive expectation model. https://kenpom.com/blog/ratings-methodology-update/
3. Ken Pomeroy, *Ratings Explanation* (2006, with later notices): historical discussion of predictive team strength and giving recent games additional weight. This is historical methodological context, not a statement that every detail remains current. https://kenpom.com/blog/ratings-explanation/
4. scikit-learn, *Common pitfalls and recommended practices*: preprocessing must be learned on training data, not validation observations. The same existing training-only RMS procedure and classifier are reused. https://scikit-learn.org/stable/common_pitfalls.html
5. Project implementation at the archived commit, `src/march_mania/advanced_features.py`: comparison against the existing season-local residual and recency features. https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/src/march_mania/advanced_features.py

These references support investigating the mechanisms. **None establishes that our four new formulas will improve Brier.** No external data is scraped or imported by this milestone.

## Exact information boundary

For each population and season independently:

- Reuse the original day-132 base snapshot for the 16 fixed reference inputs.
- Fit an additional early expectation model on official regular-season detailed games with `DayNum <= 100` only.
- Construct residuals on official regular-season detailed games with `100 < DayNum <= 132`.
- The feature module never accepts tournament results as an input. Tournament outcomes are joined later as labels, with training seasons strictly before the validation year.
- Existing seeds in the anchor assume predictions made after bracket announcement; this is not a forecast made before selection.
- No 2020 or 2022–2026 tournament targets enter this experiment. The raw snapshot can contain them, but label extraction is restricted to 2013–2019.
- Team pairs are ordered by ID for label orientation and every feature reverses sign on swapping the teams. Mirrored training observations each receive weight 0.5; the two orientations are not counted as independent physical games.

## Early ratings

Possessions use the established box-score estimate for each team:

`FGA - OR + TO + 0.475 * FTA`

Average the two estimates. As in the existing reference, exclude observations whose two estimates disagree by more than 10% of the average. Both orientations of a physical game use the same quality criterion.

For points per 100 possessions fit:

`observed_efficiency = intercept + offense[team] + allowance[opponent] + home_effect * home_sign + residual`

The sparse additive ridge model has fixed alpha 20, intercept enabled, LSQR solver and tolerance 1e-8. It uses only early games. All coefficients, including the venue effect and league intercept, remain frozen when scoring the late games. No early-game tournament labels, feature selection, calibration, or hyperparameter search is involved.

For a later team-game:

`offensive_surprise = actual_points_per_100 - frozen_expected_points_per_100`

`defensive_surprise = frozen_expected_opponent_points_per_100 - actual_opponent_points_per_100`

Positive defensive surprise means better defense than the early expectation. Offense/defense estimates for teams not represented in early clean games are not invented; those matchups are excluded from residual aggregation and counted.

## Four matchup features

Each is the corresponding team-A value minus team-B value.

### Family A: later residual level

**`diff_late_offense_surprise`** and **`diff_late_defense_surprise`** use:

`sum(weight * residual) / (sum(weight) + 5)`

where `weight = 0.5 ** ((132 - DayNum) / 14)` on days 101–132. The five-game zero-centered prior is fixed before evaluating outcomes. It reduces the magnitude of thin or stale evidence. It is a heuristic shrinkage choice, not a fitted Bayesian prior.

### Family B: later residual change

**`diff_late_offense_change`** and **`diff_late_defense_change`** use:

`sum(residual in days 117–132) / (n_later + 5) - sum(residual in days 101–116) / (n_earlier + 5)`

This measures a change in surprise relative to the same frozen expectation, separately for offense/defense. Both window means are shrunk independently. Support differences can affect the resulting contrast; the notebook explicitly reports them. No observation in a window gives its declared zero-centered prior, not an assertion of observed average play.

The constants 100/116/132, 14 days, alpha 20 and five pseudo-games are predeclared design choices. They were not selected by testing these new feature results.

## Why not call this momentum or a leakage repair?

Frozen earlier expectations can become stale. A later residual could reflect the opponent changing, small-sample shooting variation, coaching/personnel changes, weaker connectivity in the early schedule, or model misspecification rather than a genuine change in the team's underlying strength. No causal attribution or injury inference is made.

The existing season-end residual was not necessarily leaked: all its games were available before the tournament. This is a contrast between representations and temporal information, not an unsupported accusation that earlier features used tournament outcomes.

## Controlled experiment

Evaluate 2017 and 2019 for men and women. The tournament training years are 2013 through the prior year. Both validation seasons have already been used in this project; label this exploratory historical work.

Four fixed configurations: reference (16), reference plus level (18), reference plus change (18), reference plus both (20). Fixed logistic C=0.1, no intercept, LBFGS, max_iter=2000, tolerance=1e-7, random seed 20260911, two threads. Reuse the existing code for training-only RMS scaling and JSON model serialization. Constant columns may be excluded using training data only. No broad marginal screening, capacity competition, temperature tuning, or ensemble.

Three existing baseline models are replayed: W2017, W2019 and M2019. Verify their IDs, labels, split, scaling, probabilities and Brier. Fit M2017 reference and twelve challengers: **13 new tournament fits**. Existing full-season rating snapshots are read-only. The new early expectations require **14 regular-season fits**, separately checkpointed, one for each of seven seasons in each population.

## Evidence and stopping rules

Report official Brier calculation on the actual selected historical games, not the 2026 competition rows. Also report log loss, season deltas, feature/probability swap errors, training-only overlap, coefficients, conditional family additions, coverage and sparse calibration.

A population/recipe qualifies only for *considering* unchanged wider replication if both test years improve and mean Brier delta is at most −0.0005. This is a heuristic compute-allocation rule, not a p-value or feature promotion. No larger run launches automatically. Do not change the thresholds after results arrive.

Keep negative findings. Do not combine the failed shooting and record features into this test. A positive result still needs broader season stability, component tests where justified, and transfer into a fixed stronger production recipe. The current compact logistic reference is not the final submitted XGBoost/conference-logistic combination. This experiment cannot establish which fraction of the leaderboard gap is due to features versus modeling or selection.

## Execution and preservation

Three supervised stages with hard ceilings: prepare 300s; evaluate 240s; report 120s. Heartbeats every 15s, single-run advisory lock, process-group termination, and content-verified per-rating, per-feature-snapshot and per-classifier checkpoints. Missing/changed upstream artifacts cause a stop; there is no automatic multi-gigabyte recovery or full rebuild.

The raw data, source checkout, index representation, existing two edited notebooks and upstream cache files used by the run are checked and preserved. Only the new companion directory is written. The return archive excludes raw game rows, model JSON and game-level predictions. GitHub and AWS APIs are not called.

## Subsequent research backlog, not launched here

The current result does not exhaust basketball features. Plausible later directions include temporally valid ranking-system disagreement (especially the men's route), opponent-specific turnover/rebounding mechanisms rather than generic products, robust schedule-connectivity and shrinkage variants, and historically timestamped roster/availability data when rules and access permit. Existing feature families must be compared by actual definitions and final-model usage before duplication. No new broad sweep is justified merely by generating more columns.
