# Employer walkthrough

## The result

**Alvaro Mendizabal built an auditable NCAA probability-forecasting system that received a confirmed Kaggle late-submission Brier score of 0.1067095.** This is **0.0030359 lower, or 2.77% less Brier loss**, than the official winning score of **0.1097454**. Lower is better.

The comparison has a precise boundary: the official competition closed on March 19, 2026; this forecast was submitted on October 8, after outcomes had been available and repeatedly inspected. It is a measurable retrospective improvement, not an official competition victory or a prospective outperformance claim. See the [benchmark comparison](benchmark_comparison.md) and [release evidence](../portfolio/release_evidence.json).

## What I contributed

The system builds on credited public methods, including Harrison Horan's work. Its submitted composition adapts the men's probability system and retains the women's reference baseline. I independently reconstructed and checked important source, feature, training, and inference contracts instead of treating a downloaded prediction file as a complete model.

My work spans four connected engineering problems:

- **Forecast construction:** gender-specific probability modeling, reconstructed team-strength and ranking information, calibration, and controlled composition of complementary signals.
- **Source provenance:** raw receipts, immutable hashes, publication-time checks, provider-specific identities, and explicit quarantine when a source cannot support the intended claim.
- **Numerical reproduction:** matched-input checks that isolate implementation drift from source differences.
- **Operational delivery:** bounded AWS/SageMaker jobs with self-tests, checkpoints, heartbeats, resumable work, and verified return bundles.

A matched retrospective reconstruction makes the contribution more concrete: the men's Brier falls from **0.1430858925 to 0.1366807914**, while the women's result remains approximately **0.076738317**. The combined result falls from **0.1099121050 to 0.1067095543**. This local reference is distinct from the official leaderboard score. It locates the improvement in the men's adapted system; isolating individual features still requires matched ablations.

## Evidence that goes beyond a single score

| Engineering result | Verified scope |
|---|---|
| Official raw-game foundation | 42 men's and 29 women's seasons; 13,753 and 9,851 team-season rows |
| Women's numerical reconstruction | 65,703 pairwise probabilities within 1e-4 of the archived reference |
| Men's procedure reproduction | 66 core members and 66 margin members; 31 auxiliary features reconciled |
| Historical cohort repair | All 558 saved control predictions reproduced; eight legitimate games restored for a complete 566-game cohort |
| Independent feature replay | Men's and women's raw-to-feature outputs rebuilt and compared |
| Submitted artifact | 132,133 prediction rows; accepted late submission with matching public/private displayed scores |

These are separate pieces of evidence. Source reconstruction does not by itself prove forecast quality, and numerical parity does not certify the original source's publication timing.

## Research judgment

Several plausible ideas improved a recent slice but failed broader historical requirements. Mirrored training and an exact-date AP integration are examples. Their source assets and findings were retained; the failed recipes were not silently promoted.

The project also repaired semantic errors that ordinary model tuning would miss: AP edition interpretation, historical activation boundaries, equal-seed filtering, team order, margin targets, and source-object identity. This is the practical work behind a trustworthy probability system.

## Current work and remaining limits

The confirmed score is the current delivered result. A separate original-boxscore acquisition and qualification package, v99, has been delivered for owner execution; its actual return is pending. It audits the known historical cache and attempts an original-source sample of 60 games across 20 gender-season groups. It does not create a new forecasting model or submission.

The remaining research gaps are broad original player and availability histories, dated BPI and market coverage, a newly validated complementary representation, and a complete prospective 2027 run. Derived third-party NCAA records are not relabeled as original ESPN data, and current historical responses do not establish that the same bytes existed before the tournament.

## Review the project

Start with [the repository guide](../START_HERE.md), run the [public review notebook](../portfolio/verified_result.ipynb) or [standard-library audit](../portfolio/reproduce_release.py), then inspect the [reproduction matrix](reproduction_matrix.md) and [2027 readiness contract](2027_readiness.md). The public audit reproduces aggregate release checks; it does not rerun the exact private forecasting pipeline. Private prediction rows, fitted competition artifacts, and exact private composition rules are withheld.
