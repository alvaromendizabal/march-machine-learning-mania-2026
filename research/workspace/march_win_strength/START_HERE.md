# March Mania · Milestone 10

## Run one notebook: men's win-loss strength

Use the existing **march-mania-dev** JupyterLab and **Python (March Mania)** kernel. This kit lives beside the repository. No package installs, AWS API calls, Git writes, downloads, or submissions occur.

The prior bracket result is negative: mean Brier change **+0.0004021** beyond the seed-status control, improvement in 2/4 seasons. Its gate remains closed. Do not rerun it.

### 1. Preserve the existing work

Save and close other project notebooks and shut down their kernels. Keep every previous folder and `private_runs` directory. This milestone specifically reads:

```text
march-machine-learning-mania-2026/
march_shooting_research/
march_schedule_research/
march_temporal_form/
march_possession_research/
```

It verifies the precise saved cache fingerprints from your returned reports. A missing or changed artifact causes a stop, never a hidden rebuild. Your two edited repository notebooks remain untouched.

### 2. Upload and extract

Upload **march_win_strength.zip** into JupyterLab's home directory, beside those folders. Open **File → New → Terminal**:

```bash
cd "$HOME"
python3 -m zipfile -e march_win_strength.zip .
cd "$HOME/march_win_strength"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  -m unittest discover -s tests -v
```

Expected: **56 tests, OK**. These are small synthetic tests, not a run on your real competition data. No installation is needed. Stop before the experiment if tests fail.

Do not extract over an existing `march_win_strength` installation to resume. Reopen its notebook instead; validated checkpoints are reused.

### 3. Execute the notebook

Open **10_mens_win_strength.ipynb**, select **Python (March Mania)**, then **Restart Kernel and Run All Cells**.

| Stage | Work | Hard ceiling |
|---|---|---:|
| Prepare | Verify seven base snapshots and four references; fit seven season-local win-loss rating models; build their pair features | 300 seconds |
| Evaluate | Replay four references; fit eight challengers, at most | 180 seconds |
| Report | Ten Plotly charts, preservation checks, return archive | 120 seconds |

Heartbeats occur every 15 seconds. These are process ceilings, not expected runtimes or AWS billing caps; the JupyterLab instance is not stopped automatically. Regular-season rating fits are distinct from the eight tournament classifier fits.

On resumption, completed rating and classifier fits are reused after checksum verification. No unchanged failed job is automatically retried. The tables do not call pandas `.style`; Jinja2 is not required.

### 4. Interpret the actual comparisons

- **Primary:** `ability_given_anchor` in `ablations.csv` = reference + Bradley–Terry ability minus the unchanged reference. Negative is better.
- **Secondary:** `uncertainty_given_ability` = reference + ability + uncertainty correction minus reference + ability. This tests whether approximate uncertainty adds anything beyond ability.

A registered resource-allocation rule requires mean change ≤ −0.0005, at least 3/4 seasons improving, and worst deterioration ≤ +0.003 to consider an unchanged later-era check. It is not a significance test or automatic promotion. A good secondary cannot replace a failed primary claim. No subsequent experiment launches.

There are only two candidate features; each comes from a substantive rating representation, not a claim that more columns imply better science. The classifier stays fixed at the existing 16-input logistic reference, C=0.1, with train-only scaling. This is NOT the best submitted production recipe.

### 5. Save and return

Save the executed notebook with **Ctrl+S**. Download:

```text
march_win_strength/reports/milestone_10_return.zip
```

The notebook also links a self-contained HTML report. Keep all `private_runs` folders. The return archive excludes raw rows, model files/covariance, individual predictions, and private edited notebooks. Stop this milestone here.

### Technical failures

Save the notebook with the error; retain `reports/failure.json` and the stage log. Do not reset Git, wipe the space, reinstall packages, delete caches, loosen checks, or increase limits without identifying the cause. Lack of numerical convergence or disconnected seeded schedule components is a deliberate diagnostic stop.

### Terminal alternative—not in parallel with the notebook

```bash
cd "$HOME/march_win_strength"
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"
"$PYTHON" run_round10.py prepare --max-seconds 300 && \
"$PYTHON" run_round10.py evaluate --max-seconds 180 && \
"$PYTHON" run_round10.py report --max-seconds 120
```

### Delivery status

This download is not pushed, committed, or merged to GitHub. The pinned source reference remains `84b8fb36644a6558beded6dad84f5645ea4405d3`. This package checks against the supplied evidence; it does not fetch a moving branch. No new real-data score has been produced by delivering the kit.
