# Completion audit · expanded NCAA feature research

Evidence date: 2026-09-08. The expanded experiments and all six native notebooks are
complete and published. Final merge/check status is recorded on PR #8. The original 124-feature release remains in Git
history and its versioned archives; its final predictions are not relabeled as new work.

**Current location:** the repository's `main` branch, under `notebooks/00` through
`05`. The expanded 02 → 03 → 04 lineage is complete, not waiting for its first
training run. A follow-up prompted by the question “are enough features actually
used?” adds the completed capacity study in section 17. The first release's
execution proof remains in `reports/validation/release.json`.

## 1. Where the project started

The main branch already contained executed 124-feature research: 660 feature-ablation
fits and a 497-fit model comparison. A later 553-fit extension added ranking tree
families against the same 124 features and was completed privately, but unpublished.
Its best scores remained unchanged. The remade wide notebook 02 had not supplied the
features for either run. The user's concern about training lineage was justified.

## 2. Stale or incomplete work

The branch contained expanded feature code but unexecuted revised notebooks 02–05,
a coach-feature type-check failure, stale 124-feature narrative/results, incomplete
coach/conference integration and weak source-to-report freshness enforcement. The
2022–2025 benchmark had already been used. Historical Kaggle score refinements after
outcomes became available could not support a new prospective accuracy claim.

## 3. Changes to notebook 02

The feature stage now documents a broad basketball feature catalog, missing-source
coverage, temporal target/coach histories, annual conference context, train-only
screening and controlled full/drop-one ablations. Each saved estimator records the
exact retained columns. Notebook 02 displays the results and rejection counts with
interactive figures and static fallbacks suitable for GitHub review. Exact data,
configuration, source and environment hashes connect its matrix to notebooks 03–05.

## 4. Candidate and retained feature counts

The completed bank has **3,106 candidates**: 124 existing signals, 2,944 distribution,
recency, venue, opponent, trajectory and peer summaries, 26 coach signals and 12
conference-context signals. All 20 full-bank ablation fits retain **128 inputs each**.
There are **251 distinct retained features across those fits**, not a single globally
selected 251-feature model. Across 1,050 fits, 1,674,530 screening decisions include
1,585,764 rejections and 88,766 retentions. Public `screening_summary.csv` and
`selection_stability.csv` expose the counts; the full per-candidate audit is archived.

## 5. Target encoding and leakage evidence

Encoding uses strictly earlier tournament seasons, both team perspectives once,
historical categories from each game's own season, a fixed Beta(10,10) prior,
three-season half-life and five-season window. Cold starts return 0.5; unavailable
rank categories remain missing. The first configured 2013 season is intentionally
cold even though older raw labels exist. Current seeds/ranks never reassign historical
outcomes to new bins.

Tests perturb or remove current/future labels, change current seed/rank categories,
shuffle input order, separate genders and exercise cold starts/window boundaries.
Model selection, calibration and blend tests independently perturb outer/future labels.
This demonstrates the implemented temporal boundaries; it is not a claim that any
finite test suite proves every possible absence of leakage. Default random-fold
`TargetEncoder` was not substituted for chronological encoding.

## 6. Massey coverage and measured contribution

Every active men's team in 2013–2026 has a legal ranking snapshot; the latest ranking
day is 128 against a day-132 cutoff. System counts vary by season. The official raw
coverage table also records pre-2003 absence and earlier partial years. Women's Massey
is unavailable, so women's and pooled common models exclude all 23 ranking-derived
inputs rather than impute a fabricated source. See the complete
[source coverage table](../reports/feature_store/source_coverage.csv).

Adding Massey to the screened men's bank changes mean-season Brier by **−0.002479**
for histogram boosting (95% season-bootstrap interval **[−0.005634, 0.000761]**) and
**+0.003250** for logistic (**[−0.001947, 0.008863]**). These conditional pipeline effects
include rescreening. Neither full-bank interval establishes a reliable improvement. In the separate compact
strength-plus-rankings histogram comparison, rankings improve mean-season Brier by
**−0.010687 [−0.016580, −0.002978]**. That interval excludes zero for this specific
retrospective contrast; it is exploratory and unadjusted for the many comparisons.

## 7. Coach features and measured contribution

