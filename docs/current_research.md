# Current result and evaluation boundaries

## Retained scored boundary

Retain post-competition submission **56500599** at **0.1072824 Brier**. The retained prediction artifact is checksum-tracked privately as
`36bdd994ffbe675550521b6e3149ef37cf3f1845816b57cfa82ab899739e831b`.

The published 2026 first-place benchmark is **0.1097454**, so the retained late score is numerically lower by **0.0024630**, approximately **2.24% lower Brier**. This does not establish an original competition placement or prospective superiority.

The active stretch target is **0.0900000**. The remaining absolute reduction is **0.0172824**. That gap is large enough that ordinary parameter nudges and near-duplicate feature variants are no longer the primary research strategy.

## Latest unscored frontier candidate

Run `20260924T041114549348Z-2633` completed a frozen nested-residual candidate build. It did **not** make a Kaggle submission.

The pre-2026 selector compared eight coherent residual representations using season-grouped historical evidence. The selected family was `volume_plus_differences`:

- aggregate Brier gain versus the base margin reference: **0.0037810**;
- recent selection seasons improved: **5 of 6**;
- worst single-season movement: **-0.0011233**;
- known 2026 tournament outcomes used for selection or training: **none**;
- futures/market inputs used for selection or training: **none**.

The larger `all_residual` family produced a higher aggregate mean gain (**0.0049982**) but failed the predeclared stability guardrail because its worst season deteriorated by **0.0031222**. It was rejected rather than promoted on the basis of mean performance alone.

This candidate therefore represents a new capability: chronology-safe selection of a complementary residual representation under an explicit stability constraint. It is **not** yet a scored improvement.

## Candidate integrity

The candidate-build milestone performed **90 new tree fits** and produced a 132,133-row frozen challenger with checksum
`d3f1be06bba2328f8747c24d907f75af9109da82d0d3692ba9d991b49ff065c4`.

Its scope contract passed:

- **2,278** approved men's rows changed;
- **129,855** rows remained byte-identical;
- all **65,703 women's rows** remained byte-identical;
- candidate/template ID order was preserved;
- **12 model/integrity tests** passed;
- the executed candidate notebook retained **6 inline Plotly outputs** after reopen;
- no automatic submission occurred.

The scored champion remains **0.1072824** until the exact challenger is separately scored.

## Futures provenance boundary

The 2026 blend and pairwise transformation logic were independently recreated and the resulting artifacts were checksummed. However, the original 2026 market observations were pinned from a post-competition public repository rather than independently rebuilt from timestamped raw pre-deadline API responses.

Accordingly, those observations are classified as **pinned post-competition reproduction, not prospectively verified**. They may remain a fixed opaque component in retrospective research, but they are not used to fit the residual model or choose its configuration. They do not establish a prospective leakage-safety claim for 2026.

The prospective 2027 standard is stronger: raw responses first, immutable timestamped snapshots, explicit season validation, source checksums, and a final cutoff freeze that refuses stale or post-cutoff substitution.

## Research status

The project has recreated, adapted, or tested multiple leading public mechanisms, but it does not claim exhaustive parity with every archived solution. Important negative results remain visible: broad feature fusion, nested binary selection, a women's margin extension, alternative robust loss, tree-leaf readout, fourth-place calibration, sparse-ranking selection, broad market overlays, and unstable all-residual representations were not promoted as the strongest system.

The private research system currently combines four high-level capabilities:

1. a compact statistical tournament reference;
2. a complementary men's score-margin ensemble;
3. a bounded championship-strength information layer;
4. chronology-safe residual-family selection and a frozen no-submit challenger.

The next frontier is structural: score the exact frozen challenger once, then use the result to decide whether to promote it or move directly to women-specific reconstruction, roster/availability information, and a leakage-safe heterogeneous OOF ensemble.

## Evaluation boundary

The 2026 competition is complete. All retained scores described here were obtained during post-competition research after public solution information and prior score feedback were available. They should therefore be described as **post-competition benchmark-informed applied ML research**, not as original leaderboard results.

The next stronger generalization claim must come from forecasts frozen before genuinely future outcomes. The 2027 program is designed around that prospective standard.
