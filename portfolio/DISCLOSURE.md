# Publication and evaluation disclosure

## Current result

The current confirmed result is **v54 forecast, delivered through v93r1: 0.1067095 Brier**, accepted by Kaggle as a late submission on October 8, 2026. Both displayed score fields match. The corresponding local 126-game audit is **0.1067095543**.

The official winning score was **0.1097454**, from predictions submitted by the March 19 competition deadline. The numerical difference is **0.0030359**, or **2.77% lower Brier loss**. Because this project submitted after outcomes were known and inspected, the comparison does not establish an official victory, an equal-information contest, statistical significance, or prospective superiority. Historical fold metrics use different populations and are not interchangeable with the submission score.

The [benchmark comparison](../docs/benchmark_comparison.md) and [release evidence](release_evidence.json) are the current references. Earlier snapshots reporting 0.1222672 or identifying the 0.1067 reconstruction as unsubmitted describe earlier lifecycle states.

## Attribution and contribution

Public forecasting work, including Harrison Horan's, informed the project. The submitted composition adapts the men's probability system and retains the women's reference baseline. I built and integrated source qualification, matched-input model checks, validation repairs and cloud execution around the retained forecasting system. These are my project contributions; the underlying credited methods are not presented as my inventions.

The measured score belongs to the complete submitted composition. Individual changes are not assigned causal credit without matched ablation evidence. Likewise, reproducing archived predictions does not certify every original source's timing.

## Reproducibility scope

The public repository provides aggregate evidence, reviewable metric and validation contracts, architecture, documented source lineage, and reproduction procedures. The [notebook](verified_result.ipynb) and [audit CLI](reproduce_release.py) reproduce aggregate checks; they do not train the private system or regenerate its prediction rows. Exact private replay requires retained inputs, configurations, models, and prediction artifacts.

Private prediction rows, fitted competition models, raw supplemental archives, detailed private feature/correction rules, weights, credentials, and cloud orchestration state are intentionally withheld. Publicly exposed historical code retains its existing scope and license; this disclosure does not promise that all previously public methods have become private.

Derived third-party NCAA player records are not relabeled as original-owned ESPN records. Original response acquisition, source timing, identity mapping, and model admission are separate checks. The latest inspected execution return, v128 on October 10, 2026, ended SOURCE_PARTIAL: 2,258 market-quote rows repaired and 1,075 still missing, with model admission false and zero fits, inferences, candidates or submissions. The [sanitized receipt](latest_execution.json) records the inspected-return scope; it is not a claim about uninspected live AWS files. Earlier v99 snapshots remain dated historical records.

## Public demo boundary

[Tournament Lab](../docs/public_demo.md) uses eight authored fictional teams, a transparent rating-to-probability rule and a small authored synthetic scoring sample. Its exact bracket calculation is exact only under those declared assumptions. It is not the private forecast, a trained model, calibrated NCAA evidence or a prospective test. Interactive parameter changes are exploration, not independent repeated validation.

## Prospective boundary

The 2022–2025 benchmark and 2026 outcomes have been consumed. Complete 2027 readiness requires actual incoming-season data and a frozen pre-outcome run under the [readiness contract](../docs/2027_readiness.md). Historical source replay and a lower retrospective score are not substitutes for that evidence.

Earlier presentation snapshots remain in Git history for provenance. Existing MIT and third-party notices remain unchanged.
