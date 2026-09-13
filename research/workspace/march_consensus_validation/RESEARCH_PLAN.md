# Milestone 13 — Ranking consensus in a later era

## Decision from the supplied evidence
The uploaded milestone 12 archive is the basis for selecting this experiment. All 20 archived members covered by its integrity manifest matched their recorded SHA-256 values. Its main test, `pairwise_given_consensus`, worsened mean Brier by +0.0011137347240833678, improved two of four years, and failed the registered gate. The separate established control, `consensus_given_anchor`, improved mean Brier by −0.0009205404070523199, improved three years, and qualified for an unchanged later-era investigation.

Do not promote the failed pairwise family, replace the primary claim with the secondary, or characterize the consensus control as a new invention. Original metrics and decisions are included byte-for-byte under `evidence/round12/`.

## Hypothesis and experimental unit
The hypothesis is that the information summarized by pre-tournament published ranking consensus adds predictive information to the 16-column compact reference in **men’s 2022–2025 tournaments**.

Two arms only: `anchor` (16 original inputs) and `anchor_consensus` (17 inputs). The single difference is `diff_rank_consensus_logit`. The classifier, C=0.1, absence of intercept, mirrored orientations, physical-game weights, train-only root-mean-square scaling, random seed, and convergence settings are copied from the frozen earlier implementation.

The unit of evaluation is one played main-draw tournament game, represented once for scoring. Both orientations are used only during training, each weighted 0.5. No current validation labels affect coefficients, feature definitions, ranking panels, scaling, input support decisions, calibration, or settings. A given validation year's outcomes can become legitimate training observations for a later year, consistent with forward forecasting.

There are no new feature definitions, no capacity-based screening, no algorithm change, no hyperparameter sweep, no per-system selection, and no ensemble. This remains evidence-building for a representation, not a final model launch.

## Unchanged consensus formula
For each ranking system, select its latest complete publication with `118 <= RankingDayNum <= 132`. Do this before filtering to tournament participants. Never fill a team absent in that edition with an older ranking.

Normalize within the published cohort using its maximum ordinal:

`percentile = 1 − (OrdinalRank − 1) / max(max_ordinal_in_edition − 1, 1)`.

For each team, take the median percentile across available legal systems, clip it to [0.01, 0.99], and take its log odds. The matchup feature is team 1’s value minus team 2’s. The formula and cutoff exactly match the round-12 consensus control; local tests establish parity against that implementation.

System sets are allowed to vary by year because the original rule used all contemporary legal systems. They are correlated sources, not independent observations. Counts and publication dates are diagnostics, not estimated sample sizes for probabilistic confidence. Original historical sources may have been revised; the supplied CSV cannot independently certify absence of historical revision.

## Extending reference snapshots without reviving failed families
Existing 2013–2019 matrices are read from the completed round-12 run. They are not retrained. Four saved consensus classifiers replay on their original historical games, with scores checked against the uploaded report.

For 2021–2025, the reference is computed using the original `compact_strength` and `standard_control` functions. These perform one opponent-adjusted margin ridge fit and one additive offense/opponent-defense ridge fit per year. Shooting priors, mean rates, and aggregate statistics are unchanged. The old leave-opponent-out shooting residuals and three additional profile fits are not needed for the reference and are not called.

Reference-only construction is explicitly tested against the complete old snapshot function. Margin and efficiency rating outputs are sealed separately; final compact snapshots and matchup tables are separately sealed. A failure after one completed rating component need not repeat it.

Seeded-team requirements: all 68 teams; finite original reference inputs; at least ten detailed games, five possession-quality-valid games, and 80% detailed-game coverage. The latest legal ranking editions must retain at least three shared systems for every potential seeded pair. A violation stops and is reported; missing values are not fabricated or silently dropped.

## Labels, canceled tournaments, and 2021
- Snapshots: 2013–2019 and 2021–2025.
- Validation: 2022, 2023, 2024, 2025.
- Training: all eligible earlier seasons starting in 2013.
- No 2020 or 2026 labels are used. The 2020 tournament was canceled; 2026 remains outside this experiment.
- First Four games are identified by opposing teams assigned `a`/`b` variants of the same three-character seed stem. This is a label-population rule, not a feature. It avoids reusing a constant day cutoff that would include 2021’s later First Four.
- The documented 2021 Oregon–VCU no-contest is excluded from played-game training. It can be absent in the CSV or represented administratively; either way, no played result is invented. Team IDs are resolved from the pinned official MTeams table.
- Expected played main-draw count: 62 in 2021 and 63 in each other declared season. Expected First Four exclusions: four per season. Inconsistency stops rather than inventing labels.

