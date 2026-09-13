# March Mania — milestone 12
## Shared-system ranking matchups

This is a **new companion kit**, not a repository overwrite. Do not wipe the SageMaker space, download raw data again, change dependencies, rerun completed studies, or change Git state.

### 1. Open the existing workspace

Use `march-mania-dev` in your existing SageMaker JupyterLab. Save and close other project notebooks and shut down their kernels. Retain all previous research folders and their `private_runs` directories. The new kit reads `march_shooting_research`, `march_schedule_research`, `march_temporal_form`, `march_possession_research`, and the completed `march_margin_research` report.

### 2. Upload and extract

Upload `march_ranking_matchups.zip` to the home directory, **beside** those folders. Open **File → New → Terminal** and paste:

```bash
cd "$HOME"
python3 -m zipfile -e march_ranking_matchups.zip .
cd "$HOME/march_ranking_matchups"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  -m unittest discover -s tests -v
```

Expected: `Ran 52 tests` and `OK`. The tests use small synthetic fixtures, not your competition data. No package installation is needed. Stop if a test fails. This first installation should create a new sibling folder, not overwrite any earlier kit.

### 3. Open the notebook

Open `march_ranking_matchups/12_shared_ranking_matchups.ipynb`. Select **Python (March Mania)** and choose **Restart Kernel and Run All Cells**.

The notebook has eight code cells. It first displays the prior result, verifies the exact source/data/cache identities, then streams legal ranking editions, builds seven matchup tables, replays four references, and fits at most sixteen challengers. It saves the report before showing the ten Plotly charts. Neither the notebook nor the HTML uses pandas Styler; Jinja2 is not required for those displays.

### 4. Check the workload

- Seven base snapshots reused, 2013–2019.
- Seven legal publication panels and seven matchup tables built (reused on repeat execution).
- **Zero new rating fits.**
- Four existing reference classifiers replayed.
- **At most 16 new classifiers**, or fewer when complete checkpoints exist.
- Twenty comparisons: five representations × four seasons.

Hard process ceilings: preparation 300 seconds; evaluation 180 seconds; report 120 seconds. Fifteen-second heartbeats and chunk/season/fit counters show progress. These are limits, not runtime estimates or AWS billing caps. The app is not shut down by a timeout.

### 5. Interpret the declared comparison

The primary effect in `ablations.csv` is **`pairwise_given_consensus`**: the reference plus consensus and both matchup features, minus the reference plus consensus alone. Negative `delta_brier` is better.

`consensus_given_anchor` separately measures the established ranking control. A gain there is not proof that the two new matchup features help. `median_given_votes` and `votes_given_median` remove one candidate while holding the remaining columns fixed.

The primary gate requires mean change ≤ −0.0005, improvement in at least three of four seasons, and worst deterioration ≤ +0.003. These are compute-allocation rules, not significance tests. A technical `COMPLETE` can accompany a scientific `DO_NOT_EXPAND_AUTOMATICALLY`; export the report either way. No further experiment or submission launches.

### 6. Return one archive

Save the executed notebook with **Ctrl+S**. Download:

```text
march_ranking_matchups/reports/milestone_12_return.zip
```

The notebook supplies links to that file and the self-contained HTML report. Keep `private_runs/<fingerprint>/`: it contains the checkpointed panels, feature tables, models, and predictions. The return ZIP contains aggregate evidence and the prior scientific report, not raw rankings, models, pair rows or edited notebooks.

### On a technical failure

Do not retry unchanged, delete caches, increase limits, reset Git or reinstall dependencies. Preserve the executed notebook and stage log. The runner attempts to create:

```text
march_ranking_matchups/reports/milestone_12_failure.zip
```

This contains bounded error/log/version diagnostics only. If the failure happened before the runner started and no archive exists, return the notebook or test output. Contract checks intentionally stop on changed inputs, missing references, fewer than three shared systems for a field pair, unsupported environment or corrupted completed checkpoints. Missingness is never silently changed into a favorable rank.

### Terminal alternative

Use this instead of notebook execution, never simultaneously:

```bash
cd "$HOME/march_ranking_matchups"
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"
"$PYTHON" run_round12.py prepare --max-seconds 300 && \
"$PYTHON" run_round12.py evaluate --max-seconds 180 && \
"$PYTHON" run_round12.py report --max-seconds 120
```

The same report and checkpoints are produced. For deliberate nondefault sibling locations, the runner supports `MARCH_REPO` and `MARCH_SHOOTING_KIT`, `MARCH_SCHEDULE_KIT`, `MARCH_TEMPORAL_KIT`, `MARCH_POSSESSION_KIT`, `MARCH_MARGIN_KIT`. Do not change these for the recorded default workspace.

## Status

This delivery was tested locally on synthetic fixtures. No AWS experiment, Git write, paid job, Kaggle download or submission was performed by the assistant. The kit is not committed or merged. The private workspace still needs to execute the real-data experiment. Best submitted Brier remains the user-reported 0.1222672; target 0.1097454. No gain is promised.
