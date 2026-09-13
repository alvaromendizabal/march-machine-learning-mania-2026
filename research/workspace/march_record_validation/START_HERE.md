# March Mania — milestone 05

## Run one notebook; no setup repeat

Notebook **05_womens_record_replication.ipynb** checks whether the four unchanged schedule-record features reproduce their women's 2018 improvement. The uploaded experiment reported 0.1536501252 → 0.1522387388, a Brier change of −0.0014113864. That is an exploratory 2018 result, not a 2026 leaderboard gain.

This milestone adds **no new feature definitions**. It tests the value and stability of four implemented features before expanding them. It performs five new tournament-classifier fits first. Only a passed, predefined replication gate permits 16 drop-one fits. There are zero new rating-model fits, three mandatory existing classifier replays, and one new schedule snapshot using the same formulas.

## 1. Open the existing workspace

Return to `march-mania-dev` JupyterLab. Save/close other project notebooks and shut down their kernels. Do not delete the space, change its instance type, sync Git, reinstall packages, or download Kaggle again.

Keep these existing directories intact, including their `private_runs` folders:

```text
/home/sagemaker-user/march-machine-learning-mania-2026/
/home/sagemaker-user/march_shooting_research/
/home/sagemaker-user/march_schedule_research/
```

The two known edited repository notebooks remain unresolved, preserved and unexecuted by this kit. New or different edits trigger a stop instead of being overwritten.

## 2. Upload and extract

Upload `march_record_validation.zip` to the JupyterLab **home directory**, beside the existing folders. In File → New → Terminal, run:

```bash
cd "$HOME"
python3 -m zipfile -e march_record_validation.zip .
cd "$HOME/march_record_validation"

"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  -m unittest discover -s tests -v
```

Expected final test output:

```text
Ran 34 tests
OK
```

Tests create tiny synthetic basketball data and models in temporary directories; they do not use the real Kaggle dataset, cloud APIs, or your private experiment models. Stop if a test fails. No package installation is needed.

Do not extract into the Git repository, shooting kit or schedule kit. On a later retry, keep the already-extracted folder and its checkpoints rather than repeatedly extracting source over an open notebook.

## 3. Run the notebook

Open:

```text
march_record_validation/05_womens_record_replication.ipynb
```

Select **Python (March Mania)** → **Restart Kernel and Run All Cells**.

The notebook has nine code cells. It uses normal pandas tables and Plotly, not pandas Styler; Jinja2 is not required by these displays.

Stages and hard limits:

| Stage | Limit | Work |
|---|---:|---|
| Prepare | 300 seconds | Verify inputs; reuse seven women base and six schedule snapshots; build the missing 2019 schedule snapshot |
| Replicate | 180 seconds | Five new classifiers; replay the two 2018 classifiers and the 2019 reference |
| Ablate | 240 seconds | Zero fits when the gate fails; at most 16 drop-one fits when it passes |
| Report | 120 seconds | Preservation checks, HTML report, aggregate return ZIP |

These are process ceilings, not runtime predictions or billing caps. Heartbeats occur every 15 seconds. A lock refuses simultaneous runs from this kit. Valid completed snapshots and models are reused by checksum. Missing prior caches stop rather than causing a hidden rebuild.

## 4. Understand the gate

The baseline and complete four-feature family are compared in 2016–2019 using only earlier tournament labels for each year. Since 2018 selected this family, the gate uses **2016, 2017 and 2019 only**:

- Mean Brier change ≤ −0.0005.
- At least two of three seasons have negative change.
- Worst season change ≤ +0.003.

All conditions are required. Thresholds are an explicit compute-allocation rule, not a statistical significance test.

`SKIPPED_BY_GATE` is **not an error**. Continue to the report cells. Do not modify the threshold to force more runs. A passed gate is **not** permission to claim an improved submission or automatically select a feature subset.

For family comparisons, negative `delta_vs_anchor` is better. For drop-one comparisons, positive `delta_vs_full` means removal hurt: that is evidence of conditional usefulness within this fixed recipe.

## 5. Review and return

The notebook produces eight Plotly charts. A passed gate adds two ablation charts. Save with **Ctrl+S**.

Download and attach only:

```text
march_record_validation/reports/milestone_05_return.zip
```

The notebook also links the self-contained HTML. Return files contain aggregate metrics, training-only coefficient/correlation summaries, gate, definitions, config and provenance. Raw rows, private notebooks, predictions and fitted models are excluded.

Keep:

```text
march_record_validation/private_runs/<fingerprint>/
```

Stop this milestone after returning the ZIP. Do not start the shooting panel, run a submission, modify Git, or retrain the full bank.

## Terminal alternative — instead of notebook execution

```bash
cd "$HOME/march_record_validation"
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"

"$PYTHON" run_round05.py prepare --max-seconds 300 && \
"$PYTHON" run_round05.py replicate --max-seconds 180 && \
"$PYTHON" run_round05.py ablate --max-seconds 240 && \
"$PYTHON" run_round05.py report --max-seconds 120
```

The `ablate` command respects the gate and may complete with zero fits. Do not use the terminal and notebook concurrently. To view afterward, use only the notebook's saved-output/plot cells; source computations need not be repeated.

## When something stops

Do not delete caches, reset Git, increase limits or reinstall dependencies. Preserve the error notebook plus `reports/failure.json` and the applicable `reports/replication_<stage>.log`. A successful stage receipt does not erase older failure logs; inspect their stage/time rather than assuming an old file describes the latest run. Hash/version stops intentionally prevent comparisons across different inputs.

This kit performs no AWS control-plane calls and no GitHub writes. Existing app compute remains a user-controlled AWS resource; process timeouts do not stop the app itself. No new live GitHub inventory is claimed by this offline package.
