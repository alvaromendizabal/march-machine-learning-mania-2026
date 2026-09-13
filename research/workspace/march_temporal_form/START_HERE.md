# March Mania — Milestone 06

## What changed in the decision

The women's schedule-record features did not replicate. Only 2017 improved among the three additional seasons (2016, 2017, 2019); mean change was **+0.0002387543 Brier**. The 2018 gain was the discovery result that selected the hypothesis. The existing `STOP_EXPANSION` and `SKIPPED_BY_GATE` decisions remain in force. Do not rerun its component ablations or the old shooting panel.

This milestone tests **four different temporal features**: later offense/defense surprises relative to ratings fitted before those later games, and changes in those surprises across two late-season windows. It leaves the classifier and 16 reference inputs unchanged. These features are hypotheses, not proven improvements.

## 1. Stay in your existing AWS JupyterLab

Use **march-mania-dev**. Save and close other project notebooks and shut down their kernels. Do not delete or reset the space, reinstall the environment, pull/reset Git, or download Kaggle data again.

Keep `march_shooting_research/private_runs` and `march_record_validation/private_runs`. Their completed snapshots and models are required. Leave `march_schedule_research` intact as well, even though this new run reads its lineage from the returned evidence rather than modifying that folder.

## 2. Upload and extract

Upload **march_temporal_form.zip** in the JupyterLab home directory, beside—not inside—the project repository and previous kits. Open **File → New → Terminal** and paste:

```bash
cd "$HOME"
python3 -m zipfile -e march_temporal_form.zip .
cd "$HOME/march_temporal_form"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  -m unittest discover -s tests -v
```

Expected final lines:

```text
Ran 38 tests
OK
```

The tests create synthetic data and temporary models. They do not use your raw competition dataset or mutate existing caches. Do not continue if a test fails. No packages need to be installed.

```text
/home/sagemaker-user/
├── march-machine-learning-mania-2026/
├── march_shooting_research/
├── march_schedule_research/
├── march_record_validation/
└── march_temporal_form/
```

For an already-extracted kit, do not extract over an executed notebook; rerun the existing notebook only after inspecting why the previous run stopped. Valid completed checkpoints are reused.

## 3. Run notebook 06

Open `march_temporal_form/06_temporal_form_features.ipynb`. Select **Python (March Mania)**. Choose **Restart Kernel and Run All Cells**.

The notebook first displays your prior negative replication result, then verifies the exact source/data/environment and caches, builds the temporal features, runs the fixed comparisons, displays ten Plotly charts, and exports a return report.

Maximum new model work on a first complete run:

- **14 regular-season early-rating fits:** one per population-season, 2013–2019. These are new day-100 models, not duplicates of the cached full-season models.
- **13 tournament-classifier fits:** four configurations × two populations × two validation seasons = 16 comparisons, minus three existing reference models replayed rather than retrained.
- **14 existing full-season snapshots reused.** No original rating models, full feature bank, or Kaggle submissions are rebuilt.

The three replayed reference models are women's 2017, women's 2019 and men's 2019. Men's 2017 requires one new reference fit; the other 12 new fits are challengers.

Hard limits are **300 seconds preparation**, **240 seconds evaluation**, **120 seconds reporting**. Heartbeats appear every **15 seconds**. Limits are process ceilings, not runtime predictions or AWS billing caps. Upstream hashes and cached-model predictions must match before a replay is accepted.

## 4. Read the outcomes

`delta_vs_anchor` measures an addition versus the 16-input reference. Negative is better. In `ablations.csv`, `brier_delta` measures adding the named family while all other columns remain fixed; negative is also better. Conditional comparisons include adding levels to the change model, and adding changes to the level model. No capacity-based selector replaces columns.

`CONSIDER_UNCHANGED_REPLICATION` requires mean delta ≤ −0.0005 and improvement in both 2017 and 2019 for that population/recipe. It is a heuristic budget decision, **not statistical significance, automatic promotion, or evidence about the 2026 leaderboard**. Nothing launches after this report.

`DO_NOT_EXPAND_AUTOMATICALLY` is a valid scientific outcome, not a process error. These are previously-used exploratory seasons. No honest claim of an untouched holdout is made.

## 5. Save and return one file

Press **Ctrl+S**. In the file browser, download:

```text
march_temporal_form/reports/milestone_06_return.zip
```

Attach that one archive in ChatGPT. The notebook provides a download link to it and to the self-contained interactive HTML report.

Keep `private_runs/<fingerprint>/` for resumption. It contains early models, features, input coverage, classifiers, predictions, and per-stage receipts. The small return ZIP excludes raw game rows, model files, per-game predictions, and your edited repository notebooks.

**Stop at this milestone. Do not run additional folds, change constants, generate submissions, or force old gates.**

## On an error

Save the notebook with the error. Preserve `reports/failure.json` and the stage log. Do not delete caches, increase limits, reinstall dependencies, or reset Git. A changed hash, missing upstream artifact, unexpected working source, or missing early/late participant coverage deliberately causes a stop rather than silent reconstruction.

Table displays do not use pandas `.style` or require Jinja2. Do not install Jinja2 just for this kit.

## Terminal alternative

Use this instead of running notebook execution—not at the same time:

```bash
cd "$HOME/march_temporal_form"
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"
"$PYTHON" run_round06.py prepare --max-seconds 300 && \
"$PYTHON" run_round06.py evaluate --max-seconds 240 && \
"$PYTHON" run_round06.py report --max-seconds 120
```

The same checkpoints, hard limits, preservation checks, and HTML report apply. The notebook is preferred for reviewing metrics and plots alongside the methodology.

## GitHub status

This kit is a downloadable companion, not a new GitHub commit or merge. It makes no Git or AWS API writes. Runtime checks compare the existing checkout with the archived `84b8fb36644a6558beded6dad84f5645ea4405d3` reference and preserve the two previously identified edited notebooks. This does not claim a fresh remote-GitHub inventory.
