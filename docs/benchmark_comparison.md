# The result, the benchmark, and the difference

## Exact reported improvement

The project recorded **0.1067095 Brier** in Kaggle submission **56928396**, marked COMPLETE on **October 8, 2026 UTC**. Both reported score fields agree. The sanitized [receipt](../reports/verified_result/submission_receipt.json) records the submission identity, forecast-file hash, row count, and evidence provenance without publishing prediction rows.

The [official final leaderboard](https://www.kaggle.com/competitions/march-machine-learning-mania-2026/leaderboard) lists **harry / Harrison Horan at 0.1097454** in first place. The numerical difference is:

| Quantity | Value |
|---|---:|
| Published winning Brier | 0.1097454 |
| This project's confirmed late-submission Brier | 0.1067095 |
| Absolute reduction | **0.0030359** |
| Relative reduction in Brier error | **2.7663%** |

Relative reduction is the score difference divided by the reference score. Since Brier is mean squared probability error, this is a reduction in that loss—not a change in classification accuracy. It is a measurable difference beyond displayed rounding precision. A statistical-significance claim would require a different analysis.

**Timing matters:** the [official submission deadline](https://www.kaggle.com/competitions/march-machine-learning-mania-2026/) was March 19, 2026 at 16:00 UTC. This project was developed and submitted after the tournament, with outcomes already inspected. The score is therefore a retrospective research comparison. It does not establish an official competition win or prospective superiority over the winning entrant.

## Matched branch comparison

I separately evaluated a matched local implementation of the credited method. Its score differs slightly from the official winner, so these comparisons remain distinct.

| Population | Matched local baseline | Submitted research lineage | Relative loss reduction |
|---|---:|---:|---:|
| All 126 games | 0.1099121050 | 0.1067095543 | **2.91%** |
| Men's 63 games | 0.1430858925 | 0.1366807914 | **4.48%** |
| Women's 63 games | 0.0767383175 | 0.0767383172 | Effectively preserved |

This reveals where the observed gain occurred: the men's branch improved while the stable women's branch remained numerically stable. The program rebuilt ranking/reference information and incorporated complementary archived pregame BPI and market probabilities into its research composition. Forecasts outside the applicable source coverage were preserved. Exact private composition rules are intentionally withheld.

These are paired aggregate measurements on an inspected population. They support the observed score difference and branch-level explanation. They do not isolate every input's causal contribution or establish transfer to an unseen season. Historical promotion gates did not all pass.

## Method lineage and additional work

Harrison Horan's [first-place writeup](https://github.com/harrisonhoran/kaggle-march-mania-2026-1st-place/blob/main/kagglewriteup.md) documents the credited gender-specific XGBoost and calibration approach. The submitted research composition adapts the men's system and retains the women's baseline. Those foundational methods are not presented as my invention.

I built additional source qualification, integrated complementary pregame probability information, reconciled model procedures on matched inputs, repaired full-population evaluation and made execution recoverable. The score comparisons establish the measured differences; the broader engineering work makes those differences inspectable. It does not assign causal credit to every later source acquisition.

Original player availability and historical market coverage remain incomplete. Historical promotion and prospective validation still require their own evidence. The [latest research state](current_research.md) keeps source-only progress separate from the confirmed forecast.

## Inspect or reproduce

- [Executed result notebook](../portfolio/verified_result.ipynb)
- [Public aggregate evidence](../portfolio/release_evidence.json)
- [Standard-library audit](../portfolio/reproduce_release.py)
- [Recomputed comparison report](../reports/verified_result/reproduction.json)
- [Source and model reproduction matrix](reproduction_matrix.md)
- [Public/private boundary](../portfolio/DISCLOSURE.md)

Primary external sources were checked October 8, 2026. The public audit recomputes the table arithmetic and verifies the published receipt. Independent rescoring of the private forecast requires its withheld probabilities and is outside this public package.
