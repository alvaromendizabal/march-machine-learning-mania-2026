# March Mania — two independent feature investigations

**Run round 14, save its result, then run round 15. Both are complete experiments.**
Each has four candidate definitions, two feature families, five fixed configurations,
family ablations, ten Plotly charts and a separate report. The two rounds share tested
infrastructure, not a reduced scientific scope. Neither depends on the other improving Brier.

## Preserve the workspace

Use the existing `march-mania-dev` JupyterLab and **Python (March Mania)** kernel.
Keep your repository and every earlier `private_runs` folder. Do not reinstall packages,
download Kaggle data, reset Git, run old experiments, or change the pinned settings.
The default paths are:

```text
/home/sagemaker-user/
├── march-machine-learning-mania-2026/
├── march_shooting_research/
├── march_ranking_matchups/
├── march_consensus_validation/
└── march_feature_rounds_14_15/          # new sibling folder
```

Other research folders should remain where they are. These three prior kits contain
the completed inputs required here. The code reads them but does not change them.
The new code does not import your possibly edited repository notebooks/source.

## 1. Upload, extract, test

Save and close other project notebooks and shut down their kernels. Upload
`march_feature_rounds_14_15.zip` to the home directory, not inside the repository.
In **File → New → Terminal**, run:

```bash
cd "$HOME"
python3 -m zipfile -e march_feature_rounds_14_15.zip .
cd "$HOME/march_feature_rounds_14_15"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  -m unittest discover -s tests -v
```

Expect **69 tests / OK**. Tests use synthetic data and temporary repositories, not
competition records. A failing test is a reason to stop, not install another environment.
No package installation is needed.

## 2. Run round 14

Open **`14_ranking_resolution.ipynb`**, select **Python (March Mania)**, then
**Restart Kernel and Run All Cells**. It builds four ranking-resolution features
against the frozen 17-input consensus reference.

There are three supervised stages: preparation (300-second cap), evaluation
(180-second cap), report (120-second cap). Heartbeats every 15 seconds; these are
process ceilings, not expected runtimes or AWS billing caps. The instance remains running.

The complete run has 20 comparisons: four saved references and at most 16 new classifiers.
It reuses 12 base/reference snapshots and 12 ranking panels; it builds 12 new feature
snapshots. No rating models are fitted. Valid completed work is reused on another execution.

Review `both_given_reference` in `ablations.csv` and the additional
`both_given_duplicate` diagnostic. Negative `delta_brier` is better.
A technically successful COMPLETE is not evidence of scientific success.

Press Ctrl+S. The report is:
`reports/round14/milestone_14_return.zip`. The notebook also links the HTML report.
Close the notebook and shut down its kernel before round 15.

## 3. Run round 15 independently

Open **`15_common_opponents.ipynb`**, select the same kernel, and
**Restart Kernel and Run All Cells**. It builds four same-opponent, same-venue-category
contrasts using legal pre-cutoff regular-season games. It does not use round 14's
predictions, selected features, or scientific result.

There are again 20 comparisons: four saved references and at most 16 new classifiers;
12 base/reference snapshots are reused, 12 context tables and 12 feature snapshots are built,
and no rating models are fitted. It has the same stage limits and ten Plotly charts.
Inspect the primary and duplication-control comparisons and the explicit support diagnostics.

A negative scientific result in round 14 does not block this independent round.
A technical error or preservation failure DOES require diagnosis before continuing.
Do not edit formulas or thresholds after reading round 14 results.

Press Ctrl+S. The individual report is:
`reports/round15/milestone_15_return.zip`.
The final cell packages both verified individual reports as:

**`reports/rounds_14_15_return.zip` — download and attach this one file in ChatGPT.**

No model files, individual game predictions, raw data, or privately edited notebooks are
included in the return archives. Keep `private_runs/round14/<fingerprint>` and
`private_runs/round15/<fingerprint>` in your space for resumption.

## Failure handling

Each runner attempts to save `reports/round14/milestone_14_failure.zip` or
`reports/round15/milestone_15_failure.zip`. Save the notebook with the traceback too.
Return the diagnostic ZIP; if the error occurred before the runner started, return the
executed notebook. Do not retry unchanged failures, delete caches, increase time limits,
or alter constraints. A missing prerequisite stops rather than silently rebuilding it.

This release deliberately requires the recorded repository state and software environment.
A mismatch should be inspected, not hidden by editing `constraints.json`. It records
repository changes, raw-file hashes and exact upstream artifacts separately.

## Terminal alternative (not in parallel with notebooks)

```bash
cd "$HOME/march_feature_rounds_14_15"
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"
"$PYTHON" run_round.py 14 prepare --max-seconds 300 && \
"$PYTHON" run_round.py 14 evaluate --max-seconds 180 && \
"$PYTHON" run_round.py 14 report --max-seconds 120
```

After round 14 completes technically, run:

```bash
"$PYTHON" run_round.py 15 prepare --max-seconds 300 && \
"$PYTHON" run_round.py 15 evaluate --max-seconds 180 && \
"$PYTHON" run_round.py 15 report --max-seconds 120 && \
"$PYTHON" package_returns.py
```

The notebook route is preferable for the inline visual evidence. The scientific report is
saved before inline charts display. Tables avoid pandas Styler and do not require Jinja2.
There are no cloud API calls, Git writes, submissions, or automatic subsequent experiments.

## Interpretation

Both rounds use men's 2022–2025 played main-draw games and earlier-season training labels.
They do not read 2026 outcomes. These historical seasons have already been used in this
project; this is NOT a new untouched test. All reported additions must be distinguished
from the submitted pooled-XGBoost recipe. Production transfer of the validated consensus
control remains a separate pending experiment.

Read `ROUND_14_PROTOCOL.md`, `ROUND_15_PROTOCOL.md`, `MILESTONE_13_REVIEW.md`, and
`VALIDATION.json` for definitions, evidence and the limits of local synthetic testing.
