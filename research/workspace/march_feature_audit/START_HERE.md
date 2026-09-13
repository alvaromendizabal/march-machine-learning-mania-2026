# March Mania · One manageable next milestone

## Where you are

Your uploaded milestone 00 records the expected commit, 35 raw CSVs, no missing required/optional tables, no recorded schema errors, and no modeled-season gaps. Its readiness gate is false because `tracked_clean` is false. It does not name the changed files. Your terminal log eventually records both `restore-data` and `environment` as PASS; do not repeat those stages.

Your existing space is `march-mania-dev`, in domain `QuickSetupDomain-20260902T115323` (`d-njhxv1erusdc`), profile `default-20260902T115323`, Oregon. Those identifiers come from your supplied CloudShell output. Use the same JupyterLab app; do not create another space, launch a job, or select a GPU.

## The only milestone to run now

**Identify tracked changes and inspect the completed feature-bank study, without fitting models.** This does not rebuild features, download archives, change AWS configuration, synchronize Git, or submit to Kaggle. It makes small private copies of changed tracked-file versions and reads all scientific report bytes directly from the verified Git commit, not edited local CSVs.

### 1. Upload the ZIP beside your repository

In your current JupyterLab, save and close other project notebooks and shut down their running kernels. Leave the JupyterLab app running for this milestone. In the file browser, go to your home directory and upload `march_feature_audit.zip`.

Expected layout after extraction:

```text
/home/sagemaker-user/
  march-machine-learning-mania-2026/   # existing source, raw data and environment; untouched
  march_workspace_sync/               # keep milestone 00 and its reports
  march_feature_audit/                # this new, separate companion kit
```

### 2. Extract and run local safety tests

Open File → New → Terminal in JupyterLab (not AWS CloudShell). Paste:

```bash
cd "$HOME"
python3 -m zipfile -e march_feature_audit.zip .
cd "$HOME/march_feature_audit"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" -m unittest discover -s tests -v
```

Expected: `Ran 28 tests` and `OK`. These tests create only disposable synthetic repositories, with no remote access and no training. Do not proceed if a test fails. No package installation is needed. Do not rerun the workspace sync/environment/data restoration commands.

### 3. Open one notebook

Open `march_feature_audit/01_workspace_and_feature_evidence.ipynb` in the file browser. Select **Python (March Mania)**. Run cells from top to bottom, or use Run → Run All Cells. The notebook includes an environment check and guarded child process.

Execution budget: **300 seconds for the diagnostic process**, with 15-second heartbeats. The notebook's independent watchdog allows 10 seconds for shutdown/report handling. These are limits, not runtime estimates. The outputs do not train a model, start cloud jobs, or change Git state.

The notebook displays six chart panels for the default `M/logistic` view, plus evidence tables. Set `ROUTE` to `W/logistic`, `M/hist`, or `W/hist` in the plotting section and rerun only the plotting cells to inspect the other saved views. All available routes appear in the HTML report.

### 4. Interpret the status correctly

- `REVIEW_REQUIRED`: diagnostic complete; it names the local changes or other unresolved checks. Continue viewing the saved plots. Do not reset, restore, stash, reinstall, or rerun unchanged commands. Return the ZIP so the specific change can be handled without losing work.
- `PASS_DIAGNOSTIC`: source/data checks pass. The historical evidence was inspected, not a new experiment. Stop before training.
- `STOP` or a failed code cell: inspect and attach `reports/failure.json` (or the exact traceback if failure happened before that file was created). Do not retry repeatedly or increase the time cap.

Output-only notebook changes are classified separately, but are still preserved, not automatically discarded. Staged edits are backed up separately from unstaged edits. A changed execution tag, kernel setting, or source cell is not called output-only.

### 5. Save and return one file

Save the executed notebook with Ctrl+S. Open `march_feature_audit/reports`, right-click **`milestone_01_return.zip`**, and select **Download**. Attach that one ZIP in ChatGPT.

The ZIP includes only report/provenance tables and changed-file metadata. Do not upload `private_backups`; it may contain unpublished source, notebook outputs or other private material. Existing files remain in their original locations.

For your own review, `reports/feature_evidence.html` is a self-contained Plotly report. Download it and open it locally when JupyterLab does not render interactive HTML. It embeds the Plotly runtime and does not require an external plotting service.

Stop here. When you are done viewing/downloading the reports, stop the existing JupyterLab **app** using your normal Studio controls to avoid idle compute. Do not delete its space or storage.

## Terminal alternative (not an additional task)

Use this only instead of the notebook's diagnostic run; running both is unnecessary. It creates the same reports and self-contained Plotly HTML, but does not execute/save the notebook itself.

```bash
cd "$HOME/march_feature_audit"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" feature_evidence.py run \
  --repo "$HOME/march-machine-learning-mania-2026" \
  --prior-reports "$HOME/march_workspace_sync/reports" \
  --max-seconds 300
```

Exit code 0 means `PASS_DIAGNOSTIC`; 2 means `REVIEW_REQUIRED` with reports saved; 1 means `STOP`. Never use `git reset --hard`, `git clean`, blanket `git add .`, or forced pushes to make a readiness check green.

## What this tells us, and what it does not

The completed feature-store study reports 3,106 candidate features, 128 retained in each full-block fit, and 251 distinct retained at least once across those fits. The public feature-usage CSV exposes **only retained full-block inputs**, not the complete rejection audit or the final submitted-model input list. The new kit verifies the CSV hashes against the study manifest, reconciles retained counts, and separately records whether your raw input hashes and current committed computational-source hashes match that historical study.

Existing family-removal ablations reran screening. They therefore measure removal plus replacement of other selected inputs, not a clean isolated family effect. The next scientific question is whether a small, domain-defined family adds value to an unchanged compact anchor. That test requires known model/input lineage, frozen preprocessing/model settings, training-only selection, appropriate temporal folds, and exact prediction-row alignment. It is not launched by this kit.

Your submitted Brier remains **0.1222672**, and your research target remains **0.1097454**. No new score improvement is claimed.

## Provenance and references

User sources: uploaded `milestone_summary.json`, terminal transcript, and executed notebook 00.

Pinned repository reference, verified through connected GitHub on September 11, 2026:
`84b8fb36644a6558beded6dad84f5645ea4405d3`.

- Published study: https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/reports/feature_store/README.md
- Manifest and report hashes: https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/reports/feature_store/run.json
- Screening implementation: https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/src/march_mania/feature_selection.py
- Git diff semantics: https://git-scm.com/docs/git-diff
- Plotly self-contained HTML: https://plotly.com/python/interactive-html-export/

All generated scientific plots in the real run come from your existing verified public reports. Local software tests use explicit synthetic fixtures, not real competition evaluation. The kit is a downloadable companion, **not a pushed or merged GitHub update**.
