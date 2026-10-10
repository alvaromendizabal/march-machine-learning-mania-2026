# Engineering a verifiable probability forecast

**Alvaro Mendizabal · Probability modeling · Temporal data engineering · ML systems**

## Result and responsibility

**I built and evaluated an auditable NCAA probability-forecasting system that received a Kaggle-confirmed late-submission Brier score of 0.1067095.** That is **0.0030359 lower, or 2.77% less Brier loss**, than the official winning score of **0.1097454**.

The competition closed on March 19, 2026; I submitted this forecast on October 8 after outcomes had been inspected. The score demonstrates a retrospective numerical improvement, not an official competition victory, an equal-information contest or prospective outperformance. [Comparison scope](benchmark_comparison.md) · [Release evidence](../portfolio/release_evidence.json)

[Explore Tournament Lab](https://alvaro-tournament-lab.tartmacaw2.chatgpt.site) for a hands-on view of probability assumptions and exact bracket propagation. Its fictional data and transparent rating rule are separate from the private research forecast.

## Engineering contributions

I engineered forecast construction, source qualification, numerical verification and delivery around separate men's and women's probability branches. I integrated the men's system, retained the stable women's branch, and established the controls needed to evaluate changes without confusing input differences, implementation drift and predictive improvement.

My contributions span four connected problems:

- **Forecast construction:** gender-specific probability modeling, team-strength and ranking inputs, calibration, and controlled composition of complementary pregame signals.
- **Source qualification:** raw receipts, immutable hashes, publication-time checks, provider-specific identities and explicit quarantine when records cannot support the intended claim.
- **Numerical verification:** independently replayed features and matched-input model checks to distinguish implementation errors from input changes.
- **Operational delivery:** AWS/SageMaker execution with self-tests, checkpoints, heartbeats, resumable work and verified return bundles.

On the matched retrospective audit, men's Brier falls from **0.1430858925 to 0.1366807914** while women's Brier remains approximately **0.076738317**. Combined Brier falls from **0.1099121050 to 0.1067095543**. This local baseline is distinct from the official leaderboard score. The branch comparison locates the observed gain; causal credit for individual inputs still requires matched ablations.

## Decisions with inspectable evidence

| Engineering result | Verified scope | Decision it supports |
|---|---|---|
| Raw-game foundation | 42 men's / 29 women's seasons; 13,753 / 9,851 team-season rows | Reuse a documented feature foundation across historical regimes |
| Women's numerical parity | 65,703 pairwise probabilities within 1e-4 | Retain a stable branch while examining changes elsewhere |
| Men's procedure checks | 66 core and 66 margin members; 31 auxiliary features reconciled | Separate source differences from implementation drift |
| Complete historical cohort | 558 saved controls replayed; eight legitimate games restored; 566 total | Evaluate the full declared population |
| Independent feature replay | Men's and women's raw-to-feature outputs rebuilt and compared | Catch semantic errors before fitting another candidate |
| Delivered artifact | 132,133 validated rows and a confirmed external receipt | Distinguish generation, submission and model promotion |

Source coverage alone does not prove forecast quality. Numerical parity alone does not certify source publication timing.

## Research judgment

I retained negative findings rather than promoting a favorable slice. Mirrored training and an exact-date AP integration improved some recent results but failed broader historical requirements. Their useful source assets remained available; the failed recipes did not become approved models.

I also repaired semantic errors that tuning would miss: AP edition interpretation, historical activation boundaries, equal-seed filtering, team order, margin targets and source-object identity. These controls are central to the work, not incidental bookkeeping.

## A public demonstration of the reasoning

[Tournament Lab](public_demo.md) exposes an eight-team synthetic bracket. Changing a team's rating or the probability temperature recomputes advancement probabilities across every possible bracket path. Matchup comparisons and exported assumptions make the calculation inspectable. The JSON also includes diagnostics on a small authored scoring sample. It uses no learned model, private forecasts or real tournament outcomes.

The public result audit serves a different purpose: it verifies aggregate release arithmetic, receipt hashes and disclosure flags. It cannot regenerate withheld private prediction rows.

## Current state and remaining work

The best confirmed score remains **0.1067095**. The latest inspected execution return, **v128, completed October 10, 2026**, ended **SOURCE_PARTIAL**. It repaired **2,258 market-quote rows**, retained **1,075 rows with missing last quotes**, and admitted no model. There were **zero fits, inferences, candidates or submissions**.

Remaining gaps include exact injury inputs, broad timing-qualified player/availability and BPI/market histories, a newly validated complementary representation, and a full prospective 2027 run. Derived NCAA records are not relabeled as original ESPN records; retrieving an old game today does not prove the same bytes were available before its tournament.

[Reviewer guide](../START_HERE.md) · [Validation matrix](reproduction_matrix.md) · [Current research](current_research.md) · [2027 readiness](2027_readiness.md) · [References and comparison scope](benchmark_comparison.md) · [Disclosure](../portfolio/DISCLOSURE.md)
