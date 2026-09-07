# March Mania: reviewing executed notebooks

Open the existing [March Mania Studio](https://8i0hrdxm55pbptj.studio.us-west-2.sagemaker.aws/jupyterlab/default)
when you want to browse the existing checkout. Published notebooks already contain
outputs; opening them does not require a kernel or a new run.

## What already completed

The official Kaggle snapshot was downloaded at **2026-09-07 00:09:59 UTC**:
35 CSV files, 181,009,577 bytes. Every file has a SHA-256 entry in the data
manifest. The subsequent 104-feature run completed 540 fold tasks and 9,200
team snapshots. Its private S3 fingerprint begins `554cee2384b92`.

The current reading sequence is **00 → 01 → 02 → 03 → 04**. These are executable views over
persisted Python-pipeline outputs; their cell state is not a dependency.

| Notebook | What to inspect |
|---|---|
| 00 | Download provenance, all-file inventory, data coverage, pace and shot selection |
| 01 | Exact training/validation seasons, prediction cutoff and snapshot coverage |
| 02 | Feature definitions, actual fitted inputs, Brier ablations and uncertainty |
| 03 | Model comparison, calibration, ensembles, uncertainty and feature diagnostics |
| 04 | Actual final fits, retrospective benchmark, prediction coverage and recovery |

Notebook 03 now uses the current feature schema and has executed outputs. The
497-fit comparison completed successfully. The final-prediction stage then generated 132,133
actual 2026 probabilities, preserving four final estimators and 16 retrospective benchmark
estimators. Notebook 04 presents those results and verified S3 recovery. No 2026 tournament
outcomes enter fitting, and no Kaggle upload is claimed. Notebook 05 remains an optional appendix.

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

Open notebooks **00, 01, 02, 03 and 04** and inspect their saved outputs. You do not
need to use Run All. The maintainer executes and publishes notebook outputs.
Fresh clones can also execute the recorded evidence without downloading private
raw data. Every notebook labels local completed runs or recorded Git evidence.

If notebook 02 finds an older local 104-feature run, it selects the recorded
124-feature evidence. The older run stays intact. A completed current-schema
local run takes precedence over recorded Git evidence.

## Get the completed prediction file

No retraining is needed. The [successful run's validation artifact](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/runs/34083821689/artifacts/10004608823)
contains `final/submission.csv`. Its exact SHA-256 is
`1be5445fadc1c47531bbede2a5892327524a2aaa667663f0628d13b8057facb4`.
The independent versioned private S3 copy is:

```text
s3://sagemaker-march-mania-560403859723-us-west-2/final-predictions/794abeba97c0589751b3848117ce8588386a154b97b9ee3310127e9ef55b4c46/publication/submission.csv
```

The same run prefix preserves 53 task checkpoints, fitted estimators, prediction chunks,
manifest, source archive and UTC logs. Do not delete these to clean the Git repository.

## Reproduce or restore the final run

GitHub **Actions → Final predictions → Run workflow** uses short-lived AWS OIDC credentials.
Only this repository's `main` and `feat/final-predictions` branches are trusted. The role can read
the two exact verified input archives and read/write the final-predictions prefix. It cannot
launch AWS compute, delete S3 objects or access unrelated buckets. No long-lived keys are stored.

From an already configured Studio checkout, the equivalent command is:

```bash
.venv/bin/python -W error -m march_mania.publication.inference \
  --download-inputs \
  --s3 s3://sagemaker-march-mania-560403859723-us-west-2/final-predictions
```

This verifies/reuses the two input archives and restores completed final-run tasks. It does not
rerun the 497-fit comparison. A changed code/config/data/environment fingerprint creates a new
run rather than reusing incompatible results. A failed estimator restarts only that fit;
completed estimators and forecast chunks are verified and reused. The tested fresh-directory
recovery restored all 53 tasks and reproduced the CSV exactly with zero repeated fits.
The workflow executes all six review notebooks and, on its feature branch only, commits the
selected public reports and executed notebook outputs. It never auto-pushes generated evidence
to `main`; the maintainer reviews and merges through a pull request.

The original ranked Kaggle deadline has passed. Check late-submission availability on Kaggle
before attempting an upload; generating this CSV does not establish a score or an accepted receipt.

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

Maintainers execute all six canonical notebooks and publish their outputs:

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

## Notebook publication and submission release

The notebook runner records cell start/end, UTC timestamps, cell/task/total elapsed
time and a task heartbeat. Completed notebooks are reused only when their inputs,
source, environment and saved output checksums still match. An interrupted notebook
restarts from its first cell; earlier completed notebooks and all model checkpoints
remain intact. Publication is atomic, and concurrent publishers cannot race.
Warning or error outputs block publication instead of being hidden.

To independently replicate notebook checkpoints, add this option to the execution command:

```bash
.venv/bin/python scripts/notebook.py --execute --publish \
  --s3 s3://sagemaker-march-mania-560403859723-us-west-2/notebooks
```

The release utility now has one responsibility: audit and durably package an existing
prediction CSV. The old installer and score-driven refinement generator have been
removed from the active utility; Git history retains their implementation and the
historical score records remain unchanged. Inspect its required arguments with:

```bash
.venv/bin/python scripts/portfolio_release.py --help
```

Provide the actual prediction file, official `SampleSubmissionStage2.csv`, and the
recorded SHA-256 when available. An optional `--s3` prefix mirrors the exact CSV and
audit. A manifest without the corresponding CSV is not a validated release. This
command does not train a new final model or upload to Kaggle. Late-submission
availability must be checked on Kaggle; the original deadline has passed.

GitHub changes pass through a feature branch, documented pull request and CI.
