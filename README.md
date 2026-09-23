# NCAA tournament forecasting | ML engineering case study

**Alvaro Mendizabal · probability forecasting · controlled research · cloud ML engineering**

## Achieved result: 0.1089408 Brier

The retained release achieved **0.1089408 Brier** in recorded post-competition Kaggle scoring, numerically below the published 2026 winning benchmark of **0.1097454** by **0.0008046**. This is a late-submission comparison, not an original competition placement.

**[Open the executed case study](portfolio/current_research.ipynb)** ·
[Employer walkthrough](docs/employer_walkthrough.md) ·
[Current evidence](reports/current_research/release_decision.json)

| Scored milestone | Brier | Decision |
|---|---:|---|
| Previous simplified release | 0.1098691 | Superseded |
| Margin-ensemble release | 0.1094899 | Superseded |
| Full market overlay | 0.1098037 | Rejected |
| Round-1-only market overlay | 0.1103527 | Rejected |
| **Retained futures-informed release** | **0.1089408** | **Current champion** |

![Recorded score progression](reports/current_research/figures/release_scores.png)

## What the project demonstrates

**Research judgment.** The project did not equate more features or more models with better forecasting. It rejected feature bundles, calibration variants, alternative losses, sparse-ranking variants, a full market overlay, and a Round-1-only market overlay. The strongest scored system combines a compact statistical reference with a complementary score-margin component and a bounded championship-strength information layer.

**Controlled experimentation.** Whole-season historical tests, matched controls, protected-row contracts, and one-factor score tests separate mechanisms whenever practical. The final market component was isolated only after two disjoint scored variants established which information source helped; that is explicitly post-competition and post-hoc evidence, not an independent prospective test.

**Reliable execution.** Prediction files are checksum-locked, completed checkpoints are reused, candidate scope is verified row by row, and submission attempts are at-most-once. The latest run performed zero model fits, changed 1,986 men’s rows, protected the other 130,147 rows, and recorded a single COMPLETE submission.

**Technical communication.** The executed case-study notebook exposes scored progression, negative results, scope protection, and limitations with saved inline Plotly figures. A reviewer does not need AWS access to understand the work.

## Public scope

This repository is an **employer-facing case study**, not a distribution of the current private training system. New model binaries, feature formulas, source-specific production code, private data, tuning recipes, and AWS working changes are intentionally excluded from this publication. Earlier public code and licenses remain in repository history; this update does not make previously published material confidential.

The 2026 result is a development milestone. For 2027, the stronger standard is prospective: freeze the private champion, timestamp inputs and forecasts before outcomes, audit season-specific assumptions, and evaluate against genuinely future games.

The compact reference is credited to [Harrison Horan’s first-place solution](https://www.kaggle.com/c/march-machine-learning-mania-2026/writeups/march-machine-learning-mania-2026-1st-place-solut). The market-information research was informed by the public third-place solution. The achieved post-competition result does not imply an original competition rank, medal, prize, or guaranteed 2027 advantage.
