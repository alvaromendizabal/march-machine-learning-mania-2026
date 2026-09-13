# Manual Git publication — only after both rounds finish

Nothing has been committed, pushed, merged, or checked live by ChatGPT. Keep the runnable kit outside the source repository during execution. Creating or staging repository files before the experiments changes the recorded repository state and can invalidate the preflight.

After both results are reviewed, preserve the canonical sibling kit. For publication, make an archival code-only copy; runtime instructions still refer to the sibling directory. Do not copy private_runs, reports, model weights, raw data, credentials, environment folders, or arbitrary untracked files.

```bash
cd "$HOME/march-machine-learning-mania-2026"
git status --short
git diff --stat
git diff --cached --name-only
```

If anything is already staged, stop and review it instead of combining unrelated changes. Do not discard the two known edited canonical notebooks. When ready to create an isolated code branch:

```bash
git switch -c research/feature-rounds-16-17
```

A branch-name conflict stops; do not force-reset an existing branch. Preview an explicit package-manifest file list, then create the archival copy only after reviewing it:

```bash
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  "$HOME/march_feature_rounds_16_17/prepare_publication.py"

"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  "$HOME/march_feature_rounds_16_17/prepare_publication.py" --write
```

The helper checks both completed reports, refuses an existing destination, strips notebook outputs to avoid publishing private team tables, and copies only manifest-listed sources, tests, documentation, constraints, and supplied aggregate evidence. It does not include `private_runs` or runtime `reports` and does not run Git. These are archival source notebooks, not newly executed employer-facing notebooks. Selectively publishing reviewed execution outputs is a separate step. Do not use `git add .` or `git add -A`.

```bash
git add -- research_kits/march_feature_rounds_16_17
git diff --cached --stat
git diff --cached --name-only
git diff --cached --check
```

Inspect the staged file list for outputs, secrets, environment folders, or unintended edits. Only after successful user-run tests, report review, and staged-content inspection:

```bash
git commit -m "Add controlled turnover and foul-pressure feature research"
git push -u origin research/feature-rounds-16-17
```

Open a pull request yourself, inspect its CI result and diff, and merge only after the checks you require pass. No merge is presumed. A later experimental kit will need refreshed repository-state evidence after a commit or branch change. Publishing the code does not prove a Brier improvement.
