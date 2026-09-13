# Next two feature investigations: rounds 20 and 21

There is no returned scientific result for these two rounds in the current
publication receipt. They remain prepared, not measured. They are supplied in
full without changing their 28 file hashes. Do not count this re-delivery as
another feature experiment or a scientific improvement.

The completed result record is in prior research returns. The reported best late
retrospective submission is 0.1222672 Brier; 0.1097454 is the historical research
target, not an achieved result. Compact-reference validation is not a leaderboard
score and is not the same model as the stronger released pooled-XGBoost recipe.

## Round 20: pace and shooting-variance context

Four candidates in two families:
1. Pair-tempo adjustment × margin-strength difference.
2. Pair-tempo adjustment × ranking-consensus difference.
3. Pair-shooting-variance adjustment × margin-strength difference.
4. Pair-shooting-variance adjustment × ranking-consensus difference.

Controls: ordinary differences in pace, pace variability, three-point-attempt
share and the field-goal variance proxy. The proxy is not a complete possession
simulation. Feature formulas and cutoffs remain frozen in ROUND_20_PROTOCOL.md.

## Round 21: performance against similar opponent styles

Four candidates in two families:
1. Offensive response against pace/spacing-similar opponents.
2. Defensive response against pace/spacing-similar opponents.
3. Offensive response against pressure/rebounding-similar opponents.
4. Defensive response against pressure/rebounding-similar opponents.

Distinct opponents, not repeated meetings, receive the intended weighting. Direct
response rows against the target opponent are excluded and low-support increments
are shrunk. The opponent's full legal season profile is not claimed to be fully
leave-pair-out. Exact definitions are in ROUND_21_PROTOCOL.md.

## Equal per-round scope

| Item | Each round |
|---|---:|
| Candidates / families / descriptive controls | 4 / 2 / 4 |
| Reference inputs | 17 (includes ranking consensus) |
| Fixed configurations | 6 |
| New feature snapshots | 12 |
| Reference classifier replays | 4 |
| Maximum new tournament classifier fits | 20 |
| New rating-model fits | 0 |
| Planned inline Plotly charts | 10 |
| Validation years | 2022–2025, previously explored |

The fixed classifier, scaling, cutoffs and declared criteria are unchanged. No
ensemble, model search, leaderboard tuning or automatic cross-round selection.
Production-transfer assessment of useful signals is still pending.

## Run in the existing AWS paths, not the publication archive

The original sources are already at:
`$HOME/march_next_steps/rounds_20_21/`.
The unchanged source copy is also supplied under `research_rounds/rounds_20_21/`
in this download for recovery/reference. Do not overwrite a newer edited kit or
run its independent caches in a different folder merely because it is supplied.

Use the original location:

```bash
cd "$HOME/march_next_steps/rounds_20_21" && \
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" run_tests.py
```

There are 51 prepared scientific test methods. They have NOT been executed by the
assistant in this correction. Require `TEST_GATE: PASS` and its matching receipt.

Open `20_pace_and_variance.ipynb` with Python (March Mania). Restart the kernel.
Run setup, all-season audit, 2013 smoke and immediate replay. Require
`READY_FOR_REMAINING_PREPARATION`, with zero new snapshots on replay. Then run the
remaining cells, save, close/reopen to check inline Plotly output persistence, and
shut down the kernel. Repeat with `21_opponent_style_responses.ipynb`.

A negative scientific outcome does not block the independent other round. An
unresolved technical or integrity failure does. Each round retains its own source,
configuration and data hashes; do not copy a nominal winning family between them.

Primary: `context_given_controls` in ablations.csv. Negative delta_brier is better.
Additional work is considered only for mean <= -0.0005, at least three of four
years improving, worst deterioration <= +0.003, and mean improvement beyond the
duplicate-control diagnostic. These are allocation rules, not significance tests.

Ceilings per round: audit 120 seconds, smoke/replay 90 each, prepare 300,
evaluate 180, report 120. Two numerical threads, a 6 GiB worker RSS guard and
15-second progress heartbeats. They do not limit idle AWS billing or stop the
Studio instance. Scientific output must be distinguished from test-fixture output.

After both reports:

```bash
cd "$HOME/march_next_steps/rounds_20_21" && \
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" package_returns.py
```

Return `reports/rounds_20_21_return.zip`. Keep all private_runs.
Do NOT run the old two-repository github_publish.py after either experiment.

The primary sources and hypothesis qualifications remain in the two protocols.
No scientific feature gain is claimed by the publication correction.
