# Public-solution reproduction program

This research area preserves two distinct tracks:

1. **Reference-exact**: reproduce a public solution's published feature definitions,
   estimator family, hyperparameters, validation, calibration, ensembling and
   post-processing as faithfully as the available source permits.
2. **Adapted challenger**: change one component at a time under this repository's
   leakage-safe evaluation protocol.

Reference-exact results never overwrite the historical submission portfolio.
Existing submission-producing routes remain frozen and reproducible.

## First-place source pin

- Repository: `harrisonhoran/kaggle-march-mania-2026-1st-place`
- Commit: `c4db013f88cf14a036ed4881bbffb05845f5bcd1`
- Reported final Brier: `0.1097454`
- Public license: MIT
- Exact dependency pins: `first_place_requirements.txt`

The clean-room module re-expresses the published mathematics and training
configuration. The pinned public repository remains the gold-source reference
for score/byte reproduction.

## Research rules

- Never use known 2026 tournament outcomes for model selection or tuning.
- Keep `first_place_exact` and adapted variants separately named.
- Record source commit, environment versions, input hashes and feature coverage.
- Preserve published quirks in the exact route; test corrections only as
  separately named adapted variants.
- Treat current-season external inputs separately from historically reproducible
  external inputs.
