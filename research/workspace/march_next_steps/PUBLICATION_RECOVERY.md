# Publication repair: exclude the generated tools environment

Update identifier: `publication-tools-environment-20260912`.

The supplied terminal log identifies four links under
`march-machine-learning-mania-2026/.tools`: `lib64`, `bin/python`,
`bin/python3`, and `bin/python3.12`. The repository's `scripts/bootstrap.py`
creates `.tools` with `python -m venv`; these are generated environment files,
not research source. The previous scanner omitted that exact environment path.

## What changes

The source scanner excludes only the documented original-repository `.tools`
subtree before traversing it. It does not delete, move, modify, dereference, or
publish the environment. Other source symlinks, potential secrets, missing sources,
and unexpected source edits remain subject to the existing safeguards.

The public aggregate CSV is normalized from CRLF to LF, with every parsed field
unchanged. This prevents a downstream `git diff --check` failure. Its allowlist
hash is updated. No feature/training code or experiment result changes.

Successful test fixture output is buffered, so mocked `REVIEW_BLOCKED` and
`LOCAL_PLAN_READY` messages no longer look like the real workspace result.

## Run in the existing Studio terminal

Download the newly supplied `apply_publication_update.py`. Upload it into your
JupyterLab home directory, replacing only the older home-directory updater.
Preserve all original research folders, raw data, environments, and private_runs.

```bash
cd "$HOME" && python3 apply_publication_update.py   --kit "$HOME/march_next_steps"   --expected-update-id publication-tools-environment-20260912 && cd "$HOME/march_next_steps" && export PATH="$HOME/.local/bin:$PATH" && python3 run_publication_tests.py && python3 github_publish.py plan
```

Required: `PUBLICATION_UPDATE_INSTALLED` (or `PUBLICATION_UPDATE_ALREADY_INSTALLED`),
`PUBLICATION_TEST_GATE: PASS`, `UNRESOLVED_BLOCKERS: 0`, then `LOCAL_PLAN_READY`.
The local test suite contains 53 tests; two exercise real Git in temporary local
repositories with GitHub API operations simulated. No research models are fitted.

Open the printed `REVIEW.md` and review the source/exclusions and public file
list. The plan intentionally does not copy raw inputs, environments, models,
private checkpoints, full executed research outputs, or old Git history.
Then run:

```bash
cd "$HOME/march_next_steps" && python3 github_publish.py publish && python3 github_publish.py merge
```

At the first prompt type `PUBLISH` after reviewing the local plan. The command
prints two pull-request links. Review their file changes before answering the
subsequent `MERGE` prompt. It does not bypass pending/failing reported checks or
GitHub branch protection. A GitHub refusal stops rather than force-pushing.

Destinations remain `alvaromendizabal/march-mania-research` (private source) and
`alvaromendizabal/march-mania-portfolio` (public evidence-only allowlist).
The original scientific checkout is not pulled, reset, or changed.
Existing GitHub CLI authorization is reused; no new password/token/login prompt
is started automatically. Do not run `auth` again for this scanner problem.

Successful remote publication ends with `MERGED_AND_PUBLICATION_CLONES_VERIFIED`.
Return `$HOME/march_publication/publication_return.zip`.
If preparation stops on a genuinely different issue, return
`$HOME/march_publication/publication_diagnostic.zip` or the test-return ZIP.
Do not rerun unchanged commands or delete the environment.

## Evidence and limits

Local tests establish this correction on temporary fixtures, including all four
reported links and actual local Git operations. GitHub API/PR replies were
simulated. No live AWS shell, remote Git push, repository creation, or merge was
performed by these local tests. Live ownership, visibility, authorization, network,
and remote checks are still verified during your execution.

The full local validation record is `PUBLICATION_TOOLS_VALIDATION.json`.
