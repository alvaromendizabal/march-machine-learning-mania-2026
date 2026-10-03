# Repository publication policy

## Current direction: employer-facing evidence, private ongoing implementation

The sole current public destination remains `alvaromendizabal/march-machine-learning-mania-2026`.

Do not create additional repositories, rewrite Git history, change repository visibility, or change licensing without explicit owner authorization.

## Publish

Publish reviewed, employer-facing material that demonstrates:

- achieved project metrics and exact evaluation context;
- aggregate experiment progression;
- source-ownership and provenance states;
- temporal-validation methodology;
- numerical-reproduction evidence;
- negative-result discipline;
- cloud/research engineering;
- prospective 2027 readiness contracts;
- public-safe aggregate tables / notebooks needed to support those claims.

The public repository should make the project easy for an employer to understand without turning it into a turnkey competition implementation.

## Keep private

Do not publish:

- private row-level predictions;
- submission candidate CSVs unless explicitly approved;
- raw supplemental source archives;
- fitted competition models;
- exact private feature formulas;
- exact correction rules, thresholds, or weights;
- source-specific identity / mapping logic that exposes the private pipeline;
- credentials, tokens, environment files, or private endpoints;
- canonical AWS orchestration state;
- large private checkpoints;
- private experiment bundles.

Private repeatability is not the same as distributing a public reproduction kit.

## Benchmark / ranking presentation

Current employer-facing surfaces should present the project's own results, engineering evidence, and research progression **without competitor score comparisons or leaderboard-ranking claims**.

If a historical file or Git commit contains an older comparison, preserve Git history rather than rewriting it. New and current-facing pages should not repeat the comparison unless the owner explicitly authorizes it later.

## Semi-reproducible standard

A public employer-facing milestone should expose enough information to understand and audit:

- the official metric;
- evaluation populations;
- source provenance categories;
- experimental lifecycle states;
- aggregate result tables;
- what was reproduced versus adapted;
- what failed and why;
- what remains private.

It should not expose enough implementation detail to regenerate the current competition system exactly.

## Existing material

Previously published source and license grants remain in repository history.

This policy is prospective: it neither retracts past permissions nor makes previously public material confidential.

Removing existing public code, rewriting history, changing visibility, or changing licenses is a separately scoped operation.

## Merge discipline

Before a publication milestone is merged:

1. work on a reviewed branch;
2. verify current-facing text does not expose private implementation;
3. verify no credentials / private raw source archives are introduced;
4. verify aggregate values are internally consistent;
5. verify repository checks on the exact PR head;
6. merge only after the head being reviewed is the head being merged.

Never force-push a reviewed publication branch to bypass required checks.
