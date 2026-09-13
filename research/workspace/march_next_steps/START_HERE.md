# Latest publication correction

Use [PUBLICATION_RECOVERY.md](PUBLICATION_RECOVERY.md) for the exact `.tools` environment repair. Do not repeat login or reset the research workspace. Scientific rounds below remain unchanged.

# March Mania — publication repair and two pending research rounds

**Immediate priority:** repair the blocked publication plan. Your GitHub login already succeeds; do not authenticate again. The full public source synchronization did not occur in PR #23.

## A. Publication

Read [PUBLICATION_RECOVERY.md](PUBLICATION_RECOVERY.md). Existing installation: upload the separately supplied `apply_publication_update.py` to HOME and run:

```bash
cd "$HOME"
python3 apply_publication_update.py --kit "$HOME/march_next_steps"
cd "$HOME/march_next_steps"
export PATH="$HOME/.local/bin:$PATH"
python3 run_publication_tests.py
```

Require `PUBLICATION_UPDATE_INSTALLED` then `PUBLICATION_TEST_GATE: PASS`. Next:

```bash
python3 github_publish.py inspect
python3 github_publish.py plan
```

Inspect the five previously flagged paths and the printed REVIEW.md. Require `UNRESOLVED_BLOCKERS: 0` and `LOCAL_PLAN_READY`. A remaining source/secret blocker is a deliberate stop, not a request to log in again. Return `$HOME/march_publication/publication_diagnostic.zip` when blocked. No source contents or tokens are needed.

After the clear plan is reviewed:

```bash
python3 github_publish.py publish
```

Type `PUBLISH`. Review both printed PRs, then:

```bash
python3 github_publish.py merge
```

Type `MERGE`. Pending/failing checks or changed heads stop, without admin bypass. Success produces `$HOME/march_publication/publication_return.zip`. Only separate private/public publication clones are advanced; your original scientific checkout and existing caches remain untouched. Do not run `git pull` in the original scientific checkout merely to absorb PR #23: the experiments intentionally pin their scientific source and local-edit state.

No command is claimed infallible. Network, permissions and unresolved source content can still stop publication. The repair exposes those states before a blind retry and retains the reviewed source and partial Git state.

## B. Two full research rounds — 20 and 21

The provided log establishes publication problems and older tests/reports, not completed results for rounds 20/21. These are still the next two experiments; they are not renamed to imply new research. Both are included at full scope and byte-identical to the previously delivered scientific files. No model or feature cache is invalidated by this publication-only update.

- [Round 20 — pace and shot-variance context](rounds_20_21/ROUND_20_PROTOCOL.md)
- [Round 21 — performance against similar opponent styles](rounds_20_21/ROUND_21_PROTOCOL.md)

Each has four candidates, two families, four descriptive controls, six fixed configurations (17/21/23/23/25/25 inputs), 12 feature snapshots, four saved reference replays, at most 20 new classifiers, no new rating fits, and ten planned inline Plotly charts. Neither round selects features from the other. All 2022–2025 results are exploratory on previously used years.

Keep every earlier folder. Dependencies include `march_shooting_research`, `march_ranking_matchups`, `march_consensus_validation`, and the original `march-machine-learning-mania-2026/data/kaggle/raw`. No data download, reinstall or old experiment rerun.

### Research test gate (separate from publication)

```bash
cd "$HOME/march_next_steps/rounds_20_21"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" run_tests.py
```

51 prepared test methods; NOT executed by the assistant. Require `TEST_GATE: PASS`. These are temporary synthetic fixtures, not new real-data scores. Stop and return `reports/test_return.zip` on failure.

### Round 20

Open `20_pace_and_variance.ipynb` with **Python (March Mania)**. Restart kernel. Run its first four code cells: setup, all-season audit, 2013 smoke, smoke replay. Require `READY_FOR_REMAINING_PREPARATION`, with zero new feature snapshots in the replay. Then run remaining cells. The scientific report is written before inline charts. Save with Ctrl+S; close/reopen to verify outputs persisted, then stop its kernel.

### Round 21

Open `21_opponent_style_responses.ipynb`. Repeat the same gates. A scientific negative finding in round 20 does not block independent round 21. Do not proceed through an unresolved shared data, environment or integrity error. Do not run both simultaneously.

### Interpretation

Primary `context_given_controls`: Brier of both families plus controls minus Brier of controls. Negative is better. Conditional add/drop comparisons keep other inputs fixed. `both_given_duplicate` is a regularization-sensitivity diagnostic, not a count of new features. Expansion rule: mean <= -0.0005, at least three of four years improve, worst <= +0.003, negative mean versus duplicate control. These are compute-allocation criteria, not significance tests or promotion to production.

### Limits

Audit 120 seconds; smoke and replay 90 each; preparation 300; evaluation 180; report 120. Research test ceiling 300 seconds. Two numerical threads, 6 GiB worker resident-memory guard, progress heartbeats every 15 seconds. Runtime and costs are not measured. Instance billing includes idle time and is not stopped by process timeouts. All accepted snapshots and fits are checkpointed with content hashes; no blind reuse based only on existence.

### Return

The last round-21 cell packages both reports. Terminal equivalent, AFTER completed scientific reports:

```bash
cd "$HOME/march_next_steps/rounds_20_21"
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" package_returns.py
cd "$HOME/march_next_steps"
python3 collect_returns.py
```

Return `march_next_steps/reports/next_steps_return.zip`. It identifies missing research/publication components rather than treating them as successful. Technical failures produce `reports/round20/milestone_20_failure.zip` or the round-21 equivalent. Never include GH configuration, tokens, raw rows or private models.

## Delivery status

Static inspection only. No newly prepared tests or notebooks were executed, and no new model fits or account writes were performed. The source and test manifests document prepared work, not actual passing execution. Refer to PREPARED_VALIDATION.json.
