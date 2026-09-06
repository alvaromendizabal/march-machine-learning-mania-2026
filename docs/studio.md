# Studio setup and first real run

## Provisioned resources

Verified on 2026-09-06:

- Region: **Oregon (`us-west-2`)**.
- Existing domain: `d-njhxv1erusdc`; owner profile: `default-20260902T115323`.
- Private JupyterLab space: **`march-mania-dev`**, display name **March Mania Research**.
- Persistent EBS: **50 GB**; configured CPU: **`ml.m7i.xlarge`**; image: SageMaker Distribution CPU **4.4.2**.
- Idle timeout: **60 minutes**. Compute was not started by this setup.
- Dedicated bucket: `sagemaker-march-mania-560403859723-us-west-2`.
- Bucket versioning enabled, AES256 server-side encryption enabled, all four public-access blocks enabled.
- IAM policy simulation allowed the existing Studio role to list the bucket and read/write research objects. This is not a substitute for the first live transfer from the Studio runtime.

[Open the SageMaker console in Oregon](https://us-west-2.console.aws.amazon.com/sagemaker/home?region=us-west-2#/studio). Launch the existing domain/profile, choose **JupyterLab → March Mania Research → Run space**, then **Open JupyterLab**. Starting the space incurs compute charges; stopped-space storage and S3 also have storage charges. Stop the space when finished. Persistent EBS survives stopping the app; deleting the space removes its EBS data. S3 provides the independent copy.

## 1. Clone and bootstrap

In the new space's terminal:

```bash
git clone https://github.com/alvaromendizabal/march-machine-learning-mania-2026.git
cd march-machine-learning-mania-2026
python3 scripts/bootstrap.py
```

If already cloned, enter that directory and use `git pull --ff-only` when the worktree is clean. Bootstrap installs its own pinned uv under `.tools/`, creates the locked Python 3.12 environment under `.venv/`, registers **Python (March Mania)**, and runs the quality gate. It never upgrades the Studio base environment or uses `exec`, `exit`, or shell replacement. Each command prints timestamps, elapsed seconds and a heartbeat.

## 2. Upload the official competition ZIP once

Download the official ZIP using your Kaggle account after accepting the competition's data terms. Upload `march-machine-learning-mania-2026.zip` into the repository root with JupyterLab's file browser. Then:

```bash
.venv/bin/python scripts/inspect_data.py march-machine-learning-mania-2026.zip
.venv/bin/march-research --preflight
```

The extractor locates the eight required CSV basenames even inside a ZIP folder. It refuses duplicate basenames and different contents at an existing raw-data path. The research pipeline does not need the original processed Parquet files. Raw data remains outside Git. The first S3-backed run saves these exact inputs.

## 3. Start the feature benchmark

```bash
.venv/bin/march-research \
  --output outputs/research \
  --s3 s3://sagemaker-march-mania-560403859723-us-west-2/research
```

Expect `task_started`, `heartbeat`, `task_completed`, `task_uploaded`, and `progress` events. The default run has 120 model-fold tasks, plus season snapshot tasks. Every event includes UTC and total elapsed seconds; heartbeat events also include the current task's elapsed seconds. Memory usage is reported when the host permits it.

To watch from a second terminal:

```bash
tail -f outputs/research/events.jsonl
```

An open terminal does not guarantee protection from Studio idle shutdown. If compute stops or the terminal session ends, restart the space and repeat the exact benchmark command. Completed, checksum-valid tasks are reused; only unfinished or corrupt tasks recompute. Individual estimators restart their unfinished fit; this is task-level resumption, not iteration-level booster checkpointing.

A failed S3 upload fails the command explicitly. Completed local model artifacts remain reusable; repeating the command retries their uploads without retraining. Local logs are live; S3 logs synchronize at task boundaries and completion. An interrupted task can lose progress since its latest completed checkpoint.

## 4. Review the notebook and report

Open `notebooks/05_feature_research.ipynb` using **Python (March Mania)**. It shows the original score evidence, the new feature ladder, and results when the run exists. It is a review surface; the terminal command owns training.

Completed run artifacts:

- `report.html`: self-contained interactive comparison, season trends, ablation intervals and reliability charts; download and open in your browser if Jupyter's HTML viewer suppresses scripts.
- `leaderboard.csv`, `metrics_by_season.csv`, `combined_metrics_by_season.csv`, `ablation_intervals.csv`, `reliability.csv`.
- `features.parquet`, `predictions.parquet`, `coverage.csv`.
- Per-fold `model.joblib`, `predictions.parquet`, `fold.json`, `checkpoint.json`.
- `manifest.json`, `summary.json`, `events.jsonl`.

The run is retrospective development evidence, not an improved Kaggle score. Do not choose a winner from one favorable season.

## 5. Restore onto a replacement space

`summary.json` contains the exact remote run URI. Before completion, the URI is the configured S3 prefix plus the fingerprint in `manifest.json` (also visible under the bucket's `research/` folder).

```bash
.venv/bin/march-research \
  --restore s3://sagemaker-march-mania-560403859723-us-west-2/research/REPLACE_WITH_RUN_FINGERPRINT \
  --output outputs/restored
```

Use an empty destination and the same code/dependency revision. The restore checks SHA256 metadata before publishing downloaded files. Resume with the restored raw inputs:

```bash
.venv/bin/march-research \
  --raw outputs/restored/raw \
  --output outputs/restored \
  --s3 s3://sagemaker-march-mania-560403859723-us-west-2/research
```

Code, data, dependency or experiment changes require a new output directory. Existing experiments remain intact and comparable. Load model files only from your own trusted runs.

## GitHub workflow

Changes use ordinary file names, a feature branch, a documented pull request and CI before merge. `scripts/quality.py` checks all package code, tests, and the four new setup/validation scripts; mypy checks the four new research modules. The large legacy notebook implementations and release scripts are preserved and are not claimed to have been revalidated on real data in this phase. CI validation files are retained as Actions artifacts; source and documented validation summaries are retained in Git.

The `uv.lock` environment is for the new research path. The historical Windows environment exports remain provenance for notebooks 00–04; migration of their optional XGBoost, LightGBM, SHAP, Optuna and neural dependencies remains separate work.

[Persistent Studio spaces](https://aws.amazon.com/blogs/machine-learning/boost-productivity-on-amazon-sagemaker-studio-introducing-jupyterlab-spaces-and-generative-ai-tools/) · [Configure a space](https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-jl-user-guide-configure-space.html)
