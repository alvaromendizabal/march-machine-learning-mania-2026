# Completed release gates

The official-data research, final prediction delivery, score reconciliation and
employer presentation are complete. The final observed best Brier is **0.1222672**.

| Gate | Completed evidence |
|---|---|
| Data and temporal integrity | Official snapshot coverage, game uniqueness, day-132 cutoffs, training-only screening and target histories |
| Feature research | 3,106 basketball/coach/conference hypotheses plus 840 ranking definitions; add/remove-family, capacity and ranking-system comparisons |
| Model comparison | Four model families, temporal selection, calibration, blends, matched metrics and retained negative findings |
| Production and recovery | Original 50 files, 33 fitted estimators, 344 verified recovery checkpoints and exact saved-model replay |
| Bounded refinements | Eight probability/blend adjustments, six men’s challengers and six women’s challengers; pre-2026 fitting and preserved model identities |
| Submission results | All 70 current files scored, 12 final observations recorded, eight overlapping screenshot scores cross-checked and 18 legacy observations retained |
| Final model | Pooled men’s XGBoost T=0.90 + women’s conference logistic C=1.0, T=1.10; both displayed Brier columns 0.1222672 |
| Employer handoff | Concise README, exact winner trace, interactive Plotly report, static GitHub previews and executed canonical notebooks |
| Repository release | Source and native outputs committed through a feature branch/PR; exact proposed revision must pass the required quality workflow before merge |

The final [score report](../reports/final_results/README.md),
[collection receipt](../reports/final_results/collection.json),
[storage receipt](../reports/final_results/storage.json) and
[native notebook receipt](../reports/validation/final_results.json) define the
release’s concrete artifacts. The PR records the exact tested commit and merge.

## Reproducibility contract

- The original frozen inference reference remains unchanged. The final observed
  leaderboard winner is reported as retrospective, with no prospective rank claim.
- Every saved submission retains its original bytes and unique model filename.
  Packaging and publication reuse completed work and do not trigger new fitting.
- Default notebook review is read-only for training and submission generation.
  Explicit controls support authorized recovery or reproduction.
- Official game-weighted Brier and mean-season Brier retain their population and
  protocol labels. The already-consumed benchmark is not presented as a fresh holdout.
- Source/configuration/input hashes, versioned private model archives, UTC logs,
  heartbeats, failures and checkpoint recovery remain part of the delivered product.

There are no remaining required modeling or submission steps for this release.
Additional timestamped player-availability sources and future-tournament validation
are separate research extensions.
