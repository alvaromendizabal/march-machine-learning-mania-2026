# Notebook 05 evidence

The first official-data benchmark completed **120 folds in 31.545 seconds**.
Its original AWS run contains 533 artifacts. The eight raw-file hashes and the
result-object hashes were verified against S3. `run.json` records the original
manifest, completion summary and checksums for the result tables in this folder.

Strength logistic leads both compact benchmarks: mean season Brier 0.191268 for
men and 0.144308 for women. The full 25-feature candidate worsens both scores.
These are retrospective development results, not new Kaggle submission scores.

`validation.json` preserves the original implementation gate: 39 synthetic tests
and 90% coverage across its four modules. It is historical engineering evidence.
Current rebuilt-store validation is recorded in `../feature_store/validation.json`.

Canonical notebook 05 now displays the completed run. Rebuilt notebook 02 tests
additional feature families and records the next experiments in `../feature_store`.
Static notebook plots have been rendered and inspected. CI executes both review
notebooks in their actual Jupyter kernel.
