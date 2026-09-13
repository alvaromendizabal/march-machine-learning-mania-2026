# March Mania — Milestone 11: margin robustness

## Start from the completed recovery, not from setup

Your uploaded `milestone_10_recovery_return.zip` records `REPORT_COMPLETE`:
seven rating seasons accepted, twelve historical comparisons completed, and ten
Plotly figures exported. Do not rerun the recovery notebook or milestone 10.

The full scientific archive already exists at:
`$HOME/march_win_strength/reports/milestone_10_return.zip`.
This new notebook verifies that exact archive and includes it in the next return
ZIP automatically. It does not regenerate the old report or refit its models.

## 1. Open your existing workspace

Open the existing `march-mania-dev` JupyterLab in US West (Oregon), `us-west-2`.
The previously identified domain is `QuickSetupDomain-20260902T115323`, profile
`default-20260902T115323`. Save and close other notebooks and shut down their
kernels. Keep the existing CPU instance and **Python (March Mania)** environment.
No GPU, package installation, raw-data download or Git reset is needed.

Keep all prior research folders. Required readers for this milestone are:
`march_shooting_research`, `march_schedule_research`, `march_temporal_form`,
`march_possession_research`, and `march_win_strength`. Keep their `private_runs`.

## 2. Upload and test

Upload `march_margin_research.zip` to your JupyterLab home directory, beside the
repository and other research folders. Open File → New → Terminal and run:

```bash
cd "$HOME"
python3 -m zipfile -e march_margin_research.zip .
cd "$HOME/march_margin_research"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  -m unittest discover -s tests -v
```

Expected: `Ran 43 tests` and `OK`. These tests use temporary synthetic fixtures;
they do not use your competition rows or fitted models. Stop if a test fails.

## 3. Run the notebook

Open `march_margin_research/11_margin_robustness.ipynb`.
Choose **Python (March Mania)**. Restart Kernel and Run All Cells.

There are eight code cells. The sequence verifies inputs and the saved milestone
10 science archive; builds two margin representations; replays four unchanged
references; fits twelve challengers; exports the report; then displays ten
interactive Plotly figures. The tables do not use pandas `.style`.

The fixed budgets are:

| Stage | Hard wall limit | Work when nothing new is cached |
|---|---:|---|
| prepare | 300 seconds | 7 base snapshots reused; 14 rating fits; 7 new pair tables; 4 reference replays |
| evaluate | 180 seconds | 12 classifiers fitted; 4 reference models replayed |
| report | 120 seconds | charts, integrity checks, return ZIP; no fitting |

A rating fit has at most 100 IRLS iterations (Huber) or one sparse linear solve
(compressed margin). Each accepted rating and matchup table has an individual
checkpoint. All stages emit 15-second heartbeats. These are process ceilings,
not expected runtimes or AWS billing caps. The script never shuts down your app.

## 4. Read the measured contribution

Primary comparison: `huber_given_anchor` in `ablations.csv`.
Secondary conditional comparison: `compression_given_huber`.
Negative `delta_brier` is better. A successful process status is not a successful
hypothesis. No model or feature is automatically promoted.

The resource-allocation gate requires a mean delta ≤ −0.0005, improvement in
at least 3 of 4 seasons, and worst deterioration ≤ +0.003. These are not
significance thresholds. The secondary result cannot substitute for the primary.

## 5. Export and stop

Save the executed notebook with Ctrl+S. Download:

`march_margin_research/reports/milestone_11_return.zip`

Return that one ZIP to ChatGPT. It includes the existing complete milestone 10
scientific archive, so there is no separate upload request. The notebook also
links the self-contained HTML report. Keep the new `private_runs` directory.

The archive excludes new raw rows, model objects, per-game predictions and edited
repository notebooks. It carries aggregate metrics, definitions and provenance.

## Technical failures

Stop and save the executed notebook with its traceback. Preserve `reports/failure.json`
and the corresponding stage log. Do not repeatedly retry an unchanged failure,
raise time limits, reinstall packages, or delete caches. A hash mismatch for the
old science archive means its bytes differ from the uploaded recovery receipt;
return the existing `march_win_strength/reports/milestone_10_return.zip` for review
rather than rebuilding it. A missing cache is not permission to start a full rebuild.

A failed scientific gate is not a technical exception; let the report export finish.

## Terminal alternative

Use this instead of notebook execution, not simultaneously:

```bash
cd "$HOME/march_margin_research"
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"
"$PYTHON" run_round11.py prepare --max-seconds 300 && \
"$PYTHON" run_round11.py evaluate --max-seconds 180 && \
"$PYTHON" run_round11.py report --max-seconds 120
```

No AWS resources or GitHub contents are changed by these scripts. The new kit is
not a pushed/merged repository change. Publication should follow evidence review,
not expose raw rows or private model files via a blanket `git add .`.
