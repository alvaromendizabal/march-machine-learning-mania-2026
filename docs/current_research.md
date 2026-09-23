# Current result and evaluation boundaries

## Retained scored release

Retain post-competition submission **56479241**, **0.1089408 Brier**, prediction SHA-256
`b10aeddf304ca6f5e2c6f749ce4a792210ac554f6a99bb6d8b68aeabbfe110d9`.

The published 2026 first-place benchmark is **0.1097454**, so the retained late score is numerically lower by **0.0008046**. This does not establish an original competition placement or prospective superiority.

## How this release emerged

The prior margin-ensemble release scored **0.1094899**. Two subsequent market experiments were intentionally separated:

- full market overlay: **0.1098037**, rejected;
- Round-1-only market overlay: **0.1103527**, rejected.

Those scored variants changed disjoint components. Their exact row sets made the championship-futures component algebraically identifiable before it was uploaded. The inferred score interval was approximately **0.10894075–0.10894105**; the frozen futures-only candidate then scored **0.1089408**, consistent with that decomposition.

This is unusually strong internal consistency, but it is still **post-hoc component selection using post-competition leaderboard feedback**. It is not an independent test or evidence that the same mechanism will improve 2027 forecasts.

## Latest run integrity

The successful run finished in **30.66 seconds** and performed:

- zero tree fits;
- zero probability-model fits;
- one submission upload attempt;
- zero automatic follow-up submissions.

The candidate contained **132,133 unique IDs**, changed exactly **1,986 men’s rows**, and protected the other **130,147 rows**, including all **65,703 women’s rows**. The previous 0.1094899 artifact remained unchanged.

## Research status

The project has recreated or adapted mechanisms from multiple leading public solutions, but it does not claim complete parity with every archived top submission. Important negative findings remain part of the research record: broad feature fusion, nested binary feature selection, a women’s margin extension, alternative robust loss, tree-leaf probability readout, fourth-place calibration, sparse ranking selection, the full market overlay, and Round-1-only market information did not become retained scored improvements.

The strongest private system now contains three high-level capabilities:

1. a compact statistical tournament reference;
2. a complementary men’s score-margin ensemble;
3. a bounded men’s championship-strength information layer.

Details sufficient to regenerate the current private system are intentionally not added to this public report.

## Evaluation boundary

The 2026 competition is complete. The retained score was obtained during post-competition late-submission research after public solution information and prior score feedback were available. It should therefore be described as **post-competition benchmark-informed applied research**, not as an original leaderboard result.

The next stronger generalization claim must come from forecasts frozen before genuinely future outcomes. The 2027 readiness plan should preserve timestamped inputs, model identities, prediction hashes, and a predeclared evaluation procedure.
