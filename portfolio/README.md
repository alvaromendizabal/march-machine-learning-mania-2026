# NCAA probability forecasting: portfolio evidence

**Alvaro Mendizabal · probability modeling · temporal validation · source provenance · AWS/SageMaker**

The featured result is **0.1034347 retrospective Kaggle Brier**, submission 57122407. [Current score and context](../docs/champion_result.md). The [engineering review](engineering_review.ipynb) adds executed coverage analysis and a synthetic recovery demonstration.

The **October 30 V350 owner replay (Pacific)** reused **302 fitted operations** with **zero new fits** and **925 matched physical games**. The accepted control remains selected and the whole run remains **PARTIAL**. Odds reconciliation improved 34.37%, while total time grew 31.93% with consolidation. Unknown sources fell to 71; all 3,482 new selections are current-endpoint records without historical snapshots. Cleanup released 0.367 GB and moved 472 notebooks/HTML files; indexed references and unresolved diagnostics remain distinct. The recent eleven-run ledger has zero SUCCESS, seven PARTIAL and four STOPPED outcomes. [Latest aggregate evidence](owner_replay.json) · [Scientific decision, source limits and execution ledger](../docs/owner_replay.md)

The **October 26 acquisition record** reports **133/221** numerical box-score candidates, 88 remaining, and **102/583** required women's venue rows qualified, up from 27 with zero losses. The **107-unit** acquisition milestone succeeded, including 27 fresh captures; **481** women's rows and the historical-admission gate remain open. The [qualification frontier](../docs/qualification_frontier.md) partitions that gap by edition and missing qualification dimension. [Current snapshot](acquisition_progress.json) · [Execution evidence ledger](../docs/execution_evidence.md). Source recovery is separate from training admission and forecast improvement.

The earlier October 8 **0.1067095** scored case study and its comparison with the official winning reference remain below. Different submission dates and outcome availability prevent a prospective-superiority claim.

## Earlier scored case study

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

## Earlier source foundation: v170

The **v170 October 14** return completed source reconstruction over **14,311 team-season profiles** and recovered **132,133 valid existing matchup probabilities**. All **19 manifested members** passed integrity checks. It did not create a new candidate or submission, complete the full private forecast reconstruction, or pass historical admission. Injury transformation and exact source timing remain incomplete.

The [execution receipt](latest_execution.json) contains only allowlisted aggregates. The scored case study above is a dated published receipt, not a statement of the best or newest private experiment. [Current evidence](../docs/current_research.md) · [Executable public example](../docs/public_reproduction.md)

## Review path

1. [Start here](../START_HERE.md): project overview and review order.
2. [Benchmark comparison](../docs/benchmark_comparison.md): result, arithmetic, credit, and evaluation conditions.
3. [Executed review notebook](verified_result.ipynb) or [audit CLI](reproduce_release.py): reproducible aggregate checks without private training artifacts.
4. [Employer walkthrough](../docs/employer_walkthrough.md): technical contributions and interview discussion.
5. [Reproduction matrix](../docs/reproduction_matrix.md): demonstrated mechanisms and remaining gaps.
6. [2027 readiness](../docs/2027_readiness.md): prospective execution contract.
7. [Release evidence](release_evidence.json): machine-readable facts for the earlier scored case study.
8. [Disclosure](DISCLOSURE.md): publication and reproducibility boundaries.

Earlier files in this directory preserve research snapshots. Their historical lifecycle labels do not override the current release evidence or [current research boundary](../docs/current_research.md).

The public layer exposes reproducible review procedures and aggregate evidence. It withholds private row-level predictions, fitted models, raw supplemental archives, and exact competition composition rules. The public audit does not rerun the exact private forecasting pipeline.
