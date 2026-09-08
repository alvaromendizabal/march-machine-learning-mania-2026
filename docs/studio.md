# March Mania: run, review, and generate your own file

## Read the project

Employers can open the saved notebook outputs without AWS, data downloads or a kernel.
Start with **03** for model evaluation and **05** for current research conclusions;
**00 → 01 → 02** document data, chronological validation and feature engineering.
**04** evaluates the current lineage on the consumed benchmark and contains the default-off generation cell.

The old 120-fold research and August score log are historical records, not results from
the rebuilt 3,106-candidate matrix. Notebook 05 verifies the 02 → 03 dependency and compares
matching forecast rows. Report execution and model training are different operations.

## Update your existing Studio checkout

Save and close notebooks, then run:

```bash
cd "$HOME/march-machine-learning-mania-2026" &&
python3 scripts/update.py
```

The updater preserves edited tracked notebooks in a named Git stash, fast-forwards main,
installs the locked environment and runs checks. It stops for unrelated edits or divergence.
Do not delete raw data, output directories or stashes to bypass a stopped update. Do not pop
old rendered notebooks over newly published ones without reviewing their differences.

## Train from notebooks

Open `02_feature_store_and_diagnostics.ipynb`. In its first code cell replace the mode
assignment with:

```python
MODE = "train"
```

Run all cells in **02**, then do the same in
`03_model_comparison_and_diagnostics.ipynb`. Notebook 02 builds or verifies/reuses features.
Notebook 03 fits or restores estimator checkpoints using the exact current matrix. Then run
notebook 04 in train mode to evaluate the current retrospective benchmark without exporting
a submission.
Changed raw inputs or feature code require 02 before 03; changed model inputs require 03
before final generation. Existing local `data/kaggle/raw` is preferred over the recorded
archive, so genuinely new data is not silently replaced with an old snapshot.

The equivalent terminal operation executes the canonical notebook code:

```bash
MARCH_NOTEBOOK_MODE=train .venv/bin/python scripts/notebook.py --execute --publish --timeout 5400
```

This does not enable submission generation. Completed estimators are reused only for matching
fingerprints and verified bytes. An interrupted estimator restarts that fit; an interrupted
notebook starts from its first cell and calls the resumable stages again.

To render review outputs without initiating training:

```bash
.venv/bin/python scripts/notebook.py --execute --publish
```

Keep `MODE = execution_mode()` as the committed notebook default. It selects review mode
unless the explicit training environment variable is present. The mode is part of the
notebook cache identity, so a previous review cannot count as a training execution.

## Generate and download your own submission

After 02 and 03 have completed in your workspace, open
`04_locked_benchmark_and_final_submission.ipynb`. Its final cell defaults to:

```python
GENERATE_SUBMISSION = False
```

Change it to `True` and run that cell when ready. The code verifies the feature/model
handoff, fits or restores the declared final recipe, produces the official template in its
original order, audits the probabilities and saves **`submissions/submission.csv`**.
The cell displays its checksum and a download link. The same file is available through
JupyterLab's file browser. No Kaggle upload is made. The benchmark tables do not imply that
this cell has generated a new file; generation remains an independent opt-in action.

The final recipe remains the explicitly configured logistic families in
`configs/inference.json`; a research challenger is not automatically promoted based on a
consumed benchmark. A new model-family export requires a reviewed recipe implementation.
The 2022–2025 benchmark has already been consumed. Retrospective results and historical
score logs must not be described as new untouched validation or authenticated Kaggle receipts.

## Logs, preservation, and tests

UTC events record progress, task/total elapsed time and 15-second heartbeats. Publication
rejects error and warning outputs and atomically replaces notebooks only after success.
Notebook reports are not a substitute for estimator training logs.

The **Notebook research** GitHub workflow uses temporary, restricted AWS credentials and
CPU runners. It executes training notebooks, checks fresh-directory S3 recovery, renders
review notebooks and commits only public reports/notebooks to its feature branch.
A separate quality workflow tests pull requests. No new AWS compute is provisioned.

Private checkpoint and archive prefixes are under:

```text
s3://sagemaker-march-mania-560403859723-us-west-2/final-predictions/notebook-research/
```

Feature, model and benchmark archive IDs/checksums are recorded in their `reports/*/run.json` files.
Raw data, fitted estimators and checkpoints stay outside Git. GitHub validation artifacts
have 90-day retention; private versioned S3 archives and committed notebooks are separate
copies. Existing historical experiment prefixes are retained, not overwritten by cleanup.

Run the locked quality gate with:

```bash
.venv/bin/python scripts/quality.py
```

All changes use canonical filenames, documented commits, pull requests and exact-head
checks before merge. Do not rename corrected files to fix/fixed/repair variants.
