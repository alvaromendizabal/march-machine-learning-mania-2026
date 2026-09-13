# March Mania — Milestone 13
## Test the unchanged ranking-consensus signal in 2022–2025

**Run only `13_consensus_later_era.ipynb`.** No setup restart, environment installation, Kaggle download, Git change, or cloud API action is needed. Keep all previous research folders and `private_runs` directories.

### Why this milestone
Your completed milestone 12 has two distinct conclusions. The new pairwise family worsened mean Brier by **+0.0011137347** beyond consensus and failed its gate. Consensus alone improved mean Brier by **−0.0009205404**, improving 3/4 discovery seasons. This kit replicates only the latter, unchanged. It does not claim consensus is a novel invention or promote either result to your submitted model.

**No new feature definitions in this milestone.** It measures whether one established input actually deserves continued use. The 2022–2025 outcomes were already used elsewhere in this project: this is a later-era exploratory check, not untouched testing.

## 1. Open the existing space
Use the existing `march-mania-dev` SageMaker JupyterLab and **Python (March Mania)** environment. Save and close other notebooks and shut down their kernels.

Preserve all previous folders. The direct dependencies for this kit are:

```
/home/sagemaker-user/
├── march-machine-learning-mania-2026/
├── march_shooting_research/
├── march_ranking_matchups/
└── march_consensus_validation/       # new kit
```

No older kit needs to execute. The new preflight reads pinned snapshots and the completed round-12 report. A missing or changed cache causes a stop rather than a silent rebuild.

## 2. Upload and test
Upload `march_consensus_validation.zip` into your **home directory**, beside the repository and other kits. Open **File → New → Terminal** and run:

```bash
cd "$HOME"
python3 -m zipfile -e march_consensus_validation.zip .
cd "$HOME/march_consensus_validation"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  -m unittest discover -s tests -v
```

Expected: **54 tests, OK**. Tests use synthetic fixtures and temporary repositories/models. They do not run your Kaggle experiment or load your private fitted models. Stop before the notebook if any test fails.

## 3. Run the notebook
Open `march_consensus_validation/13_consensus_later_era.ipynb`.
Select **Python (March Mania)**, then **Restart Kernel and Run All Cells**.

The eight code cells:

1. Locate the kit and show the kernel path.
2. Display the preserved round-12 results and decisions.
3. Verify inputs; reuse old matrices; build only missing later-year reference/consensus tables; audit labels and replay four old consensus models.
4. Fit the eight fixed later-era classifiers and display measured results.
5. Save the scientific report and return ZIP before inline visualization.
6–7. Display ten Plotly charts.
8. Provide report download links.

### Work budget
- Reuse seven 2013–2019 base/matchup snapshots and four consensus classifiers.
- Build five compact snapshots for 2021–2025, with **two ridge calculations per year: ten new regular-season rating fits**. Margin and efficiency outputs are checkpointed separately.
- Build five legal ranking-publication panels and five matchup tables.
- Fit **eight tournament classifiers**: reference and reference-plus-consensus for each validation year 2022, 2023, 2024, 2025.
- No new feature definitions, failed pairwise features, shooting residuals, algorithm search, calibration sweep, ensemble, or submission.

Hard limits: **prepare 300 seconds; evaluate 180 seconds; report 120 seconds**. Heartbeats every **15 seconds**. These are process ceilings, not estimates or AWS billing caps. They do not stop the running JupyterLab instance.

## 4. Interpret the right result
`ablations.csv` contains `consensus_given_anchor`.

```
Brier(reference + consensus) − Brier(reference)
```

Negative is better. Use the **2022–2025 results only** for this decision; do not pool discovery scores to rescue a failed replication.

A next fixed-production-recipe test is considered only if mean change ≤ **−0.0005**, at least **3/4 seasons** improve, and worst deterioration ≤ **+0.003**. Otherwise, the decision is `DO_NOT_PROMOTE_TO_PRODUCTION`. Either decision can follow a technically successful run. The rule is not a significance test, and nothing promotes or executes automatically.

The plots cover discovery versus later years, Brier, ranking-publication coverage, common-system support, 2025 input profiles, calibration, consensus coefficients, training-only overlap, confidence-bin paired losses, and leave-one-season-out sensitivity.

## 5. Return one archive
Save the notebook with **Ctrl+S**. Download:

```
march_consensus_validation/reports/milestone_13_return.zip
```

The notebook also links the self-contained Plotly HTML. Keep every `private_runs` directory. The return ZIP contains aggregate metrics and provenance, not raw ranking rows, models, individual predictions, or private notebooks.

If a technical stage stops, preserve the notebook and return:

```
march_consensus_validation/reports/milestone_13_failure.zip
```

If the error precedes the runner, return the executed notebook. Do not delete caches, loosen validation, reinstall packages, reset Git, increase limits, or repeat the unchanged failure.

### Terminal alternative
Use this **instead of** notebook execution, never simultaneously:

```bash
cd "$HOME/march_consensus_validation"
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"
"$PYTHON" run_round13.py prepare --max-seconds 300 && \
"$PYTHON" run_round13.py evaluate --max-seconds 180 && \
"$PYTHON" run_round13.py report --max-seconds 120
```

For nondefault locations only, set `MARCH_REPO`, `MARCH_SHOOTING_KIT`, and `MARCH_RANKINGS_KIT` to the existing paths. Do not relocate or reset a functioning default installation.

**Stop this milestone after the report.** No GitHub push/merge or Kaggle submission is made by this kit.
