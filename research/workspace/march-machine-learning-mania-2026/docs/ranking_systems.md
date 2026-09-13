# Individual ranking systems: declared feature experiment

Protocol written before fitting this experiment, 2026-09-08. The development
seasons have been explored previously; this is retrospective research, not a new
holdout. No 2022–2026 outcomes enter generation, screening or selection.

The consensus may discard differences among ranking methods. This experiment
tests whether those differences add information beyond the existing compact
strength-plus-consensus representation. It uses the official ordinal table already
in the verified source snapshot. No new external data or undocumented vendor
efficiency statistics are substituted for ordinal ranks.

The system vocabulary is frozen from legal day-132 publication panels in 2003–2012,
before the first training season. Retired systems may be rejected as unavailable;
systems first appearing in 2013 or later are deliberately outside this vocabulary.
Every current and historical panel uses each system's latest edition no more than
14 days old, and normalizes within that publication's own cohort. A team absent
from that edition remains absent. Source revisions after publication cannot be
independently ruled out by the downloaded historical table.

| Family | Hypothesis | Candidate definition per known system |
|---|---|---|
| Levels | Systems can differ in predictive quality and tail separation | Normalized ordinal percentile and clipped logit |
| Deviations | Consensus hides informative disagreement | Percentile and logit departures from the contemporaneous median |
| Momentum | Method-specific movement may precede the tournament | Matched-system changes at 7, 30 and 60 days |
| Availability | Missing coverage may distinguish incomplete information | Team availability indicator, differenced between opponents |
| Combined | Families may complement each other | All eight features per system |
| Embedding | Correlated systems may share a small latent structure | Eight training-fitted PCA components from levels and deviations |

All inputs are team-one minus team-two values. Base features are screened on the
training fold independently and are preserved in each augmented model. A separate
training-only screen retains at most 16 additional columns: this limits variance
without letting many correlated ranks displace the compact baseline. PCA replaces
that additional screen in the embedding arm; its imputation, scaling, usable-column
mask and components are fit only on mirrored training games. Eight is a fixed
upper bound, limited by training dimensions. No component count is tuned here.

Controls are the existing compact strength model (no Massey) and compact consensus
model. Logistic regression and shallow histogram boosting retain their original
fixed recipes. Verified original outer control fits are reused. All other fits use
the same physical games and earlier-season training history. Arms, capacities,
transformations and learner settings will not be changed after inspecting results.

Inner OOF forecasts from 2014 onward select among consensus and its six additions
for each outer year using only earlier seasons, with ties favoring the baseline.
Five outer seasons are 2016–2019 and 2021. Both game-weighted Brier and equal-season
Brier are reported. Paired season-bootstrap intervals and season-specific effects
are exploratory, with no multiple-testing correction or independent confirmation.

The stopping question is whether individual-system information shows a stable,
worthwhile improvement over the compact consensus. Uncertain or negative results
remain published. This study does not silently replace the frozen notebook 03/04
recipe. Player injuries, returning production and women's source parity require
different, verified historical inputs and are not manufactured from this table.

Source context: [Kaggle data](https://www.kaggle.com/competitions/march-machine-learning-mania-2026/data),
[Massey ranking comparison archive](https://masseyratings.com/cb/compare.htm).
