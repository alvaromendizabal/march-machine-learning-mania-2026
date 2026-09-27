# Current result and evaluation boundaries

## Retained scored boundary

The current private post-competition system is **0.1051853 Brier** on the complete 126-game 2026 men’s + women’s cohort. The published 2026 first-place benchmark is **0.1097454**. The numerical comparison is favorable, but the timing matters: this is **post-competition, benchmark-informed research**, not an original leaderboard placement or prospective superiority claim.

The active stretch target is **0.0900000**, leaving **0.0151853** absolute Brier.

## Latest completed experiment

The chronological-ensemble milestone rebuilt a new historical prediction bank directly from official competition data so that training and selection lineage is auditable.

### Reconstruction

- 31 official-data matchup-difference features;
- 1,385 men’s + 945 women’s main-bracket historical labels = **2,330 supervised games**;
- **84,376** all-pair feature rows;
- main-bracket membership determined from official seed suffixes rather than a generic day cutoff;
- play-ins excluded consistently;
- historical snapshots use regular-season information through Day 133.

### Model families

Three fixed reference families were trained separately by gender:

1. seed-only logistic regression;
2. broad standardized logistic regression using the 31-feature representation;
3. compact boosted-tree probability model using a small strength/seed subset.

For each forecast year, model fitting and preprocessing use only earlier tournament seasons. Chronological blend weights use only earlier frozen out-of-time predictions and labels.

### Result

The learned blend was rejected.

| Assessment | Equal / incumbent | Chronological ensemble | Movement |
|---|---:|---:|---:|
| Historical pooled | 0.1634288 | 0.1638382 | −0.0004094 gain |
| 2026 men | 0.1357844 incumbent | 0.1568559 | worse |
| 2026 women | 0.0745863 incumbent | 0.0995077 | worse |
| 2026 combined | **0.1051853 incumbent** | **0.1281818** | **−0.0229965 gain** |

The three experts also show very high residual correlation (roughly **0.956–0.975** pairwise), explaining why learned weights do not add enough genuinely new information.

## Validation correction from the prior milestone

A previous audit found that an older correction selector had used the same later seasons in both eligibility/ranking and subsequent confirmation language. The retained score itself reproduced correctly, but that historical selection process did not support an independent-confirmation claim.

The chronological reconstruction addresses this by creating a new auditable forecast history with explicit training-year boundaries and past-only ensemble weights. Repeatedly examined 2023–2026 outcomes remain retrospective research evidence, not pristine holdouts.

## Data recreation boundary

The private AWS project independently reconstructs or operationalizes official results, seeds, team identity mappings, conferences, coaches, detailed box scores, efficiency/four-factor/shooting/tempo features, recent form, Elo/SRS/Colley/quality systems, selected rating/market histories, player-season history, roster continuity, and regular-season pregame examples.

Not every external source is complete or prospectively verifiable. Remaining gaps include complete historical predeadline BPI, contemporaneous injury/availability history, authorized proprietary player value, licensed KenPom inputs, multi-book no-vig consensus, and stronger women-specific external/player-value history.

The correct language is **point-in-time controlled, chronology-gated, cutoff-eligible, raw-first, and checksum-verified where supported**—not universally “leakage-proof.”

## 2027 prospective state

The latest run captured **1,629 men’s** and **2,280 women’s** 2027 schedule records. Neither catalog contained completed games at capture time. Official 2027 competition mappings and the final deadline are not yet available, so downstream team states correctly remain waiting states.

This is intentional. Missing future data must not be backfilled with final or later information.

## Current decision

Retain **0.1051853**. Close the highly correlated chronological-ensemble direction. Prioritize structurally new information or representations whose residuals are demonstrably complementary before another blend or submission is considered.
