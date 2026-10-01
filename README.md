# NCAA tournament forecasting | ML engineering case study

**Alvaro Mendizabal · probability forecasting · temporal validation · cloud ML engineering**

## Current verified research boundary: 0.1033437 Brier

The strongest **AWS-reproduced post-competition research system** scores **0.1033437 Brier** on the complete 126-game 2026 men's + women's cohort. The published 2026 winning benchmark was **0.1097454**. This comparison is benchmark-informed, post-competition research—not an original competition placement or a prospective superiority claim.

The active stretch target is **0.0900000**, leaving **0.0133437** absolute Brier to close.

A further **0.1027974 local replay candidate** has passed aggregate reconstruction checks but is intentionally labeled **pending canonical AWS reproduction** rather than promoted.

**[Open the executed frontier notebook](portfolio/frontier_research.ipynb)** · [Current research boundary](docs/current_research.md) · [Post-merge research log](docs/post_merge_research_log.md) · [Supplemental-source ownership](docs/supplemental_source_ownership.md) · [Employer walkthrough](docs/employer_walkthrough.md)

| Boundary | Brier | Interpretation |
|---|---:|---|
| Published 2026 winner | 0.1097454 | Original competition benchmark |
| Previous retained research system | 0.1051853 | Earlier post-competition boundary |
| Owned external-consensus system | 0.1043513 | Independently reconstructed external inputs |
| **AWS-reproduced current system** | **0.1033437** | Current canonical research boundary |
| Local replay candidate | 0.1027974 | Pending canonical AWS reproduction |
| Stretch target | 0.0900000 | Research objective, not achieved |

## What changed since the previous public release

The private AWS program shifted from broad representation search to **owned supplemental data, strict source timing, and selective residual correction**.

### Independently reconstructed supplemental inputs

- **AP polling:** competition-era weekly observations are independently collected and mapped; the private feature layer retains trajectory summaries rather than depending on a frozen public CSV.
- **Dated BartTorvik:** **9,652 dated observations across 27 editions** are retained with explicit cutoff eligibility.
- **Supplemental games/context:** **96,531 corroborated games**, **19,006 cutoff-specific team profiles**, **90,550 venue-context rows**, **3,486 conference-context rows**, and **19,006 observed coach-history rows**.
- **Player-value research:** **1,210,609 pre-cutoff player-game rows** and **53,808 player source/profile rows** support independently derived player-value/availability proxies; these are not relabeled as proprietary BPR or medical injury data.
- **ESPN game context:** game-specific BPI/predictor and multi-provider market information are independently captured and normalized; the strongest stable gain came from a selective men-only correction while protecting women and previously strong first-round rows.

These counts describe different observation grains and are not additive training examples.

### Modeling conclusions

- generic public-solution model replacements repeatedly failed transfer even when development looked strong;
- direct player-value, trajectory, sparse-LR, and broad rating-consensus variants were rejected under frozen gates;
- an owned external-consensus correction improved the complete cohort to **0.1043513**;
- an uncertainty-gated dated-Torvik correction reproduced at **0.1033437** on AWS;
- a narrower agreement-gated candidate reaches **0.1027974** in local replay but remains pending canonical AWS reproduction;
- women remain substantially stronger than men, so current private research concentrates new correction capacity on men while protecting women's predictions.

## What this project demonstrates

**Temporal validation discipline.** Development, confirmation, and final-audit stages remain separated. A direction is rejected when early and recent evidence disagree instead of being rescued with post-hoc threshold changes.

**Data ownership without false equivalence.** Public solution mechanisms are decomposed into upstream data requirements and independently reconstructed where feasible. Proprietary KenPom/EvanMiya values and contemporaneous historical injury feeds are explicitly labeled unavailable rather than approximated into false parity.

**Negative-result discipline.** Successful execution is distinct from successful science. Engineering failures, source/timing blocks, and model rejections are tracked separately.

**Selective residual modeling.** The strongest post-release gains come from preserving strong baseline rows and applying complementary signals only where historical transfer supports them.

**Cloud ML engineering.** Private runners are checkpointed, resumable, integrity-checked, memory/time bounded, and package deterministic research evidence with executed notebooks.

## Competition-era scope

Active supplemental reconstruction and modeling use **men 2003+** and **women 2010+** where the competition-era inputs support them. Earlier cached observations may remain as inert provenance but are not an active modeling target.

## 2027 prospective infrastructure

The 2027 path is built around real publication timing:

- raw source responses are captured before feature normalization;
- capture timestamps and checksums are retained;
- missing future data remains **WAITING_FOR_TARGET_DATA**;
- unavailable sources do not become zero-valued pseudo-features;
- tournament mappings, seeds, bracket, and final cutoff remain unresolved until they actually exist;
- roster/availability information is intended for prospective capture rather than retrospective relabeling.

## Public/private boundary

This repository is an **employer-facing, semi-reproducible research case study**. It publishes aggregate methods, experiment outcomes, validation contracts, source-ownership states, and executed report notebooks.

It intentionally excludes raw supplemental datasets, row-level predictions, private candidate CSVs, fitted production models, private orchestration archives, exact production correction weights/gates, source-specific identity logic, credentials, and canonical AWS paths.
