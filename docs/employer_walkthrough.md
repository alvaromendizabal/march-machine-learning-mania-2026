# A two-minute review of NCAA forecasting research

**The scored incumbent achieved 0.1098691 late-submission Brier.** The latest
unsubmitted challenger improves historical men's Brier from **0.1795046 to
0.1774648**. These are different evaluation settings and must not be conflated.

Start with the [executed current research notebook](../portfolio/current_research.ipynb).
It requires no AWS access to inspect and opens with saved metrics and six charts.

## What the work demonstrates

**Research judgment.** The notebook retains failed feature-fusion, subset-selection
and correction hypotheses. Rather than continuing to rearrange features, the next
experiment changed the target to signed point margin. A matched binary-target
control identifies the contribution of the objective, not merely extra complexity.

**Validation.** Assessment uses earlier-season training, whole-season inner folds,
training-only transformations and outer-year exclusion. The fixed 25% blend and
three-seed average prevent selecting weights or favorable seeds after evaluation.
Reused 2023–2025 seasons and shared inner early-stopping/calibration data are
explicit limitations, not described as pristine holdouts.

**Engineering.** AWS experiments preserve fitted models and content-hashed fold
receipts, can resume completed work, run correctness gates, emit progress, and
package results on failure. The latest robustness run completed 360 model fits
and passed 61 regression tests. The publication layer instead performs no training:
it validates aggregate arithmetic, executes a report notebook and verifies saved
Plotly and image outputs.

**Practical evidence.** The fixed margin blend improves the core in all three years
and all three seeds. It beats the matched binary blend in two of three years,
not uniformly. The original incumbent remains untouched; the decision is a
candidate-build review, not automatic promotion.

## A deeper review

Follow the [method and provenance note](current_research.md) for the experiment
contract, publication boundary and source hashes. Inspect
[Notebook 00](../notebooks/00_data_audit_and_preparation.ipynb) and
[Notebook 01](../notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb)
for data/split engineering; [Notebook 02](../notebooks/02_feature_store_and_diagnostics.ipynb)
and [Notebook 03](../notebooks/03_model_comparison_and_diagnostics.ipynb) show the
broader earlier feature and model research. Their metrics belong to their own
lineages, not the current margin experiment.

The [older scored collection](../reports/final_results/README.md) is preserved for
traceability. Its 0.1222672 result was the best of that historical collection;
it is not the project's latest observed score. The current release intentionally
does not redistribute the entire AWS source tree, datasets or fitted model files.

## Honest completion

This is a completed, reproducible **research-report milestone**. The margin
challenger is not yet a scored 2026 prediction artifact. The next modeling decision
is to freeze and validate one candidate before separately authorizing a submission.
Nothing here claims first place, a future win, or independent confirmation from
previously consumed seasons.
