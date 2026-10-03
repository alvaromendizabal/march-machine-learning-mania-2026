# Employer walkthrough

## 60-second summary

This project is a post-competition NCAA tournament probability-forecasting research program centered on **temporal validation, source provenance, numerical reproduction, and cloud ML engineering**.

The accepted owned-data system scores **0.1206458 Brier** on a late/post-competition submission, and an independently reconstructed local scorer reproduces the full 126-game result at **0.1206458343**.

The private reconstruction program has also reached **0.1069362 Brier** on the same 126-game retrospective audit. That lower score remains experimental because its parent lineage did not satisfy every historical promotion gate. The repository therefore distinguishes a strong retrospective research result from an accepted production-style champion.

## What I built

- an independently recreated Bart Torvik Time Machine bank with historical source receipts and chronology checks;
- a repaired AP polling archive with 117 rank-complete and 95 vote-complete editions;
- official-data rating systems including Elo, SRS, Colley, Bradley-Terry, efficiency, pace, schedule strength, recency, and Massey consensus;
- original-source postseason-selection facts from dated announcements;
- a historical player-box infrastructure with more than 1.2M mapped pre-cutoff men's player-game rows;
- partial original-source market and ESPN BPI archives with strict timing qualification;
- a complete 126-game scorer that reproduces the accepted v26 result exactly;
- resumable AWS runners with self-tests, checkpoints, telemetry, cost accounting, and failure packaging.

## The strongest technical result

The native women's XGBoost branch was independently reconstructed from owned inputs and numerically reproduced against the archived reference:

- **65,703 pairwise probabilities** checked;
- every row within **1e-4**;
- maximum difference about **4.2e-05**;
- mean difference about **2.35e-08**;
- all **15** historical member-fit counts and best-iteration receipts matched;
- 63-game women Brier: **0.0767383172**.

This is a useful example of model-reproduction work that goes beyond "I reimplemented something similar." The source contract, feature semantics, training procedure, calibration, and inference behavior were all reconciled.

## Engineering lessons from the men’s reconstruction

Several subtle mismatches were discovered because the project compared the implementation at component level rather than relying only on final score:

- wrong AP edition indexing;
- current versus previous rank semantics;
- pre-2008 activation differences;
- postseason membership scope differences;
- raw versus overtime-normalized margin supervision;
- probability conversion before versus after member averaging.

After repair, the four audited historical core ingredients and all 31 auxiliary margin features match the archived definitions at numerical tolerance.

The remaining differences are concentrated in external information families that are still not fully independently owned.

## What I rejected

A strong research process includes explicit negative results.

Correctly executed but rejected directions include:

- broad internal-strength expansion;
- recent rotation / continuity;
- richer boxscore player-impact proxies;
- dynamic opponent-adjusted offense / defense / pace / margin;
- several championship-market transformations;
- broad blends of highly correlated weaker branches.

Those experiments remain in the ledger because they prevent repeated spending on ideas that look different syntactically but add little new information.

## Why this project is useful to discuss in an interview

### Temporal ML discipline

Tournament forecasting is a small-data, nonstationary setting. Source timing matters as much as model choice. Historical features are accepted only when the information could have existed before the relevant prediction cutoff.

### Reproducibility as an engineering target

A saved prediction file is not considered a reproducible system. The project distinguishes:

- replaying an output;
- reacquiring the underlying source;
- reproducing the feature contract;
- reproducing the model procedure;
- validating historical transfer;
- rehearsing the incoming-season pipeline.

### Failure classification

The experiment ledger separates:

- successful runs;
- successful negative experiments;
- engineering failures;
- source/timing blocks;
- promotion failures.

That makes cost and scientific progress much easier to reason about.

### Cloud execution

AWS/SageMaker is the canonical workspace. Long-running milestones are self-gating, resumable, resource-aware, and packaged with structured evidence so a later debugging step does not require rerunning completed expensive work.

## Current frontier

The next high-information work is source/representation recovery rather than another generic boosting sweep:

- broader original-version BPI / availability history;
- stronger roster-role representations from owned raw sources;
- remaining defensible NET history;
- a complete incoming-season rehearsal from acquisition through immutable candidate freeze.

## Public/private boundary

The public repository is intentionally semi-reproducible.

It exposes:

- source provenance states;
- evaluation populations;
- aggregate experimental results;
- reproduction status;
- engineering controls;
- negative-result conclusions.

It does not publish:

- private row-level predictions;
- raw supplemental archives;
- fitted competition models;
- exact private correction rules / thresholds / weights;
- source-specific identity logic;
- credentials or AWS-local orchestration state.

That keeps the project legible to an employer without turning the repository into a turnkey competition system.
