# Round 15 — common-opponent, venue-matched comparisons

**Four candidates, two families, sixteen new classifier fits maximum, ten Plotly charts.**
This is a complete independent investigation, not an optional subset of round 14. It
retains the same frozen 17-input reference and does not carry forward ranking-transform
features, coefficients, validation choices or a selected arm from the first round.

## Rationale and novelty boundary

Average team statistics can conceal how two teams performed against the same opposition.
Compare their performance against a common third opponent in the same venue category,
then retain the residual matchup-specific contrast as an explicit feature. This differs
from adding an overall opponent-strength average or the existing cross-team rate products.

Common opponents are mentioned in NCAA selection-criteria explanations, including the
women's criteria. That is domain motivation, not proof of predictive efficacy in this
men's experiment. Matching an opponent and venue does not randomize the games, and
postseason-selection criteria are not a substitute for probabilistic validation.

## Inputs and availability

Use regular-season compact and detailed records through day132 in each snapshot year.
Check that detailed records agree with compact results. Team-level game rates use the
existing shared-possession estimate and the existing <=10% possession-discrepancy clean
flag. Compact margins/wins are not discarded just because detailed support is absent.
No NCAA tournament outcome, realized round, or location is passed to the feature builder.

Home category is encoded from each team's perspective: home +1, away -1, neutral 0.
Match exact categories, not simply "not home." The prediction itself is a neutral
pre-tournament pairing; these are past-game comparison contexts, not its future location.
A neutral category does not guarantee equal travel or geographic advantages.

## Context construction and weighting

For each team, third-opponent ID and venue category, average every eligible meeting.
For an ordered pair A/B, retain contexts present for both teams. Compute A minus B in
each matched context, then average contexts belonging to the same third opponent.
Finally give every distinct common opponent equal weight. Thus rematches and multiple
venue contexts cannot automatically give an opponent extra influence.

If n opponents have usable measurements, a candidate is `sum(opponent contrasts)/(n+4)`.
Four is a fixed neutral-opponent prior, declared before evaluation; it is not tuned.
With no common evidence the incremental feature is zero and its support is explicitly
zero. This means "no comparison evidence," NOT "the teams are equally strong."
Training ignores support as an extra model input here, but coverage and loss diagnostics
stratify by support. Sparse evidence can make this representation uninformative.

## Family A — score and result (two candidates)

1. **`common_venue_margin_gap`**: the shrunken difference in points scored minus points
   conceded against matched opponents/categories.
2. **`common_venue_win_gap`**: the corresponding shrunken difference in win fractions.

These use compact-game support. Scoring margins retain their point units; win fractions
remain fractions. They can duplicate general strength, which is explicitly measured by
training-only correlations and the duplicate-input diagnostic.

## Family B — offense and defense (two candidates)

3. **`common_venue_offense_gap`**: shrunken contrast in points scored per 100 shared
   estimated possessions in clean detailed games.
4. **`common_venue_defense_gap`**: shrunken contrast in negative points conceded per 100
   estimated possessions, so better defense is positive.

The two efficiency candidates share detailed support, which can differ from compact
support. A missing rate is not a manufactured zero allowed score. Comparisons use only
contexts with both measurements finite; support counts describe that narrower set.

Direct A-vs-B games cannot qualify as a common-third-opponent comparison because a team
never plays itself. The implementation uses one vectorized matched-context self-join per
season, then opponent-level aggregations, rather than thousands of repeated dataframe joins.

## Comparison and diagnostic

Arms: reference, score_and_result, offense_and_defense, both, duplicate_control.
The duplicate control adds four copies of the existing margin-strength difference.
The two conditional family effects hold all other inputs fixed; no screening replacement.

Preparation reuses 12 base/reference snapshots, builds 12 context tables and 12 feature
snapshots, and fits zero rating models. Four reference fits are replayed; sixteen new
classifiers evaluate the four non-reference arms on the four later seasons.

The ten plots cover fixed-recipe scores, changes, conditional ablations, duplicate
sensitivity, matched-opponent coverage, calibration, confidence-binned loss, coefficients
and training-only overlap. Zero-support pairs remain visible rather than excluded from
validation to improve apparent scores.

## Explicit limitations and tests

