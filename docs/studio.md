# March Mania Studio

The existing private space is **March Mania Research** (`march-mania-dev`) in
**Oregon / us-west-2**, domain `d-njhxv1erusdc`, profile
`default-20260902T115323`. Its JupyterLab app was verified running on 2026-09-06.
It has 50 GB persistent EBS, a configured `ml.m7i.xlarge` CPU instance, SageMaker
Distribution CPU 4.4.2, and a 60-minute idle timeout.

[Open the existing Studio](https://8i0hrdxm55pbptj.studio.us-west-2.sagemaker.aws/jupyterlab/default)

The private bucket is `sagemaker-march-mania-560403859723-us-west-2`. Encryption,
versioning and public-access blocking are enabled. The notebook 05 run's 533 S3
artifacts and completed summary verified that transfers from Studio work.

## Update the existing checkout

Save notebook work before updating. In the repository terminal:

```bash
git status --short
git pull --ff-only
python3 scripts/bootstrap.py
```

If Git reports modified notebooks, preserve those changes in a named commit or
stash before pulling. Do not discard notes to make an update proceed. Bootstrap
creates the locked project environment and kernel without changing the Studio
base environment, then runs timestamped quality checks with heartbeats.

## Pull Kaggle and build notebook 02

```bash
.venv/bin/march-data --output data/kaggle \
  --s3 s3://sagemaker-march-mania-560403859723-us-west-2/data
.venv/bin/march-features --raw data/kaggle/raw \
  --output outputs/feature_store \
  --s3 s3://sagemaker-march-mania-560403859723-us-west-2/feature-store
```

Existing Kaggle credentials are used in the Studio runtime. If authentication
fails, run `.venv/bin/kaggle auth login` there and repeat `march-data`. Kaggle's
competition data terms must be accepted by the account. No credential is needed
in source code or a notebook.

Repeat the same commands after interruption. Completed downloads, season
snapshots and model folds are verified by checksum and reused. An unfinished
estimator restarts its fit. Source/configuration/data/dependency changes require
a new run directory. The original `outputs/research` experiment remains intact.

```bash
tail -f outputs/feature_store/events.jsonl
.venv/bin/python scripts/notebook.py --execute
```

The notebook command executes both canonical review notebooks and writes rendered
copies into `outputs/validation`. In Jupyter, open canonical notebook 02 using
**Python (March Mania)** and choose **Run All** to refresh its visible outputs.
Open `outputs/feature_store/report.html` for interactive charts.

See [the complete feature contract](feature_store.md) for definitions, artifacts,
limits and the model-development handoff. Notebook 03 retains its historical
schema until that migration is completed.

## Durability and restoration

Stopping the app retains its EBS data; deleting the space removes that volume.
Private S3 provides the independent copy. The `--s3` commands upload inputs,
per-task outputs, checkpoints and the final completion record. A failed upload
fails explicitly and can be retried without recomputing completed tasks.

A portable archive can preserve a completed run plus the exact raw inputs and
hashed source files:

```bash
.venv/bin/python scripts/archive.py create \
  --run outputs/feature_store --raw data/kaggle/raw \
  --destination outputs/feature_store.zip
.venv/bin/python scripts/archive.py restore outputs/feature_store.zip \
  --destination outputs/restored_feature_store
```

Restoration validates ZIP CRC and SHA-256, rejects unsafe paths, and reuses
already restored matching files. It refuses to overwrite different contents.
The archive contains `run/`, `raw/` and `source/`; use the recorded source and
locked environment when resuming `run/`.

The first rebuilt-store archive's private S3 location and checksum are recorded
in `reports/feature_store/run.json`. Download it from S3 before running the
restore command. Regular Studio runs also retain individual mirrored objects;
`march-research --restore EXACT_REMOTE_RUN_URI --output EMPTY_DIRECTORY` uses
the shared, checksum-verifying S3 restore implementation for either run type.

GitHub retains code, rendered notebooks and small evidence tables. Raw data and
model artifacts remain outside the public repository. Changes pass through a
feature branch, documented pull request and CI before merge.
