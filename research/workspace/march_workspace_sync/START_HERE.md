# March Mania • Manual workspace recovery and research restart

**Milestone 0: synchronize source, preserve work, verify raw data. No model training.**

Best submitted Brier: **0.1222672**. Research target: **0.1097454**. Absolute gap: **0.0125218**; closing it requires about **10.24%** reduction from the current score. These are reported historical scores, not a result produced by this kit. Feature engineering is reopened. The earlier release can remain archived without treating the feature space as exhausted.

## What was verified, and what was not

On September 11, 2026, the connected GitHub reads showed:

| Item | Observed state |
|---|---|
| Published main | `84b8fb36644a6558beded6dad84f5645ea4405d3` |
| Latest release | PR #22, merged September 9, 2026 at 22:55:33 UTC |
| Post-merge quality | Run `34414562516`: completed/success on that exact main SHA |
| Open pull requests | None returned by the live open-PR read |
| Best submitted release | Men: pooled XGBoost, temperature 0.90. Women: conference logistic, C=1.0, temperature 1.10. Brier 0.1222672 |
| Existing research | 3,106 matchup candidates plus a separate 840 individual-ranking definitions; broad banks did not establish a stable gain |
| Studio space | `march-mania-dev` is the repository-documented space, not a newly verified live observation |
| Current AWS filesystem | **Not inspected**. Connected AWS inventory was blocked. Do not assume the space is synchronized or contains all raw inputs |
| New kit | Prepared and tested locally; **not committed, pushed or merged** into your repository |

A published branch does not prove there is no unpublished notebook work in Studio. Existing remote feature branches are not automatically merged by this kit. Fresh GitHub reads may change after this snapshot; the synchronization command stops when `origin/main` differs from the audited SHA.

