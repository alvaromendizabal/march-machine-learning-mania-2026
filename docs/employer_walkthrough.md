# Employer walkthrough

## 60-second summary

This project is a post-competition NCAA tournament probability-forecasting research program focused on three things:

1. **temporal validation discipline** — policies are selected on earlier seasons and frozen before a 2026 audit;
2. **supplemental-data ownership** — useful public-solution inputs are independently reconstructed from official/original sources rather than copied from competitor CSVs;
3. **cloud ML engineering** — source acquisition, caching, validation, modeling, notebook reporting, cost logging, and failure packaging are automated in bounded AWS runners.

The current fully owned/recreated system scores **0.1206458 Brier** on a late/post-competition Kaggle submission and **0.1206458343** on an exact independently reconstructed 126-game local audit.

## What I built

- independently reconstructed Bart Torvik Time Machine history;
- competition-era AP polling archive and trajectory features;
- official-data rating systems including Elo/SRS/Colley/Bradley-Terry/Massey-derived consensus;
- point-in-time source eligibility and quarantine logic;
- a reliability-gated correction system that improved all three recent confirmation seasons;
- a 126-game scorer that independently reproduces the Kaggle Brier;
- resumable/cached AWS research runners with telemetry and deterministic return artifacts;
- a source-ownership matrix for 2027 prospective collection.

## What I rejected

A core part of the project is not promoting attractive-looking models that fail transfer.

Rejected directions include:
- broad internal-strength expansion;
- simple recent rotation continuity;
- richer boxscore player-impact proxies;
- dynamic opponent-adjusted offense/defense/pace/margin;
- broad blending among highly correlated weaker branches.

Historical BPI and historical timestamped market odds were blocked by source/timing constraints rather than forced into the model.

## Why the current public score looks worse than an older research score

The project deliberately tightened its ownership standard for 2027. Older post-competition research reached lower retrospective Brier values using external artifacts that are no longer considered independently reproducible. Those scores remain research history; the **0.1206458 v26 system is the current owned/recreated boundary**.

That distinction is intentional: reproducibility and source provenance are part of the engineering target, not cleanup after the fact.

## What I would discuss in an interview

- why Brier score changes model-selection behavior relative to accuracy;
- why temporal validation matters in tournament forecasting;
- how source timing can invalidate an otherwise useful feature;
- how I separate engineering failure, source block, and scientific rejection;
- why residual complementarity matters more than model count;
- how AWS caching/checkpointing avoids redoing expensive source work;
- how the 2027 source contract prevents hindsight and silent future-data fabrication.

## Public/private boundary

This repository exposes the research story and aggregate evidence without publishing raw third-party source archives, candidate prediction rows, exact private model gates/weights, credentials, or private orchestration artifacts.
