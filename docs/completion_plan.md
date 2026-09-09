# Finish the research product

This release completes the bounded official-data research product, prediction
production and reviewer handoff.
This plan defines observable completion gates instead of assigning an unsupported
quality score or completion percentage.

| Release | Deliverable | Completion gate | Status |
|---|---|---|---|
| Research release | Controlled feature studies, current model comparison, executed notebooks, audited metrics and durable archives | Current source lineage, release audit, cloud/recovery receipts and merged CI | Complete through PR #11 |
| Development portfolio | 50 candidate plans from 15 recorded procedures | Matched games, earlier-season decisions, blend reconstruction, distinct vectors, reproducible metrics and CI | Complete through PR #12 |
| Prediction production | 50 complete 2026 submission CSVs plus frozen specifications and manifests | Exact template/order, valid probabilities, swap symmetry, explicit seeded/seed-free routes, final-vector uniqueness and training through 2025 only | Complete: 50 distinct files, 33 fitted models, 344 checkpoints |
| Recovery and presentation | Versioned prediction/model archive; notebook 04 generation/review controls; concise employer walkthrough | Fresh restore, zero new fits, identical prediction bytes, all six executed notebooks published and merged-main checks | Complete in PR #15: native outputs, reviewer guide and recovery receipts; merge requires the full quality gate |

## Delivery evidence

The [production implementation](../reports/prediction_production/README.md) has
completed the generation gates below. Local archive recovery reused all 344
checkpoints without fitting, and all 33 models reproduced all 259 probability
chunks exactly. The completed archive is available with the project handoff.

The owner approved the exact archive and destination. The upload and fresh,
version-pinned S3 recovery are complete: all 344 checkpoints were reused, zero
new fits ran and all fifty CSVs remained byte-identical. See
[s3_recovery.json](../reports/prediction_production/s3_recovery.json).

Notebook 04 contains the production audit, archive restoration and frozen
generation controls. The [employer walkthrough](employer_walkthrough.md) connects
the research findings to the reference file and its lineage. All six notebooks
were executed natively and their exact outputs published with the
[handoff validation receipt](../reports/validation/production_handoff.json).
[PR #15](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/pull/15)
records final-commit validation; the required quality workflow also runs on merged
`main`. The following production requirements are satisfied:

1. Restore the verified **current expanded** feature and model archives. Reject a
   historical 124-feature matrix, stale source/configuration, or incomplete raw data.
2. Freeze concrete component choices from recorded **pre-2022 development** evidence.
   Preserve `configs/inference.json` as the reference contract. Give the portfolio
   its own explicit final-generation specification, including any training-fitted
   ensemble weights. Do not choose or tune using 2022–2025 or 2026 outcomes.
3. Fit and checkpoint each distinct training-population/model/feature-route
   combination once. Reuse it across the 50 pairings. Use identity calibration for
   the declared raw streams and the recorded blend method; do not introduce a
   leaderboard-derived temperature grid.
4. Generate all template rows in restartable chunks. Fit seed-free routes explicitly
   for teams without seeds. Validate complete files and save the recipe, population,
   input/source/configuration hashes, fitted-model identity and file checksum.
5. Archive the completed release and prove recovery from that exact remote version.
   If two final vectors are identical, report the shortfall and review the candidate
   design; do not count renamed duplicates toward 50.

The count is a delivery target, not evidence of scientific independence or improved
accuracy. These are retrospective sensitivity candidates. The catalog includes the
strongest observed development streams, but comparing 50 plans does not create a
fresh holdout or justify promoting an apparent winner.

## Employer review and acceptance

The README and walkthrough provide a two-minute overview: research question, measured
feature contribution, negative findings, validation limits and engineering evidence.
The five-notebook path supports a deeper review; notebook 05 remains an optional
appendix. Notebook 04 includes the production evidence and default-off controls.
All six canonical notebooks have native executed outputs and verified figures.

An employer can:

- Follow one prediction from official pre-tournament inputs through its fitted
  model to a validated CSV and checksum.
- Distinguish feature research, nested development evaluation, consumed benchmark
  diagnostics, final training and actual submission generation.
- Reproduce the public evidence without private cloud access, and restore the
  private trained artifacts without repeating completed fits when authorized.
- Find the current default recipe, measured limitations, tests, archived source and
  passing checks without reading historical repair discussions.

The existing `reports/submission_portfolio/` remains historical, explicitly
post-result sensitivity analysis. The current development work lives in
`reports/prediction_portfolio/`. Neither the old shortlist nor this candidate catalog
counts as 50 newly generated current-lineage CSVs. The current manifests are in
`reports/prediction_production/`; the fifty complete CSVs are in the referenced
artifact archive.

Additional timestamped player-availability or returning-production sources are a
future research extension. They are not a prerequisite for finishing this bounded
official-data product. A fresh tournament under a frozen protocol is the appropriate
future test of forecasting improvement.