Official men's coaches are matched to their actual day intervals. Current stints,
changes and tenure use pre-cutoff assignments; performance and tournament experience
use strictly earlier seasons. Conference membership respects annual realignment;
independents are not pooled as a fictitious conference. Women have no official coach
table in this snapshot, and that limitation remains explicit.

Keeping coach features in the expanded non-Massey men's bank changes logistic Brier
by **−0.010429 [−0.031271, 0.009248]** and histogram Brier by
**−0.006302 [−0.014599, 0.002199]**. Men’s target encodings change these same pipelines
by **−0.000715 [−0.003142, 0.000807]** and **−0.001076 [−0.003754, 0.001378]**.
All intervals include zero. Women's coach-removal predictions are identical because
that source is unavailable. Feature-group effects are not causal effects on basketball.

## 8. With- and without-Massey model results

| Best observed development stream | Mean season Brier | Game-weighted Brier |
|---|---:|---:|
| Men, no-Massey pooled blend | 0.188396 | 0.188324 |
| Men, ranking logistic | 0.188468 | 0.188403 |
| Women, separate logistic without Massey | 0.144823 | 0.144823 |

These are selected minima on five explored development seasons. A matched family
ablation is stronger evidence about the ranking contribution than comparing unlike
winning model families. The common no-Massey column universe is identical between
separate and pooled fits; men's coach availability still differs from women's.

## 9. Initial expanded-release notebook execution

All canonical notebooks **00 → 01 → 02 → 03 → 04 → 05** passed real Jupyter execution,
with **39 executed code cells** and no error/warning outputs. The final review pass
reused all six verified notebook checkpoints and started zero new notebook tasks.
Train mode also passed for 02, 03 and 04 using the completed current artifacts.

The publication workflow independently downloaded the model archive into a fresh
directory, restored and reused **all 901 task checkpoints**, repeated **zero tasks**,
and reproduced byte-identical CSV and Parquet predictions. This proves restoration
and reuse of these stored artifacts, not bitwise equivalence of fresh fits across
all hardware platforms. The completed source, outputs and logs are preserved in the
[successful native run](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/runs/34202281698)
and the versioned validation archive referenced by `reports/validation/release.json`.

A local kernel restriction was handled through actual GitHub Actions Jupyter execution;
Python preflight or simulated outputs were never substituted for that gate.

## 10. Initial expanded-release tests and quality gates

**202 tests passed, with zero failures, errors or skips.** Compilation, Ruff lint,
formatting and mypy passed in the locked Python 3.12.13 environment. Measured line
coverage is **84.54%** (2,718 / 3,215 lines across the modules selected by the quality
script). This is not a whole-repository or branch-coverage claim.

The tests cover temporal encoding, coach histories, ranking publication cutoffs,
conference realignment, screening, probability symmetry, nested selection/calibration,
checkpoint corruption/interruption, clean-checkout publication and real-kernel reuse.
The native gate caught and led to fixes for a transient lock in the public manifest
and a stale appendix feature-count assertion. The final source passed both the
[independent review workflow](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/runs/34202284245)
and the full artifact-backed publication workflow. Exact final branch checks remain
visible on PR #8; merge is conditional on those checks passing.

## 11. Git and durable experiment evidence

