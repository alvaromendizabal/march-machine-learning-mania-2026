# Current result and evaluation boundaries

## Retained scored boundary

The current private post-competition system remains **0.1051853 Brier** on the complete 126-game 2026 men's + women's cohort. The published 2026 first-place benchmark is **0.1097454**.

The numerical comparison is favorable, but the timing matters: this is **post-competition, benchmark-informed applied ML research**, not an original competition placement or a prospective generalization claim.

The active stretch target is **0.0900000**, leaving **0.0151853** absolute Brier.

## Post-release research program

Since the previous public release, the private AWS research program expanded in two directions simultaneously:

1. **new data and provenance layers** — player, shot-context, possession, roster, schedule, and prospective source captures;
2. **strictly matched model tests** — control vs augmented comparisons with fixed gates and earlier-year-only fitting.

The retained champion did not change. Several credible directions were closed cleanly rather than tuned until they looked favorable.

## Major reconstructed data layers

| Layer | Verified scale | Boundary |
|---|---:|---|
| Advanced-context regular-season games | 154,657 | Source-reconstructed, independently matched to official games |
| Daily pregame examples | 167,143 total / 86,929 eligible | Same-day state frozen before the current game |
| Possession-level lineup records | 12,397,243 across 88,079 games | Provider-reconstructed lineups; not raw ground truth |
| Historical roster attributes | 125,657 observations | Retrospective attributes; original predeadline publication time not certified |
| Scoped CSV registry | 4,318 hashed paths | 903 match discovered reconstruction receipts |
| Frozen 2027 preseason reference forecasts | 99 men's / 366 women's | Preseason research priors, not tournament submissions |

Counts above describe different grains and should not be summed as independent observations.

## Model findings since the previous public release

### Corrected player-impact exposure

After fixing the exposure denominator and protected-row handling, development improved by **0.0006080 Brier**, but pooled confirmation worsened by **0.0003626**. Rejected.

### Shot-context reconstruction and transfer

A broad source-recovery pass increased advanced-context coverage to 154,657 games. The tournament-only correction still failed: development moved by **-0.0000445** and pooled confirmation by **-0.0002799**.

A separate daily pregame experiment found a real regular-season gain of **+0.0008394** across 19,205 held-out games, but tournament confirmation moved by **-0.0001033**. This is an important domain-transfer result: useful regular-season signal did not automatically translate into tournament improvement.

### Possession and lineup research

The possession pipeline validated 88,079 games and 12.4 million possession rows and completed 48 player-effect fits. The fixed later-regular-season holdout formulation was slightly worse, and tournament profile coverage was insufficient for the planned correction. The data layer is retained; the fixed model direction is closed.

### Cross-season player-origin signal

The cross-season origin correction improved 2023, 2024, and 2025, with pooled recent confirmation **+0.0009086**, but development improved only **+0.0001023**. The predeclared development threshold was not met. Rejected.

### Residual fusion

A past-only combination of distinct corrections improved development by **+0.0011638** and recent confirmation by **+0.0004496**. The confirmation requirement was +0.0005, so it remained below the promotion line by roughly 0.0000504. Rejected without changing the gate.

### Joint 33-feature representation

A matched linear/nonlinear model using the reconstructed origin + shot-context representation improved recent confirmation by **+0.0008437**, but development deteriorated by **0.0008591**. Rejected.

### Roster geometry

The roster-attribute reconstruction produced 125,657 rows and 25,524 cutoff profiles. The first model run fitted nothing because women's 2018 had **67 eligible prior games** against the fixed minimum of 80. The direction is **blocked, not rejected**. The next private milestone uses an explicit cold-start policy that leaves that fold unchanged while keeping every assessment game in the score.

## Provenance boundary

The project uses several different evidence standards:

- **receipt-matched reconstruction:** current bytes match a recorded reconstruction recipe;
- **temporal eligibility:** the feature contract admits only observations satisfying the forecast cutoff;
- **historical publication provenance:** whether a source snapshot can be proven to have existed before the original forecast;
- **predictive evidence:** whether a fixed, matched comparison improved its assessment window.

These are not interchangeable. A hash alone is not a leakage claim. A retrospective roster archive can be useful for research without being labeled prospectively verified.

## Remaining external gaps

The private system still lacks complete point-in-time versions of several inputs used or approximated by leading systems: historical predeadline BPI, contemporaneous player availability/injury information, authorized proprietary player-value data, licensed KenPom inputs, multi-book no-vig consensus, and stronger women-specific external/player-value history.

These are kept as explicit gaps. The project does not relabel reconstructed box-score or roster proxies as equivalent sources.

## 2027 state

The 2027 machinery is functioning but intentionally incomplete. The project has frozen 465 preseason reference forecasts and retained roster/schedule captures as dated observations. Missing target-season sources remain waiting states. Official tournament mappings, bracket, seeds, and final deadline are not guessed.

The next stronger generalization claim must come from forecasts frozen before genuinely future outcomes.
