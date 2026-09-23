# NCAA tournament forecasting | ML engineering case study

**Alvaro Mendizabal · probability forecasting · controlled experimentation · cloud ML engineering**

## Best recorded result: 0.1089408 Brier

A checksum-verified post-competition submission achieved **0.1089408 Brier**, numerically below the published 2026 winning benchmark of **0.1097454** by **0.0008046** (about **0.73% lower Brier**).

This is a **post-competition benchmark result**, not a claim of original first place, prize eligibility, or independent prospective superiority.

| Recorded milestone | Brier | What changed |
|---|---:|---|
| Earlier scored reference | 0.1098691 | Compact reference refinement |
| Margin-ensemble champion | 0.1094899 | Rich score-margin model added to compact core |
| **Current recorded best** | **0.1089408** | Fixed BPI championship-futures information layered onto the champion |
| Published 2026 winning benchmark | 0.1097454 | External reference |

**[Employer walkthrough](docs/employer_walkthrough.md)** ·
[Evaluation boundaries](docs/current_research.md) ·
[Machine-readable milestone](reports/current_research/latest_score.json)

## Why the project is interesting

**Modeling contribution.** The strongest statistical release did not come from blindly expanding a winning feature set. A compact XGBoost win-probability core was complemented by a richer XGBoost score-margin ensemble using efficiency, shooting, possession, ratings, schedule and recent-form information. That division of labor produced the 0.1094899 scored release.

**Information contribution.** Subsequent controlled ablations showed that game-specific Round-1 market forecasts hurt this completed-tournament score, while a predeclared championship-futures tier improved it. The resulting 0.1089408 artifact changed 1,986 men’s matchup rows while preserving 130,147 rows, including all 65,703 women’s predictions.

**Research discipline.** The project retains negative results: women’s margin transfer, broad market overlays, Round-1 market blending, sparse ranking selection, robust loss, leaf readout, feature-family removal and calibration did not earn promotion. A failed hypothesis is not rewritten as a success.

**Engineering discipline.** Experiments use checksummed artifacts, protected-row contracts, restartable checkpoints, independent prediction verification, bounded fit counts and at-most-once submission logic. The latest scored run fitted **zero models**, made exactly **one upload attempt**, passed all 11 stages, and matched the score predicted by a disjoint-component Brier decomposition.

## Current system, at a glance

The retained modeling lineage combines a compact men’s XGBoost core with a richer score-margin XGBoost ensemble. The latest scored artifact then adds a fixed BPI championship-futures information tier on 1,986 men’s pairings. The detailed current training implementation, fitted models, private feature formulas, tuning recipes, raw data and AWS working state are intentionally not distributed by this public case-study update.

Earlier source code and license grants already present in Git history remain accessible. This publication does not rewrite history or claim that previously public material is confidential.

## What the score does—and does not—mean

The official 2026 winning score was **0.1097454**, not 0.09. The project’s **0.09** figure is an unachieved stretch research target. Moving from 0.1089408 to 0.0900000 would still require another **0.0189408 absolute Brier reduction**, roughly **17.4%**.

The latest component choice used post-competition leaderboard feedback to isolate two disjoint market tiers. That makes the result useful for retrospective research and portfolio evidence, but **not an independent estimate of 2027 performance**. Future claims require forecasts frozen before outcomes are known.

For 2027, the priority is prospective evaluation: timestamped pregame inputs, frozen model-selection rules, auditable season-transition checks, and predictions recorded before games occur. See [2027 readiness](docs/2027_readiness.md).

The compact reference lineage is credited to Harrison Horan’s public first-place solution. This repository presents the user’s subsequent engineering and research work without claiming ownership of public methods or an original competition win.
