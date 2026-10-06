# Portfolio | NCAA tournament forecasting research

**Alvaro Mendizabal · temporal ML · probability forecasting · source provenance · AWS/SageMaker**

This directory is the compact, employer-facing evidence layer for the project. It summarizes the research without publishing the private competition implementation.

## Current verified boundary

| System | Evaluation | Brier | State |
|---|---|---:|---|
| v26 owned-data control | submitted result | **0.1206458** | Accepted / submitted |
| v26 exact local replay | 126 scored games | **0.1206458343** | Verified scorer |
| Native women reconstruction | 63 women games | **0.0767383172** | Numerically reproduced |
| v54 reconstructed research frontier | 126 scored games | **0.1067095543** | Experimental / not promoted |

Lower Brier is better. The experimental result is presented as retrospective research, not as a replacement for the accepted system.

## What this portfolio demonstrates

### Source ownership and provenance

The project independently reconstructed or derived substantial supplemental information instead of relying on another competitor's prepared feature files:

- 15 men's Bart Torvik tournament seasons with dated source receipts;
- 117 rank-complete AP editions and 95 ballot-complete editions;
- official-derived Elo, SRS, Colley, Bradley-Terry, efficiency, pace, schedule, and Massey context;
- more than 1.2M mapped pre-cutoff men's player-game rows;
- independently reconstructed postseason-selection facts;
- partial original-source market and ESPN BPI history;
- complete 68-team men's publisher probability fields for 2025 and 2026.

### Numerical reproduction

The native women's model was reconstructed from owned inputs and reproduced **65,703 pairwise probabilities within 1e-4** of the archived reference.

The men's reconstruction separately established same-input procedure parity for **66 core members** and **66 margin members**, plus reconciliation of 31 auxiliary feature columns.

### Reproducible raw-game foundation

The latest AWS milestone rebuilds a broad official-data foundation from raw compact and detailed game records:

- 13,753 men’s team-season rows across 42 raw seasons;
- 9,851 women’s team-season rows across 29 raw seasons;
- all 566 historical men’s matchup identities covered by both teams;
- complete performance and schedule feature pairs for all 566 games;
- temporal / venue feature completeness for 554 / 566 games;
- separate-process raw-to-feature replay for both genders;
- 2026 feature generation rehearsed as an incoming-season update.

This evidence strengthens reproducibility without changing the accepted or experimental score boundary.

### Validation repair

The historical men's evaluation bank now covers **566 played main-bracket games across nine forecast seasons**.

The project reproduced all **558 previously saved control predictions** before restoring eight legitimate later-round games that an old equal-seed filter had omitted.

### Negative-result discipline

Recent matched experiments were not promoted simply because a recent confirmation slice improved:

- mirrored pair-exchange training improved all three recent confirmation seasons but worsened development;
- exact-date AP integration improved aggregate recent confirmation but worsened development;
- complete publisher probability reconstruction succeeded as source recovery but its fixed forecast blend was rejected.

This distinction between a successful execution and a successful scientific hypothesis is central to the project.

## Evidence map

- [Start here](../START_HERE.md)
- [Employer walkthrough](../docs/employer_walkthrough.md)
- [System architecture](../docs/architecture.md)
- [Current research boundary](../docs/current_research.md)
- [Source ownership](../docs/supplemental_source_ownership.md)
- [Owned raw-game foundation](../docs/reproducible_source_foundation.md)
- [Reproduction matrix](../docs/reproduction_matrix.md)
- [Research log](../docs/post_merge_research_log.md)
- [Owned-data frontier](owned_frontier_2027.md)

Machine-readable summaries:

- [reconstruction_frontier.json](reconstruction_frontier.json)
- [owned_frontier_milestones.csv](owned_frontier_milestones.csv)
- [owned_frontier_experiments.csv](owned_frontier_experiments.csv)
- [supplemental_source_status_2027.csv](supplemental_source_status_2027.csv)
- [owned_source_foundation_v76.json](owned_source_foundation_v76.json)

## Public/private boundary

Published here:

- aggregate metrics and exact evaluation populations;
- source-coverage and provenance states;
- reproduction evidence;
- historical validation decisions;
- negative-result conclusions;
- public-safe notebooks and architecture.

Intentionally withheld:

- row-level private forecasts;
- fitted private competition models;
- raw supplemental source archives;
- exact private correction rules, thresholds, and weights;
- source-specific identity logic;
- credentials and AWS-local orchestration state.

The goal is a technically auditable portfolio, not a turnkey competition package.
