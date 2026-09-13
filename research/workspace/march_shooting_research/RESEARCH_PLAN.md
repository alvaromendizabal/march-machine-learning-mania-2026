# Round 02 — Opponent shooting environment and matchup-specific shot profiles

## Research question

Do schedule-aware shooting residuals and separately opponent-adjusted 2P/3P/shot-mix features improve historical main-draw Brier over an unchanged 16-feature reference?

This is a new feature experiment, not another stand-alone environment audit, not a reproduction of the final submission, and not a claim that the feature space is exhausted. Every recipe uses the same logistic regression settings. The submitted Brier remains **0.1222672**; **0.1097454** is the historical research target. Neither is an output of this experiment.

## What the user's new receipt establishes

The returned `milestone_01_summary.json` records 35 raw tables rechecked unchanged, 13/13 historical input hashes matching, and 15/15 computational files matching the recorded study. It identifies two changed tracked notebooks, with no changed computational files. Its status is still `REVIEW_REQUIRED`. The earlier clean-worktree gate is not relabeled as passed.

Instead, this kit executes only its own standalone modules from a separate directory. It reads raw inputs, checks Git objects, and preserves the two notebooks without importing, restoring, stashing, staging, or deleting them. Any other tracked edit blocks the run. The original notebook edits can be reconciled separately before publication; they do not need to be destroyed to test isolated features.

## Existing representation and the novelty boundary

Reviewed at Git commit `84b8fb36644a6558beded6dad84f5645ea4405d3`:

- `src/march_mania/features.py`: compact strength, schedule strength, box rates and simple cross-team products.
- `src/march_mania/advanced_features.py`: adjusted offense/defense, adjusted Four Factors, 100-attempt shooting posteriors, uncertainty and generic shooting interactions.
- `src/march_mania/candidate_features.py`: broad distribution, opponent-strength-group, venue, trajectory and peer summaries.

Those already implement valuable concepts. Reintroducing raw shooting averages or adjusted efficiency alone would not be novel. This round's new mechanisms are exclusion of repeated head-to-head meetings in opponent-shooting baselines, and opportunity-weighted additive decomposition of **2P accuracy, 3P accuracy and 3PA share separately**, followed by mechanically defined cross-matchup composition. This is novelty relative to the reviewed implementations, not a claim of scientific invention or a complete audit of every historical private artifact.

The final published 0.1222672 submission is a pooled XGBoost men's component with a women's conference-logistic component. This isolated reference is deliberately different and smaller. A positive result here must still transfer to a stronger fixed reference before it changes the production recipe. A negative linear-model result does not prove a family can never help another model.

## Primary-source rationale

1. Ken Pomeroy, *Offense vs. Defense: free throw percentage* (2015): free-throw accuracy is primarily an offensive property; the analysis excludes the focal game when estimating season averages. This motivates a schedule-aware opponent baseline and an explicit exclusion test. This kit strengthens exclusion to all same-opponent meetings, including those meetings' contribution to its league prior.
   Source: https://kenpom.com/blog/offense-vs-defense-free-throw-percentage/
2. Pomeroy, *Offense vs. Defense: Three-point attempts* (2015): shot selection and shooting accuracy differ substantially in predictability. This motivates representing 3PA share separately from 3P accuracy rather than treating every observed shooting rate as equally stable.
   Source: https://kenpom.com/blog/offense-vs-defense-threepoint-attempts/
3. Pomeroy, *Offense vs. Defense: The summary* (2015): offensive/defensive influence differs by statistic, and random variation remains important. These men's-college findings motivate hypotheses; their transfer to women's basketball is tested separately, not assumed.
   Source: https://kenpom.com/blog/offense-vs-defense-the-summary/
4. Pomeroy, *Ratings methodology update* (2016): opponent adjustment, additive offense/defense effects and game-date context are important architectural considerations. Our rate regressions are approximations inspired by the additive idea; they are not KenPom's proprietary system.
   Source: https://kenpom.com/blog/ratings-methodology-update/
