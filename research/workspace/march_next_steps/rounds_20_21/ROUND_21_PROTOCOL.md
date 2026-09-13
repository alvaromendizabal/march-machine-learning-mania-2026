# Round 21 — Performance against similar opponent styles

**Status: prepared, unexecuted.** Four hypotheses, two families, same experimental resources as round 20. Men, played 2022–2025 main draws, already-explored years. Independent from round 20: no use of its results, selected features or predictions.

## Why this investigation
The exact-common-opponent experiment failed its promotion criterion. This alternate representation compares opponents by *style*, not only identical team IDs. It tests whether a team's conditional performance differs from its unconditional performance against similarly paced/spaced or pressure/rebounding opponents. NBA matchup research motivates matchup dependence, but does not establish the effectiveness of this NCAA kernel construction. We are not implementing LinNet, using lineup data, or claiming its reported performance.

## Legal data and cached adjustment
Use only current legal regular-season detailed games through day132 and previously verified same-season opponent-adjusted offense/defense snapshots. No new rating fits.

For team A against historical opponent j:
`offense response = points/possessions ×100 + cached defensive strength(j) − 3×home`
`defense response = cached offensive strength(j) − allowed/possessions ×100 − 3×home`.
Higher defensive response means better-than-otherwise defensive performance. Three efficiency points is a fixed location heuristic, not a new fitted home effect or a causal estimate.

Average repeated games within (team, opponent). For each target matchup A versus B, exclude **every response row against B**. Styles themselves still describe full legal seasons. Thus this is direct-response exclusion, **not** a claim that every intermediate statistic is leave-pair-out.

## Style descriptions and candidates
Two standardized style spaces, scaled by contemporaneous full-league population SD:

1. Pace / spacing: mean possessions per40 and three-point-attempt share.
2. Pressure / rebounding: opponent turnovers per possession and offensive-rebound share.

Use a fixed Gaussian weight exp(−distance²/2), with distance>2 assigned zero weight. Each distinct opponent gets at most one weight. Center its offense/defense response by A's unconditional mean over eligible distinct opponents. Divide the weighted centered sum by total weights+5 to shrink sparse evidence toward a neutral increment.

Four candidates are A's target-specific response minus B's reverse response:
- offense and defense against pace/spacing neighbors;
- offense and defense against pressure/rebounding neighbors.

No neighbors means zero increment with zero-support diagnostics—not equal true strength or a fabricated measurement. Support is weighted distinct-opponent count, not an independent effective sample size. Styles use fixed small-sample smoothing as documented in `feature_rounds.py`.

Controls: unconditional neutral-adjusted offense/defense response and shrunk nonhome deviations, each A−B. This compares conditional representation against ordinary unconditional summaries rather than a deprived baseline.

## Equal scope and validation
Six configurations with 17/21/23/23/25/25 inputs; twelve new feature tables, four reference replays, twenty new classifiers, zero rating fits. Reference, regularization, train-only scaling and split definitions are frozen. Repeated-opponent aggregation and target kernels are descriptive pre-tournament construction, not tournament-trained transforms.

Primary `context_given_controls`; conditional add/drop comparisons; `both_given_duplicate` must be negative. Same gate as round20: mean≤−.0005, ≥3/4 years improved, worst≤+.003, negative duplicate-control comparison. No automated expansion or tuned bandwidth. Same data audit, one-season smoke, reuse proof, bounded stages and report scope.

## Failure conditions / limitations
Stop for missing cached opponent adjustments, undefined style-scale dimensions, nonfinite values or <10 detailed games per seeded team. Do not silently fill unknown opponent ratings. Zero neighborhood support is an expected condition, explicitly recorded. Home/away mix, game dates, personnel, changing opponents, conference clustering, scorekeeping and stale season-average adjustments can confound response estimates. Four reused seasons and repeated hypotheses limit interpretation. A favorable result still needs transfer to the stronger production recipe and a defensible subsequent assessment.

## Sources
- Pelechrinis, LinNet: Probabilistic Lineup Evaluation Through Network Embedding (2017): https://arxiv.org/abs/1707.01855 . NBA lineup-matchup dependence as context; not the algorithm/data/score of this experiment.
- Pomeroy, Stats Explained: https://kenpom.com/blog/stats-explained/ . Possession and rate definitions.
- Prior local round15 common-opponent experiment: negative fixed-reference evidence. This change has to prove itself beyond that negative result, not erase it.
