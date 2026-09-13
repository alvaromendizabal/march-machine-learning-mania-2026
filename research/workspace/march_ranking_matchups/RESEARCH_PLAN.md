# Milestone 12 — shared-system ranking matchups

## Decision from milestone 11

The supplied, checksum-verified archive completed 14 regular-season rating fits and 12 new tournament classifiers, with four replayed references. The primary Huber addition had mean Brier change −0.000198729856 and improved one of four seasons. The conditional compression addition had mean change −0.000303125026 and improved three; neither passed the registered mean-gain requirement. We do not relabel the nominally most favorable alternative as a successful primary test. No margin-feature expansion follows automatically.

## Why this is the next experiment

The recent manual reference contains sixteen internally derived/seeded inputs but no published-ranking input. The broader repository previously tested ranking consensus and an additional 840 system-specific candidates; its report retained compact consensus and did not promote that broad addition. Repeating the entire bank is not justified.

This round first makes the established ranking information explicit as a control, then tests **two matchup-level summaries of systems covering the same two teams**. It is not a claim that rankings are new to the project or that these formulas are novel statistics. Its goal is to distinguish a missing established signal from incremental value in a different pair representation.

Repository sources inspected at pinned commit `84b8fb36644a6558beded6dad84f5645ea4405d3`:

- `src/march_mania/rankings.py` — latest-edition selection, publication-cohort normalization, marginal consensus and per-team trends.
- `reports/ranking_systems/README.md` — prior results and the decision to retain the compact consensus, not 840 additional per-system definitions.

Links:
https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/src/march_mania/rankings.py
https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/reports/ranking_systems/README.md

## Data and information timestamp

Use only the already-audited `MMasseyOrdinals.csv` with SHA-256 `a14234e3fe3b63efe286fbbaf9bbc550ef2e52688c50ceadb2acb593e57634f8`. Its file hash is rechecked; no external rankings are downloaded. The data contain **ordinals**, not the vendors' underlying efficiency ratings. Do not relabel ordinal values as KenPom adjusted efficiency.

For each season 2013–2019 and each system, choose its latest entire edition in days 118–132. The edition is selected before restricting teams to the announced tournament field. A team absent in that edition remains missing; do not backfill an older rank. Days after 132, later seasons, tournament scores and outcomes do not enter a ranking panel.

Normalize using that publication's maximum ordinal, consistent with the pinned repository: q = 1 − (rank−1)/max(max_rank−1,1). Clip q to [0.01,0.99] only before logits. This is a cohort-scaled ordinal score, not a probability. Current systems receive equal treatment with no outcome-based weighting or selection. All contemporary systems are eligible, unlike the older system-level study's vocabulary frozen before 2013. This difference is explicit, and the paired and consensus arms use the same panel.

Seeds and base snapshots are available after field announcement. Potential pairings among all seeded teams are created without the realized bracket outcomes. Main-draw labels are attached afterward for the declared evaluation. Women are not assigned synthetic Massey data.

Historical downloaded rankings may contain retrospective revisions; the supplied snapshot cannot independently prove original publication bytes. This is an acknowledged source limitation.

## Fixed feature definitions

Let q_{s,t} be the normalized rank for team t in system s, and l_{s,t}=logit(clip(q_{s,t},.01,.99)). Let C_ab be the systems covering both opponents. All formulas negate exactly under a↔b.

**Established control**: c_ab = logit(clip(median_s q_{s,a})) − logit(clip(median_s q_{s,b})). The marginal median can use different available sets for each team. This reproduces the existing marginal-consensus definition, not a novel feature.

**Candidate A — paired median residual**: median_{s in C_ab}(l_{s,a}−l_{s,b}) − c_ab. Median of paired differences need not equal a difference of marginal medians. Thus shared-system comparisons can carry information absent from separate team summaries. The subtraction makes this distinction explicit; its usefulness is unproven.

**Candidate B — shared-system preference log ratio**: log[(w_ab + 0.5 t_ab + 1)/(w_ba + 0.5 t_ab + 1)], where w counts systems preferring each team and t counts genuinely tied original ordinals. The pseudocount is fixed, not tuned. Original ordinals determine ties: clipping logit tails must not merge ranks 1 and 2 into a fake tie. This represents agreement, not an NCAA win probability.