[PR #8](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/pull/8)
contains the completed work and records the final merge and branch checks.

| Public commit | Purpose |
|---|---|
| `8dac9f8` | Complete temporal features, source lineage and benchmark integration |
| `6067b08` | Publish completed expanded experiments and honest measured findings |
| `cf715fc` | Exclude temporary locks from public benchmark evidence |
| `5257522` | Bind appendix dimensions to the catalog and clarify feature plots; final validated computational/notebook source |
| `5ac339e` | Publish all six actually executed notebooks and verified recovery evidence |

`reports/validation/release.json` records workflow links, exact notebook byte hashes,
quality results, model recovery and independent verification that the public source
commit matches every recorded computational source hash. Full feature, model,
benchmark and validation archives have version IDs and verified SHA-256 checksums.
Private raw files, trained binaries and credentials are excluded from Git. Historical
artifacts and the local computation history were preserved. No new AWS compute was
provisioned, and no new submission file or Kaggle upload was produced.

## 12. Final measured metrics and lineage

| Completed stage | Fits | Evidence fingerprint |
|---|---:|---|
| Feature ablations | 1,050 | `199b4c00a8b59393a1290727ca6e0e5b9f9bbc5a17db18e1b02354229e5eed89` |
| Nested model comparison | 861 | `20e69d30dc746f39f9395f96d1ff13d7a24cb0a7998fd096a0409c31fa7d7193` |
| Current retrospective benchmark | 16 | `2680bf105e369bbeb1b937d504c8b4f4c8c3772895869acc8b7c5decd0fb9b74` |

| Frozen benchmark route, 2022–2025 | Men Brier | Women Brier |
|---|---:|---:|
| Seeded | 0.198288 | 0.146881 |
| Seed-free | 0.197639 | 0.148550 |
| Previous 124-feature seeded anchors | 0.198014 | 0.138599 |

The enlarged bank does not improve both populations. Men's best development score
is essentially tied with the old 0.188476; women worsen from 0.143867 to 0.144823.
The current women's conference anchor also regresses on the consumed benchmark.
Its family/block/penalty choices were frozen from pre-2022 forecasts before benchmark
labels were read, and are not reselected after seeing this result. The benchmark
includes play-ins and cannot be equated to Kaggle scores. No 2026 estimator or
submission file was produced by this work.

## 13. Remaining research weaknesses

Five development seasons, limited early calibration history, a large retrospectively
explored search space and an already-consumed benchmark constrain generalization
claims. The primary combined coach/encoding and full-bank Massey controls do not resolve a
benefit. Several individual groups show deterioration, and compact men’s rankings
help histogram boosting in a different contrast; these are unadjusted exploratory
intervals, not independent confirmation after the search. Women's
ranking/coaching source parity is absent. Player availability and returning production
would require timestamped historical data not present in this snapshot. The original
rich-system men's score of 0.180669 used a different schema/history; it is retained
as historical evidence rather than credited to this run. Historical neural and margin
models were not retrained. No new leaderboard ranking or medal is established.

## 14. Honest completion estimate

At audit start, approximately **70–75% of the intended deliverable** was complete:
substantial engineering existed, but the expanded-feature experiment and notebook
handoff evidence were missing. The requested implementation, evaluation, reproducibility
and employer-facing publication work is now complete, subject to the final merge gate.

Engineering and portfolio readiness are **about 95%**, as a judgment rather than a
measured percentage. That must not be interpreted as 95% of a guaranteed accuracy
improvement. The claim that the expanded features materially improve both populations
remains unproven. The capacity follow-up strengthens the feature-sufficiency audit,
but still does not beat the compact leaders. A genuinely unseen tournament would
provide new generalization evidence; rerunning consumed years cannot do so. A
guaranteed 9.9/10 rating or state-of-the-art accuracy claim is not supported.

## 15. Employer readiness

**Yes: this is ready to present as an employer-facing ML research and engineering
project.** The notebooks let a reviewer trace data, temporal features, model choices,
calibration, uncertainty and negative results without an AWS account. The repository
now demonstrates completed experiments, readable executed notebooks, tested handoffs,
versioned artifacts and recovery from a clean environment.

Its strongest claim is disciplined research and reproducible engineering. The expanded
features did not establish forecasting superiority, and the presentation says so.
Keeping that distinction explicit is part of the project's scientific quality.

## 16. Highest-value remaining step

Freeze a compact recipe and evaluate the next genuinely unseen tournament with
pre-tournament source snapshots and a predeclared scoring population. Retain the
previous frozen artifact while treating the expanded recipe as retrospective research.
Further tuning on 2022–2025 or adding unvalidated columns cannot create fresh evidence.
The release can be reviewed now. The completed capacity experiment below resolves
an additional reasonable question about the feature screen; it does not justify
blindly expanding the number of model inputs or rerunning identical completed fits.
Higher-value future research would require independently useful inputs with verified
historical availability, or prospective outcomes. The current evidence is a bounded
search over the official data, not a proof that every conceivable representation has
been exhausted.

## 17. Completed retained-feature capacity follow-up

The initial 128-input cap was a modeling assumption. The follow-up compares **32,
64, 128 and 256** on the identical expanded matrix, holding screening logic and
the two estimator recipes fixed. It covers men with Massey, men without Massey,
and women. Seven earlier OOF seasons support forward-only capacity selection for
the five reported outer seasons. There are **168 evaluated fits: 138 fresh fits
and 30 inherited 128-input fits** whose original checkpoints and populations were
verified. All 42 fits at each limit retain exactly that many inputs. The new audit
records 519,232 candidate decisions, 20,160 retentions and 499,072 rejections;
these are repeated per-fit decisions, not that many distinct features.

| Fixed estimator / route | Original cap 128 | Forward-selected cap | Brier change |
|---|---:|---:|---:|
| Logistic / men with Massey | 0.207742 | 0.192095 | −0.015647 |
| Logistic / men without Massey | 0.204492 | 0.194492 | −0.010000 |
| Logistic / women | 0.171561 | 0.164711 | −0.006850 |
| Histogram / men with Massey | 0.192678 | 0.196706 | +0.004027 |
| Histogram / men without Massey | 0.195157 | 0.194984 | −0.000173 |
| Histogram / women | 0.167173 | 0.167077 | −0.000096 |

These are mean-season Brier scores. All six forward-selected comparisons have
paired season-bootstrap intervals including zero. The men's four fixed comparisons
of 256 versus 128 have positive intervals excluding zero: expanding capacity hurts
these particular exploratory contrasts. No multiplicity correction is claimed.
Smaller broad models still trail compact model leaders. This is evidence for
strong regularization and diminishing returns to more retained candidates, not a
new best model or proof of global feature-space exhaustion.

Notebook 02 contains the actual tables, interactive capacity curves and a static
GitHub fallback. The original 03/04 source, feature/model fingerprints and declared
recipes stay current: their estimates are not relabeled as results from this
follow-up. Target encoding continues to use strictly earlier seasons, and capacity
selection never reads outer/future labels. Ten additional automated tests cover
these boundaries, equivalent original-recipe predictions, fitted-state removal,
matched-game selection, corrupt reference checkpoints and an end-to-end study that rejects future labels and resumes without fitting again.

A second execution reused **all 168 capacity tasks**, repeated **zero fits**, left
every model file unchanged and reproduced prediction SHA-256
`db437ef2b1755133a0a266d6954c8d2332d185e9af6bc1dcfc4df6e6ca010ed3`.
See the [complete capacity results](../reports/feature_capacity/README.md) and
their [exact fingerprint](../reports/feature_capacity/run.json). The new portable
archive is now uploaded after the explicit storage approval. AWS verified its
48,840,617-byte size and full-object SHA-256 checksum. A fresh download of version
`vLVWiCH59.GqdWUvQJw1QhkVwwh2IOEJ` restored all 168 tasks, repeated zero fits and
reproduced byte-identical predictions. The existing verified feature run supplies
the original estimator templates; the recovery receipt makes this dependency explicit.

The previous 124-feature studies, current 3,106-candidate model comparison, and
this capacity sensitivity study are three distinct pieces of evidence. A fresh
inspection of GitHub and S3 verified that all completed current artifacts exist.
The SageMaker space `march-mania-dev` still exists with 50 GB of persistent storage;
its JupyterLab app is stopped. Its filesystem was not claimed to be synchronized
with the newly published GitHub notebooks.

The follow-up passed actual native execution of **all six current notebooks and
40 code cells**, with no error/warning outputs; a second pass reused all six
notebook checkpoints. The validated source passed 211 tests. The publication
revision adds the tested end-to-end case, bringing the suite to 212; exact-head
checks are recorded on PR #9. The [follow-up validation receipt](../reports/validation/capacity.json)
records the exact source checkout, notebook hashes, original test count, fresh
archive restore and the subsequent verified versioned S3 recovery. It does not relabel
an ordinary Python preflight as native notebook execution.


## 18. Individual ranking systems and the feature-research stopping decision

The consensus could conceal informative differences between ranking methods. This
remaining official-data hypothesis is now tested: 105 pre-2013 systems generate
840 additional definitions, bringing the project-wide explored definitions to
3,946. The independent study retains the compact base and compares level,
deviation, momentum, availability, combined and eight-component PCA additions.
All source panels, screening and embedding boundaries are chronological. Twelve
new automated tests exercise these boundaries and end-to-end recovery.

The study completed 112 fits, of which 20 verified controls were reused and 92
were fresh. All 112 saved models reload and reproduce their predictions exactly;
all 18 metric rows were independently recomputed. A second execution reuses the
matrix and all fits (113 tasks) without fitting again. The same 334 men's outer
games are scored by every arm. See the [complete measured results](../reports/ranking_systems/README.md).

A fixed individual-level logistic model nominally improves mean-season Brier from
0.187608 to 0.186924, but its delta interval crosses zero. The combined screen
selects only those level logits and produces identical predictions. Across the
ten combined outer fits, 22 distinct additions survive; 818 never do. Forward-only
representation selection worsens logistic Brier to 0.195240. Histogram variants
also fail to beat the consensus on average. No 2022–2026 labels are consulted and
no final recipe is changed after seeing these results.

The evidence supports closing the **bounded official-data representation search**:
1,050 primary ablation fits, the 168-fit capacity sensitivity and the 112-fit
individual-system study cover the main plausible avenues in the available inputs.
Larger retained representations, extra ranking detail and its latent embedding
have not shown stable incremental benefit. The search does not establish that
all imaginable features are exhausted. Player availability/returning production
and women's coach/rating parity lack verified historical sources in this snapshot;
claiming to have tested them would be false. Raw historical target encodings also
remain weak and uncertain, despite explicit temporal tests and drop-one controls.

The final conclusion remains a negative-result research project with defensible
feature contributions from compact team strength and consensus ratings, not a
claim that thousands of generated inputs beat every earlier model. Final tuning
on consumed benchmark years would not resolve that limitation. Additional useful
accuracy evidence requires independently informative timestamped inputs or a
prospective tournament evaluated under a frozen protocol.


Both follow-ups now have verified versioned S3 archives and canonical fresh-checkout
restoration. The recovery path reused 168 capacity tasks and 113 ranking-system
tasks, preserving all 280 model files and both prediction hashes. Four additional
workflow tests cover version-specific restoration, existing-run reuse, changed
source and rejected archive lineage. Notebook 02 calls this recovery path directly
in train mode. Native validation and final publication checks are recorded in the
ranking-system validation receipt and its pull request.


## 19. Latest executed publication evidence

The ranking-system revision passed **228 tests**, zero failures/errors/skips,
compilation, lint, formatting and type checks in the locked environment. Actual
Jupyter execution completed **all six canonical notebooks and 42 code cells** in
27.82 seconds. The second pass reused all six notebook checkpoints in 0.56 seconds.
No warning/error outputs were present. The two new figure PNGs exactly match the
visually inspected preflight figures; preflight itself is not counted as Jupyter.

Measured coverage is **3,141 / 3,733 lines (84.14%)**, limited to the modules selected
by the quality script. The native checkout is `a5920532286abbcc92751eed82774d7ad688e13e`,
GitHub's merge checkout for source head `ed08fd3714fb4c8d15663926251a999115cf6a0a`.
Every computational source hash and notebook definition was independently matched
before copying the actually executed notebook bytes into the publication commit.
[Workflow 34288566061](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/runs/34288566061)
and [the validation receipt](../reports/validation/ranking_systems.json) preserve
this evidence. Final publication checks and the merge are recorded on
[PR #10](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/pull/10).

Portfolio and engineering readiness remain approximately **95%**, a judgment rather
than a measured completion fraction. The current remaining limitation is independent
predictive evidence, especially for women, not missing executions or unchecked
feature handoffs. The richer bank still does not establish superiority over the
prior frozen anchors. A 9.9/10 forecasting or employer rating cannot be guaranteed
by more tuning on already-consumed seasons. The defensible deliverable is a completed,
reproducible retrospective feature-research project with explicit positive and
negative results, and a clear boundary around what has not been demonstrated.


## 20. Current release reconciliation

PR #10 merged as `d044a0e2814f36749c8fe4a2be6b8cb2772e949b`.
The publication head and the merged-main quality run both passed. The latter,
[workflow 34289790258](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/runs/34289790258),
passed 228 tests in 229.52 seconds and executed all six notebooks in 24.143
seconds; its second pass reused all six notebook checkpoints.

The previous `reports/repository_release/repository_release_audit.json` was a
historical Windows checklist. Its PASS status established file existence rather
than current publication integrity. It has been replaced in place by a reproducible
audit of the current source, feature/model/benchmark lineage, feature counts,
saved predictions, notebook bytes, exported figures and cloud receipts.

`python -m march_mania.publication.release --check` independently recomputes all
102 published model, capacity, ranking and benchmark leaderboard rows. It checks
game-weighted Brier separately from mean-season Brier, plus log loss, ROC AUC,
average precision, threshold diagnostics and calibration error. It rejects
changed game populations, duplicate predictions, conflicting targets, incorrect
seasons, stale source/configuration, corrupted reports and changed notebook bytes.
The two README figures are exact PNG fallbacks from notebook 02's Plotly outputs;
the audit requires those bytes to match.

The 3,106-candidate main study made 1,674,530 screening decisions across ablations:
88,766 retained and 1,585,764 rejected. Those are repeated decisions, not counts of
unique definitions. Rejections reconcile to 1,469,578 capacity limits, 86,816
redundancy decisions, 28,814 absent training signals and 556 near-constant inputs.
Within the 20 main full-bank outer fits, all retain 128 features; 251 distinct
features occur across fits and 2,855 never occur in those fits. Feature-family
ablations can still use candidates absent from the full-bank selections. The
840 individual-ranking additions remain a separate study, so the project-wide
explored-definition count is 3,946 rather than a single 3,946-column fitted matrix.

On September 9, 2026 UTC, six successful live AWS HeadObject calls reverified the
recorded object versions and sizes. Five returned full-object SHA-256 checksums
matching the archive records. The 18,070,392-byte benchmark archive instead
reported a composite checksum; a fresh exact-version download independently
matched SHA-256 `4e243437990b48311238286a9585c83997ea84915a090c44a2ca711845965a01`.
The [cloud verification receipt](../reports/repository_release/cloud_verification.json)
preserves those observations. Replaying the offline audit checks that receipt;
it does not claim to have made new AWS calls or repeated earlier recovery fits.

This release adds no predictive experiment and does not alter any frozen recipe.
The retrospective official-data research deliverable is complete within its
stated scope. Predictive superiority, player-level availability and women's
historical source parity remain unproven. They require a new research question
with timestamped evidence or prospective outcomes, not rerunning successful fits
or selecting against already-consumed seasons.


## 21. Development portfolio and remaining production gates — September 9, 2026 UTC

The current-model evidence now supports a reproducible catalog of 50 candidate
plans: ten men's procedures crossed with five women's procedures. It reuses 15
published nested development streams, including the men's pooled blend and women's
separate logistic. Every pairing covers the same 649 physical games from the five
development seasons. The catalog verifies 95 earlier-season component-selection
records and reconstructs the pooled blend from its saved raw components and weights.

`python -m march_mania.publication.portfolio --check` recomputes the catalog,
250 annual metric rows, selection history and all 1,225 pairwise prediction
differences from checksum-verified committed evidence. All 50 development vectors
are distinct; the smallest pairwise mean absolute probability difference is
0.008814. Both Brier averages and supporting probability diagnostics remain visible.
Tests reject contaminated or unmatched games, invalid probabilities, missing or
future selection history, invalid blends, duplicate vectors and changed artifacts.

This release performs zero new fits and produces zero submission CSVs. Its scores
describe nested procedures on explored years; final model specifications are not yet
frozen. Pairings were assembled retrospectively and are correlated sensitivity
candidates, not 50 independent experiments. No consumed-benchmark or 2026 labels
enter the catalog. The older submission portfolio retains its post-result label.

The [completion plan](completion_plan.md) makes the remaining work explicit:
restore current artifacts, freeze concrete pre-2022 component choices, fit each
unique component/seed route once through 2025, generate 50 complete template-aligned
files, validate final-vector uniqueness, archive them, and prove byte-identical
recovery with zero new fits. Canonical notebook 04 receives the production evidence
when that work has actually run. New external-source research is an optional
extension, not a reason to leave the current official-data product unfinished.