5. Harrison Horan, 2026 first-place solution: compact representations, seed differences, custom efficiency, quality wins and player-availability adjustments provide concrete future comparisons. The author's reported score is the user's research target; this is not evidence that any one ingredient caused it.
   Source: https://github.com/harrisonhoran/kaggle-march-mania-2026-1st-place

No external source is downloaded by the notebooks. No injury, roster, market, or post-tournament information is introduced by this round.

## Fixed reference — 16 features

Six compact-control differences: seed, ridge-adjusted scoring strength, mean opponent strength, win rate, mean margin and margin standard deviation. Two existing-concept efficiency differences: additive adjusted offense and defense using shared possessions and the existing possession-quality threshold. Six standard 100-attempt shooting posterior differences: own/opponent 2P%, 3P%, FT%. Two 3PA-share differences: own and allowed.

All are Team A minus Team B. The reference uses the project's published concepts/formulas but is not an exact re-fit of an archived submission or historical 1,050-fit study. It includes shooting information specifically so a new feature cannot claim credit just for introducing an already-known shooting concept into a seed-only baseline.

## Family R — 6 new features

For defense i and opponent j, estimate j's three-point/free-throw shooting from its other pre-cutoff games. Exclude **every game against i**, not just the current game. Also remove those physical meetings, on both orientations, from the contemporaneous league prior.

`p(j excluding i) = (makes_elsewhere + 100 * league_prior_excluding_meetings) / (attempts_elsewhere + 100)`

For each defense, aggregate `actual opponent makes - opponent attempts * p(j excluding i)`. Express the residual points per 100 possessions, with five mean-game possession exposures of shrinkage toward zero. Compute season and 30-day-half-life versions. Also retain the attempts-weighted expected opponent accuracy for each shot type.

This yields six team differences:

- season and recency-weighted 3P residual points / 100 possessions;
- season and recency-weighted FT residual points / 100 possessions;
- opponent 3P shooting schedule and opponent FT shooting schedule.

Positive residual means more points were allowed than the excluded-opponent baseline expected. It is **not identified causal luck**: player mix, shot location, defensive influence and model misspecification remain unobserved. The feature is offered to the fixed predictor, not used to hand-adjust a team's win probability.

## Family P — 8 new features

Fit three small, season-local weighted ridge regressions to regular-season rates:

`rate(i against j) = intercept + offense_i + allowance_j + home_effect * home_indicator + error`

Targets: two-point accuracy, three-point accuracy, three-point attempt share. Observation weights are target opportunities divided by their mean. Ridge alpha is fixed at 20, with no tournament-based search. This yields six offensive/allowance differences.

Compose neutral-site matchup rates from the intercept and paired effects, bounded to [0.01, 0.99]. Add two antisymmetric matchup features:

- expected eFG difference from separately composed shot share, 2P accuracy and 3P accuracy;
- strength difference scaled by a shot-mix variance proxy derived from outcomes {0, 2, 3} per field-goal attempt.

The variance proxy is not a full game-score variance model and does not include possession count, turnovers, free throws or within-game dependence. No claim of true shot quality is possible from these box scores.

## Four fixed recipes

| Recipe | Input count | Purpose |
|---|---:|---|
| anchor | 16 | unchanged existing-concept reference |
| anchor_residual | 22 | reference + Family R |
| anchor_profile | 24 | reference + Family P |
| anchor_both | 30 | reference + both families |

Training-only support/constant checks are the only feature screen. There is no 128-column cap and no replacement of one family with unrelated candidates. Drop-one comparisons are therefore controlled for input-set composition. Coefficients are refitted normally, so results remain conditional predictive contributions, not causal effects.

## Temporal and evaluation contracts

Snapshots use each season's regular-season games through day 132 and the seeds known at bracket release. Features may summarize all games before the tournament; they are not claimed to have been available before each historical regular-season game. The feature builder cannot accept NCAA target labels.

Tournament labels are constructed separately. Models train on seasons strictly before the validation year. Both populations are fitted separately. The model is logistic regression C=0.1, no intercept, fixed solver/limits, and mirrored training orientations with half-weight per orientation so a physical game retains total weight one. Scaling is fitted only on mirrored training rows. Validation contains each physical game once. Complementarity under a team swap is tested for both features and predictions.

