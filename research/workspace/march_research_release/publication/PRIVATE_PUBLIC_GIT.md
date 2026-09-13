# Manual Git publication: private source, public evidence

## The non-negotiable limitation

A public implementation is readable and copyable. GitHub permits public repository viewing/forking under its platform terms. Your original repository's LICENSE was read through the connected GitHub tool in this conversation: it is MIT and grants broad use/copy/modification/distribution rights subject to its notice conditions. Ordinary reuse under that license is not automatically theft.

Removing a file from main does not remove it from history, forks or old clones. Replacing a license does not turn previously licensed distributions into secret property. Existing permissions and third-party/contributor rights require legal review; this guide is not individualized legal advice. Making the old repository private limits new public access to that repository, but public forks/local copies remain. Do not promise that already published code can be recalled.

## Recommended layout

| Location | Visibility | Contents |
|---|---|---|
| Existing `march-machine-learning-mania-2026` | Make private manually after the public showcase is ready | Preserve original commit history and old code; do not wipe/rewrite |
| New `march-mania-research` | PRIVATE | Versioned AWS source snapshots, tests, protocols and reviewed small evidence tables |
| New `march-mania-portfolio` | PUBLIC | Fresh-history, report-only case study, aggregate results and visualization notebook |
| Existing SageMaker directories / private storage | PRIVATE | Raw data, full executed research notebooks, models and checkpoints |

Do not fork the public research repository to make the private source destination. Create a new, standalone private repository. Do not copy the old `.git` directory into the showcase. Do not use hidden notebook cells, minification or compiled Python as a confidentiality boundary.

Research continues in the ORIGINAL AWS paths. These publication clones are one-way curated snapshots; do not move the working research tree or pull public material over it. That avoids invalidating pinned Git/input states in the experiment runners.

## 1. Preserve history and uncommitted work locally

Open a terminal in the existing JupyterLab. No kernels should be editing repository notebooks during publication.

```bash
set -euo pipefail
BASE="$HOME/march_release_staging"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$BASE/backups/$STAMP"
mkdir -p "$BACKUP"
chmod 700 "$BASE" "$BASE/backups" "$BACKUP"
REPO="$HOME/march-machine-learning-mania-2026"
git -C "$REPO" bundle create "$BACKUP/legacy-history.bundle" --all
git -C "$REPO" bundle verify "$BACKUP/legacy-history.bundle"
git -C "$REPO" diff --binary > "$BACKUP/unstaged.patch"
git -C "$REPO" diff --cached --binary > "$BACKUP/staged.patch"
git -C "$REPO" status --porcelain=v1 > "$BACKUP/status.txt"
```

The bundle preserves committed history and refs, not untracked files. The source staging step below covers reviewed current source files; raw datasets and private artifacts remain at their original locations. Do not add the bundle/patches to the public repository. This is not a claim to back up every byte in the space.

## 2. Create two initialized repositories in your browser

On GitHub while signed in as `alvaromendizabal`, choose **+ → New repository**.

1. Name `march-mania-research`, choose **Private**, and add a README. Do not add a new license that purports to override existing MIT/third-party files. Create the repository and visibly confirm its **Private** badge.
2. Name `march-mania-portfolio`, choose **Public**, and add a README. Do not copy the old source repository. It will receive only the curated allowlist.

These names are the expected targets in the provided scripts. If either already exists, inspect it first; do not delete it or force-push over it. The public staging helper refuses unreviewed existing tracked files.

## 3. Stage a private source snapshot

Run after recovering the failed work, or now with unfinished work explicitly labeled. This captures current source/tests/protocols from the known research folders. Existing outputs are stripped only from the staged notebook COPIES. Original executed notebooks are not changed. Data/model/report directories and workflows are excluded; small supplied evidence tables can be included. The exclusions and every source/staged hash are recorded.

```bash
PYTHON="$HOME/march-machine-learning-mania-2026/.venv/bin/python"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SNAP="$HOME/march_release_staging/source-$STAMP"
"$PYTHON" "$HOME/march_research_release/publication/stage_private.py" --destination "$SNAP"
printf '%s\n' "$SNAP" > "$HOME/march_release_staging/latest_source_path.txt"
```

Require `SOURCE_SNAPSHOT_READY_FOR_PRIVATE_REVIEW`. Inspect `PRIVATE_SNAPSHOT.json`, especially missing roots, exclusions and source hashes. A heuristic secret/oversize/symlink finding yields `REVIEW_BLOCKED`; do not push until reviewed. A scanner is not a guarantee: inspect code and notebook inputs locally for passwords, tokens, private URLs and restricted data. Never paste credentials into ChatGPT.

## 4. Commit and push the private snapshot on a branch

The next commands assume you have working GitHub HTTPS credentials in this terminal. They do not install authentication software or print tokens. If authentication fails, stop and complete GitHub's normal sign-in/credential setup yourself rather than adding credentials to source files.

```bash
cd "$HOME/march_release_staging"
git clone https://github.com/alvaromendizabal/march-mania-research.git private-checkout
cd private-checkout
test "$(git remote get-url origin)" = "https://github.com/alvaromendizabal/march-mania-research.git"
test -z "$(git status --porcelain)"
git config user.name "Alvaro Mendizabal"
git config user.email "108156083+alvaromendizabal@users.noreply.github.com"
git switch -c research/aws-source-snapshot
SNAP="$(cat "$HOME/march_release_staging/latest_source_path.txt")"
cp -a "$SNAP/research" .
cp "$SNAP/PRIVATE_SNAPSHOT.json" PRIVATE_SNAPSHOT.json
cp "$SNAP/README.md" README.md
git status --short
```

