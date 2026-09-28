# Employer walkthrough | NCAA forecasting research

## Start here

Open the [frontier research notebook](../portfolio/frontier_research.ipynb). It is the fastest way to review the project: current score boundary, post-release experiment progression, data/provenance growth, 2027 readiness, and the public/private implementation boundary.

For the chronological details, see the [post-merge research log](post_merge_research_log.md).

## Result and framing

The retained private post-competition system scores **0.1051853 Brier** on the complete 126-game 2026 cohort. The published 2026 winner scored **0.1097454**. The private result is numerically lower, but the research is post-competition and informed by public benchmarks, so it is presented as an applied ML case study rather than an original competition placement.

The stretch target is **0.09**, leaving **0.0151853** absolute Brier.

## What to evaluate

**Research discipline.** Several post-release models improved recent seasons and were still rejected because they failed earlier development gates. The project treats stability across seasons as a first-class criterion.

**Point-in-time engineering.** Same-day states are frozen before the current game, forecast-year transforms fit only on permitted training partitions, and future source captures retain observation timestamps. Missing future data is a waiting state, not an excuse to substitute later information.

**Data-system breadth.** The private AWS workspace now spans team-game, player-game, daily pregame, possession, lineup, roster, schedule, and prospective observation layers. A scoped registry tracks 4,318 hashed CSV paths and 903 receipt-matched reconstructions.

**Matched experimentation.** New information is evaluated against an identical-row control whenever possible. Only the incremental value of the additional feature family is allowed to become a candidate correction.

**Negative-result quality.** The shot-context study is a good example: it improved held-out regular-season prediction by roughly 0.00084 Brier but did not improve tournament confirmation. That result closed a plausible transfer direction without discarding the reconstructed data layer.

**Leading-solution awareness.** Public 2025 and 2026 mechanisms are decomposed into transferable ideas and tested independently. Missing injury, proprietary player-value, and point-in-time external-rating inputs remain explicitly missing instead of being quietly approximated into claims of exact reproduction.

**Cloud engineering.** Substantial workflows are checkpointed, resumable, runtime-bounded, and packaged with an executed notebook and audit evidence. The most expensive reconstruction steps are reused instead of repeated across each experiment.

## Post-release highlights

- 154,657 validated advanced-context games.
- 167,143 daily pregame examples; 86,929 eligible under the fixed contract.
- 12.4M possession rows across 88,079 verified games.
- 125,657 historical roster-attribute observations.
- 465 frozen 2027 preseason reference forecasts.
- residual fusion that narrowly missed promotion rather than being retuned after the fact.
- a 33-feature linear/nonlinear joint model that improved recent years but failed development.
- roster-geometry reconstruction now ready for a cold-start-safe historical completion test.

## Semi-reproducible public surface

The notebook and [post_merge_experiments.csv](../portfolio/post_merge_experiments.csv) reproduce the public aggregate charts and gate interpretations without exposing the private forecasting implementation.

Public GitHub intentionally excludes raw private datasets, prediction files, model binaries, exact feature formulas, source-specific mapping logic, production correction weights, credentials, and AWS paths.
