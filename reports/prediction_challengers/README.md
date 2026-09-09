# Six retrained challenger submissions

This is the owner's requested, bounded follow-up: three pooled XGBoost recipes,
each with temperature 1.00 (raw probabilities) and 0.90 (more confident). The
64-feature pair is the priority. These are **six new, unscored CSVs**; no Kaggle
upload is performed. The prior 58 scored files and their exact bytes remain in
the [preserved collection](../submission_scores/README.md).

| Priority | Submission CSV | Change from the original pooled XGBoost |
| --- | --- | --- |
| 1 | `m_pooled_xgboost_f064_t090__w_logistic.csv` | 64 features, temperature 0.90 |
| 2 | `m_pooled_xgboost_f064_t100__w_logistic.csv` | 64 features, raw probabilities |
| 3 | `m_pooled_xgboost_lighter_t090__w_logistic.csv` | Child weight 5 / lambda 5, temperature 0.90 |
| 4 | `m_pooled_xgboost_lighter_t100__w_logistic.csv` | Child weight 5 / lambda 5, raw probabilities |
| 5 | `m_pooled_xgboost_trees240_t090__w_logistic.csv` | 240 trees, temperature 0.90 |
| 6 | `m_pooled_xgboost_trees240_t100__w_logistic.csv` | 240 trees, raw probabilities |

Extract `submissions/prediction_challengers.zip` and submit each chosen CSV
separately. The ZIP also contains the manifest and recipe; those are provenance
files. The [manifest](submission_manifest.csv) records all six SHA-256 checksums,
row counts, unchanged women's-row hash, and mean absolute change in men's
probabilities. Each file contains 132,133 rows in the exact official template order.

The three recipes use the completed [bounded historical study](../xgboost_retraining/README.md).
On its 334 men's development games, unadjusted game-weighted Brier was 0.18433349
for 64 features, 0.18508786 for lighter regularization, and 0.18511636 for 240 trees,
against 0.18513422 for the original pooled recipe. These are already-explored
historical results, **not combined 2026 Kaggle scores**. The differences are small;
season intervals include zero. Temperature 0.90 is an explicit sensitivity
comparison motivated by the previously observed best Kaggle score, 0.1225463.

## Final fitting and verification

- Final models use 2013–2025 pooled men's and women's tournament games, excluding
  canceled 2020. Every feature screen uses only those training observations.
- Three models each require a seeded and seed-free route: six final estimators.
  Every seed-derived input is removed before seed-free screening.
- These common pooled recipes exclude Massey. The matched men's Massey/coach
  comparisons are documented in the historical study, not conflated with this batch.
- Women's predictions are reused byte-for-byte from the checksum-pinned original
  logistic CSV. No women's estimator is retrained.
- No 2026 tournament outcome enters fitting or prediction. Model reloads reproduce
  probabilities exactly; team-swapped probabilities sum to one. Export checks
  validate finite probabilities, bounds, IDs, ordering, serialization and ZIP hashes.
- Final seeded forecasts and seed-free forecasts use pre-tournament 2026 team
  snapshots. Seed-free routes lack matched tournament validation.

[Fit audits](fit_audits.json), [routing counts](routes.csv), and the
[generation receipt](summary.json) record the executed batch. The private versioned
AWS archive and checksum verification are recorded in [storage.json](storage.json);
[recovery.json](recovery.json) records checkpoint reuse with no new fitting.
All earlier scores remain in the separate score ledger; these six await results.

## Reproduce

Notebook 04 has an explicit `GENERATE_CHALLENGERS = False` control and displays
the completed generation in ordinary review mode. To execute from the command line,
first restore the original production ZIP and the pinned feature-store inputs:

```bash
uv run --locked python -m march_mania.publication.challengers --generate \
  --inputs outputs/retraining_inputs \
  --source-archive submissions/prediction_portfolio.zip
uv run --locked python -m march_mania.publication.challengers --check
```

Matching source, configuration, environment and input hashes reuse verified
fit, prediction and export checkpoints. The existing frozen inference reference
is not promoted or rewritten by this exploratory batch.
