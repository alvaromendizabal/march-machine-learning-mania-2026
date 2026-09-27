# NCAA tournament forecasting | ML engineering case study

**Alvaro Mendizabal · probability forecasting · temporal validation · cloud ML engineering**

## Current verified research boundary: 0.1051853 Brier

The strongest retained private post-competition system scores **0.1051853 Brier** on the complete 126-game 2026 men’s + women’s cohort. The published 2026 winning benchmark was **0.1097454**. The retained late score is numerically lower, but this repository is **benchmark-informed post-competition research**, not an original competition placement or claim of prospective superiority.

The active stretch target is **0.0900000**, leaving **0.0151853** absolute Brier to close.

**[Open the current frontier notebook](portfolio/frontier_research.ipynb)** · [Employer walkthrough](docs/employer_walkthrough.md) · [Current research boundary](docs/current_research.md) · [Research frontier](docs/frontier_research.md)

| Boundary | Brier | Interpretation |
|---|---:|---|
| Published 2026 winner | 0.1097454 | Original competition benchmark |
| **Retained private post-competition system** | **0.1051853** | Current research boundary |
| Latest independent chronological ensemble | 0.1281818 | Rejected |
| Stretch target | 0.0900000 | Research objective, not achieved |

## Latest milestone: auditable chronological reconstruction

The newest milestone rebuilt a clean prediction history from official competition data rather than inheriting an uncertain historical forecast bank. It produced:

- **31** matchup-difference features;
- **2,330** main-bracket historical supervised games;
- **84,376** all-pair feature rows;
- **78** recorded model fits across seed-only logistic regression, broad logistic regression, and a compact boosted-tree reference;
- **26** chronological blend checkpoints whose weights use only earlier out-of-time predictions and labels;
- **53** regression/self-tests and an executed notebook with **6 Plotly figures** plus static fallbacks;
- prospective 2027 schedule capture for **1,629 men’s** and **2,280 women’s** schedule records, with **0 completed games** correctly treated as a waiting state.

The learned blend did **not** pass promotion. Historical Brier was **0.1638382** versus **0.1634288** for the equal blend, and the frozen 2026 replay scored **0.1281818** versus the retained **0.1051853** system. This is a useful negative result: the three independently reconstructed experts are highly correlated, so more weighting sophistication does not create missing information.

## What this project demonstrates

**Point-in-time validation.** Forecast-year models use only earlier tournament labels; preprocessing and ensemble weights are fitted inside their allowed historical partitions; 2026 outcomes enter only after prediction files are frozen.

**Research judgment.** Negative experiments are retained when they close a credible direction. The latest ensemble was rejected rather than tuned against the assessment cohort.

**Reproduction discipline.** Public 2025/2026 solution mechanisms are tracked individually as adapted, validated, rejected, blocked, or still missing. Similarity of an idea is not presented as an exact reproduction.

**Data engineering.** Official results, seeds, mappings, detailed box scores, multiple strength systems, player histories, market histories, and prospective source captures are maintained privately on AWS with cutoffs, checksums, receipts, and explicit waiting/quarantine states.

**Engineering discipline.** Substantial runs are bounded, checkpointed, resumable, test-gated, and packaged with an executed notebook and evidence bundle. Private model binaries, prediction files, data, and competitive implementation details remain off public GitHub.

## Current frontier

The latest experiment shows that another blend of highly correlated team-level experts is unlikely to close the remaining gap. The highest-value missing capabilities are **new information**, especially prospectively captured player availability / injury context, stronger women-specific external ratings and player value, and genuinely complementary representations whose residuals are measurably different before blending.

The 2027 pipeline is already operating in prospective mode: raw source objects are timestamped and checksum-tracked, missing target-season data is treated as `WAITING_FOR_TARGET_DATA`, and future competition identifiers / deadlines will be mapped only when officially available.

## Public scope

This repository is an employer-facing research case study. It publishes aggregate methodology, validation design, experiment evidence, negative results, and engineering decisions. It intentionally does **not** publish private datasets, credentials, fitted production models, exact private feature formulas, candidate prediction bytes, or the full AWS research workspace.
