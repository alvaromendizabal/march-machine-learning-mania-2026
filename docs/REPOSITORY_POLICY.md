# Repository publication policy

## Current direction: employer-facing evidence, private ongoing implementation

This policy supersedes earlier instructions to publish the full evolving research
implementation. The sole current public destination remains
`alvaromendizabal/march-machine-learning-mania-2026`; do not create extra repositories
or change repository visibility without explicit owner authorization.

Publish only reviewed case-study narrative, achieved scores, aggregate comparisons,
appropriate attribution, engineering evidence, and executed report notebooks. Report
code may validate/render the approved aggregates, but it must not add the current
training pipeline, private feature formulas, parameter recipes, model binaries,
private datasets, environment directories, credentials or AWS working changes.
Do not add public retraining tutorials or promise full reproduction of the system.

Retain private source versions, data hashes, tests and checkpoint receipts for the
owner's debugging, audit and future competition work. Private repeatability is not
the same as distributing a public reproduction kit.

## Existing material

Previously published source and license grants remain in the repository and its
history. This change is prospective: it neither retracts past permissions nor makes
existing public material private. Existing MIT and third-party notices are unchanged.
Removing public code, rewriting history, changing visibility or licensing would be
a separate scoped operation, not an implied side effect of updating the case study.

Never force-push, bypass required checks, reset the AWS workspace, or publish
unreviewed files. Preserve original evidence; distinguish scored releases, historical
research, prepared code and future plans. New publication changes require a reviewed
branch, tests and exact-head checks before merge.
