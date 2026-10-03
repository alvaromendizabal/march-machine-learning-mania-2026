# NCAA tournament forecasting | owned-data ML engineering case study

**Alvaro Mendizabal · probability forecasting · temporal validation · source provenance · cloud ML engineering**

This repository is an employer-facing case study of a multi-season NCAA tournament forecasting program built around one principle: **use strong predictive information only when its provenance, timing, transformation, and evaluation can be defended.**

## Current verified state

The accepted owned-data submission remains **v26 at 0.1206458 Brier**. An independently reconstructed local scorer reproduces the complete 126-game result at **0.1206458343** across **63 men's and 63 women's games**.

The private reconstruction program has also produced a stronger **experimental** post-competition forecast at **0.1069362 Brier**. It is intentionally not called the champion because its parent lineage did not pass every historical promotion gate. That separation between *best retrospective result* and *best accepted system* is part of the research discipline.

| System | Evaluation setting | Brier | Lifecycle |
|---|---|---:|---|
| v26 owned Torvik reliability system | late/post-competition submission | **0.1206458** | Accepted / submitted control |
| v26 exact local audit | complete 126-game reconstructed audit | **0.1206458343** | Verified scorer |
| Native women reconstruction | 63 women tournament games | **0.0767383172** | Numerically reproduced research branch |
| Reconstructed research frontier | complete 126-game post-competition audit | **0.1069362213** | Experimental; not promoted |

Lower Brier is better. These are post-competition research measurements; they are not presented as original competition placement claims.

**[Employer walkthrough](docs/employer_walkthrough.md)** ·
[Current research boundary](docs/current_research.md) ·
[Supplemental-source ownership](docs/supplemental_source_ownership.md) ·
[Research log](docs/post_merge_research_log.md) ·
[Reproduction matrix](docs/reproduction_matrix.md) ·
[Owned-data portfolio](portfolio/owned_frontier_2027.md)

## What makes this project technically interesting

### 1. Source-equivalent reconstruction, not CSV copying

The project retired supplemental artifacts that could not be independently regenerated. Useful signals were decomposed into their underlying information families and rebuilt from original or authoritative sources.

Current owned/recreated infrastructure includes:

- **Bart Torvik Time Machine:** 15 men's tournament seasons, 5,268 / 5,304 team-season rows in the active source window, with dated source receipts and point-in-time checks.
- **AP polling archive:** 117 rank-complete editions and 95 vote-complete editions, with repaired edition semantics, current/previous-rank separation, and chronology-aware activation.
- **Official-derived ratings:** Elo, SRS, Colley, Bradley-Terry, efficiency, pace, schedule strength, recent form, and Massey consensus.
- **Tournament-selection facts:** independently reconstructed NIT/WBIT/WNIT membership from original announcements.
- **Historical player infrastructure:** more than 1.2M mapped pre-cutoff men's player-game rows, retained for controlled roster/availability research.
- **Original-source market and BPI research:** independently archived target-season observations with source-time qualification rather than copied prediction tables.

### 2. Numerical reproduction of a strong public mechanism

The women's native four-feature XGBoost branch was rebuilt from owned inputs and reproduced **65,703 pairwise probabilities within 1e-4** of the archived reference.

The reconstructed model scored **0.0767383172 Brier** on the 63 scored women's games, while all 15 historical member-fit counts and best-iteration receipts matched the archived behavior.

That result is important because it demonstrates that stronger historical behavior can be recovered without relying on another competitor's prepared feature file.

### 3. Reproduction errors are treated as engineering defects

The program identified and repaired several subtle mismatches that materially changed model behavior:

- AP edition indexing;
- current rank versus previous rank;
- pre-2008 feature activation;
- WBIT-only versus expanded postseason membership;
- raw versus overtime-normalized margin supervision;
- probability-conversion and ensemble-order differences.

A changed implementation is no longer described as a failed reproduction.

### 4. Negative results are first-class evidence

The project records successful negative experiments instead of hiding them. Examples include:

- broad internal-strength expansion;
- two player/availability representations;
- dynamic opponent-adjusted offense/defense/pace/margin states;
- several market transformations;
- broad blends of highly correlated weaker branches.

This keeps the experiment queue focused on genuinely missing information rather than repeated parameter motion.

### 5. Cloud research engineering

Private AWS/SageMaker runners are:

- self-testing and self-gating;
- resumable and checkpointed;
- source- and artifact-hash aware;
- bounded by runtime, memory, storage, and cost limits;
- instrumented with timestamped heartbeats and JSONL telemetry;
- capable of packaging diagnostics on success, failure, or timeout;
- designed to preserve completed work rather than restart expensive stages.

The exact 126-game scorer is downstream of policy freeze and is used as a final audit rather than a tuning loop.

## Current research frontier

The highest-value remaining capabilities are not another round of tiny hyperparameter changes. They are:

- broader original-version BPI / availability reconstruction;
- stronger point-in-time player and roster representations;
- remaining historical NET coverage where source timing is defensible;
- a complete incoming-season acquisition → mapping → feature → train/infer → candidate-freeze rehearsal for 2027.

The current private program already parameterizes many source and feature routines by season, but the complete 2027 chain is **not** claimed finished until it is exercised end to end.

## Public/private boundary

This repository is deliberately **semi-reproducible**.

Published:

- metric definitions and evaluation populations;
- aggregate source coverage and provenance state;
- public-safe experiment outcomes;
- validation and lifecycle rules;
- reproduction status of public mechanisms;
- engineering architecture and negative-result conclusions.

Intentionally withheld:

- row-level private predictions;
- candidate submission CSVs;
- raw supplemental source archives;
- fitted private models;
- exact private correction rules, thresholds, or weights;
- source-specific identity logic;
- credentials and private AWS orchestration state.

The goal is to make the research legible and technically credible to employers without distributing the competitive implementation.
