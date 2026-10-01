# Research extension · owned supplemental data frontier

**Alvaro Mendizabal · NCAA tournament probability forecasting**

This portfolio documents the post-competition research program after the earlier public release. It is an employer-facing aggregate presentation, not a public distribution of the private training/submission pipeline.

## Current research boundary

| Measurement | Value | Interpretation |
|---|---:|---|
| Published 2026 winner | 0.1097454 | Original competition benchmark |
| Previous retained post-competition system | 0.1051853 | Earlier private research boundary |
| Owned external-consensus system | 0.1043513 | Independently reconstructed external context |
| **AWS-reproduced current system** | **0.1033437** | Current canonical post-competition research boundary |
| Agreement-gated replay candidate | 0.1027974 | Pending canonical AWS reproduction |
| Stretch target | 0.0900000 | Research objective, not achieved |

Lower Brier is better. None of the post-competition rows above should be interpreted as an original competition placement.

## What changed

The private research program now emphasizes **independent supplemental-source reconstruction, source timing, and selective residual correction** rather than broad feature accumulation.

Public-safe highlights:

- 96,531 corroborated supplemental games;
- 19,006 cutoff-specific team profiles;
- 90,550 venue-context rows;
- 3,486 conference-context rows;
- 19,006 coach-history rows;
- 9,652 dated BartTorvik observations across 27 editions;
- 1,210,609 pre-cutoff player-game rows supporting owned player-value/participation proxies;
- competition-era AP polling reconstructed and mapped independently;
- ESPN game-specific predictor/BPI and multi-provider market context normalized independently.

These observation counts are at different grains and are not additive samples.

## Evidence

- [Executed frontier notebook](frontier_research.ipynb)
- [Aggregate experiment ledger](post_merge_experiments.csv)
- [Supplemental source ownership matrix](supplemental_source_ownership.csv)
- [Current research boundary](../docs/current_research.md)
- [Post-merge research log](../docs/post_merge_research_log.md)
- [Supplemental-source ownership and 2027 contract](../docs/supplemental_source_ownership.md)

## Research conclusions

**Source ownership and model usefulness are separate.** AP reconstruction succeeded as a data milestone even though the tested AP-enhanced booster failed confirmation.

**Broad replacement is fragile.** Several public-solution-inspired LR/XGBoost/rating replacements improved development or recent years and then failed the complete 2026 audit.

**Selective correction transfers better.** The current retained gain comes from preserving strong baseline rows and applying complementary information only to historically supported men's cases.

**Timing is a first-class feature contract.** Historical season-level BPI was available but updated after tournament cutoffs; the project archived it and refused to use it as pre-tournament history.

**Negative results remain part of the portfolio.** Rejected models, timing blocks, and engineering failures are separated instead of collapsed into a single success/failure label.

## 2027 readiness

The private pipeline is designed to collect future observations prospectively with real timestamps and checksums. Missing target-season sources remain waiting states until publication. No 2026 value is silently copied into 2027.

The highest-value remaining data gaps are women-specific external rating parity and prospective roster/availability information.

## Public/private boundary

Published here:

- aggregate experiment outcomes;
- executed report logic;
- source ownership/provenance states;
- validation and timing contracts;
- negative results and limitations.

Intentionally withheld:

- raw/private supplemental data;
- prediction CSVs;
- fitted production models;
- exact residual gates/weights;
- source-specific identity logic;
- credentials;
- private orchestration archives and AWS paths.
