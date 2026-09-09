# Current-development prediction portfolio

This catalog is the first release toward **50 reproducible 2026 submission files**.
It contains 50 candidate **plans**, combining ten men's procedures with five women's
procedures already evaluated in the current research. **No new submission files or
final models have been produced by this release.**

Start with the [candidate catalog](candidate_catalog.csv). Each row identifies its
two component streams, both Brier averages, supporting diagnostics, and distance
from the existing separate logistic reference procedures. The catalog is ordered
by its declared configuration, not by a claimed submission priority.

| Men's procedures | Women's procedures |
|---|---|
| Separate logistic, histogram boosting, XGBoost, LightGBM | Separate logistic, histogram boosting, XGBoost, LightGBM |
| Separate ranking-aware logistic, XGBoost, LightGBM | Pooled common-feature logistic |
| Pooled common-feature blend, histogram boosting, XGBoost | |

The men's pooled blend and women's separate logistic include the best observed
development streams. Their presence does not promote a new final estimator. Broad
and compact alternatives remain visible as sensitivity comparisons. The catalog
does not reopen feature research, invent probability perturbations, or use the
older leaderboard-informed temperature grids.

## How to read the evidence

Every plan has forecasts for the same **649 physical games**: 334 men's and 315
women's games in 2016–2019 and 2021. Parameters were selected using earlier seasons
within the recorded research. The public [selection history](selection_history.csv)
contains 95 component decisions for the 15 streams. The pooled blend is reconstructed
from the published raw component predictions and convex weights before admission.

- `brier` weights every game equally, including in the combined men's/women's score.
- `mean_season_brier` weights each of the five seasons equally. It is not the mean
  of the men's and women's scores. The catalog also reports both definitions for
  each gender.
- Log loss, ROC AUC, average precision and calibration error supplement Brier.
  [Annual metrics](metrics_by_season.csv) expose season variation.
- [Pairwise diversity](prediction_diversity.csv) measures all 1,225 pairs. Exact
  duplicate prediction vectors are rejected. Distinct files can still be highly
  correlated; 50 pairings are not 50 independent experiments.

These are **nested selection-procedure scores on already-explored development
years**, not validation of a single frozen final estimator. The portfolio itself
was assembled retrospectively. It does not establish an unbiased winning recipe
or superior forecasting accuracy. The consumed 2022–2025 benchmark and 2026 labels
do not enter this catalog.

## Reproduce the catalog

```bash
uv run --locked python -m march_mania.publication.portfolio --check
```

This recomputes all four tables from committed, checksum-verified research. It needs
no AWS account, raw competition data, fitted models or new training. To intentionally
publish revised catalog evidence after a reviewed code/configuration change:

```bash
uv run --locked python -m march_mania.publication.portfolio --write
```

The [manifest](manifest.json) binds the source, configuration, feature/model run IDs,
upstream report hashes and exact output bytes. CI checks the saved files against a
fresh computation. The default notebook workflow continues to review the research;
generating submission files remains an explicit later operation.

## Next release

Freeze concrete model specifications using only the declared pre-2022 development
predictions, then fit each unique component once through 2025. Reuse those components
across pairings. Pooled components need their actual common-feature training
population, and every procedure needs an explicit route for unseeded teams.

Generate and validate the 50 complete Stage 2 CSVs, record exact checksums and model
lineage, reject duplicate final probability vectors, archive models and files, and
prove fresh-directory recovery without new fits. Development-vector uniqueness
does not guarantee final-vector uniqueness. Generation is separate from an accepted
Kaggle upload. The [completion plan](../../docs/completion_plan.md) records the gates.
