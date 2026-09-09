# Six women’s challenger submissions

Women’s separate logistic regression won every model pairing in the observed 50-file batch. We now test whether nearby regularization and confidence choices improve that stream. All six new files keep men’s exact prediction rows from `m_pooled_xgboost_t090__w_logistic.csv`, the observed **0.1225463** combined Brier leader.

All six files have now been scored. The C=1.0 conference model at temperature 1.10 won at **0.1222672** combined Brier; [the final report](../final_results/README.md) records every outcome. Extract `submissions/women_challengers.zip` and submit individual model CSVs. The original priority column records the historical ordering; its first choice did not win on Kaggle. The ZIP’s manifest and recipe provide provenance; neither is a Kaggle submission.

| Priority | Submission CSV | Women’s historical Brier |
| --- | --- | ---: |
| 1 | `m_pooled_xgboost_t090__w_conference_c030_t110.csv` | 0.14216685 |
| 2 | `m_pooled_xgboost_t090__w_conference_c010_t110.csv` | 0.14288091 |
| 3 | `m_pooled_xgboost_t090__w_conference_c100_t110.csv` | 0.14295785 |
| 4 | `m_pooled_xgboost_t090__w_dynamic_c030_t110.csv` | 0.14311639 |
| 5 | `m_pooled_xgboost_t090__w_conference_c010_t100.csv` | 0.14333128 |
| 6 | `m_pooled_xgboost_t090__w_dynamic_c030_t100.csv` | 0.14386673 |

## What the historical comparison means

The unchanged women’s reference is conference logistic **C=0.30**, at **0.14289055** Brier. Temperature 1.10 softens probabilities toward 0.5; the leading alternative reaches **0.14216685**, a difference of **−0.00072370**. Its exploratory 95% season-bootstrap interval is **[−0.00150146, −0.00004390]**, unadjusted for selection and multiple comparisons. This is a small retrospective signal, not a guarantee. Only the top two alternatives beat the unchanged reference historically; priority 2 is essentially tied.

Five raw recipes at three temperatures make 15 fixed hypotheses: conference logistic C=0.10, 0.30, 1.00 and 3.00, plus dynamic logistic C=0.30; temperatures are 0.90, 1.00 and 1.10. The top six alternatives exclude the existing reference and duplicate forecast vectors. C=3.00 did not enter the final batch. The two C=0.30 control recipes reuse 14 saved candidate folds; the other three require 21 historical fits.

All candidates use identical women’s games. Training starts in 2013 and always precedes the validation year. The 2014–2015 folds supply selection warmup; the reported development population contains 315 games in 2016–2019 and 2021. Equal game counts per year make game-weighted and mean-season Brier equal here. These years have already been explored. The complete [leaderboard](leaderboard.csv), [annual metrics](metrics_by_season.csv), [predictions](predictions.csv) and [fit audits](fit_audits.json) remain reviewable.

Selecting a recipe using only strictly earlier out-of-fold seasons yields **0.14527664** Brier, worse than the fixed reference. The [selection record](selection.csv) keeps that negative finding visible. Fixed historical ranking is therefore only an exploratory submission priority. No 2026 outcomes enter fitting or selection, and the frozen production reference is retained.

## Final fitting, data boundaries and preservation

Three selected new raw recipes are retrained on women’s tournament games from 2013–2025, excluding canceled 2020. Each has seeded and seed-free routes, making six final estimators. Every seed-derived input is removed before the seed-free training screen. The reference C=0.30 conference stream reuses the exact saved women’s probabilities, so its leading temperature alternative needs no new estimator.

Massey and coach histories are unavailable for women in this snapshot. The women’s conference/dynamic models do not use those men’s inputs. The earlier matched men’s comparisons remain in [the retraining study](../xgboost_retraining/README.md). Final predictions use pre-tournament 2026 snapshots. The seed-free route has no matched tournament validation.

Each CSV has 132,133 rows in official template order. Export verifies unique IDs, finite bounded probabilities, numeric serialization, distinct file hashes, archive contents and byte-identical men’s rows. Saved models reproduce predictions exactly after reload. Tests exercise temporal mutation, game uniqueness, forward selection, team-swap symmetry, corrupted checkpoints, resume and malformed exports.

The [generation receipt](generation.json), [final fit audits](final_fit_audits.json), [routes](routes.csv), [submission manifest](submission_manifest.csv), [recovery record](recovery.json) and [private storage receipt](storage.json) preserve this batch. The prior 58 scored files remain in their original collection; the earlier six men’s challengers remain in their original ZIP. The final inventory is **70 current CSVs, all scored**. Generation manifests retain their original `unscored` status; the final observed ledger records subsequent outcomes. Prior score ledgers and original prediction bytes are preserved.

## Reproduce

Notebook 03 exposes `RUN_WOMEN_STUDY = False`; notebook 04 exposes `GENERATE_WOMEN_CHALLENGERS = False`. Routine review recomputes metrics and checks receipts without fitting or creating submission CSVs. To run explicitly after restoring the pinned production inputs and refinement ZIP:

```bash
uv run --locked python scripts/women_challengers.py --study
uv run --locked python scripts/women_challengers.py --generate \
  --source-archive submissions/prediction_refinement.zip
uv run --locked python scripts/women_challengers.py --check
```

The independent runner in `scripts/women_challengers.py` reuses the existing modeling and production helpers, with its own configuration/source/dependency fingerprints. Keeping it separate preserves the completed men’s study’s source inventory. The model, prediction and export tasks have verified completion checkpoints, UTC events and heartbeats. Matching inputs and code reuse completed work. No automatic Kaggle upload is performed.
