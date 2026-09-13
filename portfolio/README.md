# Research extension · Evidence portfolio

**Alvaro Mendizabal · NCAA tournament probability forecasting**

This portfolio documents continued feature-first research after the original scored release. It presents supplied aggregate measurements and their limitations; it is not a public distribution of the new private training pipeline.

## Three numbers with different meanings

| Measurement | Value | Interpretation |
|---|---:|---|
| Best reported late Kaggle submission | 0.1222672 | Preserved original observed submission result; no new submission is claimed here |
| Historical research target | 0.1097454 | Target supplied for this project, not a newly verified live leaderboard position |
| Later-era compact-reference consensus effect | −0.0006879 | Mean-season Brier change on explored men's 2022–2025 tournament games; not a production-model or leaderboard result |

Lower Brier is better. A validation improvement is not evidence that the Kaggle target has been reached.

## Research question

Which representations improve pre-tournament probabilities on matched games, survive additional-season checks, and justify their complexity? The work compares new feature families against fixed references and relevant ordinary-statistic controls. It separates real incremental information from effects caused by extra correlated inputs and regularization.

The inspected extension reports include shooting, schedule records, temporal form, possession accounting, bracket context, alternative strength representations, ranking information, common opponents, and opponent-adjusted box-score behavior. Negative findings remain visible rather than being removed from the story.

## Evidence and navigation

- [Experiment ledger](EXPERIMENT_LEDGER.md): completed, rejected, inconclusive, and pending investigations.
- [Validation summary](validation_summary.csv): all configuration/population groups from the 252 selected supplied result rows, aggregated equally across their recorded seasons.
- [Provenance](PROVENANCE.json): exact source-table hashes, source archives, and publication scope.
- [Disclosure](DISCLOSURE.md): limits of this publication and the private/public boundary.
- [Original executed notebooks](../README.md#original-review-notebooks): the preserved released research presentation.

The summary table's arm labels are anonymized presentation identifiers from the supplied public-only package. They are meaningful only within a round; `Arm 2` is not a common model across rounds. Exact recipes and implementations are withheld from this extension publication.

## Findings that changed the research direction

**Replication matters.** Initial schedule-record and temporal-change gains did not consistently repeat on the additional seasons selected for their checks. Their expansions were stopped under their declared rules, rather than retuned to rescue a favorable result.

**Controls matter.** Some apparent gains against a small reference disappeared when the comparison already included the same ordinary rates or ranking consensus. The correct primary comparison is the one specified for the investigation, not whichever baseline gives the largest improvement.

**Consensus is useful under one tested setting.** In the later compact-reference check, ranking consensus improved three of four seasons. Much of the gain came from 2024. Testing against the actual fixed production recipe remains a separate, unfinished obligation.

**Successful execution is not successful science.** Round 17's mean change beyond its rate control was −0.0004715, just short of its declared improvement threshold. Rounds 18 and 19 had mean changes of +0.0010283 and +0.0003371 against their rate controls. These findings did not justify promotion.

## Reading the summary correctly

`mean_season_brier` is the arithmetic mean across the seasons listed in that row. `delta_vs_round_reference` subtracts the reference from the same round, population, and season set. Negative is better. These are not pooled leaderboard scores, independent replications, statistical-significance results, or the original study's game-weighted metrics.

Several rounds contain both discovery and additional-season results. Their all-season means are descriptive only: promotion decisions must still use the predeclared evaluation subset and conditional baseline. Reused reference rows must not be counted as newly fitted models. Absent reports are not assigned fabricated scores.

## Current publication status

This is an evidence-only extension of the existing public repository. The original MIT release, canonical notebooks, and scientific source are preserved. New private implementation, raw inputs, models, predictions, and credential-bearing files are not included. The blocked AWS publication plan has not been approved or represented as synchronized.
