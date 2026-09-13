# Consolidate into the original March Mania repository

**Only GitHub destination:** `alvaromendizabal/march-machine-learning-mania-2026`.
No new GitHub repository is created. Research source is now intentionally public,
as requested. Credentials, raw restricted data, environments and model binaries
remain excluded. Existing scientific workspaces and checkpoints are not modified.

## What this package actually does

It uses your supplied successful publication receipt to recover **881 research
files and 10 public-presentation files** from the existing AWS publication clones.
It preserves their exact bytes in the original repository, adds a navigable
research index and a professional README, commits and pushes a normal branch,
opens a PR, waits for the existing `quality` and `notebook-publication` checks,
merges only a matching successful head, and verifies every migrated file in main.

It then deletes ONLY `alvaromendizabal/march-mania-research` and
`alvaromendizabal/march-mania-portfolio`, after independent local Git-history
backups and another main/hash check. It refuses deletion when either extra repo
has a new main commit or a branch/tag object missing from its backup.

The two source snapshots are already committed in your recorded local clones:
`~/march_publication/plans/20260913T025519Z-4d425c/checkouts/private`
and `.../checkouts/public`. Do not move or delete those folders.
This migrates the publication snapshot you returned, not unreported changes after
that snapshot. All AWS originals remain available, including full notebook outputs.

## 1. Upload

Open the existing `march-mania-dev` JupyterLab. Save/close the old publication and
research notebooks and shut down their kernels. Upload `march_canonical_release.zip`
to HOME, beside `march_next_steps` and the original project. Do not run old
`github_publish.py` commands: those describe the retired two-repository layout.

## 2. Extract and run the publication-only tests

Open File → New → Terminal. Paste:

```bash
cd "$HOME" && \
python3 -m zipfile -e march_canonical_release.zip . && \
cd "$HOME/march_canonical_release" && \
export PATH="$HOME/.local/bin:$PATH" && \
python3 -m unittest discover -s tests -q
```

Require `Ran 44 tests` and `OK`. Tests use temporary local Git repositories and
simulated GitHub replies. They do not call your accounts, read competition data,
run scientific notebooks, or fit models. There is no package installation.

## 3. Run the single-destination repair

```bash
cd "$HOME/march_canonical_release" && \
python3 consolidate_march.py run \
  --approve-public-source \
  --delete-extra-repos \
  --wait 600
```

The flags explicitly approve publishing the snapshot into the original PUBLIC
repository and deleting the two literal extra repositories after preservation.
No interactive password, token request, automatic login, or force push is used.

Stages: `PLAN_READY` → `PUSHED_TO_ORIGINAL` →
`MERGED_IN_ORIGINAL_AND_VERIFIED` →
`CONSOLIDATED_AND_EXTRA_REPOSITORIES_REMOVED`.

Only the LAST status establishes both migration and cleanup. Check the printed
repository: it must be the original name, never either extra repo.
The printed PR link allows review while the existing repository's checks run.
Do not bypass those checks. New archived research source is outside the original
CI's scientific test scopes; passed legacy CI is not new scientific validation.

A separate LOCAL clone is used for publication. It is another local checkout of
THE SAME original GitHub repository, not a new GitHub repository. The existing
scientific checkout remains pinned so old feature/model cache identities are not
invalidated by publication.

## 4. Handle bounded pending states

`CHECKS_PENDING` means the 600-second CI polling window ended. Nothing was merged
or deleted. Run the same repair command again; it reuses its plan, commit and PR.
It does not generate another experiment. A failed check is a STOP, not a permission
to merge anyway. This package does not modify repository protections or CI.

`MIGRATED_CLEANUP_PENDING` means source is merged and verified but GitHub refused
repository deletion. Your existing login may lack the separate `delete_repo`
scope. Only in that case:

```bash
gh auth refresh --hostname github.com --scopes delete_repo
```

Follow the browser/code approval, then run:

```bash
cd "$HOME/march_canonical_release" && \
python3 consolidate_march.py cleanup --delete-extra-repos
```

This adds only the permission needed for your explicitly requested deletion; it
is not automatic and does not bypass authentication. GitHub may require browser
sign-in or 2FA. Never paste the code or any credential into ChatGPT. Browser manual
deletion is also possible after migration verification through each EXTRA repo's
Settings → General → Danger Zone → Delete this repository. Never select the original.

Any other STOP writes a diagnostic receipt. Do not repeatedly retry unchanged
failures, delete caches, change source hash checks, or reinstall the environment.

## 5. Return one receipt

Download and attach:

`~/march_publication/canonical/consolidation_return.zip`

It records the original repo's commit/PR/merge/hash verification and individual
cleanup outcomes. Local code/history backups remain under:

`~/march_publication/canonical/backups/`

These are local Git mirrors and self-contained bundles plus selected GitHub
metadata/comments. They are NOT a complete archive of every GitHub service (for
example Actions logs, settings, packages or wiki data). Release assets trigger a
stop for separate backup rather than silent deletion. Your original extra-repo
working clones are retained even after remote deletion.

## Presentation and source layout

The root README links the original scored release and executed review notebooks,
the research implementation index, a report-only Plotly notebook, and exact migration
provenance. Each AWS kit's source is preserved under `research/workspace/`.
`research/publication_archive/` preserves the earlier presentation bytes for provenance;
its old privacy/right statements are not the current repository policy.

Imported scientific notebooks are SOURCE snapshots with empty outputs (as in the
publication you already performed), not newly executed employer notebooks. The six
original executed release notebooks stay intact. A new report-only notebook at
`portfolio/research_results.ipynb` has three inline Plotly charts when the user runs
it; no training code is imported. Do not claim its outputs already exist.

## Research next

Read RESEARCH_NEXT.md. Rounds 20 and 21 remain the next complete prepared pair;
your current upload is a publication receipt, not results from those experiments.
Each retains four candidates and ten planned inline Plotly figures. Do not start
extra rounds merely to compensate for a publication failure.

## Validation and limits

See VALIDATION.json for the actual local publication-test record. No scientific
code or models were executed by preparation of this correction. GitHub API calls
and deletions were simulated in local integration tests; live permissions,
connectivity and CI still need to pass. This is not a guarantee of zero runtime
errors or a claim that a remote migration has already happened.

Individual commands have 180-second limits (300 for clones/pushes), with 15-second
heartbeats. CI polling is separately capped at 600 seconds by the command above
(maximum configurable 900). These are process ceilings, not expected duration or
AWS billing limits. The running Studio instance is not stopped by this helper.

Official documentation:
- https://cli.github.com/manual/gh_repo_delete
- https://cli.github.com/manual/gh_pr_merge
- https://docs.github.com/en/repositories/archiving-a-github-repository/backing-up-a-repository

After a verified merge, the helper also backs up and disables the receipt-matching old `~/march_next_steps/github_publish.py` so it cannot recreate the split destinations. An unknown local edit is preserved and explicitly reported instead of being overwritten. No scientific module is changed.
