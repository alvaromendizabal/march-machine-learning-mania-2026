# NCAA tournament forecasting | reproducible ML research case study

**Alvaro Mendizabal · probability forecasting · temporal validation · source provenance · AWS ML engineering**

This repository is an employer-facing case study of a multi-season NCAA tournament forecasting program built around one principle: **predictive information is useful only when its provenance, timing, transformation, and evaluation can be defended.**

## Current verified state

The accepted submitted owned-data system remains **v26 at 0.1206458 Brier**. An independently reconstructed scorer reproduces the complete 126-game result at **0.1206458343** across **63 men's and 63 women's games**.

The private reconstruction program has also produced a stronger **experimental** post-competition forecast at **0.1067095543 Brier** on the same 126-game audit. It remains experimental because the project requires historical transfer evidence before promotion.

| System | Evaluation setting | Brier | Lifecycle |
|---|---|---:|---|
| v26 owned Torvik reliability system | late/post-competition submission | **0.1206458** | Accepted / submitted control |
| v26 exact local audit | complete 126-game reconstructed audit | **0.1206458343** | Verified scorer |
| Native women reconstruction | 63 women tournament games | **0.0767383172** | Numerically reproduced research branch |
| Reconstructed research frontier | complete 126-game post-competition audit | **0.1067095543** | Experimental; not promoted |

Lower Brier is better. These are post-competition research measurements, not claims about original competition placement.

**[Employer walkthrough](docs/employer_walkthrough.md)** ·
[Current research boundary](docs/current_research.md) ·
[Supplemental-source ownership](docs/supplemental_source_ownership.md) ·
[Research log](docs/post_merge_research_log.md) ·
[Reproduction matrix](docs/reproduction_matrix.md) ·
[Owned-data portfolio](portfolio/owned_frontier_2027.md)

## What makes this project technically interesting

### 1. Source-equivalent reconstruction instead of CSV copying

Supplemental artifacts that could not be independently regenerated were retired. Useful signals were decomposed into their underlying information families and rebuilt from official or original sources.

Current owned/recreated infrastructure includes:

- **Bart Torvik Time Machine:** 15 men's tournament seasons, 5,268 / 5,304 team-season rows in the active window, with dated source receipts and point-in-time checks.
- **AP polling archive:** 117 rank-complete editions and 95 vote-complete editions, with repaired edition semantics and chronology-aware activation.
- **Official-derived ratings:** Elo, SRS, Colley, Bradley-Terry, efficiency, pace, schedule strength, recent form, and Massey consensus.
- **Tournament-selection facts:** independently reconstructed NIT / WBIT / WNIT membership from dated announcements.
- **Historical player infrastructure:** more than 1.2M mapped pre-cutoff men's player-game rows retained for controlled roster / availability research.
- **Original-source market and BPI research:** independently archived observations with source-time qualification rather than copied prediction tables.
- **Original publisher bracket tables:** complete 68-team men's probability fields recovered for 2025 and 2026 and evaluated under explicit source-version rules.

### 2. Numerical reproduction of a strong public mechanism

The native women's four-feature XGBoost branch was rebuilt from owned inputs and reproduced **65,703 pairwise probabilities within 1e-4** of the archived reference.

The reconstructed model scored **0.0767383172 Brier** on the 63 scored women's games. All 15 historical member-fit counts and best-iteration receipts matched the archived behavior.

That result demonstrates source, feature, training, calibration, and inference reconciliation—not merely a similar reimplementation.

### 3. Men's model behavior was isolated from source differences

The men reconstruction eventually separated model-procedure parity from missing external information.

Public-safe verification includes:

- **66 core members:** matching best iterations and same-input predictions at numerical precision.
- **66 margin members:** matching best iterations and calibration slopes; same-input prediction differences are negligible relative to the forecast gap.
- **Complete historical cohort:** 566 played men's main-bracket games restored across nine evaluation seasons.
- **Control replay:** all 558 previously saved historical predictions reproduced before adding the eight legitimately omitted equal-seed games.

This narrowed the remaining uncertainty from "is the model different?" to specific source and representation questions.

### 4. Reproduction defects are treated as engineering defects

The program found and repaired subtle mismatches that materially changed behavior:

- AP edition indexing and current-versus-previous rank semantics;
- historical activation boundaries;
- WBIT-only versus expanded postseason membership;
- an equal-seed filter that removed legitimate later-round historical games;
- raw versus transformed margin-target assumptions;
- probability conversion and team-order sensitivity;
- source-version and aggregate-hash assumptions.

When an implementation changes the original contract, the result is not described as a failed reproduction.

### 5. Negative results are first-class evidence

The project records successful negative experiments instead of hiding them. Recent examples include:

- full publisher-bracket probability reconstruction;
- matched equal-seed training correction;
- mirrored pair-exchange training;
- exact-date AP feature refresh;
- broad internal-strength expansion;
- two player / availability representations;
- dynamic opponent-adjusted offense / defense / pace / margin;
- multiple market transformations.

Several later experiments improved recent confirmation seasons but were still rejected because development behavior deteriorated. That promotion discipline prevents favorable slices from becoming automatic "wins."

### 6. Cloud research engineering

AWS/SageMaker is the canonical research environment. Private runners are:

- self-testing and self-gating;
- resumable and checkpointed;
- source- and artifact-hash aware;
- bounded by runtime, memory, storage, and cost limits;
- instrumented with timestamped heartbeats and JSONL telemetry;
- capable of packaging diagnostics on success, failure, or timeout;
- designed to reuse completed work rather than restart expensive stages.

The exact 126-game scorer sits downstream of policy freeze and is used as an audit, not as a tuning loop.

## Validation discipline

The project separates:

1. chronological historical development;
2. later-season confirmation;
3. the exact 126-game 2026 retrospective audit;
4. externally submitted results.

A lower retrospective score does not automatically become the accepted champion.

The historical men's evaluation bank now covers **566 played main-bracket games across nine forecast seasons**. The corrected complete 2023–2025 confirmation population contains **189 games**.

## Current research frontier

The highest-information open capabilities are:

- temporally separated calibration using earlier-season held-out predictions;
- broader original-version availability / player-value history;
- stronger point-in-time roster-role representations;
- remaining defensible historical NET coverage;
- a complete incoming-season acquisition → mapping → feature → train/infer → immutable-candidate rehearsal.

The complete future-season chain is not called finished until exercised end to end.

## Public/private boundary

This repository is deliberately **semi-reproducible**.

Published:

- metric definitions and evaluation populations;
- aggregate source coverage and provenance state;
- public-safe experiment outcomes;
- validation and lifecycle rules;
- reproduction status of public mechanisms;
- engineering architecture and negative-result conclusions;
- machine-readable aggregate portfolio artifacts.

Intentionally withheld:

- row-level private predictions;
- candidate submission CSVs;
- raw supplemental source archives;
- fitted private models;
- exact private correction rules, thresholds, or weights;
- source-specific private identity logic;
- credentials and private AWS orchestration state.

The repository is designed to be technically reviewable by employers without distributing a turnkey competition system.
