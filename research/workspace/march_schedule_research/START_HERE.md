# March Mania — next bounded feature investigation

## Run notebook 04 only

Your completed 2019 shooting experiment was technically successful but **all six challenger comparisons worsened Brier**. We are pausing the old notebook 03 expansion. We are not discarding the saved models or declaring the shooting families universally useless.

This kit reuses your prior snapshots, diagnoses the old errors without fitting again, and tests **seven quality-win / schedule-record features** on **2018**. The classifier and 16-input reference stay unchanged.

**No wiping, Git reset, raw-data download, environment reinstall, GPU, AWS API call, GitHub push, or Kaggle submission is needed.** The two edited canonical notebooks remain untouched and are not executed. Their repository-cleanliness issue is not silently marked resolved.

## 1. Open the existing space

Use your existing `march-mania-dev` JupyterLab, not CloudShell. Your earlier inventory identified the Oregon domain `QuickSetupDomain-20260902T115323`, profile `default-20260902T115323` and space `march-mania-dev`. Those are your supplied settings, not a new live AWS observation.

Save and close other project notebooks and shut down their kernels. Do not delete the space, repository, `march_shooting_research`, or its `private_runs` directory.

## 2. Upload this ZIP to your JupyterLab home directory

Upload `march_schedule_research.zip` beside the project and prior research kits. Expected structure after extraction:

```text
/home/sagemaker-user/
├── march-machine-learning-mania-2026/
├── march_workspace_sync/
├── march_feature_audit/
├── march_shooting_research/         # KEEP: contains completed snapshots and fits
└── march_schedule_research/         # THIS new kit
```

Do not extract over either the repository or the old shooting kit.

## 3. Extract and test

In **File → New → Terminal**, paste:

```bash
cd "$HOME"
python3 -m zipfile -e march_schedule_research.zip .
cd "$HOME/march_schedule_research"

"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  -m unittest discover -s tests -v
```

Expected ending: `Ran 36 tests` and `OK`. Tests use small synthetic fixtures and temporary repositories, never your real raw dataset or AWS resources. Stop if a test fails.

## 4. Run the notebook

Open `march_schedule_research/04_quality_wins_and_schedule.ipynb`.

Choose **Python (March Mania)**. Select **Restart Kernel and Run All Cells**.

The notebook has nine code cells. It:

1. Displays the actual 2019 results you supplied.
2. Checks source, data, environment, prior snapshots and fit checksums.
3. Replays all eight saved 2019 prediction streams, verifying Brier and row alignment; no fitting.
4. Produces private per-game loss diagnostics, so we can see where shooting features added error.
5. Builds seven new features for 12 team-season combinations using 14 already-completed upstream snapshots (2013–2019, men/women).
6. Trains only eight classifiers for the 2018 experiment: four input sets × men/women.
7. Shows ten Plotly charts and saves a self-contained HTML report and return archive.

Feature construction uses 2013–2018 snapshots; the additional 2019 snapshots are read only for the prior-error diagnosis. **Zero new strength/efficiency/rating fits.** No 2022–2026 tournament targets are used for modeling or evaluation.

Stage limits are 300 seconds preparation, 180 seconds evaluation, and 120 seconds report rendering. Heartbeats occur every 15 seconds. These are hard process limits, not runtime promises or AWS billing caps. Stopping a process does not stop the JupyterLab app or its billing.

## 5. Read the outcome correctly

`delta_vs_anchor = challenger Brier − reference Brier`.

- Negative: an improvement for these historical games and this fixed recipe.
- Positive: worse.
- Near zero: little observed contribution.

No full-panel expansion or feature promotion is automatic. A change at or below **−0.001** is merely a preregistered reason to consider an unchanged replication. That threshold is a practical research decision, not a significance test. Both add-alone and add-to-other-family effects are reported. Men and women are evaluated separately.

**Do not compare the 2018 or 2019 Brier scores directly with the 2026 target as if they scored the same games.** These are already-consumed exploratory seasons and the classifier is a fixed research control, not your production pooled XGBoost model.

## 6. Save and return one ZIP

Save the executed notebook with **Ctrl+S**. In the file browser, download:

```text
march_schedule_research/reports/milestone_04_return.zip
```

Attach that ZIP to ChatGPT. It contains metrics, ablations, provenance, the registry and aggregate prior-error diagnostics. It excludes raw rows, private edited notebooks, models, and game-level predictions.

The notebook supplies a link to the interactive HTML at:

```text
march_schedule_research/private_runs/<fingerprint>/schedule_report.html
```

Stop this milestone here. Do not run the old shooting season panel.

## Terminal alternative — use instead of the notebook, not simultaneously

The notebook is preferred. These are exactly the same stages:

```bash
cd "$HOME/march_schedule_research"
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"

"$PYTHON" run_round04.py prepare --max-seconds 300 && \
"$PYTHON" run_round04.py evaluate --max-seconds 180 && \
"$PYTHON" run_round04.py report --max-seconds 120
```

Do not run this block while the notebook is active. An exclusive lock refuses concurrent stages.

## Stop conditions and recovery

A technical failure is different from a worse Brier score. A completed worse score is evidence to preserve.

For errors, inspect `reports/failure.json` and `reports/smoke_prepare.log`, `smoke_evaluate.log`, or `smoke_report.log`. Do not increase limits, wipe directories, reset Git, alter expected hashes or repeat an unchanged failing command.

A missing prior cache stops rather than rebuilding expensive upstream work. The cache path is explicitly pinned to the fingerprint in your milestone-02 report, not guessed from the newest directory. A changed environment stops before comparing differently generated results.

Validated completed new snapshots and fits are reused on an intentional resume. Corrupt or partial receipts stop. Once the cause of a failure is resolved, rerun the failed stage; do not rerun all earlier stages unnecessarily.

GitHub was not modified by this delivery. This ZIP is a manual companion research kit. Publish reviewed code and non-sensitive results in a separate, tested commit/PR after the milestone; never `git add .` over raw data, private caches, backup notebooks or model files.

## Verification scope

Read `VALIDATION.json` and `validation_test_log.txt`. Local tests and notebook execution used synthetic data with fixture-only identities. The numerical formulas, model settings, stage commands and cache paths were exercised; your real AWS dataset has not been run through this new experiment by the assistant.
