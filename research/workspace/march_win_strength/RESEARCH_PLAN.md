# Milestone 10 · Men's joint win-loss strength and rating uncertainty

## Decision from milestone 09

The predeclared `scaled_given_status` comparison worsened average women's Brier by **0.0004020908104074364**, improving only 2/4 seasons. The gate is `DO_NOT_EXPAND_AUTOMATICALLY`. All 16 comparisons completed, with 12 new classifiers, four replays and no rating fits. Preserve the finding; do not tune hosting exceptions selectively against these outcomes. The supplied metrics, manifest and all 18 return hashes have been checked in this kit's evidence review.

## Why investigate a different strength representation

Repeated rate/residual/context additions have not yet demonstrated reliable gains. We should not interpret this as proof that features are exhausted, nor as proof that the production-model gap is entirely attributable to features. The small fixed reference is an experimental comparison, not the submitted winner. The old historical seasons have been repeatedly examined.

This round targets a core quantity: **the ability to win against a schedule of opponents**, estimated jointly for all teams. Unlike margin-based strength, it intentionally discards winning margin. Unlike ordinary win percentage, it estimates opponent ability simultaneously. Unlike an Elo update loop, it fits all legal same-season outcomes jointly with a fixed probabilistic likelihood. The inspected repository's margin/efficiency and Elo implementations are different representations. Repository search was incomplete, so absence of every possible related implementation is NOT established. Bradley–Terry itself is an established method, not a novel scientific contribution.

### Evidence versus hypothesis

Turner and Firth (2012) describe Bradley–Terry paired-comparison models, including home/order effects. That supports the chosen model class. It does not establish that these particular fixed priors, derived uncertainty feature, historical panel or reference classifier will improve tournament Brier. Our implementation is Python with fixed Gaussian regularization; it is not a reproduction of every fitting method in their R package.

The uncertainty feature below is a mathematical construction using a Laplace approximation and numerical Gaussian integration. Its finite numerical checks do not establish empirical posterior calibration or predictive improvement.

## Rating model and objective

Use only `MRegularSeasonCompactResults.csv` rows in the snapshot season with `DayNum <= 132`. Input columns are `Season`, `DayNum`, `WTeamID`, `LTeamID`, and `WLoc`. The constructor filters before validating; later seasons and post-cutoff rows are excluded. Score columns are not read by the rating builder.

For a single physical game, define x with +1 for the winning team, −1 for the losing team, and v for location (+1 winner at home, −1 away, 0 neutral). Let theta contain team abilities a and a shared home log-odds coefficient h.

```text
P(winner defeats loser | ratings, venue) = sigmoid(a_winner - a_loser + h*v)
Objective = sum_games log(1 + exp(-x*theta)) + 0.5*theta' * Precision * theta
Team priors: a_i ~ Normal(0, 2^2)
Home prior: h ~ Normal(0, 1^2)
```

Every physical game enters once. There is no score-margin weighting, recency weighting, season carryover, or tournament label. Same-season modeling is appropriate for the frozen pre-tournament snapshot, not a claim of pregame predictions during that regular season. Priors are chosen before observing round10 tournament results, not estimated from those labels. They are not asserted optimal.

A proper Gaussian prior keeps unbeaten or winless teams finite. L-BFGS-B has a 500-iteration cap. Acceptance requires successful optimizer termination and maximum gradient ≤ 1e-4. Analytic derivatives are tested by finite differences.

## Two candidate features

1. **`bt_logodds_difference`**: d = a_A − a_B, using neutral venue for the potential matchup.
2. **`bt_uncertainty_correction`**: logit(E[sigmoid(Z)]) − d, with Z ~ Normal(d, v).

