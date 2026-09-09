# Final observed results

**Best Brier: 0.1222672.** All 70 current submissions have been scored. Both displayed
Kaggle columns agree. These were late submissions, and the final model was selected
retrospectively. The original frozen development reference remains preserved.

| Rank | Model pair | Observed Brier |
|---|---|---:|
| 1 | Original pooled XGBoost T=0.90 + women’s conference logistic C=1.0, T=1.10 | **0.1222672** |
| 2 | Lighter-regularization pooled XGBoost T=0.90 + original women’s logistic | 0.1223389 |
| 3 | 64-input pooled XGBoost T=0.90 + original women’s logistic | 0.1224358 |
| 4 | Original pooled XGBoost T=0.90 + original women’s logistic | 0.1225463 |
| 5 | Lighter-regularization pooled XGBoost T=1.00 + original women’s logistic | 0.1227222 |
| 6 | 64-input pooled XGBoost T=1.00 + original women’s logistic | 0.1227821 |

![Final score leaders](leaders.png)

The winner improves Brier by **0.0002791** from the previous 58-file best and
**0.0006747** from the original 50-file best. The 240-tree challengers were worse;
women’s dynamic features were also worse. The historically preferred women’s
C=0.30/T=1.10 choice scored 0.1231223; the final winner was third in that historical
shortlist. This disagreement matters: historical selection and observed Kaggle
scores must not be presented as interchangeable evidence.

## Exact winning model

`m_pooled_xgboost_t090__w_conference_c100_t110.csv`

| Property | Men | Women |
|---|---|---|
| Family | XGBoost | Logistic regression |
| Training population | Pooled men and women | Women only |
| Training seasons | 2013–2025, excluding 2020 | 2013–2025, excluding 2020 |
| Physical training games | 1,575 | 772 |
| Feature block | Common full bank, training-only screen | Conference |
| Retained inputs | 128 per route | 16 seeded / 15 seed-free |
| Main settings | 120 trees, depth 2, learning rate 0.04, child weight 10, lambda 10 | C=1.0 |
| Temperature | 0.90 | 1.10 |

The men’s component is `c_7808f53a9ebd1b6bf13a` / `xgboost_full_2` in the
[production recipe](../prediction_production/recipe.json). The women’s models are
`conference_c100` in the [final fit audit](../women_challengers/final_fit_audits.json).
Both have separate seeded and seed-free routes, with seed inputs removed before
seed-free screening. The winning pooled stream excludes Massey and retained no
coach inputs; comparable women’s rating/coach histories are unavailable.

The CSV contains **132,133 rows**, **4,638,012 bytes**, and SHA-256
`b7704da76ea2b48839e1fdfaa32d593cf0cc23171d3b67e13987f152342bc92e`.
The [machine-readable final record](summary.json) ties this byte identity to the
model audits and source ledger. No 2026 tournament outcomes entered fitting or
prediction. Observed 2026 scores informed later hypotheses and final selection.

## Complete score history and charts

The [70-row ledger](kaggle_scores.csv) records filenames, scores, batches, hashes
and provenance. The [latest screenshot transcription](latest_scores.csv) contains
12 new observations and eight repeated observations; all eight repetitions match
the preserved earlier ledger. [Screenshot evidence](score_evidence.png) and
[provenance](provenance.json) retain the source, checksum and recording time.
Exact submission IDs and timestamps were not supplied and are not invented.

![Completed score progression](progression.png)

Download and open [results.html](results.html) in a browser for the self-contained
Plotly report: the six leaders, cumulative batch progress, all 70 individual
observations and a complete table. Notebook 04 embeds the same interactive charts
with static GitHub previews. Scores are shown to the supplied seven-decimal precision.

The original 18 legacy score observations remain in their [separate ledger](../submission_portfolio/kaggle_scores.csv).
Immutable generation manifests retain their generation-time `unscored` field;
this final observed ledger is authoritative for the completed submission status.

## Delivery and recovery

`submissions/final_submissions.zip` contains all 70 CSVs at the ZIP root, followed
by the final score ledger, model summary and provenance. Its [collection receipt](collection.json)
verifies original file bytes, unique filenames, all official rows and zero new fits.
The three earlier archives remain unchanged. [Storage records](storage.json) identify
the final private download by checksum and the original archives by S3 version and checksum.

Notebook 04 can repackage the collection from the three preserved archives through its explicit default-off control. The combined download is also delivered directly to the project owner.
Generation and recovery are separate actions; ordinary notebook review creates
no submissions and does not retrain. To repackage from the three preserved archives:

```bash
uv run --locked python scripts/final_report.py --check
uv run --locked python scripts/final_report.py --archives \
  submissions/submission_collection.zip \
  submissions/prediction_challengers.zip \
  submissions/women_challengers.zip
```

Content-verified packaging checkpoints reuse a completed collection. Public code,
score evidence and executed notebooks are committed in Git; full prediction and
model archives are preserved privately. The required workflow checks the final
ledger, prior release evidence, model boundaries, native notebook execution and
checkpoint reuse. **This bounded project release is complete.**
