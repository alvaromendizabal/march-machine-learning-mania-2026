# Milestone 11 — opponent-adjusted margin robustness

## Decision that led here

The completed milestone 10 primary ability feature lowered mean Brier by
0.0002997002, but improved only two of four seasons. Its conditional uncertainty
addition lowered the mean by only 0.0000158293, also improving two seasons. Neither
meets the declared −0.0005 / 3-of-4 expansion rule. These are calculations from
all twelve score events in the uploaded recovery log. No new leaderboard score
was produced. Full scientific diagnostics were not part of that uploaded recovery
archive; this milestone first reads and verifies the already-saved full science
ZIP, rather than pretending unseen diagnostics were reviewed.

## Research rationale and contrary evidence

Scoring margin is informative about basketball ability; throwing it away is a
substantial information choice. Ken Pomeroy's 2013 rematch analysis found predictive
information even in large margins. That is evidence AGAINST assuming all blowouts
are meaningless or that clipping must improve prediction. [1]

Huber loss is quadratic for residuals within a declared threshold and linear
outside it. It limits the influence of very large *prediction residuals*. It
is not equivalent to truncating the score of a lopsided game. [2]

An older Pomeroy ratings FAQ described a margin cap. That is historical methodological
context, NOT the specification of present-day KenPom ratings, not evidence for
our specific parameter, and not a reason to dismiss the contrary 2013 analysis. [3]

We therefore compare two distinct hypotheses under the unchanged tournament
classifier. Neither is described as a new statistical method. No broad new
source or injury signal is being added in this small experiment.

## Comparison with the existing implementation

The frozen `shot_features.compact_strength` function fits raw scoring margin to
winner-team, loser-team, and home/away columns with Ridge(alpha=20,
fit_intercept=False). It already supplies `diff_strength` in the 16-input control.
The wider repository has Elo/margin and numerous distributional features. The
new distinction is the **loss/target used in joint schedule-adjusted margin
estimation**, not a claim that score margins or robustness are new concepts.

The read-only review of `reports/ranking_systems/README.md` also showed that
individual ranking additions have already been investigated, including a failed
forward-selected representation. We do not repeat that search merely because the
current small companion model does not contain every project feature. [4]

## Fixed mathematical definitions

For a regular-season physical game g, let m_g be winner score minus loser score,
v_g be +1 for a home winner, −1 for an away winner, and 0 at a neutral site.
The design x_g contains +1 for the winner's team coefficient, −1 for the loser's,
and v_g for the common home coefficient. All games through day 132 are included.
No tournament result is passed to either fitting function.

**Primary candidate — residual-robust strength.** Estimate theta by minimizing

`sum_g H_15(m_g - x_g theta) + 10 * ||theta||^2`.

The ridge alpha is 20 (including the home term), matching the frozen control's
penalty convention. The Huber threshold of **15 score points** is a predeclared
research choice, NOT a fitted optimum, a literature-derived universal threshold,
or a hyperparameter selected on these tournament outcomes. A 30-point win with
an expected margin of 28 has a residual of 2 and is not downweighted. An unexpected
30-point win with an expected margin of 2 has a residual of 28 and receives reduced
influence. The matchup feature is the difference in the two fitted team coefficients.

**Secondary candidate — compressed-margin strength.** Estimate theta by minimizing

`0.5 * sum_g (15*tanh(m_g/15) - x_g theta)^2 + 10 * ||theta||^2`.

Unlike the primary candidate, this compresses *every observed margin* toward a
15-point saturation limit. It intentionally sacrifices margin magnitude. Its
failure is plausible and should be retained as evidence. The matchup feature is
the difference in the two fitted team coefficients.

No derived 'robust minus raw' column is added: with raw strength already in the
reference it would be an exact linear combination, not an additional independent
representation. No unconstrained cross-products or thousands of filler columns
are generated.

## Data availability and leakage assumptions

Use men, seasons 2013–2019, regular-season day ≤132. Filtering precedes validation
so post-cutoff rows cannot contaminate estimates. Every used game must have finite
integer identities/scores, a valid location, a positive winning margin, and no
repeated physical-game identity. The input is validated before aggregation.

Use the cached same-season team rows and announced seeds only to construct all
potential seeded matchups. Seeding is available after the bracket announcement.
Only later does the classifier join historical main-draw tournament labels.
The new rating models neither read those labels nor condition pair construction
on realized tournament opponents. No 2026 outcome enters fitting or selection.

Within-season use of final pre-tournament opponent ratings is legal for a
pre-tournament forecast. It is NOT a pregame regular-season backtest.