**Before staging, revisit the GitHub repository and confirm its Private badge.** A matching name/remote alone does not prove privacy. Do not run this in the original research repository or the public clone.

```bash
git add -- research PRIVATE_SNAPSHOT.json README.md
git diff --cached --stat
git diff --cached --check
git diff --cached --name-only
```

Review the staged content, not just filenames. Do not represent source preparation as successful test execution. The provided validation records explicitly say new tests are unexecuted until your returned receipts establish otherwise. The full original history remains in the bundle and old repository; this new private repo begins with a curated current snapshot.

When that review is complete:

```bash
git commit -m "Preserve audited AWS research source and manual execution protocols"
git push -u origin research/aws-source-snapshot
```

In the browser, open the **private** repository → Pull requests → New pull request. Compare `research/aws-source-snapshot` into `main`. Review Files changed, then **Create pull request → Squash and merge → Confirm squash and merge**. Do not claim CI passed unless a real check reports success. No AWS-triggering workflow is included.

After merging:

```bash
git switch main
git pull --ff-only origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
```

That establishes this publication clone matches its fetched `origin/main`; it does not change the original scientific checkout. Later snapshots use a new review branch, not a force push.

## 5. Execute the safe public results notebook

Open `$HOME/march_research_release/public_portfolio/notebooks/portfolio_results.ipynb` in JupyterLab with Python (March Mania). Run its three code cells, save, close and reopen to check outputs. It renders three charts solely from aggregate supplied evidence and writes `public_portfolio/results.html`. It imports no feature/training pipeline and has no cloud calls.

Read the README, case study, experiment ledger and rights notice. Scores are historical/retrospective; unfinished research is marked pending. No full public reproducibility claim is made. Update status only from actual executed reports, not from guessed gains. Do not add original research notebook outputs, full feature registries, raw per-game data, weights or checkpoints to this directory.

## 6. Stage only the public allowlist, then commit/push/merge

```bash
cd "$HOME/march_release_staging"
git clone https://github.com/alvaromendizabal/march-mania-portfolio.git public-checkout
cd public-checkout
test -z "$(git status --porcelain)"
git config user.name "Alvaro Mendizabal"
git config user.email "108156083+alvaromendizabal@users.noreply.github.com"
git switch -c portfolio/research-case-study
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  "$HOME/march_research_release/publication/stage_public.py" \
  --destination "$HOME/march_release_staging/public-checkout"
git status --short
```

Require `PUBLIC_FILES_COPIED_FOR_REVIEW`. This helper checks the exact public remote and the allowlist; it does not commit or push. Inspect every public file including the notebook's visible source/outputs and embedded HTML data. All of it will be copyable.

```bash
git add -- README.md RIGHTS.md CITATION.cff .gitignore docs data notebooks results.html
git diff --cached --stat
git diff --cached --check
git diff --cached --name-only
```

Only the case-study/ledger/rights files, the sanitized aggregate table/provenance, the report-only notebook, and its HTML report should be staged. No `research/`, original `src/`, models, secret files, raw tables or `private_runs/` may appear.

After review:

```bash
git commit -m "Publish report-only NCAA forecasting case study and aggregate evidence"
git push -u origin portfolio/research-case-study
```

In GitHub: open the public repository → compare branch → review Files changed → Create pull request → Squash and merge. Then:

```bash
git switch main
git pull --ff-only origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
git log -1 --oneline
```

Open the public repo signed out to review the employer view. Pin this new repository on your profile and replace résumé links with this showcase. Plotly runs in the saved HTML/Jupyter notebook, not necessarily in GitHub's static notebook preview. Optionally enable GitHub Pages from `main` at `/` and use the generated `results.html` page after its deployment succeeds; that action deliberately publishes all showcase files.

## 7. Limit future access to the old implementation

Only after the new public showcase and private snapshot are confirmed, go to the original repository → Settings → General → Danger Zone → Change repository visibility → Private. Review GitHub's confirmation and effects. Keep the repository name and local folder unchanged; do not delete/rewrite history. This is a manual visibility action, not something any script here performs.

Existing public forks remain public, old clones remain, stars/watchers can be lost, and Pages availability can change. If you choose to leave the original MIT repository public, then its implementation remains public and the new portfolio does not hide it. That is incompatible with preventing further direct access to that old code.

## 8. Verify what was actually synchronized

After the private clone is clean and fetched, run:

```bash
"$HOME/march-machine-learning-mania-2026/.venv/bin/python" \
  "$HOME/march_research_release/publication/verify_snapshot.py" \
  --checkout "$HOME/march_release_staging/private-checkout" \
  > "$HOME/march_release_staging/private_sync_receipt.txt"
cat "$HOME/march_release_staging/private_sync_receipt.txt"
```

Require `LISTED_SOURCE_SNAPSHOT_MATCHES`. It checks listed live AWS source files against their staged hashes, not new unlisted files or dataset/model storage. Save private and public merge SHAs from each browser PR. The separate clones should be clean and match their fetched remote main. The original AWS research checkout should remain unchanged. Preserve `PRIVATE_SNAPSHOT.json` as a mapping from original source bytes to staged files (not a claim that raw data/models are in Git). Future source changes require a new explicit snapshot/review. Report only these observed outcomes—do not call all AWS data backed up or all old public copies removed.

## Sources and licensing caution

- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository
- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility
- https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
- Original project's LICENSE: MIT, observed via read-only connected fetch.

If actual credentials were exposed, revoke/rotate them first; changing visibility alone is not remediation. This package does not perform a complete historical secret audit. Licensing of previously released or jointly authored work should be reviewed by a qualified lawyer before asserting restrictions. Public portfolio presentation cannot technically prevent screenshots or copying.
