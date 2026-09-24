# NCAA tournament forecasting | ML engineering case study

**Alvaro Mendizabal · probability forecasting · controlled research · cloud ML engineering**

## Current verified boundary: 0.1072824 Brier

The strongest retained private release achieved **0.1072824 Brier** in recorded post-competition Kaggle scoring. The published 2026 winning benchmark was **0.1097454**, so the retained late score is numerically lower by **0.0024630** (about **2.24% lower Brier**). This is benchmark-informed post-competition research, not an original competition placement, medal, or prize.

The active stretch target is **0.0900000**. The remaining absolute reduction is **0.0172824**, so the research program is now focused on structural capability gains rather than cosmetic tuning.

**[Open the current frontier notebook](portfolio/frontier_research.ipynb)** ·
[Employer walkthrough](docs/employer_walkthrough.md) ·
[Current research boundary](docs/current_research.md) ·
[Frontier and reproduction matrix](docs/frontier_research.md)

| Scored milestone | Brier | Status |
|---|---:|---|
| Previous simplified release | 0.1098691 | Superseded |
| Margin-ensemble release | 0.1094899 | Superseded |
| Futures-informed public release | 0.1089408 | Superseded privately |
| **Retained private post-competition champion** | **0.1072824** | **Current scored boundary** |
| Stretch target | 0.0900000 | Research objective, not achieved |

## Latest frontier milestone

A chronology-safe residual-family study produced a new **unscored** challenger without using 2026 tournament outcomes for selection or fitting. Eight coherent residual representations were evaluated on season-grouped historical evidence. The selected `volume_plus_differences` family improved the base margin reference by **0.0037810 Brier** across the six-season selection window, won **5 of 6 seasons**, and stayed within the predeclared worst-season guardrail.

The larger `all_residual` representation had a stronger aggregate mean gain (**0.0049982**) but violated the stability gate because its worst season deteriorated by **0.0031222**. It was rejected. That decision is important: the research process optimizes for stable, transferable evidence rather than maximizing one summary statistic.

The resulting frozen challenger:

- performed **90 new tree fits** during the candidate-build milestone;
- changes **2,278 approved men's rows**;
- preserves **129,855 rows byte-for-byte**, including all **65,703 women's rows**;
- passed **12 model/integrity tests**;
- produced an executed notebook with **6 inline Plotly outputs**;
- made **no Kaggle submission** in the candidate-build milestone.

Until that exact challenger receives a separately authorized score, **0.1072824 remains the scored champion**.

## What the project demonstrates

**Frontier-aware research judgment.** Leading public mechanisms are independently adapted rather than copied wholesale. The project now contains a compact statistical tournament reference, a complementary score-margin system, bounded market information, chronology-safe residual-family selection, and prospective external-data collection. The public reproduction matrix states which mechanisms are validated, rejected, adapted, blocked, or still missing.

**Validation discipline.** Season-grouped and nested selection, predeclared promotion gates, protected-row contracts, and strict point-in-time rules are used to prevent easy but misleading gains. Stronger average performance can be rejected when its year-level stability is unacceptable.

**Leakage honesty.** The 2026 futures observations used in retrospective scoring were pinned from a post-competition public source, not independently reconstructed from raw timestamped pre-deadline captures. They are therefore treated as a fixed retrospective component and excluded from residual-model training and configuration selection. The 2027 collector architecture uses raw-first immutable snapshots and explicit target-season eligibility gates.

**Engineering discipline.** Prediction artifacts are checksummed; candidates preserve protected rows exactly; experiments are bounded, restartable, and test-gated; notebooks retain inline Plotly evidence after reopen; and public GitHub remains intentionally separated from private AWS research state.

## 2027 prospective infrastructure

The project has moved beyond retrospective modeling into prospective data engineering:

- **Kalshi:** raw-first men's and women's championship-market collection is operational;
- **ESPN:** collector is operational, with stale-season rows explicitly quarantined instead of silently admitted;
- **BartTorvik:** men's ratings and schedule capture is operational;
- **Remaining information gaps:** roster continuity, transfer value, player availability/injuries, target-season women's external ratings, and a stronger heterogeneous ensemble.

These gaps define the next frontier. The goal is not to keep producing tiny variants of the same model; it is to add information and modeling capabilities that plausibly close the remaining distance to 0.09.

## Public scope

This repository is an **employer-facing and research-frontier case study**, not a distribution of the current private competition system. Current model binaries, candidate prediction bytes, private datasets, exact production feature formulas, source-specific private logic, tuning recipes, credentials, and AWS working changes remain outside the public release.

Previously published source and licenses remain in repository history. The public artifacts expose the research questions, controlled evidence, engineering decisions, negative results, provenance limitations, and forward research plan without pretending the private system is fully reproducible from GitHub alone.

The compact reference is credited to [Harrison Horan's first-place solution](https://www.kaggle.com/c/march-machine-learning-mania-2026/writeups/march-machine-learning-mania-2026-1st-place-solut). Market-information research was informed by the public [third-place solution repository](https://github.com/kevin1000/march-mania-2026-3rd-place). Those sources inform mechanisms; the implementation and validation decisions in this project are independent.
