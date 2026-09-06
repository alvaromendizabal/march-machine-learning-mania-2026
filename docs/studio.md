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

The pasted failure log showed a blocked fast-forward: local executed notebook 05
would have been overwritten. The shell continued, installed the old checkout,
and then could not find the new commands. The 120-fold notebook 05 run succeeded.

For that exact existing checkout, save/close open notebooks and run this once:

```bash
(
  set -e
  git stash push -m "Studio notebook 05 before feature update" -- notebooks/05_feature_research.ipynb
  git pull --ff-only
  python3 scripts/bootstrap.py
)
```

The stash preserves the full notebook; it is deliberately not popped over the
new canonical version. `git stash list` shows it. To inspect it later without
changing files, use `git show STASH_COMMIT:notebooks/05_feature_research.ipynb`.
Stashes are local Git objects retained on Studio's persistent volume; they are
not automatically uploaded to GitHub or S3. The original research outputs are
already independently stored in S3.

For future updates, the canonical command is:

```bash
python3 scripts/update.py
```

It fetches first, verifies main can fast-forward, preserves modified tracked
notebooks in a named stash, updates, then runs bootstrap and quality checks.
It refuses unrelated edits, untracked files or divergent commits for review.
Each failed step stops the sequence. Tests reproduce a dirty notebook, network
failure and divergence and verify that work survives. Bootstrap verifies all
installed project entry points as well as tests and the pinned environment.

## Pull Kaggle and build notebook 02

```bash
(
  set -e
  .venv/bin/march-data --output data/kaggle \
    --s3 s3://sagemaker-march-mania-560403859723-us-west-2/data
  .venv/bin/march-features --raw data/kaggle/raw \
    --run-root outputs/feature_store --require-massey \
    --s3 s3://sagemaker-march-mania-560403859723-us-west-2/feature-store
)
```

Existing Kaggle credentials are used in the Studio runtime. If authentication
fails, run `.venv/bin/kaggle auth login` there and repeat `march-data`. Kaggle's
competition data terms must be accepted by the account. No credential is needed
in source code or a notebook.

Repeat the same commands after interruption. Completed downloads, season
snapshots and model folds are verified by checksum and reused. An unfinished
estimator restarts its fit. Source/configuration/data/dependency changes automatically create
a new fingerprinted run directory; identical commands resume the same version. The original `outputs/research` experiment remains intact.

```bash
tail -f outputs/feature_store/FINGERPRINT/events.jsonl
.venv/bin/python scripts/notebook.py --execute
```

The notebook command executes both canonical review notebooks and writes rendered
copies into `outputs/validation`. In Jupyter, open canonical notebook 02 using
**Python (March Mania)** and choose **Run All** to refresh its visible outputs.
Read `outputs/feature_store/latest.json` for the completed fingerprint.
Open `outputs/feature_store/FINGERPRINT/report.html` for interactive charts.

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
  --run outputs/feature_store/FINGERPRINT --raw data/kaggle/raw \
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
