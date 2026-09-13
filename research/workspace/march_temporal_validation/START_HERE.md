# March Mania · Milestone 07

## Run one notebook: validate the two women's temporal-change features

The real round-06 result is promising but not confirmed: women's change-only Brier improved by 0.0042154 in 2017 and 0.0002204 in 2019. Those discovery years selected the family. The next decision uses **2016 and 2018 only**. These are already-used project seasons, not untouched tests.

There are **no new feature definitions, no new feature snapshots, and no new rating fits** in this milestone. Two new tournament classifiers are enough to check additional-season replication. If the gate passes, at most eight component fits follow. Nothing promotes features or submits predictions automatically.

## 1. Open your existing space

Use the existing `march-mania-dev` JupyterLab, not CloudShell. Its previously verified region is `us-west-2`, domain `QuickSetupDomain-20260902T115323` (`d-njhxv1erusdc`), owner profile `default-20260902T115323`.

Save and close other project notebooks and shut down their kernels. Do not delete the space or its storage. Do not synchronize Git again, reinstall packages, or redownload Kaggle.

Keep all previous folders and their `private_runs` directories:

```text
/home/sagemaker-user/
├── march-machine-learning-mania-2026/
├── march_shooting_research/
├── march_schedule_research/
├── march_record_validation/
├── march_temporal_form/
└── march_temporal_validation/    # this new kit
```

The old folders supply verified snapshots and numeric-JSON models. Missing artifacts stop the process; the kit never downloads or rebuilds them implicitly.

## 2. Upload and extract

Download `march_temporal_validation.zip` from ChatGPT. In JupyterLab, navigate to your home directory and upload it there. Do not place it inside the repository or another kit.

Open **File → New → Terminal**, then run:

```bash
cd "$HOME"
python3 -m zipfile -e march_temporal_validation.zip .
cd "$HOME/march_temporal_validation"

"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  -m unittest discover -s tests -v
```

Expected ending:

```text
Ran 39 tests
OK
```

The tests use tiny synthetic basketball data, models, and temporary repositories, not your real dataset or previous models. They also exercise hard timeouts. No installation is needed. If any test fails, stop and save the terminal output.

## 3. Run notebook 07

Open `07_womens_temporal_change_replication.ipynb`. Select **Python (March Mania)** and choose **Restart Kernel and Run All Cells**.

The notebook has eight code cells. It displays your real discovery results, verifies all inputs, replays six existing classifiers, fits two new replication classifiers, runs or skips conditional component tests, creates Plotly charts, and exports one ZIP.

Hard process ceilings (not runtime estimates or AWS billing caps):

| Stage | Ceiling | New real-data fits |
|---|---:|---:|
| Prepare | 180 seconds | 0 |
| Replicate | 120 seconds | At most 2 classifiers |
| Components | 180 seconds | 0 or at most 8 classifiers |
| Report | 120 seconds | 0 |

Every stage emits 15-second heartbeats while active. Individual successful classifier artifacts are sealed with hashes. Resumption reuses verified completed fits. No background job or automatic retry is launched.

## 4. Read the gate and results

`delta_vs_anchor < 0` means the complete two-feature family lowered Brier. The gate uses only 2016 and 2018; it requires both to improve and their mean delta to be at most -0.0005.

- `RUN_BOUNDED_COMPONENTS`: the notebook will test dropping offensive change and dropping defensive change separately across 2016–2019 (at most eight fits).
- `STOP_EXPANSION` followed by `SKIPPED_BY_GATE`: a valid scientific result, not an error. Continue through the report cells. Do not loosen the threshold.

For components, `delta_vs_full > 0` means removal worsened Brier, supporting conditional usefulness in this fixed recipe. Removal does not replace the omitted input with another selected feature. Components are exploratory post-selection diagnostics, not automatic input selection.

The notebook produces **10 Plotly charts**, or **12** if components run. The HTML report is self-contained. Tables use ordinary displays, not pandas Styler, so they do not require Jinja2.

A technical `COMPLETE` is not proof of a useful feature. The output is historical validation, not a new 2026 leaderboard score. The 2017/2019 discovery results must not be averaged into the new replication gate.

## 5. Save and return one file

Save the notebook with **Ctrl+S**. Download:

```text
march_temporal_validation/reports/milestone_07_return.zip
```

Attach that ZIP in ChatGPT. The notebook provides links to the archive and HTML report.

Keep `march_temporal_validation/private_runs/<fingerprint>/`. It contains the new models and predictions needed for reuse. The small return archive omits raw rows, models, per-game predictions, and private edited notebooks.

Stop this milestone here. No submission, model sweep, feature expansion, Git commit, or merge is triggered.

## If something stops

Save the notebook with the error. Preserve `reports/failure.json` and the corresponding stage log. The failure report can be stale from an earlier attempt; use the current traceback, current stage receipt, and timestamp together.

Do not delete caches, overwrite raw data, reset Git, or reinstall dependencies. A different environment, source hash, raw hash, unexpected edit, or missing prior cache needs diagnosis before retrying. `SKIPPED_BY_GATE` is not an error and still produces a normal report.

## Terminal alternative

Use this instead of notebook execution, never simultaneously:

```bash
cd "$HOME/march_temporal_validation"
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"

"$PYTHON" run_round07.py prepare --max-seconds 180 && \
"$PYTHON" run_round07.py replicate --max-seconds 120 && \
"$PYTHON" run_round07.py components --max-seconds 180 && \
"$PYTHON" run_round07.py report --max-seconds 120
```

The component command honors the gate. An exclusive lock prevents simultaneous stages in this kit. Preserve prior directories and avoid running other project experiments while this kit runs.

## Publication status

This kit is a local downloadable research increment, not a newly committed/merged GitHub release. The workflow verifies the repository against the source recorded in your previous report; it does not fetch GitHub or establish that a newer remote commit does not exist. Do not use `git add .` on raw inputs, private models, or edited notebooks. Publication belongs after the measured evidence is reviewed.