Sources: [main](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/tree/84b8fb36644a6558beded6dad84f5645ea4405d3), [PR #22](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/pull/22), [post-merge CI](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/runs/34414562516), [Studio handoff](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/docs/studio.md).

## Do not wipe anything

Do not delete the SageMaker space, its volume, the repository folder, `data`, `outputs`, models, submissions, or Git stashes. Do not run `git clean -fdx`, `git reset --hard`, a forced pull, or `git push --all`.

GitHub deliberately excludes the raw dataset and large private artifacts. Downloading source again is not a data-recovery operation. This kit updates tracked source **in place**. It preserves ignored/untracked files, archives tracked edits in a named local stash, and saves patches plus a local Git bundle before switching/fast-forwarding main. Divergence, conflicting untracked files, and a changed upstream SHA stop the operation rather than erase work.

The recovery bundle and original data are still on the same Studio volume. They are not an independent disaster-recovery backup. Do not delete the space after running this kit. Existing versioned S3 archives are documented in the repository, but their current availability was not verified here.

## 1. Download the kit to your computer

Download `march_workspace_sync.zip` from the ChatGPT reply. Keep it as a ZIP for upload to JupyterLab. Everything in this guide assumes the extracted kit will be at:

```text
/home/sagemaker-user/march_workspace_sync
```

The kit stays **beside**, not inside, your Git repository. It does not replace any of your six canonical project notebooks.

## 2. Find the existing space without guessing the domain

Open the [AWS SageMaker AI console in Oregon](https://us-west-2.console.aws.amazon.com/sagemaker/home?region=us-west-2). Sign in and verify the region is **US West (Oregon), us-west-2**.

The repository documents the space name as **march-mania-dev**. The current domain and owner profile were not verifiable through the connected AWS call, so use AWS CloudShell to identify them rather than selecting the domain of a different project.

In the AWS console, click the **CloudShell** terminal icon in the top bar. Paste this entire block. It only reads resource descriptions:

```bash
(
  set -euo pipefail
  export AWS_PAGER=""
  DOMAIN_ID="$(aws sagemaker list-spaces --region us-west-2 \
    --query "Spaces[?SpaceName=='march-mania-dev'].DomainId" --output text)"
  if [[ -z "$DOMAIN_ID" || "$DOMAIN_ID" == "None" || "$DOMAIN_ID" == *$'\t'* || "$DOMAIN_ID" == *$'\n'* ]]; then
    echo "STOP: expected exactly one march-mania-dev space. Do not create or delete anything."
    exit 1
  fi
  aws sagemaker describe-domain --region us-west-2 --domain-id "$DOMAIN_ID" \
    --query '{DomainName:DomainName,DomainId:DomainId}' --output table
  aws sagemaker describe-space --region us-west-2 --domain-id "$DOMAIN_ID" \
    --space-name march-mania-dev \
    --query '{Space:SpaceName,Status:Status,OwnerProfile:OwnershipSettings.OwnerUserProfileName,InstanceType:SpaceSettings.JupyterLabAppSettings.DefaultResourceSpec.InstanceType}' \
    --output table
)
```

It prints the domain name, domain ID, owner profile, space and configured instance type. No app is started. If nothing matches or more than one match appears, stop; do not create or delete a space to resolve it. `locate_space.sh` in the kit performs the same read-only lookup with network timeouts.

Now return to **SageMaker AI → Studio**, choose the printed domain and owner profile, and select **Open Studio**. Inside Studio, select **JupyterLab → march-mania-dev**. Open the already running app, or select **Run** for this existing space and then **Open JupyterLab**. Use an existing small CPU configuration for this setup/audit milestone; no GPU or separate training/processing job is needed. Starting the app is a manual action and incurs its configured charges. Do not increase its storage or provision a replacement.

Official procedures: [launch Studio](https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-launch.html), [JupyterLab and persistent storage](https://docs.aws.amazon.com/sagemaker/latest/dg/studio-updated-jl-user-guide.html).

## 3. Upload and unpack the kit

In JupyterLab, save and close any open project notebooks. Shut down running notebook kernels so no process changes data during synchronization. In the left file browser, navigate to the home directory, showing the project folder. Click **Upload Files** and choose `march_workspace_sync.zip`.

Open **File → New → Terminal** (or Launcher → Terminal). Run:

```bash
cd "$HOME"
python3 -m zipfile -e march_workspace_sync.zip .
cd "$HOME/march_workspace_sync"
python3 --version
python3 -m unittest discover -s tests -v
```

The extraction is for this generated kit, not for untrusted competition archives. The safety tests use temporary synthetic data and local Git repositories. They neither access AWS APIs nor train models. Python 3.10 or newer and Git are required. If either is missing or a test fails, stop and preserve the error.

## 4. Inventory first

```bash
cd "$HOME/march_workspace_sync"
python3 workspace_sync.py inventory --max-seconds 600
```

The default project folder is:

```text
/home/sagemaker-user/march-machine-learning-mania-2026
```

The inventory reports its commit/branch, changed tracked paths, raw-data directories, private-file counts and disk space. Sensitive file contents and credentials are not printed. Git histories and local patch files produced later remain private on the volume.

If the repository is missing, check you opened `march-mania-dev`, not another project's space. Locate an existing checkout before cloning:

```bash
find "$HOME" -maxdepth 4 -type d -name 'march-machine-learning-mania-2026' -print
```

Pass its exact path using `--repo /actual/path` on **every** subsequent command, and set `MARCH_REPO` in the notebook. If the correct space truly has no checkout, the optional `clone` subcommand creates a fresh source directory only when the destination does not exist. It never restores raw data:

```bash
python3 workspace_sync.py clone --max-seconds 300
```

## 5. Synchronize GitHub source without wiping private files

```bash
cd "$HOME/march_workspace_sync"
python3 workspace_sync.py sync --max-seconds 600
```

The command checks the remote identity; fetches remote branches; confirms the audited main SHA; refuses unpublished/divergent local commits; checks for ignored/untracked path collisions; records raw CSV hashes and private artifact metadata; preserves tracked edits in a named stash plus local patches and Git bundle; fast-forwards main; and verifies tracked source and private-file preservation.

It deliberately does **not** pop the stash over updated notebooks. Local code/notes are preserved for review, not silently mixed into the published source. It does not upload, push, create a GitHub PR or merge one.

Successful `reports/sync.json` includes:

```json
{
  "status": "PASS",
  "head": "84b8fb36644a6558beded6dad84f5645ea4405d3",
  "tracked_matches_origin_main": true,
  "private_metadata_unchanged": true,
  "raw_sha256_unchanged": true,
  "github_writes": false,
  "training_started": false
}
```

Also inspect `raw_data_present` and `raw_files_hashed`: preserving zero raw files does **not** mean the dataset exists. If upstream has advanced, the command prints both SHAs and stops. Do not change `--expected-commit` blindly; review the new commit and its exact-head CI first.

## 6. Reuse the raw files or restore them from Kaggle

The project expects the official CSVs directly inside:

```text
$HOME/march-machine-learning-mania-2026/data/kaggle/raw/
```

If that folder already contains the complete dataset, do not download it again. If the inventory finds the official CSVs directly in `data/kaggle` instead, copy them into the canonical directory without deleting the originals:

```bash
python3 workspace_sync.py restore-data \
  --source "$HOME/march-machine-learning-mania-2026/data/kaggle" \
  --max-seconds 600
```

For another inventory-reported folder, replace only the `--source` path. This operation verifies hashes and never overwrites a differing destination file.

If raw files are genuinely missing, open the [competition data page](https://www.kaggle.com/competitions/march-machine-learning-mania-2026/data), sign in, complete any required rules/terms acceptance, and use **Download All**. Upload the resulting `march-machine-learning-mania-2026.zip` to JupyterLab's home directory. Then run:

```bash
cd "$HOME/march_workspace_sync"
python3 workspace_sync.py restore-data \
  --source "$HOME/march-machine-learning-mania-2026.zip" \
  --max-seconds 600
```

Use the actual downloaded filename if your browser appended a number. Do not put a Kaggle token in the terminal, chat, notebook, or GitHub. This browser-download route needs no token in the kit.

The importer rejects path traversal, symlinks, duplicate basenames, incomplete core archives, oversized archives, and conflicting existing bytes. It copies only official-looking CSVs after validating the complete copy plan. A conflict means the snapshots differ; keep both original sources, stop, and decide which version is appropriate rather than mix them.

The audit checks both men's and women's teams, seasons, regular compact/detailed results, tournament compact results and seeds. Rankings, coaches, conferences, game cities and sample templates are reported separately. Missing optional files are not invented. Current Kaggle downloads may contain completed 2026 tournament results: their presence must not become permission to train a 2026 predictor on them.

## 7. Install the repository's locked environment

```bash
cd "$HOME/march_workspace_sync"
python3 workspace_sync.py environment --max-seconds 900
```

This reads the pinned `uv` version from the actual committed `scripts/bootstrap.py`, uses the committed `.python-version` and `uv.lock`, installs into the repository's `.tools`/`.venv`, registers **Python (March Mania)**, and smoke-tests imports. It does not alter Studio's global Python packages. The stage has a total 15-minute cap and prints 15-second heartbeats; that is a stop limit, not a runtime prediction. A failed network/install step is not automatically retried indefinitely. Saved stages remain on disk.

Unlike the repository's original bootstrap, this setup milestone does not automatically run the entire quality suite or any existing training notebook. Locked environment installation and live AWS/network operation were not executed during local kit tests.

## 8. Run the visualization-led preflight notebook

In JupyterLab open:

```text
march_workspace_sync/00_workspace_sync_and_data_audit.ipynb
```

Select **Python (March Mania)** as the kernel. Run cells from top to bottom. The notebook runs only the data preflight and reads committed reports; it does not invoke model training. It produces an interactive data-coverage heatmap, legal pre-cutoff ranking coverage, data sizes, research-priority tables, and a saved HTML report.

The underlying audit streams the actual CSVs, validates key columns, counts records/seasons, records SHA-256 values and flags 2026 tournament labels. Per-file checkpoints are reused only when file bytes match. This is a table-level readiness audit—not proof of all per-team coverage, leakage safety, or feature usefulness.

Expected outputs are inside `march_workspace_sync/reports/`:

```text
sync.json
raw-file and stage receipts under runs/
environment.json
data_audit.json
data_coverage.csv
milestone_summary.json
workspace_audit.html
```

**Success gate:** `ready_for_next_feature_milestone` must be `true`. Read every optional-data warning even on a successful gate. This means source/raw-data setup is ready for the next bounded investigation; it does not mean new features have been implemented or validated, that private old checkpoints were restored from S3, or that a score improved.

## 9. Stop this milestone and preserve the result

Save the setup notebook. Download `reports/milestone_summary.json` through JupyterLab (right-click → Download), and attach that one file to ChatGPT. It contains file-level hashes/row counts and readiness results, not raw rows or credentials. Do **not** upload the entire recovery directory, command logs, patch files, Git bundle or private model archives.

Stop the JupyterLab **app** through Studio when finished with manual work; do not delete the space. Closing the browser tab alone is not the same action.

Do not change `MODE` to `train` in canonical notebook 02 or run all existing training notebooks yet. First use this inventory and the existing evidence to define one new feature-family experiment with a fixed comparator, training-only selection and a hard stop. See `FEATURE_RESEARCH_PLAN.md`.

## What to send when a command stops

Send its short terminal `STOP` reason or the shareable `milestone_summary.json`, not credential/patch logs. The kit intentionally stops rather than resets on divergence, data conflicts or missing inputs. Do not immediately rerun an unchanged failed command except for a diagnosed transient failure. No expensive job should be used to discover a schema or checkout problem.