Model teams can have disconnected schedule components, but seeded teams spanning
different components are rejected rather than assigning a spurious cross-component
ordering. Every matchup input reverses sign under a team swap. The classifier
retains mirrored orientations and complementary predicted probabilities.

## Frozen evaluation

Men only; validate 2016, 2017, 2018, 2019. Train from 2013 through year t−1.
Main-draw games only, matching the earlier reference. Four configurations:

| Name | Inputs | Role |
|---|---:|---|
| anchor | 16 | Replay, no refit |
| anchor_huber | 17 | Primary representation |
| anchor_compressed | 17 | Alternative representation |
| anchor_both | 18 | Conditional-complementarity check |

C=0.1, no intercept, original fixed logistic recipe, training-only RMS scaling,
mirrored orientations with total weight one per physical game. Only columns
constant in training can be removed. There is no capacity-based displacement,
model search, calibration sweep, resampling search, or ensemble.

Primary: `huber_given_anchor`. Secondary: `compression_given_huber`.
Other add/drop contrasts remain descriptive and cannot replace the declared primary.
Mean Brier improvement ≥0.0005, gains in at least 3/4 seasons, and worst deterioration
≤0.003 are requirements for CONSIDERING further work. They are resource-allocation
rules, not statistical significance tests. No automatic promotion or new run follows.

Brier, log loss, per-season deltas, controlled family effects, coefficients,
training-only overlap, and pooled calibration are saved. Four equally sized folds
make equal-season and game-weighted Brier coincide in this main-draw design;
no comparison to a 2026 leaderboard Brier is made as though the game sets matched.

## Numerical and execution contracts

Huber uses deterministic iteratively reweighted least squares (IRLS), at most 100
steps, solving a sparse ridge system each step. Objective nonincrease and the
maximum analytic-gradient norm ≤1e−5 are checked. These are new rating objectives,
not another modification of the BT recovery or its 1e−4 certificate.

Compression uses one sparse normal-equation solve and the same 1e−5 gradient check.
All accepted fits are checkpointed individually; model JSON and iteration trace
have a hash-verified completion marker. Seven seasons × two rating kinds = **14
new rating fits**. Seven potential-pair tables are cached separately.

Four references are replayed against their previously saved probabilities. Sparse
legacy metric metadata are normalized from verified predictions, not assumed to
contain log_loss. Cached models are native JSON, not pickle execution. New classifiers
receive a separate three-file checkpoint. At most 12 classifiers are fitted.

The already completed full milestone 10 science report is read with a pinned SHA,
size/path/scope checks and its own inner integrity ledger; its twelve Brier values
must match the recovery log. Its exact bytes are included in the next return ZIP.

Stage caps: preparation 300s; evaluation 180s; reporting 120s. Heartbeats every 15s;
exclusive lock; checkpoint reuse; no automatic repeated solver retries. Previous
source, raw input, reference, environment and report identities are checked before
and after stages. Missing inputs stop rather than triggering a rebuild.

## Interpretation limits and next research priorities

An atypical residual is not proof of corrupt data, garbage time, injury or coach
behavior. Heavy shrinkage can already dampen outliers; extra robustness may simply
remove true signal. A fixed 15-point threshold may not transport to women or later
eras. Neither candidate accounts directly for possessions, lineup changes or travel.

These seasons have been reused for many hypotheses. A failed fixed-recipe test does
not rule out every future model, and a successful one is not a fresh holdout success.
The strongest submitted model is not this compact logistic control. The score gap
cannot be attributed solely to missing features from these experiments.

After this bounded check, prioritize independently informative, historically
verifiable sources or a prespecified stronger-production-recipe/later-era transfer
study over an endless succession of variations on the same small old-season control.
Candidate source investigations include archived player minutes/returning production,
pre-announcement availability, and confirmed venue/travel information. Each needs
permission, timestamp, coverage and team-mapping checks before use; none is downloaded
or claimed available in this milestone. Feature engineering remains open, but a large
candidate count is not evidence of value.

## Primary sources and inspected project evidence

[1] Ken Pomeroy, *Evidence that scoring margin matters*, 22 January 2013.
https://kenpom.com/blog/evidence-that-scoring-margin-matters/

[2] SciPy, *scipy.special.huber*. Formula and robustness interpretation.
https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.huber.html

[3] Ken Pomeroy, *Pomeroy Ratings FAQ* (historical method; not a current specification).
https://kenpom.com/blog/pomeroy-ratings-faq/

[4] Project ranking-systems report at the previously verified commit
84b8fb36644a6558beded6dad84f5645ea4405d3.
https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/reports/ranking_systems/README.md
