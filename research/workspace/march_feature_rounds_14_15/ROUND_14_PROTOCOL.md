# Round 14 — ranking resolution and cardinal-strength mappings

**Four candidates, two families, sixteen new classifier fits maximum, ten Plotly charts.**
Hypotheses specified before any round-14 or round-15 competition-data output. The
validated 17-input reference is frozen. This round explores how ordinal consensus is
represented, not which individual system to select.

## Rationale and novelty boundary

The earlier published system study and round 12 already investigated ranking levels,
disagreement and momentum. Here the question is narrower: does clipping the consensus
at 0.01/0.99 lose informative top-tail separation, and can a declared mapping to an
existing league-strength distribution make its spacing more useful?

With a 365-place edition the old formula `1-(rank-1)/(N-1)` puts ranks 1–4 at or above
0.99, so the fixed clip can assign them the same transformed value. Restoring resolution
can also amplify noisy extremes. Ordinal ranks provide ordering, not vendor cardinal
ratings, and the mappings below do not reconstruct unavailable vendor efficiencies.

## Inputs and availability

Reuse each system's frozen latest edition in days 118–132 from round 12/13. No team
backfill, newly selected edition, changed system vocabulary, or future publication is
introduced. `N` is the maximum published ordinal in that edition, preserving the earlier
cohort convention rather than pretending to know an omitted population. Systems are
correlated sources, not independent votes.

Reuse cached same-season pre-day132 league `strength`, `adj_offense`, `adj_defense`.
No new rating models are fitted. The mapping uses at least 50 teams with all three
cardinal fields finite; missing league rows are reported and excluded from both cardinal
maps consistently. This is legal cross-sectional pre-tournament information, not
validation-label-based feature selection.

## Family A — tail resolution (two candidates)

For system j and team t, let `p_jt = 1-(r_jt-0.5)/N_j`. These plotting positions are
strictly inside (0,1), unlike a hard 1% clamp. Define `P_t = median_j(p_jt)`.
Let `L_t` be the existing clipped-logit consensus, independently reproduced and checked.

1. **`rank_midpoint_logit_correction`**: define `c_t = logit(P_t)-L_t`, then return
   `c_A-c_B`. The existing L difference remains in the reference.
2. **`rank_normal_quantile_correction`**: define
   `c_t = (pi/sqrt(3))*Phi_inverse(P_t)-L_t`, then return `c_A-c_B`.
   The fixed scale matches the variance of a standard logistic distribution; it does not
   assert that true team ability is normally or logistically distributed. This tests
   another fixed tail shape, not a fitted normality model.

## Family B — cardinal mappings (two candidates)

Let Q_strength be the empirical inverse CDF of the complete league margin-strength
values, and Q_efficiency the corresponding inverse CDF of `adj_offense+adj_defense`.
Both use fixed linear quantile interpolation, at the same P_t defined above.

3. **`rank_mapped_margin_gap`** = Q_strength(P_A)-Q_strength(P_B).
4. **`rank_mapped_efficiency_gap`** = Q_efficiency(P_A)-Q_efficiency(P_B).

These impose an experimental common marginal scale. They need not match a particular
team's existing margin or efficiency rating; their ranking comes from the publications.
They can be redundant with the existing consensus and league strength, which is why
conditional effects and training-only overlap are reported rather than assuming novelty
of information from novelty of column names.

## Comparison and diagnostic

Arms: reference, tail_resolution, cardinal_mapping, both, duplicate_control.
The duplicate control adds four copies of the existing consensus input.
`tail_resolution_given_cardinal_mapping` and `cardinal_mapping_given_tail_resolution`
are controlled family removals from the full four-candidate representation.

Preparation reuses 12 base/reference snapshots and 12 publication panels, and builds
12 feature snapshots. Candidate total = four, not the four duplicated control columns.
The ten visualizations include per-season Brier and deltas, controlled ablations,
duplicate sensitivity, ranking-profile spacing, support, calibration and redundancy.

## Explicit limits and tests

Team-swap antisymmetry, input-order invariance, strict date range, one edition per system,
rank positivity/integrality, duplicate rejection, consensus numerical parity, adequate
mapping population and nonfinite values are tested. No post-day132 row is admitted.
The common shrinkage/strength scale is descriptive, not a new fitted tournament prior.
A gain requires confirmation before production transfer; the current logistic reference
is not the submitted pooled 128-input XGBoost recipe.

## Domain/implementation sources

- Repository publication-cohort implementation inspected in the preceding milestone:
  https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/src/march_mania/rankings.py
- Previous system study and its negative/uncertain findings:
  https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/reports/ranking_systems/README.md
- SciPy inverse normal CDF reference:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.norm.html
- Opponent/pace-adjusted basketball-strength context:
  https://kenpom.com/blog/ratings-glossary/

The new transforms are hypotheses proposed in this release, not claims that any cited
source demonstrated their competition value.

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
