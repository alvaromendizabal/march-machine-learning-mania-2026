# Complete current submission collection

This collection preserves all **58 submitted files** from the current research
lineage: 50 original model pairs and eight subsequent probability adjustments.
Every CSV keeps its unique model name and exact original bytes. Each contains
132,133 matchup rows. `kaggle_scores.csv` records public and private Brier scores,
CSV hashes, source screenshots and observation dates.

The best observed score is **0.1225463** for
`m_pooled_xgboost_t090__w_logistic.csv`, compared with the original best of
0.1229419. The absolute improvement is 0.0003956. Lower Brier is better.
The temperature-0.90 adjustment sharpens men's probabilities; women's logistic
predictions are unchanged. All eight adjustments now have recorded Kaggle scores.

These are late, retrospective observations. Temperature 0.90 was worse on the
historical development games, illustrating that historical and single-tournament
preferences can disagree. Its 2026 score does not justify treating it as an
independently validated calibration choice.

The ZIP also preserves the separate 18-row legacy score ledger. Those earlier
model lineages and prediction archives retain their original identities; their
prediction CSVs are not relabeled as current-model files or included among these 58.
The original and refinement recipes accompany the score ledger.

Extract `submission_collection.zip`. Upload a chosen prediction CSV individually
to Kaggle. The score ledger, recipe and manifest files are documentation, not
prediction submissions. These 58 candidates already have observed scores.

Reproduce the collection with the verified original downloads available:

```bash
uv run --locked python -m march_mania.publication.scoreboard --check
uv run --locked python -m march_mania.publication.scoreboard --package
```

Packaging verifies source ZIP hashes, row IDs, probabilities, individual CSV
checksums and the resulting ZIP. Repeating it reuses the completed checkpoint.
It performs no training and sends no Kaggle upload.
