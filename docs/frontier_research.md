# Research frontier and leading-solution reproduction matrix

## Why this document exists

The project has already crossed the published 2026 winning benchmark in post-competition scoring, but the **0.09 stretch target remains materially distant**. The purpose of the frontier review is to prevent repeated small variants of an already mature system and keep each new round tied to a missing capability.

Current verified boundary:

| Boundary | Brier |
|---|---:|
| Published 2026 winner | 0.1097454 |
| Retained private post-competition champion | **0.1072824** |
| 0.09 stretch target | 0.0900000 |
| Remaining absolute reduction | **0.0172824** |

This is benchmark-informed post-competition research. It is not an original leaderboard placement.

## Leading-solution reproduction matrix

| Public mechanism | Project status | Evidence / decision |
|---|---|---|
| Compact first-place statistical tournament reference | **Adapted and validated** | Used as a compact reference system and benchmarked against richer models. |
| First-place-style score-margin supervision | **Adapted and validated** | Produced a complementary men's model and a stronger scored release. |
| Residual feature representation around the margin model | **Recreated and validated historically** | Chronology-safe family selection chose `volume_plus_differences`; a frozen 2026 challenger is built but unscored. |
| Broad all-residual representation | **Recreated and rejected for instability** | Higher mean gain, but the worst recent season breached the predeclared guardrail. |
| Third-place-style championship futures information | **Adapted retrospectively** | Helpful in scored post-competition research, but the 2026 raw pre-deadline capture chain is not independently verified. |
| Broad / Round-1 market overlays | **Recreated and rejected** | Both lost against the retained system in controlled late-score tests. |
| Fourth-place calibration / post-processing ideas | **Recreated and rejected** | Did not become a retained scored improvement. |
| Women's richer margin extension | **Recreated and rejected** | Historical improvement did not transfer to the scored candidate. |
| Tree-leaf probability readout | **Recreated and rejected** | Did not justify promotion. |
| Sparse ranking-selection variants | **Recreated and rejected** | Did not become the strongest system. |
| Prospective Kalshi collection | **Operational** | Raw-first scheduled snapshots for men's and women's title markets. |
| Prospective ESPN collection | **Operational but target-season gated** | Stale-season rows are archived but excluded from eligible model tables. |
| Prospective BartTorvik ratings / schedule collection | **Operational for men's data** | Raw-first men's team-ratings and schedule capture. |
| Roster continuity / transfer-value signal | **Not yet validated** | High-value information gap for the prospective system. |
| Injury / player-availability signal | **Not yet implemented** | Requires timestamped, competition-compliant source data. |
| Heterogeneous OOF stacking across genuinely different model families | **Not yet validated** | High-priority structural ensemble gap. |

The matrix is intentionally conservative. A public solution is not marked “recreated” merely because its idea was discussed or a similar feature exists somewhere in the repository.

## Latest structural advancement

The nested-residual milestone added a capability the previous system did not have: **chronology-safe representation selection under a stability constraint**.

Eight coherent residual families were compared using historical seasons only. The selected `volume_plus_differences` representation achieved **0.0037810 Brier improvement** over the base margin reference across the six-season selection window and improved **5 of 6** seasons. Its worst season moved by **-0.0011233**.

The full 31-feature residual panel achieved a larger mean gain of **0.0049982**, but its worst season deteriorated by **-0.0031222**, violating the promotion gate. It was rejected.

That rejection matters more than the raw leaderboard of candidate representations: it demonstrates that the project is now optimizing not only for average fit but for **transfer stability across seasons**.

## Frozen challenger boundary

The resulting no-submit 2026 challenger:

- contains 132,133 unique prediction IDs in the official order;
- changes 2,278 approved men's rows;
- preserves 129,855 rows byte-for-byte;
- preserves all 65,703 women's rows byte-for-byte;
- uses no 2026 tournament outcomes for model selection or training;
- uses no futures inputs for residual training or configuration selection;
- passed 12 model/integrity checks;
- retained six inline Plotly outputs after notebook reopen;
- remains unscored.

The candidate is therefore a valid score-gate experiment, not yet a new champion.

## Provenance boundary for the 2026 market layer

The 2026 pairwise and blending transformations were independently rebuilt, but the original historical futures observations were pinned from a public post-competition artifact rather than reconstructed from raw timestamped pre-deadline API responses.

For that reason, the 2026 market layer is treated as a fixed retrospective component. It is not used as evidence of prospective leakage safety, and it is not used to choose the residual representation.

The 2027 collector architecture is designed to eliminate this ambiguity: raw-first objects, capture timestamps, source URLs, checksums, immutable run manifests, target-season validation, and eventual cutoff freezing.

## What must improve to approach 0.09

A 0.1072824 → 0.09 move is too large to justify a strategy based on more micro-variants of the same margin model. The remaining research backlog is therefore structural:

1. **Score the exact frozen residual challenger once.** This determines whether chronology-safe historical gain transfers to 2026.
2. **Run error decomposition against the promoted champion.** Men vs women, round, seed disparity, confidence, favorite/upset, market tier, and challenger disagreement should identify where Brier is still concentrated.
3. **Rebuild the women's system as its own research problem.** The prior transfer attempt failed; women should not remain an untouched legacy component indefinitely.
4. **Add prospective roster continuity, transfers, and player availability.** These represent information unavailable to the current historical feature system.
5. **Evaluate a heterogeneous OOF ensemble.** Blend or stack only models with demonstrably complementary errors, using out-of-fold predictions rather than evaluation-set weight fitting.
6. **Keep the 2027 process prospective.** Freeze model/data identities and predictions before outcomes so future evidence can support a genuine generalization claim.

## Public/private publication boundary

This document publishes aggregate methodology, evidence, negative results, and the research backlog. It intentionally does not publish the current private training pipeline, exact production feature formulas, fitted models, candidate prediction bytes, private datasets, credentials, or AWS working state.

That boundary keeps the repository useful to employers and technical reviewers while preserving an actively evolving research system.
