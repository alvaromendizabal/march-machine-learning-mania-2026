# Post-merge research log | September 27–28, 2026

This log summarizes the major private AWS milestones completed after the previous employer-facing GitHub release. It publishes aggregate evidence only.

## Research timeline

| Milestone | Status | Key evidence | Decision |
|---|---|---|---|
| Corrected player-impact exposure | Rejected | Dev +0.0006080; confirmation -0.0003626 | Exposure definition fixed; signal did not transfer |
| Shot-context recovery | Rejected | 154,657 verified games; dev -0.0000445; confirmation -0.0002799 | Coverage solved; tournament gain absent |
| Daily shot-context transfer | Rejected | 167,143 pregame rows; regular-season +0.0008394; tournament -0.0001033 | Useful regular-season signal, failed tournament transfer |
| Lineup-stint pilot | Implementation blocked | Pilot admission exposed incompatible duration assumption | Replaced with possession-grain design |
| Possession-lineup reconstruction | Data retained / fixed model closed | 88,079 games; 12.4M possessions; 48 effect fits | First holdout formulation did not pass |
| Data-readiness registry | Completed | 4,318 hashed CSV paths; 903 receipt matches | Replaced stale inventory with file-level evidence |
| 2027 launch reference | Completed | 99 men's + 366 women's frozen preseason forecasts | Prospective infrastructure operational |
| Cross-season player-origin correction | Rejected | Dev +0.0001023; recent +0.0009086 | Recent gain insufficient without development support |
| Residual-source fusion | Rejected narrowly | Dev +0.0011638; recent +0.0004496 | Missed +0.0005 recent gate by ~0.0000504 |
| Joint 33-feature representation | Rejected | Dev -0.0008591; recent +0.0008437 | Recent improvement did not offset development regression |
| Roster geometry reconstruction | Blocked | 125,657 roster rows; 25,524 cutoff profiles; 67 prior games in women's 2018 | Data retained; historical completion pending cold-start policy |

Positive gain means lower Brier relative to the matched baseline.

## Validation lessons

### Recent strength must agree with earlier evidence

Two post-release models looked promising in 2023–2025 but failed earlier development windows. The project keeps the original promotion criteria rather than redefining success after seeing the assessment.

### A source can be useful without transferring to the tournament

Shot-context features improved later regular-season prediction but did not improve tournament confirmation. The data layer remains reusable while the tested transfer rule is closed.

### Provenance is multi-dimensional

A file may be hash-verified without having a discovered reconstruction recipe. A reconstructed historical source may still lack proof that the same observation existed before the original forecast. A prospectively captured source may still be ineligible for a model because the competition mapping or cutoff does not yet exist.

The public documentation keeps these states separate.

## Engineering lessons

- expensive raw acquisition and reconstruction are checkpointed separately from model fitting;
- failed gates stop later stages before candidate construction;
- protected prediction rows are verified byte-for-byte before a candidate is considered;
- new feature families are compared against identical-row controls whenever possible;
- missing 2027 data produces explicit waiting states rather than fabricated replacements.

## Current next milestone

The roster-geometry dataset is fully reconstructed, but one early women's fold had 67 prior eligible games versus the fixed minimum of 80. The next private run uses an explicit cold-start policy: keep that fold's reference probabilities unchanged, keep every game in the score, and fit only folds with sufficient earlier history.

That is a new documented evaluation protocol. It does not retroactively pass the blocked run or lower the training minimum.
