# NCAA forecasting: a two-minute employer walkthrough

**The current recorded late submission scored 0.1094899 Brier.** It is numerically
below the published 0.1097454 first-place benchmark, but is a retrospective late
submission—not an original competition placement or proof of prospective superiority.

Start with the [executed research case study](../portfolio/current_research.ipynb).
It opens with saved tables and eight charts without requiring AWS access.

## Research judgment

The notebook retains negative full-bundle, residual-PCA, nested-subset and correction
experiments. The useful change was to learn actual winning margins in a complementary
model. Matched binary-target controls, fixed blending, whole-season validation and
predeclared seeds separate the hypothesis from opportunistic selection.

The men's historical robustness gain survived three years and three fixed seeds.
A 66-fit candidate build then produced one Kaggle submission, reference 56447505.
The improvement was 0.0003792 versus the previous scored incumbent. Protected-row
checks kept all 65,703 women's prediction lines unchanged.

## The latest research

A separate women's margin experiment completed 48 fits, 46 regression tests and seven
execution stages in 18.80 seconds. Historical Brier improved from 0.1405293 to 0.1387757
on 504 main-bracket games, with six of eight seasons improving. It passed the screen;
it has not been submitted. Fuller-ensemble validation is the next explicit decision.

## Engineering to inspect

The report is reproducible from compact committed aggregates. It verifies score identity,
metric arithmetic, evaluation populations, source hashes, clean-kernel execution, saved
Plotly outputs and image fallbacks. The AWS workflows separately retain checkpoints,
resource guards, exact experiment policies and failure diagnostics. This publication
performs no model training and does not pretend to mirror the complete AWS training tree.

For deeper review, follow the [methods note](current_research.md),
[data audit](../notebooks/00_data_audit_and_preparation.ipynb),
[split protocol](../notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb),
[feature diagnostics](../notebooks/02_feature_store_and_diagnostics.ipynb), and
[model comparison](../notebooks/03_model_comparison_and_diagnostics.ipynb).
Earlier notebooks and the original scored collection retain their own model lineages.

## Honest completion

The scored men's release and this evidence publication are completed milestones.
The women's extension is a passed historical screen, not a deployed model. Repeatedly
used development years, sequential hypothesis selection, and shared inner early-stopping
and calibration scores limit inference. Additional seeds do not create independent
tournaments. The repository shows what improved, what failed and what is still unknown.
