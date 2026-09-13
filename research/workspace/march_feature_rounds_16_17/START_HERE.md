# Start here — March Mania rounds 16 and 17

**Status: prepared and statically reviewed, NOT executed or tested by ChatGPT.** You execute everything. No current AWS/GitHub state is claimed from connected access. The previous results are from your supplied report.

## What you receive

Two complete independent feature rounds, four adjusted candidates and four corresponding ordinary-rate controls each. Twelve seasons of feature construction; 2022–2025 men's validation; six fixed configurations; 20 new tournament classifiers and 24 new descriptive rate-model fits per round. Ten Plotly charts per notebook. Primary comparison: opponent-adjusted candidates beyond the direct rates.

Keep existing raw data, environments, private_runs, and edited notebooks. Do not reset or clean Git, download Kaggle data again, or install packages. Round 17 does not depend on round 16 improving Brier. A technical failure requires diagnosis before either experiment continues.

## 1. Open the existing space

From a fresh browser tab, open AWS SageMaker AI in us-west-2 (Oregon):
https://us-west-2.console.aws.amazon.com/sagemaker/home?region=us-west-2

Open Studio for domain `QuickSetupDomain-20260902T115323`, owner profile `default-20260902T115323`. In Studio open JupyterLab and existing `march-mania-dev`. These names came from your prior terminal output, not a live account lookup. Do not create a new space. If stopped, starting the existing space is your choice and incurs its configured charges. Use the already-established CPU environment; no GPU needed by this plan.

Save/close other project notebooks and shut down their kernels. Keep the source repository and all earlier sibling research folders.

## 2. Upload and extract

Upload `march_feature_rounds_16_17.zip` to the home directory, beside the repository. Open File → New → Terminal:

```bash
cd "$HOME"
python3 -m zipfile -e march_feature_rounds_16_17.zip .
cd "$HOME/march_feature_rounds_16_17"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" run_tests.py
```

Do not extract into the repository or overwrite any earlier research kit. Intended location: `/home/sagemaker-user/march_feature_rounds_16_17`.

The required prior siblings are `march_shooting_research`, `march_ranking_matchups`, and `march_consensus_validation`, including their `private_runs`. Other prior folders remain intact. The verified raw path is `$HOME/march-machine-learning-mania-2026/data/kaggle/raw`.

## 3. Test gate

The package contains 55 test methods covering formulas, boundaries, signs, round symmetry, corruption, interrupted-smoke resumption, replay, export, and process timeouts. This is the expected suite size, NOT a passed-test claim. The fixture tests generate only small artificial data and temporary local repositories; they do not touch your project accounts or raw dataset.

Expected successful output ends with `OK` and `TEST_GATE: PASS`. The command writes `reports/test_receipt.json`; scientific stages refuse to run without a matching executed-test receipt. Do not just run `unittest` directly because that alone does not produce the gate receipt. The test process has a 300-second ceiling; stop on failure and return `reports/test_return.zip`.

Do not edit constraints, expected hashes, formulas, or gates to bypass a failure. No dependency installation is recommended automatically. Environment differences must be reviewed.

## 4. Run round 16 in two manageable parts

Open `16_turnover_mechanisms.ipynb`. Select **Python (March Mania)** and restart the kernel.

Run the first **four code cells** in order. They display the previous results, build the 2013 smoke snapshot (two rate fits), then replay it with zero new fits. Continue only when the fourth cell prints `READY_FOR_REMAINING_PREPARATION`.

Then run the remaining cells in order. Preparation builds the remaining eleven seasons (22 rate fits), evaluation fits 20 challengers and replays four references, and reporting saves the scientific archive before displaying ten inline charts. The first run contains 24 rate fits total, not 26: the two smoke fits are reused.

Successful completion is `COMPLETE` plus a saved scientific archive, not necessarily a positive feature decision. Save with Ctrl+S. Close/reopen the notebook to confirm outputs remain visible. Close its tab and shut down its kernel before round 17.

Individual return: `reports/round16/milestone_16_return.zip`. You do not need to send it before the independent second round.

## 5. Run round 17

Open `17_blocks_and_foul_pressure.ipynb` with the same kernel. Repeat the first four smoke/replay cells, then the remaining cells after `READY_FOR_REMAINING_PREPARATION`.

A scientifically negative round 16 does not block round 17. An unresolved technical error, changed artifact, or failed preservation check does.

The scope, stage ceilings, 24 rate fits, 20 new classifiers, four replays, and ten charts are the same as round 16. No features or winning recipes from round 16 enter round 17.

## 6. Interpret and return

Read `adjustment_given_rates` in each `ablations.csv`. Negative means adjusted effects improved Brier beyond the same four raw-rate controls. Compare `both_given_duplicate` as a regularization sensitivity check. Family additions and removals keep all other inputs fixed.

The gate requires mean <= -0.0005, 3/4 seasons improved, worst deterioration <= +0.003, and negative mean against the duplicate control. This is a budget rule, not proof of significance or automatic promotion. Four reused season clusters limit uncertainty conclusions.

After round 17, its last cell creates `reports/rounds_16_17_return.zip`. Download and attach that one file. It includes both independently verified scientific reports, executed-test evidence, and available timing/resource diagnostics, but no raw rows, models, private notebooks, or individual predictions.

Keep `private_runs/round16/<fingerprint>` and `private_runs/round17/<fingerprint>`.

## Limits, interruption, runtime, and cost

| Stage | Ceiling |
|---|---:|
| User-run synthetic tests (once) | 300 seconds |
| One-season smoke | 90 seconds |
| Smoke replay | 90 seconds |
| Remaining preparation | 300 seconds |
| Evaluation | 180 seconds |
| Report | 120 seconds |

Two threads; worker RSS ceiling 6 GiB; output disk free minimum 256 MiB. These are process ceilings, not measured runtime estimates or AWS billing caps. Local runtime has not been benchmarked. No additional service or GPU is requested. Compute cost equals your actual configured instance hourly rate times running wall hours, plus storage and any other account charges. Leaving Studio idle can still accrue instance charges; these scripts do not stop the space. No verified current instance price is available in this report.

Interrupt with Kernel → Interrupt or Ctrl+C in the terminal. The supervisor terminates its child process group and keeps completed checkpoints. Once the cause is understood, rerunning the same stage resumes valid work. Do not rerun an unchanged error blindly or raise a limit just because it failed.

Technical failure archives: `reports/round16/milestone_16_failure.zip` or `reports/round17/milestone_17_failure.zip`. Return the executed notebook if failure happened before the runner started. A negative scientific gate is not a technical error; continue through export.

## Terminal route (instead of notebook execution, never concurrently)

```bash
cd "$HOME/march_feature_rounds_16_17"
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"
"$PYTHON" run_tests.py
"$PYTHON" run_round.py 16 smoke --max-seconds 90 && \
"$PYTHON" run_round.py 16 smoke --max-seconds 90 && \
"$PYTHON" run_round.py 16 prepare --max-seconds 300 && \
"$PYTHON" run_round.py 16 evaluate --max-seconds 180 && \
"$PYTHON" run_round.py 16 report --max-seconds 120
```

After technical completion, repeat with `17` and then:

```bash
"$PYTHON" package_returns.py
```

The notebook route is recommended because methods, diagnostics, and plots appear together. Scientific stages never commit, push, merge, download, install, or submit.
