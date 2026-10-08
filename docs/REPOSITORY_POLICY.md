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

## External comparison presentation

The owner explicitly authorized a sourced comparison with the official winning score on October 8, 2026. Current pages may report the exact numerical difference while placing the late-submission, inspected-outcome setting alongside the result. Do not imply an official rank, prospective superiority, statistical significance, or unsupported causal attribution. Credit the original method and describe its documented scope respectfully. Private score targets and private implementation remain outside the public narrative.

Historical comparisons remain preserved in Git history. The current result source is portfolio/release_evidence.json and its sanitized submission receipt.

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
