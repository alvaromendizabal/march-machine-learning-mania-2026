# Round 16 data-quality repair / round 17 packaging repair

## Observed evidence
- Round 16: first training season accepted; remaining preparation stopped on an inconsistent steal/turnover identity. The notebook does not give every affected raw row or establish the upstream cause.
- Round 17: scientific report and ten charts saved before its last combined-packaging cell failed. Mean primary Brier delta −0.00047146586103651716, 3/4 improvements, worst deterioration +0.0016402616886424803; decision DO_NOT_PROMOTE.

## Revised turnover evidence policy
Determine `bad = (WStl > LTO) OR (LStl > WTO)` after compact/detailed identity validation and season/day filtering. Exclude both orientations of bad physical games from both turnover-rate targets and their direct-rate controls. Do not edit raw values, base reference snapshots, or tournament training/evaluation games. Save all affected identities privately, aggregate by season and seeded team, then stop if >1% of season games or >5% of a seeded team's games are removed. Minimum seeded opportunity support remains 50. These limits are fixed safety choices, not fitted to outcomes.

This policy changes what evidence goes into the rate estimators and therefore gets a new fingerprint. It does not pretend to know corrected box scores. Report potential exclusion bias and retain counts. A high exclusion rate requires source investigation, not automatic deletion.

## Checkpoint reuse
The old folder is untouched. Migration accepts only the previously completed 2013 outputs when the original source pins, data, environment, upstream artifacts and relevant mathematical functions match, and the audit confirms zero affected 2013 games. Copy and verify file hashes; do not recompute ratings or declare edited checkpoints compatible. Reject conflicting destination checkpoints.

## Experiment
Same four adjusted features, four direct controls, six configurations and later-era splits. Complete the old question before new hypotheses. A negative result is still a completed scientific artifact.

## Reporting
Individual round 17 remains usable without round 16. The top-level collector labels partial collections and never converts missing evidence into a success claim. Prepared code is statically reviewed only; the user test gate and actual audit must pass.
