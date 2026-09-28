# NCAA tournament forecasting | ML engineering case study

**Alvaro Mendizabal · probability forecasting · temporal validation · cloud ML engineering**

## Current verified research boundary: 0.1051853 Brier

The strongest retained private post-competition system scores **0.1051853 Brier** on the complete 126-game 2026 men's + women's cohort. The published 2026 winning benchmark was **0.1097454**. The retained late score is numerically lower, but this repository is **benchmark-informed post-competition research**, not an original competition placement or a claim of prospective superiority.

The active stretch target is **0.0900000**, leaving **0.0151853** absolute Brier to close.

**[Open the current frontier notebook](portfolio/frontier_research.ipynb)** · [Employer walkthrough](docs/employer_walkthrough.md) · [Current research boundary](docs/current_research.md) · [Post-merge research log](docs/post_merge_research_log.md) · [Research frontier](docs/frontier_research.md)

| Boundary | Brier | Interpretation |
|---|---:|---|
| Published 2026 winner | 0.1097454 | Original competition benchmark |
| **Retained private post-competition system** | **0.1051853** | Current research boundary |
| Stretch target | 0.0900000 | Research objective, not achieved |

## What changed since the previous public release

The project moved from a single chronological-ensemble study into a broader **data, validation, and representation program**. The retained score did not improve, but the research boundary is much better understood.

### Data and provenance expansion

- **154,657** advanced-context regular-season games validated across 32 gender-season archives.
- **167,143** daily pregame examples reconstructed with same-day leakage controls; **86,929** met the fixed training-eligibility contract.
- **88,079** games and **12.4 million** possession-level records validated for lineup-oriented research.
- **125,657** historical roster-attribute observations reconstructed across 24 gender-season datasets.
- A scoped registry now contains **4,318 hashed CSV paths**, including **903 paths that match discovered reconstruction receipts**.
- The prospective 2027 layer froze **99 men's + 366 women's** preseason reference forecasts while keeping tournament IDs, bracket, seeds, and final cutoff explicitly unresolved.

These counts describe different observation grains. They are not additive independent training examples.

### Research conclusions

The post-release program tested several distinct hypotheses rather than continuing micro-variants of one model:

- corrected player-impact exposure improved development but failed confirmation;
- shot-context features were useful in held-out regular-season games but did not transfer reliably to tournaments;
- possession/lineup data produced a large validated warehouse, but the first fixed lineup formulation did not satisfy its own holdout gate;
- cross-season player-origin information improved all three recent assessment years but failed the earlier development gate;
- combining independent residual corrections came close to promotion but missed the recent-confirmation threshold;
- a direct 33-feature linear/nonlinear joint model improved recent seasons but regressed development;
- roster geometry and role attributes are now reconstructed, but the first historical test was blocked by one early cold-start fold rather than scored selectively.

The detailed outcomes are in [the post-merge research log](docs/post_merge_research_log.md), with aggregate machine-readable results in [portfolio/post_merge_experiments.csv](portfolio/post_merge_experiments.csv).

## What this project demonstrates

**Temporal validation discipline.** Forecast-year transforms, models, and combination weights are constrained to information available from earlier training years. Assessment outcomes do not retroactively choose the model family.

**Negative-result discipline.** A model that helps recent seasons but violates a predeclared development gate is rejected instead of promoted post hoc.

**Data engineering at multiple grains.** The private AWS workspace maintains team-game, player-game, daily pregame, possession, roster, schedule, and prospective observation layers with explicit receipts, checksums, and eligibility states.

**Reproduction without copying.** Public 2025 and 2026 solution mechanisms are decomposed into transferable ideas—strength, matchup differences, boosting, margin supervision, player context, and market information—then independently reconstructed and tested. Missing proprietary or point-in-time inputs remain labeled as missing rather than approximated into false parity.

**Cloud engineering.** Long-running steps are checkpointed, resumable, bounded by runtime/memory budgets, and packaged with executed notebooks and audit evidence.

## 2027 prospective infrastructure

The 2027 path is intentionally conservative:

- roster and schedule observations are captured with source time and season identity;
- **99 men's and 366 women's preseason reference forecasts** are frozen as dated research products;
- unavailable target-season sources remain `WAITING_FOR_TARGET_DATA`;
- raw observations are not automatically promoted into model features;
- official tournament mappings, bracket, seeds, and final cutoff remain unresolved until they actually exist.

The goal is to enter 2027 with a tested data contract, not to fabricate readiness before the competition inputs exist.

## Current frontier

The retained 0.1051853 system remains strongest. The evidence now argues against more weighting tricks on highly related team-level models. The highest-value remaining gaps are **genuinely new information**—especially point-in-time availability/injury context, stronger women's external/player-value data, and complementary representations that survive both early development and recent confirmation windows.

The next private milestone completes the roster-geometry test using an explicit cold-start policy without lowering the 80-game training minimum or dropping the blocked year.

## Public/private boundary

This repository is an **employer-facing, semi-reproducible research case study**. It publishes aggregate methods, experiment outcomes, validation contracts, synthetic-safe notebook logic, provenance boundaries, and negative results.

It intentionally does **not** publish private datasets, prediction CSVs, fitted production models, exact private feature formulas, source-specific identity logic, production correction weights, credentials, or the canonical AWS workspace.
