# NCAA tournament forecasting | owned-data ML engineering case study

**Alvaro Mendizabal · probability forecasting · temporal validation · cloud ML engineering**

## Current 2027-ready owned boundary: 0.1206458 Brier

The strongest **fully owned/recreated, 2027-ready** system is **v26**, with a late/post-competition Kaggle Brier of **0.1206458**. The exact independently reconstructed 126-game audit reproduces that result at **0.1206458343** across **63 men's + 63 women's games**.

This repository now distinguishes two research eras:

- **historical broader-data research**, which reached lower retrospective scores but depended on external artifacts that are no longer considered acceptable for the 2027 ownership standard;
- **current owned/recreated research**, where supplemental data must be independently reconstructed from official or original sources before it is model-eligible.

The active research target remains **0.0900000**, leaving **0.0306458** absolute Brier from the current owned champion.

**[Owned-frontier portfolio](portfolio/owned_frontier_2027.md)** · [Current research boundary](docs/current_research.md) · [Supplemental source ownership](docs/supplemental_source_ownership.md) · [Research log](docs/post_merge_research_log.md) · [Public-solution reproduction matrix](docs/reproduction_matrix.md) · [Employer walkthrough](docs/employer_walkthrough.md)

| Boundary | Brier | Interpretation |
|---|---:|---|
| Historical broader-data post-competition boundary | 0.1033437 | Retained as research history; not the 2027 ownership boundary |
| Historical v19 replay | 0.1027974 | Numerically stronger but retired under current source-ownership rules |
| v22 clean owned baseline | 0.1227708 | First fully clean owned/recreated submission |
| **v26 owned Torvik reliability system** | **0.1206458** | **Current 2027-ready owned champion** |
| Exact v26 offline audit | 0.1206458343 | 126/126 scored games; reproduces Kaggle |
| Stretch target | 0.0900000 | Research objective, not achieved |

Lower Brier is better. All 2026 comparisons are post-competition research measurements, not claims of original leaderboard placement.

## What changed since the previous public release

The private AWS program moved from an earlier broader-data research frontier to a stricter **owned/recreated supplemental-data standard** designed for 2027 repeatability.

### Independently recreated and validated

- **Bart Torvik Time Machine, 2011–2026:** recreated from original upstream snapshots with source receipts, timing controls, TeamID mapping, caching, and deterministic normalized outputs.
- **AP polling archive:** independently reconstructed and enriched with preseason, Week 6, Week 14, trajectory, weeks-ranked, best-rank, and mean-rank context.
- **Official-data strength systems:** carry-over Elo, SRS, Colley, Bradley-Terry, adjusted efficiency, pace, recency, schedule strength, and Massey-derived consensus features.
- **Historical player participation infrastructure:** independently captured ESPN boxscores were used to test recent rotation, continuity, and player-impact proxies.
- **Exact 2026 scorer:** 63 men's + 63 women's outcomes are independently reconstructed and matched to submission IDs, reproducing the v26 Kaggle Brier exactly.

### Major modeling conclusions

- a reliability-gated Torvik correction improved all **3/3** recent confirmation seasons and became v26;
- broad internal-strength expansions did not transfer reliably;
- historical BPI reconstruction was blocked by archive/timing limitations rather than relaxed into leakage;
- historical timestamped market odds were blocked because pre-deadline quote timing could not be established at sufficient coverage;
- simple recent-rotation features were rejected;
- richer boxscore player-impact features were rejected;
- a dynamic opponent-adjusted offense/defense/pace/margin representation was rejected before final promotion.

Negative results are retained because they narrow the search space and prevent repeated spending on high-correlation ideas.

## Exact metric boundary

The official metric is **Brier score**, lower is better.

| Population | Games | Brier |
|---|---:|---:|
| Men | 63 | 0.1445997537 |
| Women | 63 | 0.0966919150 |
| **Combined** | **126** | **0.1206458343** |

This exact local scorer is now a reusable post-freeze audit tool for future clean candidates.

## 2027 source contract

Future supplemental sources follow a stricter contract:

- preserve raw source objects before transformation;
- record source URL and capture timestamp;
- keep checksums and mapping state;
- distinguish source availability from model eligibility;
- quarantine post-cutoff or timing-ambiguous observations;
- represent unavailable future inputs as **WAITING_FOR_TARGET_DATA**;
- never copy 2026 values into 2027;
- never relabel an owned proxy as KenPom, EvanMiya/BPR, or medical injury data.

## Current open frontier

The highest-value remaining public-safe source gap is **independently reconstructed NCAA NET/WNCAA NET history**, especially the missing/uncanonical women-specific years. The next private milestone tests whether official NET/WAB/quadrant/road information adds stable historical signal beyond v26.

## Public/private boundary

This repository is an **employer-facing, semi-reproducible research case study**.

Published:
- aggregate validation results;
- source/provenance states;
- public-safe experiment ledgers;
- analytical portfolio artifacts;
- exact metric/evaluation definitions;
- negative-result conclusions;
- 2027 acquisition contracts.

Intentionally withheld:
- row-level private predictions;
- candidate submission CSVs;
- raw supplemental source archives;
- fitted private models;
- exact private correction gates/weights;
- source-specific identity logic;
- credentials;
- private orchestration archives;
- canonical AWS paths.
