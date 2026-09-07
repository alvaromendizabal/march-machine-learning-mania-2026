# March Mania: reviewing executed notebooks

Open the existing [March Mania Studio](https://8i0hrdxm55pbptj.studio.us-west-2.sagemaker.aws/jupyterlab/default)
when you want to browse the existing checkout. Published notebooks already contain
outputs; opening them does not require a kernel or a new run.

## What already completed

The official Kaggle snapshot was downloaded at **2026-09-07 00:09:59 UTC**:
35 CSV files, 181,009,577 bytes. Every file has a SHA-256 entry in the data
manifest. The subsequent 104-feature run completed 540 fold tasks and 9,200
team snapshots. Its private S3 fingerprint begins `554cee2384b92`.

The current reading sequence is **00 → 01 → 02 → 03**. These are executable views over
persisted Python-pipeline outputs; their cell state is not a dependency.

| Notebook | What to inspect |
|---|---|
| 00 | Download provenance, all-file inventory, data coverage, pace and shot selection |
| 01 | Exact training/validation seasons, prediction cutoff and snapshot coverage |
| 02 | Feature definitions, actual fitted inputs, Brier ablations and uncertainty |
| 03 | Model comparison, calibration, ensembles, uncertainty and feature diagnostics |

Notebook 03 now uses the current feature schema and has executed outputs. The
497-fit comparison completed successfully. Notebook 04 retains the earlier
benchmark/submission contract. Neither the feature experiment nor the current
model comparison creates a new submission.

## Update the checkout

This is an optional maintainer operation when a Studio checkout needs the latest
GitHub changes. Reviewing the published notebooks requires no terminal commands.
Save and close open notebooks before updating:

```bash
cd "$HOME/march-machine-learning-mania-2026"
python3 scripts/update.py
```

The update command preserves edited tracked notebooks in a named Git stash,
fast-forwards `main`, installs the locked environment, registers the kernel and
runs quality checks. Failed steps stop the sequence. Local stashes are preserved
on Studio's persistent volume; experiment artifacts are separately backed by S3.

## Review completed evidence

Open notebooks **00, 01, 02 and 03** and inspect their saved outputs. You do not
need to use Run All. The maintainer executes and publishes notebook outputs.
Fresh clones can also execute the recorded evidence without downloading private
raw data. Every notebook labels local completed runs or recorded Git evidence.

If notebook 02 finds an older local 104-feature run, it selects the recorded
124-feature evidence. The older run stays intact. A completed current-schema
local run takes precedence over recorded Git evidence.

## Maintainer reproduction and resume

Your existing `data/kaggle/raw` directory already contains the official data.
The first command below verifies/reuses completed downloads; it does not repeat
successful file transfers from Kaggle. Supply S3 to preserve each stage remotely.

```bash
(
  set -e
  .venv/bin/march-data --output data/kaggle \
    --s3 s3://sagemaker-march-mania-560403859723-us-west-2/data
  .venv/bin/march-audit --raw data/kaggle/raw \
    --run-root outputs/data_review \
    --s3 s3://sagemaker-march-mania-560403859723-us-west-2/data-review
  .venv/bin/march-features --raw data/kaggle/raw \
    --run-root outputs/feature_store --require-massey \
    --s3 s3://sagemaker-march-mania-560403859723-us-west-2/feature-store
)
```

After the feature store completes, run or resume the model comparison:

```bash
.venv/bin/march-models \
  --s3 s3://sagemaker-march-mania-560403859723-us-west-2/model-comparison
```

Only a new runtime without existing data needs Kaggle authentication. Use
`.venv/bin/kaggle auth login` there if requested. The account must have accepted
competition terms. Never place credentials in code or notebooks.

Every run emits UTC timestamps, elapsed time, progress and 15-second heartbeats.
`outputs/feature_store/latest.json` points to the completed run. Open its
`report.html` for interactive charts. Repeating the same command verifies and
reuses completed season/model tasks; an interrupted estimator restarts that fit.
Data, code, configuration or dependency changes create a new fingerprinted run.
Prior completed experiments remain available.

Maintainers execute all five current review notebooks and publish their outputs:

```bash
.venv/bin/python scripts/notebook.py --execute --publish
```

Outputs are written to `outputs/validation` and the canonical `notebooks` files;
GitHub keeps the executed notebooks
and aggregate evidence. The notebook runner also logs UTC progress and heartbeat.

## Durability

The existing Studio space uses persistent EBS. Stopping its app retains that data;
deleting the space removes the volume. S3 provides the independent copy of the
raw snapshot and experiments. No new compute instance is needed for these steps.

A portable archive can preserve a completed run, its exact raw inputs and source:

```bash
.venv/bin/python scripts/archive.py create \
  --run outputs/feature_store/FINGERPRINT --raw data/kaggle/raw \
  --destination outputs/feature_store.zip
.venv/bin/python scripts/archive.py restore outputs/feature_store.zip \
  --destination outputs/restored_feature_store
```

Restoration checks ZIP CRC and SHA-256 and reuses matching files. Different
contents are never overwritten. The restored archive contains `run/`, `raw/`,
and `source/`. Published run archives and checksums are recorded in
`reports/feature_store/run.json` and `reports/model_comparison/run.json`.
For model archives, `raw/features.parquet` is the exact upstream model matrix.
The private archive also contains the standalone interactive report in `run/report.html`.

GitHub changes pass through a feature branch, documented pull request and CI.