Only main-draw games (`DayNum >= 136`) are evaluated. This excludes First Four games and differs from older project reports that included them. Brier is `mean((probability - outcome)**2)`, without a multiclass scaling convention. Mean-season and game-weighted summaries are saved separately; combined gender scores use physical-game weighting.

**Historical seasons here have already been used by the project. They are exploratory development evidence, not untouched test data. No 2022–2026 targets are eligible, and there is no 2026 scoring, tuning or submission path.**

## Bounded milestones

**Notebook 02 now:** build 2013–2019 snapshots for both populations (14 snapshots; five small regular-season rating regressions per snapshot) and validate 2019 with four fixed tournament classifiers per population (eight classifier fits). It reuses verified snapshots and fit checkpoints on reruns. Stop after reviewing the results and return ZIP.

**Notebook 03 next:** after reviewing the smoke result, expand unchanged recipes to 2016, 2017, 2018, 2019 and 2021. The 2019 fits are reused: 40 total classifier fits, at most 32 new. Only the two 2021 team snapshots are new. The panel is a separate, deliberate action and is disabled in its notebook by default.

Preparation and evaluation each have a 600-second hard cap, report rendering 120 seconds, two compute threads, and 15-second heartbeats. These are stop limits, not runtime forecasts or permission to raise them. The 600-second cap is per stage, not per fit. No GPUs, remote jobs, hyperparameter sweeps, archive downloads, Git writes or AWS changes occur.

If every challenger worsens 2019 Brier by more than 0.01 in both populations, panel execution stops for design review. This is a compute-saving heuristic, not proof of no feature value. Do not reject or promote individual features solely because of a single season.

## Evidence gates

The five-season panel records standalone additions and conditional removals. Its predeclared practical screen is mean-season Brier change <= -0.001, improvement in at least 3 of 5 seasons, and worst-season degradation <= +0.01, per population. These thresholds are fixed before this specific run, not an externally registered study or a statistical significance claim. Season-cluster bootstrap intervals are descriptive; five reused seasons and multiple comparisons limit certainty.

Passing the screen makes a family eligible for a stronger-model transfer test, not automatic production retention. Failure means inspect support, residual assumptions and fold instability before revising the hypothesis. Do not keep increasing feature count or C merely because the first result is disappointing.

## Subsequent feature investigations — not yet implemented or declared exhausted

1. Date-aware efficiency and robust schedule strength: compare season-average baselines to contemporaneous scoring environments and WIN50-style schedule summaries. Existing adjusted ratings are a control, not a novelty claim.
2. Tournament-caliber performance and seeding residuals: formalize quality wins and under/over-seeding signals against opponent strength, accounting for opportunities and shrinkage. Audit overlap with existing upper-quartile opponent features first.
3. Team evolution and instability: isolate opponent-adjusted trends and recent role changes rather than duplicating generic rolling means. Compare recency and stationary versions on identical folds.
4. Ratings-system coverage and disagreement: use the existing Massey research as the control; investigate missing support, nonlinear consensus and residual information only when definitions are genuinely different.
5. Roster continuity, experience and availability: require documented rules permission, archived as-of snapshots and reproducible team/player joins. Current injuries or current rosters cannot be substituted into historical backtests.
6. Schedule graph, style exposure and common-opponent context: test incremental information after strength and shot-profile controls; assess disconnected or weakly connected schedule components.

Every later round requires its own rationale, novelty/overlap review, availability contract, test, bounded comparison, ablation and season-stability assessment. This list is a living research backlog, not evidence that those avenues have been exhausted.

## Publication

The kit is outside the Git repository and creates no Git commits or pushes. Its notebooks start unexecuted for the user's real run. Test fixtures are synthetic and never supply real performance claims. Keep `private_runs`, model JSONs, raw data and edited-notebook backups private. Integrate tested canonical source, selected executed notebooks and reviewed public summaries through a focused branch only after the experiment is reviewed; do not `git add .` over the workspace.
