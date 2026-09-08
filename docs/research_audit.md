# Completion audit · expanded NCAA feature research

Evidence date: 2026-09-08. The expanded experiments and all six native notebooks are
complete and published. Final merge/check status is recorded on PR #8. The original 124-feature release remains in Git
history and its versioned archives; its final predictions are not relabeled as new work.

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

## 9. Notebook execution

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

## 10. Tests and quality gates

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

Against the broader ambition of demonstrating stronger future forecasting, the honest
estimate is **about 95%**. The remaining evidence requires a genuinely unseen tournament;
it cannot be manufactured by rerunning consumed years. These are judgment-based
readiness estimates, not scientific measurements. A guaranteed 9.9/10 rating or
state-of-the-art accuracy claim is not supported by these results.

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
There is no additional feature or training task required to understand and review this
completed release; future accuracy work is a separate prospective study.
