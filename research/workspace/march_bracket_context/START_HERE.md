# Run one bounded milestone: women’s bracket context

## Current action

Run `09_womens_bracket_context.ipynb` once. Do not rerun setup or any previous experiment. Do not delete the AWS space, reset Git, install packages or redownload Kaggle.

The new kit lives **beside** your repository. It reads the existing `march_shooting_research`, `march_schedule_research` and `march_record_validation` caches. Keep all other prior folders too. None is overwritten or executed. Two previously recorded modified repository notebooks are left untouched; an additional change stops preflight.

## 1. Open JupyterLab

Return to the existing `march-mania-dev` space. Save and close other project notebooks and shut down their kernels. Use the same Python (March Mania) environment and CPU instance. No GPU is needed for this bounded logistic experiment.

## 2. Upload and extract

Upload `march_bracket_context.zip` to the JupyterLab home directory, not inside a project folder. Open **File → New → Terminal**:

```bash
cd "$HOME"
python3 -m zipfile -e march_bracket_context.zip .
cd "$HOME/march_bracket_context"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  -m unittest discover -s tests -v
```

Expected: `Ran 49 tests` followed by `OK`. The tests use synthetic 64-team fields, artificial cached ratings and temporary models. They do not touch the real competition data. A failed test is a stop, not a request to reinstall dependencies.

## 3. Run notebook 09

Open `march_bracket_context/09_womens_bracket_context.ipynb`. Select **Python (March Mania)**. Choose **Restart Kernel and Run All Cells**.

Stages: prepare (180 seconds maximum), evaluate (180 seconds maximum), report (120 seconds maximum); 15-second heartbeats. These limits cap subprocesses, not AWS instance billing. The script does not stop the JupyterLab app.

Preparation reuses seven women’s base snapshots, creates seven small all-pairs bracket tables and replays four reference classifiers. It fits zero rating models or classifiers. Evaluation fits at most 12 new classifiers, each with its own checksum-verified checkpoint. Report emits ten Plotly charts and a self-contained HTML file. Ordinary table rendering has no Jinja2 dependency.

## 4. Interpret the correct comparison

In `ablations.csv`, **scaled_given_status** is the primary delta:

`host_context_scaled − seed_status`

Negative favors the two bracket-eligibility candidates after controlling for top-four status. `host_given_status` separately examines the unscaled flag; `scaling_given_host` examines adding the variability-scaled flag. Do not select a better-looking secondary result and relabel it the primary test.

The exact primary gate is: mean delta ≤ −0.0005, at least 3/4 improved seasons, worst deterioration ≤ +0.003. A passing decision is only `CONSIDER_CONFIRMED_VENUE_REPLICATION`; otherwise `DO_NOT_EXPAND_AUTOMATICALLY`. No follow-on experiment or promotion occurs automatically. A completed process is not proof of feature value.

## 5. Return one ZIP

Save the notebook with **Ctrl+S**. Download and attach:

`march_bracket_context/reports/milestone_09_return.zip`

The notebook links both the ZIP and the HTML report. Keep `private_runs/<fingerprint>/`; it contains the reusable models and all-pairs feature tables. The return ZIP excludes raw rows, fitted models, individual predictions and private repository notebooks.

## If something fails

Save the executed notebook and `reports/failure.json` plus the stage log. Do not delete caches, increase stage limits, reset Git or rerun the same failure unchanged. Preflight stops if prior data, source, environment or checkpoint identities differ. A missing cache never causes an automatic rebuild. A `DO_NOT_EXPAND_AUTOMATICALLY` decision is scientific output: continue through report export.

## Terminal alternative — instead of notebook execution

Do not run a terminal stage and the notebook concurrently.

```bash
cd "$HOME/march_bracket_context"
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"
"$PYTHON" run_round09.py prepare --max-seconds 180 && \
"$PYTHON" run_round09.py evaluate --max-seconds 180 && \
"$PYTHON" run_round09.py report --max-seconds 120
```

## Expected folder layout

```text
/home/sagemaker-user/
├── march-machine-learning-mania-2026/
├── march_shooting_research/
├── march_schedule_research/
├── march_record_validation/
├── march_temporal_form/
├── march_temporal_validation/
├── march_possession_research/
└── march_bracket_context/
```

No code in this kit calls AWS/GitHub/Kaggle or pushes/merges a repository. This is an uncommitted companion experiment pending real execution and review, not a published production change.