Fixed coverage floor: at least three common systems for every field pair. Missing teams or insufficient overlap stop the preparation stage with evidence rather than silently imputing a good rating. Support counts, coverage fractions and paired spread are diagnostics, not additional fitted features. No feature depends on realized winners or the location of actual tournament games.

## Literature context versus our hypotheses

Khetan & Oh (2016), *Data-driven Rank Breaking for Efficient Rank Aggregation*, JMLR 17(193), discusses transforming rankings into pairwise comparisons and warns that ignoring dependencies can produce inconsistent estimates. This motivates explicit treatment of the pair structure and caution about dependence. It does not validate these specific basketball features. We do **not** fit one training observation per system vote or assert that votes are independent Bernoulli trials.
https://jmlr.org/beta/papers/v17/16-209.html

Cawley & Talbot (2010), *On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation*, JMLR 11, explains overfitting the finite-sample selection criterion. These historical years have already been used repeatedly; a passed resource gate is not an untouched-test result or a significance statement.
https://www.jmlr.org/papers/v11/cawley10a.html

A 2026 preprint, *NCAA Bracket Prediction Using Machine Learning and Combinatorial Fusion Analysis*, explores combining rank information in basketball. Its accuracy results are not Brier scores, and its method and outcomes are not reproduced here. It is contextual literature, not evidence that this kit should beat the leaderboard.
https://arxiv.org/abs/2603.10916

The Massey comparison landing page returned HTTP 403 during this review. No unavailable live content was used or invented; the experiment uses the provided official-data snapshot and the inspected repository implementation.

## Fixed comparison design

Men only. Training starts in 2013 and ends before each validation season. Validate 2016, 2017, 2018, 2019 main draws. Five configurations: reference (16 inputs), reference+consensus (17), plus candidate A (18), plus candidate B (18), plus both (19).

The exact reference fitting functions are copied unchanged from the prior kit. Logistic C=0.1, no intercept, mirrored orientations and per-physical-game weighting remain unchanged. Scaling and active-column detection use only the training partition. No per-system screening, arbitrary polynomial expansion, classifier tuning or calibration search.

Primary contrast: **pairwise_given_consensus** = both candidates+consensus−consensus. Secondary/control: consensus−reference. Also report A−consensus, B−consensus, both−B, both−A. Removing a family does not admit replacement inputs through screening.

Primary improvement must not be replaced by a favorable consensus-only or other secondary outcome. Gains in the established control can motivate a separately documented later-era control-transfer test, not a novelty claim.

Resource scope: seven existing base snapshots, seven new ranking panels, seven new matchup tables, zero rating fits; four reference replays plus sixteen new classifiers. Preparation cap 300 seconds, evaluation 180, report 120, heartbeat 15. Each completed panel, matchup table and classifier has its own checksum receipt. Missing upstream caches stop instead of rebuilding.

## Decision, uncertainty and next research

Consider unchanged later-era evaluation only when mean primary delta ≤ −0.0005, at least 3/4 seasons improve, and worst delta ≤ +0.003. These are fixed compute-allocation criteria, not significance tests. No automatic promotion, future execution, submission or model replacement occurs. Log loss, calibration and conditional add/drop effects are reported separately.

A successful historical primary would still need later-era checks and transfer to the actual stronger production recipe. Repeatedly used 2022–2025 project benchmarks are not fresh untouched tests either. No 2026 outcomes are used to fit, build, or select these features.

This closes neither feature engineering nor attribution of the leaderboard gap. Independently useful player availability, roster experience/returning minutes, actual venue information, later-era validation and production-transfer questions remain open. They require verified as-of sources and distinct experiments; no fabricated player or injury proxies are substituted here. Continued negative evidence should shift priority toward independent information and better evaluation alignment rather than endless remappings of the same averages.

## Reproducibility and safety

The report pins the raw bytes, earlier artifacts, configuration, computational code and recorded environment. The repository's two known edited notebooks are preserved but never executed. Native JSON models are replayed; no pickle/joblib models are deserialized. Outputs remain outside the source repository. The run never invokes AWS, GitHub, Kaggle, package installers or network downloads. No claims of a Git commit/merge are made.
