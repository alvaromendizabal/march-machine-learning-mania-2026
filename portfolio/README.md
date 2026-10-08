# NCAA probability forecasting: portfolio evidence

**Alvaro Mendizabal · probability modeling · temporal validation · source provenance · AWS/SageMaker**

The latest confirmed Kaggle late submission scores **0.1067095 Brier**, compared with the official winner's **0.1097454**: **0.0030359 lower, or 2.77% less probability loss**. This is a meaningful numerical reduction in the measured loss, not a 2.77-point increase in accuracy.

The official deadline was March 19, 2026; the project submitted this result on October 8 after outcomes were available. It is a retrospective improvement, not an official competition victory. The score alone does not establish statistical significance or isolate which method caused the improvement. [Read the comparison and its scope](../docs/benchmark_comparison.md).

## Delivered result

| Evidence | Value | State |
|---|---:|---|
| v54 forecast / v93r1 delivery | **0.1067095 Brier** | Confirmed; both displayed score fields |
| Submission size | **132,133 rows** | Accepted artifact |
| Corresponding local audit | **0.1067095543 Brier** | Retrospective; 126 scored games |
| Earlier v26 control | **0.1206458 Brier** | Historical submitted control |

The submitted system adapts the men's probability composition and retains the women's reference baseline. Public methods, including Harrison Horan's, receive explicit credit. This portfolio distinguishes independently engineered adaptations and reproduction work from the underlying public ideas.

## Engineering depth

- **Broad source foundation:** 42 men's and 29 women's official raw seasons, represented by 13,753 and 9,851 team-season rows, with independent raw-to-feature replay.
- **Numerical reconstruction:** 65,703 women's probabilities within 1e-4 of an archived reference; matched-input reproduction of 66 men's core and 66 margin members.
- **Complete historical accounting:** all 558 archived men's control predictions reproduced, then eight legitimately omitted games restored for a 566-game cohort.
- **Source qualification:** original receipts, timestamps, hashes, identity namespaces, and explicit missingness instead of substituting unverified values.
- **Reliable execution:** self-tests, bounded concurrency, checkpoint integrity, resumable stages, and validated output bundles on AWS/SageMaker.
- **Research judgment:** plausible experiments are retained as negative evidence when they fail declared historical requirements.

## Current frontier

v99 is delivered and awaits the owner's actual return. It audits the exact historical cache and tests an original-source boxscore route across 60 games and 20 gender-season groups. It is a source qualification milestone, not a new submission.

Broad original player/availability histories, dated market and BPI coverage, and prospective 2027 execution remain open. The earlier derived NCAA player bank is not represented as original ESPN data. Partial source coverage is not presented as a finished predictive feature.

## Review path

1. [Start here](../START_HERE.md): project overview and review order.
2. [Benchmark comparison](../docs/benchmark_comparison.md): result, arithmetic, credit, and evaluation conditions.
3. [Executed review notebook](verified_result.ipynb) or [audit CLI](reproduce_release.py): reproducible aggregate checks without private training artifacts.
4. [Employer walkthrough](../docs/employer_walkthrough.md): technical contributions and interview discussion.
5. [Reproduction matrix](../docs/reproduction_matrix.md): demonstrated mechanisms and remaining gaps.
6. [2027 readiness](../docs/2027_readiness.md): prospective execution contract.
7. [Release evidence](release_evidence.json): machine-readable current-release facts.
8. [Disclosure](DISCLOSURE.md): publication and reproducibility boundaries.

Earlier files in this directory preserve research snapshots. Their historical lifecycle labels do not override the current release evidence or [current research boundary](../docs/current_research.md).

The public layer exposes reproducible review procedures and aggregate evidence. It withholds private row-level predictions, fitted models, raw supplemental archives, and exact competition composition rules. The public audit does not rerun the exact private forecasting pipeline.
