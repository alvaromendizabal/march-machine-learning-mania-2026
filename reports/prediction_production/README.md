# Current prediction production

**50 distinct 2026 prediction files have been generated and validated**, each with
132,133 template rows. The run completed 33 model fits, one explicit neutral route,
259 prediction chunks and 344 checkpoints in 518.491 seconds. It generated
6,606,650 probabilities without using 2026 outcomes or uploading to Kaggle.

[summary.json](summary.json) records the completion result;
[submission_manifest.csv](submission_manifest.csv) identifies every complete CSV.
All 33 saved models reproduced every probability exactly across 259 chunks;
[saved_model_verification.json](saved_model_verification.json) records the check.
A fresh local archive restore reused all 344 checkpoints with zero new fits and
unchanged CSV bytes, recorded in [recovery.json](recovery.json).

The 80,110,551-byte archive contains all fifty CSVs, fitted models, checkpoints and
source provenance. Its SHA-256 and exact intended private S3 destination are in
[storage.json](storage.json). Automatic approval review requires specific approval
for that upload. **The upload and recovery from S3 have not completed.** The verified
archive is available with the project handoff while that authorization is pending.

The [development catalog](../prediction_portfolio/README.md) defines ten men's
procedures crossed with five women's procedures. [recipe.json](recipe.json)
freezes their concrete parameters and blend weights using only recorded
2016–2019 and 2021 out-of-fold predictions. Seventeen distinct components share
their fitted models across the fifty pairings. Final training uses 2013–2025,
excluding the cancelled 2020 tournament. No 2026 outcomes enter selection or fits.

The source archives are the current **3,106-feature** matrix and its matching model
comparison, with immutable S3 versions and full-object/member SHA-256 checksums in
[input_receipts.json](input_receipts.json). Recovery reads only the needed ZIP
members. Matchup features are reconstructed from the verified team snapshots in
512-row chunks; the full multi-gigabyte matchup matrix is not required on disk.

## Reproduce

Use the locked environment described in the repository README. Public checks need
no private data or AWS account:

```bash
uv run --locked python -m march_mania.publication.production_release --check
```

With access to the existing private artifact bucket:

```bash
uv run --locked python -m march_mania.publication.production --restore-inputs
uv run --locked python -m march_mania.publication.production --generate
```

Generation requires the committed recipe and input-member receipts to match. Each
component/feature route, prediction chunk and final CSV is checkpointed. Completed
models are reused; changed sources, inputs or environments create a distinct run.
Once the completed archive is published, a fresh matching run restores it
automatically before generation. `production_release --recover` also supports
an explicitly downloaded archive via `--archive`.

CSV files live under `outputs/prediction_production/<fingerprint>/csv_<candidate>/`.
The declared reference is `m_rank_logistic__w_logistic`; generating the sensitivity
variants does not promote a new default.
The public submission manifest records the exact path, row count, byte size and
SHA-256 of each complete file. Fitted models are in the handoff archive; the existing
private input archives remain version-pinned. Predictions for 4,556 seeded-team
pairs use the seeded route; the other 127,577 template pairs use seed-free fits.

For independent model verification, pass the restored run directory to:

```bash
uv run --locked python scripts/verify_prediction_production.py \
  --run PATH_TO_RESTORED_RUN --receipt outputs/saved_model_verification.json
```

This recomputes every chunk from saved models and requires exact equality with
all archived stream probabilities. It also rechecks the fifty complete CSV
checksums. No fitting occurs in this verification path.

## Interpretation

These are retrospective sensitivity candidates, not fifty independent discoveries.
The explored development years and consumed 2022–2025 benchmark do not become a
fresh holdout. Generating files does not establish better forecasting accuracy or
record an actual Kaggle upload.

Pairs with an unavailable seed use a separately fitted route with every
seed-dependent input removed. The seed-only blend component contributes exactly
0.5 on that route, retaining its frozen weight. This unseeded-team route lacks
matched tournament OOF validation. Identity calibration is retained throughout.

XGBoost's float32 outputs are promoted before symmetric averaging so reversing
team order complements the forecast at float64 precision. This corrects production
rounding; it does not rewrite archived OOF evidence or change fitted parameters.
