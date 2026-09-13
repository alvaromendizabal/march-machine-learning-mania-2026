# March Mania · Milestone 08

Run `08_possession_matchup_features.ipynb` in the existing **march-mania-dev** JupyterLab space. Do not rerun setup, download data, reset Git, reinstall packages, or delete old caches.

## Why this milestone

The uploaded milestone 07 completed successfully but failed the temporal-change replication gate. Women’s additional-season Brier changed by +0.004053923 in 2016 and −0.000460722 in 2018: mean +0.001796600, worse. Its skipped component experiments remain skipped.

The next hypothesis is different: four nonlinear possession-accounting matchup features. Six ordinary turnover/rebound/free-throw rate inputs are included as explicit comparison controls. They are not presented as new concepts to the full project.

## 1. Upload beside the existing project

Save and close other notebooks and shut down their kernels. Upload `march_possession_research.zip` to the JupyterLab home directory, beside:

```text
march-machine-learning-mania-2026/
march_shooting_research/
march_schedule_research/
march_record_validation/
march_temporal_form/
march_temporal_validation/
```

Keep every `private_runs` folder. Milestone 08 reads four upstream kits; the round-07 report is bundled as evidence, so its private cache is not required for this experiment.

## 2. Extract and test

Open File → New → Terminal:

```bash
cd "$HOME"
python3 -m zipfile -e march_possession_research.zip .
cd "$HOME/march_possession_research"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  -m unittest discover -s tests -v
```

Expected: **48 tests, OK**. The tests build tiny synthetic temporary repositories and models. They do not operate on the real project, AWS APIs, or Kaggle. Stop if a test fails. There is no dependency installation.

## 3. Open notebook 08

Open `march_possession_research/08_possession_matchup_features.ipynb`. Select **Python (March Mania)**. Restart Kernel and Run All Cells.

The source and raw data remain pinned to your returned evidence. The two existing edited repository notebooks are left untouched and never imported. A different source/data/environment state stops rather than silently changing the experiment.

Preparation reuses 14 prior base snapshots, creates 14 small rate tables by aggregation, and verifies seven saved baseline classifiers by replay. It performs zero rating fits and zero classifier fits. Evaluation has 32 fixed comparisons and at most 25 new classifiers. One is the missing men’s 2016 reference; the other 24 are the three challenger recipes across two populations and four seasons.

| Stage | Hard wall ceiling |
|---|---:|
| prepare | 300 seconds |
| evaluate | 300 seconds |
| report | 120 seconds |

Heartbeats: 15 seconds. These are execution ceilings, not estimates or AWS spending caps. No GPU, new AWS resource, remote data transfer, submission, or Git write is required. The already-running JupyterLab instance can still incur charges; the script’s timeout does not shut it down.

## 4. Read the primary comparison

`delta_vs_anchor` describes gains versus the old 16-input reference. **The primary novelty test is different:** `mechanism_given_rates` in `ablations.csv` compares the 26-input combined model against the 22-input rate-augmented reference. Negative `delta_brier` means the four nonlinear features improved Brier beyond the direct rate controls.

The four recipe sizes are 16, 22, 20 and 26. Men and women are fitted separately on 2016–2019 main draws, training strictly on 2013 through the preceding season. The logistic algorithm, regularization and train-only scaling are unchanged.

A mean primary delta ≤ −0.0005, improvement in at least 3 of 4 seasons, and a worst deterioration ≤ +0.003 earns `CONSIDER_LATER_ERA_REPLICATION`. Otherwise the decision is `DO_NOT_EXPAND_AUTOMATICALLY`. These are compute-allocation rules, not significance or production promotion. No follow-on training is automatically launched.

## 5. Save and return one file

Save the executed notebook (Ctrl+S). Download:

```text
march_possession_research/reports/milestone_08_return.zip
```

The notebook links the ZIP and the ten-chart self-contained Plotly HTML report. Keep the fingerprinted `private_runs` directory; it contains models, predictions, rate snapshots and checkpoints for reuse. The small return ZIP excludes those private per-game/model artifacts.

Stop after this milestone. Do not run old skipped feature expansions, tune thresholds after seeing the outcome, or create a submission from these historical results.

## When something stops

A scientific decision to stop expansion is not a software error. Continue to export the report when execution completed.

For a technical error, save the notebook and preserve `reports/failure.json` and `reports/possession_research_<stage>.log`. Do not reset Git, remove a cache, reinstall dependencies, or repeat unchanged failures. A missing cache is not permission to rebuild it. Completed checkpoints remain available, but retry only after diagnosing the cause.

## Terminal alternative

Use this instead of notebook execution, never at the same time:

```bash
cd "$HOME/march_possession_research"
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"
"$PYTHON" run_round08.py prepare --max-seconds 300 && \
"$PYTHON" run_round08.py evaluate --max-seconds 300 && \
"$PYTHON" run_round08.py report --max-seconds 120
```

All stages save receipts and complete the same experiment. The notebook is preferred for methods, interpretation and Plotly evidence together.

## Publication status

This is a downloaded companion experiment, not a GitHub commit or merge. The repository remains unchanged. A later publication milestone should consolidate verified feature code, executed notebooks and aggregate evidence into canonical repository locations; raw data and model caches must remain private.
