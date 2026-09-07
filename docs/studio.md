# March Mania: data to feature evidence

Open the existing [March Mania Studio](https://8i0hrdxm55pbptj.studio.us-west-2.sagemaker.aws/jupyterlab/default)
and choose the **Python (March Mania)** kernel.

## What already completed

The official Kaggle snapshot was downloaded at **2026-09-07 00:09:59 UTC**:
35 CSV files, 181,009,577 bytes. Every file has a SHA-256 entry in the data
manifest. The subsequent 104-feature run completed 540 fold tasks and 9,200
team snapshots. Its private S3 fingerprint begins `554cee2384b92`.

The current sequence is **00 → 01 → 02**. These are executable views over
persisted Python-pipeline outputs; their cell state is not a dependency.

| Notebook | What to inspect |
|---|---|
| 00 | Download provenance, all-file inventory, data coverage, pace and shot selection |
| 01 | Exact training/validation seasons, prediction cutoff and snapshot coverage |
| 02 | Feature definitions, actual fitted inputs, Brier ablations and uncertainty |

Notebooks 03 and 04 still document the earlier model/submission schema. Migrating
nested tuning and calibration to the new feature contract is the next modeling
phase. The feature experiment itself does not create a new submission.

## Update the checkout

Save and close open notebooks, then run in the Studio terminal:

```bash
cd "$HOME/march-machine-learning-mania-2026"
python3 scripts/update.py
```

The update command preserves edited tracked notebooks in a named Git stash,
fast-forwards `main`, installs the locked environment, registers the kernel and
runs quality checks. Failed steps stop the sequence. Local stashes are preserved
on Studio's persistent volume; experiment artifacts are separately backed by S3.

## Review completed evidence

Open notebooks **00, 01 and 02**, in that order, and use **Run All**. Notebook 00
reuses an existing raw-data audit when available. Fresh clones can render the
recorded aggregate evidence without downloading private raw data. Every notebook
labels whether it is showing a local completed run or recorded Git evidence.

If notebook 02 finds an older local 104-feature run, it selects the recorded
124-feature evidence. The older run stays intact. A completed current-schema
local run takes precedence over recorded Git evidence.

## Run or resume the full pipeline

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

Only a new runtime without existing data needs Kaggle authentication. Use
`.venv/bin/kaggle auth login` there if requested. The account must have accepted
competition terms. Never place credentials in code or notebooks.

Every run emits UTC timestamps, elapsed time, progress and 15-second heartbeats.
`outputs/feature_store/latest.json` points to the completed run. Open its
`report.html` for interactive charts. Repeating the same command verifies and
reuses completed season/model tasks; an interrupted estimator restarts that fit.
Data, code, configuration or dependency changes create a new fingerprinted run.
Prior completed experiments remain available.

To execute all four current review notebooks and preserve rendered copies:

```bash
.venv/bin/python scripts/notebook.py --execute
```

Outputs are written to `outputs/validation`; GitHub keeps the canonical notebooks
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
`reports/feature_store/run.json`.

GitHub changes pass through a feature branch, documented pull request and CI.
