# NCAA tournament forecasting
### A feature-first research case study · Alvaro Mendizabal

Probabilistic forecasts for men's and women's NCAA tournament matchups, with temporal validation, explicit leakage boundaries, calibrated-performance diagnostics, and reproducible experiment records.

| Observed submitted Brier | Historical research target | Interpretation |
|---:|---:|---|
| **0.1222672** | **0.1097454** | User-reported late-submission result and historical target; not a claim of current leaderboard rank |

## Explore the work

[Research case study](docs/CASE_STUDY.md) · [Experiment ledger](docs/EXPERIMENT_LEDGER.md) · [Results notebook](notebooks/portfolio_results.ipynb) · [Evidence provenance](data/evidence_sources.json) · [Disclosure boundary](docs/DISCLOSURE.md)

### What this project demonstrates

The work spans hypothesis formation, season-local feature engineering, temporal validation, model comparison, probability diagnostics, checkpoint reuse, debugging, and preservation of negative results. Experiments distinguish information gains from regularization effects and compare each candidate family with an explicit reference.

### What the results establish

An established ranking-consensus addition improved the compact men's reference in three of four 2022–2025 seasons, with mean Brier change approximately −0.0006879. Numerous more elaborate feature families did not pass their predefined stability criteria. This is exploratory historical evidence: the years were already used during development. It is not a demonstration that the current production submission improved.

The blocks/free-throw experiment completed its scientific run and ten charts. Its mean incremental change was −0.0004715, just short of its preset threshold. The returned collection lacks a completed round 16 report; its recovery is not confirmed. Rounds 18 and 19 completed but worsened mean incremental Brier by 0.0010283 and 0.0003371 respectively. Neither was promoted. No fabricated results are supplied for unfinished rounds.

### Public evidence, private implementation

This repository contains a report-only notebook, aggregate metrics, methodology and limitations. Training code, exact engineered feature formulas, weights, private checkpoints, raw competition data, and game-level predictions are not distributed here. Technical details may be reviewed with prospective employers under an appropriate access arrangement.

The notebook's only code renders aggregate evidence. Hiding notebook cells is not used as a security measure. The implementation is maintained separately; this repository does not claim full public pipeline reproducibility.

### Reading the evidence

Lower Brier is better. Compare arms only within the same experiment, population and season. Historical validation and the late-submission score use different evaluation populations. Arm labels in public tables deliberately omit private recipe details. The source manifest identifies the supplied evidence; it is not a signed Kaggle submission receipt.

**Status:** ongoing research, not a claimed leaderboard record. New rounds are marked prepared until executed evidence is returned. See [rights and prior-release scope](RIGHTS.md).