The Gaussian covariance is V = inverse(X'WX + Precision) at the fitted optimum, including the nuisance home parameter. For a neutral matchup, v = V_AA + V_BB − 2*V_AB. Omitting the covariance term would overstate or understate uncertainty; the implementation and regression test explicitly retain it.

The expectation is calculated by 64-node probabilists' Gauss–Hermite quadrature, checked against 128 nodes with a maximum absolute probability discrepancy of 1e-7. SciPy documents the nodes/weights and Gaussian weighting; numerical agreement is not a guarantee that a Gaussian approximation describes the true posterior.

Both features change sign on swapping the teams. The correction is generally a shrinkage toward zero log odds under the assumed Gaussian distribution. It does not represent a new observation independent of ability; the primary and conditional comparisons distinguish their contributions.

## Availability, leakage and support

Ratings see only legal regular-season outcomes, not NCAA tournament labels, seed strength, Massey editions, score margins, or later seasons. Existing reference snapshots keep their original provenance; they DO contain seed and margin/efficiency information. Therefore “margin-free” describes the new rating likelihood, not the entire tournament prediction system.

Matchup features are created for every pair of seeded teams in each available snapshot before attaching tournament outcomes. The reference is seed-dependent, so its intended information time is after field announcement. The new rating itself does not use seed values.

Sparse schedule-graph connectivity, per-team game counts and unique opponent counts are recorded. If seeded teams span disconnected components, the primary comparison stops: proper priors permit numerical fitting but cannot manufacture observed between-component evidence. The model supports at most 600 teams and only the declared 2013–2019 seasons in this milestone. Tournament main-draw labels remain those from the earlier validated parser. No 2026 tournament outcome is used.

## Frozen comparison and budget

Population: men only. Validation: 2016, 2017, 2018, 2019. Training labels: 2013 through validation year minus one. Every validation season is previously used exploratory history.

| Recipe | Columns | Role |
|---|---:|---|
| anchor | 16 | Verified existing reference |
| anchor_bt | 17 | Primary ability test |
| anchor_bt_uncertainty | 18 | Conditional uncertainty test |

The tournament classifier remains logistic C=0.1, no intercept, mirrored orientations and per-physical-game weighting. Scaling and constant-column checks are training-only. No column-count competition, hyperparameter search, feature selection against validation, ensemble, or probability-temperature sweep occurs.

Reuse seven base snapshots and four men's reference models: 2016 from the corrected possession run, 2017 from temporal-form, 2018 from schedule, 2019 from shooting. All are pinned to the returned bytes, not discovered by selecting the newest folder.

New work: seven season-local rating fits, seven matchup tables, eight challenger classifiers. Each rating and classifier is checkpointed independently. The uncertainty-only component ablation is deferred; this first milestone tests whether correction adds value conditional on ability rather than spending additional fits on an uninterpretable standalone shrinkage term.

Process ceilings: preparation 300 s, evaluation 180 s, report 120 s; 15 s heartbeats. These are not runtime estimates or billing caps. No new cloud resource or GPU is required. A complete rerun should reuse all seven ratings and eight challengers.

## Interpretation and decision

Primary: `ability_given_anchor = Brier(anchor_bt) - Brier(anchor)`.

Secondary: `uncertainty_given_ability = Brier(anchor_bt_uncertainty) - Brier(anchor_bt)`.

Also display `both_given_anchor`, but do not replace the primary after seeing a better secondary. Report equal-season means, game counts, all per-season metrics, log loss, calibration and training-only redundancy. The four main draws normally have the same game count; they are not independent draws because tournament participants recur.

A comparison merits **considering an unchanged later-era test** only if mean delta ≤ −0.0005, at least 3/4 seasons improve, and worst deterioration ≤ +0.003. This is a compute-allocation rule, not a significance test, guarantee or automatic promotion. The primary has not passed merely because another comparison did.

Do not loosen priors, change the epoch/window, inspect individual errors and encode overrides, or relabel a weak result “research-grade.” A later step must establish transfer to a fixed stronger production recipe and an explicitly labeled later-era panel before any claimed submission improvement.

## Limitations and research backlog

The rating assumes conditionally independent outcomes, stationary same-season ability and one common home effect. Roster/injury changes and repeated-opponent dependence are omitted. The Laplace covariance and fixed priors are approximate; confidence in team rating is not the same as randomness in a single game. Ignoring score margins may discard valuable information and increase noise. A strong correlation with the existing strength feature can make the added representation redundant. A negative result in this compact classifier does not rule out utility in every production learner.

The repeated 2016–2019 research process has selection bias. This kit does not reset the historical evidence. If another core-strength avenue fails, the next design review should explicitly compare final-model retained inputs, longer/modern training histories, source parity and external-data availability rather than continuing an unlimited sequence of minor handcrafted interactions. Individual ranking systems and consensus already have a recorded repository study; they should not be relabeled new without checking those results. Verified injuries/roster continuity, actual historical venue assignments, and modern-era feature availability remain separate unresolved input tasks.

The target is still 0.1097454 versus the last user-reported 0.1222672. Those scores refer to the 2026 leaderboard; the historical panel cannot be directly substituted for them. No claim is made that these two features will close that gap.

## Primary sources consulted

- Turner, H., and Firth, D. (2012). *Bradley-Terry Models in R: The BradleyTerry2 Package*. Journal of Statistical Software, 48(9). DOI: 10.18637/jss.v048.i09. https://www.jstatsoft.org/article/view/v048i09
- SciPy, `roots_hermitenorm` reference: probabilists' Gauss–Hermite nodes and weights. https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.roots_hermitenorm.html
- SciPy, `minimize` reference: gradient-based bounded-iteration minimization and result status. https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.minimize.html
- Inspected project source at the frozen reference: `src/march_mania/advanced_features.py`, especially the existing Elo updater; `src/march_mania/features.py` and the previously delivered frozen shooting reference distinguish margin/efficiency ratings. GitHub search returned incomplete results; no exhaustive absence claim is supported.

Research sources motivate methods; **your actual run's metrics** decide whether the candidates help.
