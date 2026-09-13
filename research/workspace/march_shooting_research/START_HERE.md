# March Mania — Run the next feature-engineering experiment

## Do this milestone only: notebook 02

The new report identifies two edited notebooks, not missing data or modified computational modules. Do **not** wipe, reset, stash, reinstall, rerun the old notebooks or download Kaggle again. This kit leaves the edits untouched and does not import repository code. It uses the existing raw CSVs and `.venv`.

1. In the existing **march-mania-dev** JupyterLab, save and close other project notebooks and shut down their kernels. Keep the existing CPU configuration; no GPU is needed. If reopening Studio, the prior terminal identified Oregon / domain `QuickSetupDomain-20260902T115323` (`d-njhxv1erusdc`) / profile `default-20260902T115323`. Do not create a new space.
2. Upload `march_shooting_research.zip` into the home directory, beside the repository and earlier kits.
3. Open **File → New → Terminal** and run:

```bash
cd "$HOME"
python3 -m zipfile -e march_shooting_research.zip .
cd "$HOME/march_shooting_research"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  -m unittest discover -s tests -v
```

The tests should end with `Ran 34 tests` and `OK`. They use synthetic fixtures, not your competition dataset. Stop if a test fails.

4. Open `march_shooting_research/02_shooting_matchup_features.ipynb`. Select **Python (March Mania)**. Use **Run → Restart Kernel and Run All Cells**.
5. Let the notebook build the 14 new feature candidates and run its eight fixed-recipe 2019 classifier fits. Preparation/evaluation each have a 600-second cap, report rendering 120 seconds; all provide heartbeats. No existing source/raw files are written. These are maximum limits, not runtime estimates.
6. Review the metric table and nine interactive Plotly charts. A lower Brier or negative delta favors the added family **in this exploratory historical comparison only**. No official score is generated.
7. Save the notebook. Download **`march_shooting_research/reports/milestone_02_return.zip`** and return that one file to the chat. Stop this milestone here. Notebook 03 is included for the next deliberate step and is disabled by default.

The earlier report's `REVIEW_REQUIRED` status is not erased. The new preflight resolves execution safety through isolation: it permits only the two previously identified notebook edits and verifies the computational files and eight raw inputs. It never runs the edited notebooks. Unexpected changes stop the stage.

## Exact terminal alternative

Use this instead of running notebook cells, not at the same time:

```bash
cd "$HOME/march_shooting_research"
PY="$HOME/march-machine-learning-mania-2026/.venv/bin/python"
"$PY" run_round02.py prepare --phase smoke --max-seconds 600 && \
"$PY" run_round02.py evaluate --phase smoke --max-seconds 600 && \
"$PY" run_round02.py report --phase smoke --max-seconds 120
```

Then open notebook 02 for review. Re-running its stage cells reuses verified checkpoints rather than refitting completed work. Run the tests first either way.

## Files and destinations

```text
/home/sagemaker-user/
├── march-machine-learning-mania-2026/       # unchanged repository, raw data, .venv
├── march_workspace_sync/                    # preserve
├── march_feature_audit/                     # preserve
└── march_shooting_research/                 # new kit
    ├── 02_shooting_matchup_features.ipynb
    ├── 03_shooting_season_panel.ipynb        # not this milestone
    ├── shot_features.py
    ├── research_workflow.py
    ├── research_plots.py
    ├── run_round02.py
    ├── expected_inputs.json
    ├── tests/
    ├── evidence/                           # earlier receipt only, no raw data
    ├── private_runs/<fingerprint>/         # created on execution
    │   ├── snapshots/                     # team features, exclusion audit, receipts
    │   ├── fits/                          # each model JSON, predictions, metrics, receipt
    │   ├── feature_registry.csv
    │   ├── smoke_metrics.csv
    │   ├── smoke_ablations.csv
    │   └── smoke_report.html              # self-contained offline Plotly report
    └── reports/
        ├── latest_run.json
        ├── milestone_02_summary.json
        └── milestone_02_return.zip         # return only this ZIP
```

No AWS, Hugging Face, Kaggle or GitHub API calls are made by these scripts. Existing Studio runtime charges still apply until you stop that app yourself. This kit does not set an AWS billing cap.

## Stop and recovery rules

- On a test failure, a `STOP`, a nonzero exit or an exception, do not proceed to later stages. Download `reports/failure.json` and the relevant stage log (for example `smoke_prepare.log`). Do not raise time limits or repeatedly retry unchanged failures.
- If the browser disconnects, check JupyterLab's running kernels/terminals before starting another copy. The supervisor uses an exclusive lock. A still-running stage must not be duplicated.
- A genuine interruption preserves completed season and fit receipts. Re-run the same stage only after determining it is no longer running and fixing the interruption's cause. Complete content-verified checkpoints are reused; partial output is not treated as a completed result.
- A corrupt checkpoint is a hard stop, not a request to wipe `private_runs`. A changed raw-data hash is a hard stop, not permission to overwrite the data.
- A poor model result is not an infrastructure failure. Preserve it and inspect family deltas; do not hide the failed hypothesis.

## What would happen next, after this result is reviewed

Notebook 03 deliberately extends the same fixed comparison to 2016, 2017, 2018, 2019 and 2021. Its `RUN_PANEL = False` switch requires an explicit change. It reuses the eight 2019 fits and runs at most 32 additional tournament classifier fits, plus only the two new 2021 snapshots. Do not run it merely because notebook 02 ran successfully; inspect the smoke evidence first. The panel is not an untouched holdout and has no 2026 evaluation path.

## Git status

Remote main was checked during preparation: `84b8fb36644a6558beded6dad84f5645ea4405d3`. This new kit is a downloadable companion, not a newly pushed or merged GitHub update. It makes no repository changes and does not reconcile or overwrite the two edited notebooks.
