# Employer walkthrough

## 60-second summary

This project is a multi-season NCAA tournament probability-forecasting research program centered on **temporal validation, source provenance, numerical reproduction, and cloud ML engineering**.

The accepted submitted owned-data system scores **0.1206458 Brier**, with an exact local 126-game audit of **0.1206458343**. The private reconstruction program has also reached **0.1067095543 Brier** on that same retrospective population. The lower result remains experimental because promotion requires historical transfer evidence, not just a favorable final audit.

## What I built

- an independently recreated Bart Torvik Time Machine bank with historical source receipts and chronology checks;
- a repaired AP polling archive with 117 rank-complete and 95 vote-complete editions;
- official-data rating systems including Elo, SRS, Colley, Bradley-Terry, efficiency, pace, schedule strength, recency, and Massey consensus;
- original-source postseason-selection facts from dated announcements;
- a historical player-box infrastructure with more than 1.2M mapped pre-cutoff men's player-game rows, plus a stricter qualified modeling bank used in later controlled experiments;
- a reproducible official raw-game foundation spanning 42 men's and 29 women's raw seasons, with independent raw-to-feature replay;
- partial original-source market and ESPN BPI archives with strict timing qualification;
- complete 68-team publisher probability-table reconstructions for 2025 and 2026;
- a complete 126-game scorer that reproduces the accepted v26 result exactly;
- a repaired 566-game men's historical evaluation bank across nine forecast seasons;
- resumable AWS runners with self-tests, checkpoints, telemetry, cost accounting, and failure packaging.

## Strongest reproduction evidence

### Native women

The native women's XGBoost branch was independently reconstructed from owned inputs:

- **65,703 pairwise probabilities** checked;
- every row within **1e-4**;
- maximum difference about **4.2e-05**;
- mean difference about **2.35e-08**;
- all **15** historical member-fit counts and best-iteration receipts matched;
- 63-game women Brier: **0.0767383172**.

### Men's model procedure

The men's reconstruction eventually separated model-procedure differences from source differences:

- all **66 core model members** reproduce their archived best iterations and same-input predictions;
- all **66 margin members** reproduce best iterations and calibration slopes, with only negligible same-input numerical differences;
- all **31 auxiliary historical feature columns** were reconciled;
- the complete historical control reproduces all **558 previously saved predictions** before restoring eight legitimately omitted games.

This is a stronger engineering claim than "I rebuilt something similar."

## Research discipline

The project discovered and corrected several subtle contract problems:

- AP edition numbering and rank semantics;
- historical activation boundaries;
- postseason-membership scope;
- equal-seed filtering that removed legitimate late-round games;
- margin-target assumptions;
- team-order asymmetry;
- source-object versus aggregate-file identity.

It also preserves negative evidence. Examples include player proxies, dynamic opponent-adjusted representations, publisher-bracket probability blends, mirrored training, and exact-date AP feature refreshes.

Some of those ideas improved recent confirmation seasons but failed development requirements. They were rejected rather than promoted selectively.

## Why this project is useful to discuss in an interview

### Temporal ML discipline

Tournament forecasting is small-data and nonstationary. Source timing matters as much as model choice. Historical features are accepted only when the information could have existed before the relevant cutoff.

### Reproducibility as an engineering target

A saved prediction file is not considered a reproducible system. The project distinguishes:

- replaying an output;
- reacquiring the source;
- reproducing feature semantics;
- reproducing the model procedure;
- validating historical transfer;
- rehearsing an incoming-season pipeline.

### Failure classification

The experiment ledger separates successful runs, successful negative experiments, engineering failures, source / timing blocks, and promotion failures.

### Cloud execution

AWS/SageMaker is the canonical workspace. Substantial milestones self-test, gate, checkpoint, resume, emit telemetry, and package diagnostics so a later failure does not force completed work to rerun.

## Current engineering frontier

The latest completed AWS milestone moved the project from source reconstruction into a replayable official-data foundation:

- broad men’s and women’s raw-game coverage is fingerprinted;
- descriptive performance, schedule, recency, and venue features are rebuilt from raw inputs;
- missing historical fields remain explicit instead of being backfilled;
- raw-to-feature outputs replay independently;
- 2026 feature generation is rehearsed as an incoming-season update;
- late or semantically ambiguous reconstructed sources remain quarantined.

The next modeling study tests whether strictly pregame regular-season supervision transfers useful information to tournaments. Separate source-equivalence work continues for original-version availability / player-value information, broader pregame probability history, and a complete incoming-season acquisition-to-frozen-candidate rehearsal.

No result is claimed until the corresponding AWS evidence exists.

## Public/private boundary

The repository is intentionally semi-reproducible.

It exposes aggregate metrics, source coverage, validation rules, reproduction evidence, experiment conclusions, and engineering architecture.

It does not publish row-level private predictions, raw supplemental archives, fitted competition models, exact correction rules / thresholds / weights, credentials, or private AWS orchestration state.