The resulting expected physical training counts are 503 for 2022, 566 for 2023, 629 for 2024, and 692 for 2025. Each validation year contains 63 played main-draw games. Features for every potential seeded pair are built before results are joined. Realized rounds and locations are not predictors.

The prior kit explicitly prohibited 2022–2026 label evaluation. This new kit intentionally introduces a documented label loader for 2022–2025; it does not silently bypass that old guard or include 2026.

## Decision and diagnostics
Primary contrast: `Brier(anchor_consensus) − Brier(anchor)` in the four later years. Lower is better. No discovery-year pooling in the gate.

Consider a separate fixed-production-recipe test only if:
- mean Brier change <= −0.0005;
- at least three of four seasons improve;
- worst season deterioration <= +0.003.

These thresholds decide further resource allocation. They are not a p-value, a confidence claim, a guarantee, or automatic feature promotion. Log loss, calibration, coefficient behavior, training-only redundancy, shared-system coverage, probability-bin paired losses, and leave-one-season-out sensitivity accompany Brier. Small calibration bins and four-season sensitivity are descriptive.

A passing later-era comparison still does not establish improvement to the submitted pooled-XGBoost/conference-logistic recipe. Transfer into a stronger fixed production comparison is a separate milestone. A negative result is retained, and the representation is not retuned on these same outcomes.

## What this cannot establish
The 2016–2019 discovery years and 2022–2025 benchmark years have already been consumed elsewhere in this project. Calling this later-era validation does not make those years an independent untouched test. Prior repeated experimentation can bias interpretation. No test here measures the user’s 2026 submission score or isolates the entire gap to the research target.

The original submitted-score context remains 0.1222672; research target 0.1097454. Nothing in this kit changes or submits probabilities for 2026.

## Reproducibility, limits, and reporting
Raw inputs, source, environment, constraints, historical reports, and upstream artifacts bind the fingerprint. Read-only source inspection preserves the two known edited repository notebooks; it does not execute them. Native JSON model coefficients are used—no pickle loading. Preserved files are checked after each stage. Interrupted valid checkpoints are reused only after checksum validation. A exclusive execution lock and hard process-group limits prevent overlapping runs or abandoned child fitting.

Budgets: ten new rating fits, eight new tournament classifiers, five compact snapshots, five panels, five pair tables. No cloud/API calls or data acquisition. Limits: preparation 300 seconds, evaluation 180 seconds, report 120 seconds; 15-second heartbeat. Report generation precedes inline chart display. The return archive excludes raw data, fitted models, individual predictions, and private notebooks.

## Next research directions after this measurement
If consensus survives this check, test it with the stronger fixed production recipe before expanding nearby ranking transformations. If not, record the failure rather than performing another unbounded ordinal sweep. A separate subsequent feature investigation should prioritize independently informative historical player availability, returning production/roster continuity, or verified venue/travel context only after acquisition rights, timestamp availability, team identity, and coverage have been established. Those sources are not downloaded or claimed to exist here. Existing catalog and ablation evidence must be compared before proposing duplicate feature families.

## Sources: outside research versus supplied project evidence
The score tables and experiment choice come from the supplied milestone-12 archive. The following outside primary sources support methodological and calendar decisions; they do not support claims of measured improvement:

1. NCAA, *March Madness tips off with First Four games March 18* (2021-01-19): First Four on March 18 and first-round games March 19–20. https://www.ncaa.org/news/2021/1/19/march-madness-tips-off-with-first-four-games-march-18.aspx
2. VCU Athletics, *VCU removed from NCAA tournament as committee declares game no contest* (2021-03-20): official no-contest explanation. https://vcuathletics.com/news/2021/3/20/mens-basketball-vcu-removed-from-ncaa-tournament-as-committee-declares-game-no-contest.aspx
3. Big West Conference (2020-03-13), reproducing NCAA’s March 12 cancellation announcement. https://bigwest.org/news/2020/3/13/general-big-west-conference-cancels-spring-competition-and-championships.aspx
4. scikit-learn documentation, *Common pitfalls and recommended practices*: fit preprocessing on training data only. https://scikit-learn.org/stable/common_pitfalls.html
5. Cawley and Talbot (2010), *On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation*, JMLR 11:2079–2107. https://www.jmlr.org/beta/papers/v11/cawley10a.html

Frozen local code provenance: prior `march_ranking_matchups` and its bundled original reference functions, all included with hashes. No new paper-derived superiority claim is made.
