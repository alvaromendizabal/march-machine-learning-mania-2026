# March Mania: repair, two independent rounds, and a protected public portfolio

**Prepared source, not runtime-tested by ChatGPT. All execution remains yours.**
**Never upload this complete ZIP to public GitHub. It contains research implementation. Only `public_portfolio/` is the public export.**

## What is already known

Round 16 stopped during preparation when credited steals exceeded opposing turnovers. Its 2013 smoke/replay succeeded; the following season failed before classifier evaluation. Round 17 completed preparation, evaluation, report export and ten plots; only the final combined archive cell failed because round 16 was incomplete. Round 17's mean incremental Brier change was −0.0004714659, 3/4 seasons improved, but the predeclared −0.0005 threshold was not met. It remains unpromoted. These are notebook observations, not a fresh AWS inventory.

## 1. Open the existing space and upload

Open SageMaker AI in US West (Oregon), then Studio → domain `QuickSetupDomain-20260902T115323` → profile `default-20260902T115323` → existing `march-mania-dev` JupyterLab. These identifiers come from your earlier terminal output. Do not create/delete a space. Save and close the failed notebooks and shut down their kernels.

Upload `march_research_release.zip` into your JupyterLab home folder beside the repository and all earlier kits. The original folders and `private_runs` remain intact. Open File → New → Terminal:

```bash
cd "$HOME"
python3 -m zipfile -e march_research_release.zip .
cd "$HOME/march_research_release"
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"
"$PYTHON" -m unittest discover -s tests -v
```

This last command runs the eight **prepared** packaging/publication tests in temporary files. Require `OK`; the count is not a claim that ChatGPT executed them. Stop on failure.

## 2. Fix round 17's last cell without fitting again

With the old notebook saved and closed:

```bash
cd "$HOME/march_research_release"
"$PYTHON" repair_notebook17.py
"$PYTHON" collect_reports.py
```

Expected update status: `PACKAGING_CELL_UPDATED` or `ALREADY_UPDATED`. The failed notebook is backed up under the original kit's `reports/notebook_backups/`. Its earlier code, outputs and charts are retained. The collector may report round 17 complete and other rounds missing. That is a valid **partial** package, not a training error.

The original individual scientific report already exists at:
`$HOME/march_feature_rounds_16_17/reports/round17/milestone_17_return.zip`.
Do not rerun that notebook's science merely to obtain a combined ZIP.

## 3. Repair round 16: tests → all-season audit → resumption

```bash
cd "$HOME/march_research_release/repair_16_17"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" run_tests.py
```

Require `TEST_GATE: PASS`. Open **this folder's** `16_turnover_mechanisms.ipynb`, choose Python (March Mania), restart the kernel, and run the first two code cells only. The second cell audits all twelve seasons with zero model fits.

The revised policy excludes a physical game from **both turnover-rate estimators and both team orientations** if either team's credited steals exceed the other team's turnovers. Raw CSVs, base features and tournament labels remain unchanged. The maximum exclusion is 1% per season and 5% of games for any seeded team; prior minimum exposure checks also remain. No values are clipped or invented. This is a documented change in the data-quality protocol, not a relaxation of a model score gate.

Continue only when `quality_audit.json` has `status: PASS`. The table shows actual exclusion counts and fractions. If it stops, preserve `data_quality.csv`, the notebook and the generated diagnostic ZIP; do not change limits or launch more fits.

Then run the next cell: it verifies original sources and input provenance and copies only unchanged 2013 checkpoints. Expect `MIGRATED_IDENTICAL_2013`, two rating reuses and one snapshot reuse. Zero model fits occur in migration; original files stay intact. The new policy and source have a new run fingerprint.

Run the remaining cells after `READY_FOR_REMAINING_PREPARATION`. For the supplied state, at most 22 additional rate fits and 20 new classifier fits remain. Individual checkpoints prevent repeated accepted computation. Report export precedes inline charts. Save with Ctrl+S.

Return report: `repair_16_17/reports/round16/milestone_16_return.zip`.

## 4. Run the next two rounds independently

```bash
cd "$HOME/march_research_release/rounds_18_19"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" run_tests.py
```

Require `TEST_GATE: PASS`. Open `18_rebounding_and_assists.ipynb`; select Python (March Mania) and restart. Run the all-season audit, then the 2013 smoke and immediate repeat. The repeat must fit zero new rate models. After `READY_FOR_REMAINING_PREPARATION`, continue through preparation, evaluation and reporting. Save/reopen the notebook to verify embedded charts, then shut down its kernel.

Repeat the same sequence for `19_scoring_source_dependence.ipynb`. The second round uses no result or winning configuration from the first. Negative scientific results do not block an independent round; unresolved technical or data-safety errors do.

Each round: four candidate features, two families, four direct-rate controls, six fixed configurations, four later seasons, 24 rate-model fits (2 smoke + 22 remaining), 20 classifier fits, four reference replays, ten planned inline plots. No rating or classifier result has been measured for these new rounds here.

Use the primary `adjustment_given_rates` contrast and the `both_given_duplicate` sensitivity contrast. Mean improvement must be at least 0.0005, at least 3/4 seasons must improve, worst deterioration ≤0.003, and average improvement versus the duplicate control must be negative before considering further testing. These are resource-allocation rules, not significance tests.

## 5. Collect results

```bash
cd "$HOME/march_research_release"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" collect_reports.py
```

Download `reports/research_return.zip`. It contains finished individual reports and `collection_status.json`, explicitly listing anything missing. Keep all original and new private checkpoints. It is a private handoff file, not a public portfolio upload.

## Limits and failure handling

User test gate: 300 seconds. Scientific all-season audit: 120 seconds. Smoke and replay: 90 seconds each. Remaining preparation: 300 seconds. Evaluation: 180 seconds. Report: 120 seconds. Worker heartbeats every 15 seconds, two numerical-library threads, 6 GiB resident-memory guard. These are process ceilings, not estimated durations or AWS billing caps. Real runtime/cost are unmeasured; the instance continues billing while running, including idle time.

A failed gate stops; no automatic retraining or downloading happens. Save the executed notebook and `reports/roundXX/milestone_XX_failure.zip` (when produced). Do not retry unchanged failures, increase limits, reinstall the environment or reset Git.

## 6. Publish only after choosing the privacy split

Read `publication/PRIVATE_PUBLIC_GIT.md`. The public repository is a fresh **report-only showcase**, and full research source goes only to a separately verified private repository. Keep the original working checkout and its pinned Git state unchanged during research. The prepared Git workflow is manual: no commits, pushes, merges or visibility changes have occurred.