Common opponents may change over time or play different personnel; schedule and venue
category matching does not control injuries, pace styles, travel or game timing. Late
fouling and blowouts can alter efficiency. The comparisons are descriptive summaries of
information available before the tournament, not causal estimates or pregame regular-season
backtests. Common-conference schedules can dominate support, including selection effects.

Tests cover exact venue matching, opponent-level equal weighting, repeated games,
no shared opponent, direct-head-to-head exclusion, defense sign, different compact/detailed
support, nonfinite input rejection, cutoff isolation, seed-pair order reversal, and
agreement of the vectorized implementation with a slower explicit reference calculation.

## Domain sources

- NCAA criteria explanation (common opponents appear in the women's list; not proof
  that this men's feature improves forecasts):
  https://www.ncaa.org/breaking-down-the-ncaa-division-i-mens-and-womens-basketball-committees-selection-criteria/
- Pomeroy, efficiency, possessions and opponent adjustment:
  https://kenpom.com/blog/ratings-glossary/

The four particular formulas, venue matching and fixed four-opponent prior are this
release's declared hypotheses. The sources motivate the mechanism, not its expected gain.

## Shared experimental contract

Men only. Reference = the original 16 columns plus `diff_rank_consensus_logit`.
Snapshot seasons are 2013–2019 and 2021–2025. Validation is 2022–2025; each fit uses
only earlier tournament seasons. Training physical-game counts are 503, 566, 629, 692;
validation has 63 played main-draw games per year. Seed-stem checks exclude First Four
and the documented 2021 no-contest is not a played label. No 2020/2026 outcomes enter.

Five configurations: 17-column reference, reference + family A (19), reference + family B
(19), reference + both (21), and a 21-column duplication control. Four verified old
reference classifiers are replayed; four configurations × four seasons require at most
16 new classifier fits. Fixed logistic C=0.1, no intercept, mirrored orientations,
physical-game weighting and training-only RMS scaling remain unchanged. Only a
training-constant column may be dropped. The builder never receives tournament outcomes.

The duplication diagnostic repeats one existing reference input four times. Those copies
are not novel features. With five identical scaled inputs, an identical total coefficient
can be distributed evenly, making its L2 contribution one fifth of the original penalty.
A prediction improvement therefore need not represent added information. This is a
sensitivity check, not a proof of causation or a perfectly matched penalty for new features.
No C tuning is conducted.

The primary contrast is `both_given_reference`. Also report the two family additions,
each family conditional on the other, `duplicate_given_reference`, and
`both_given_duplicate`. All use the same physical games. No screening algorithm inserts
replacement features after removal. Mean-season and game-weighted metrics, per-game
paired losses, fixed-bin calibration, log loss, coefficients, training-only correlations,
support counts and leave-one-season-out summaries are saved. Four equal-size validation
seasons make mean-season and game-weighted Brier identical here; both are still labeled.

An expansion candidate requires primary mean delta <= -0.0005, improvement in at least
three seasons, worst delta <= +0.003, AND a negative mean delta versus the duplicate
control. This resource gate is not a significance test, multiple-comparison adjustment,
or automatic feature promotion. No favorable secondary arm replaces the primary claim.
No experiment, Git write, AWS job, package install, or submission follows automatically.

These are repeatedly used exploratory seasons. Neither round calls them new holdouts.
The two rounds are independent experiments, not a sequential selector or ensemble;
round 15 is executed after round 14 for resource safety, but not conditioned on its gain.

## Durability and execution

Stage ceilings: prepare300s, evaluate180s, report120s; heartbeat15s. One shared lock forbids
parallel duplicate runs. Inputs, source, environment, stage tables, predictions and models
are checksum-bound. Every accepted season table and classifier is saved atomically with
its own receipt. A timeout preserves previously sealed work. No pickle is loaded: the
small saved logistic parameter dictionaries are checked before prediction replay.

The existing edited repository notebooks stay untouched; the source repository is not
imported. Known source/reference hashes, user report integrity, input data and relevant
upstream caches must agree. Outputs live only under this companion kit. Raw rows, model
objects and individual predictions are excluded from return ZIPs. A missing cache stops
instead of starting a costly recovery. HTML export precedes inline Plotly display.

## Statistical sources and limits

- Logistic regression L2 penalty and inverse regularization C:
  https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LogisticRegression.html
- Cawley & Talbot (2010), selection overfitting and evaluation bias:
  https://www.jmlr.org/papers/v11/cawley10a.html

These support the methodological caution, not a forecast that these features will win.
