# Completion audit · expanded NCAA feature research

Evidence date: 2026-09-08. This audit distinguishes completed computation from native
notebook execution and publication. The original 124-feature release remains in Git
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
include rescreening. Neither interval establishes a reliable improvement.

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

The underlying official-data audit, expanded feature study, model search and current
benchmark have completed. Native execution of canonical notebooks **00 → 01 → 02 →
03 → 04 → 05**, plus a second-pass checkpoint reuse check, is the remaining publication
gate. Local native-kernel launch is unavailable in the restricted execution environment;
no simulated notebook output is presented as execution. GitHub Actions runs the real
Jupyter kernel before publishing the saved notebooks.

## 10. Tests and quality gates

Local portable validation passed all **200 non-kernel tests**; the suite contains
**201 tests** including a real-kernel execution/reuse integration test. Compile/lint,
format and mypy checks passed. Focused final modeling, benchmark and workflow checks
passed after extending the candidate search. The full unmodified quality gate,
coverage measurement and actual notebook execution remain required on the exact
published branch head before merge; native results will be recorded here.

## 11. Git and durable experiment evidence

Work is isolated in [PR #8](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/pull/8).
Local logical commits separate temporal features, benchmark integration and audit/
notebook controls. A verified public source commit preserves the feature computation.
Full feature, model and benchmark archives were uploaded and their complete SHA-256
checksums and version IDs independently verified. Public run records reference them.
Private raw data, trained binaries and credentials are excluded from Git.

Final branch checks, fresh-directory S3 recovery, publication commit and merge are
pending and must be recorded after success. A draft or an untested commit is not
reported as a completed release.

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
claims. None of the new family effects has an interval excluding zero. Women's
ranking/coaching source parity is absent. Player availability and returning production
would require timestamped historical data not present in this snapshot. The original
rich-system men's score of 0.180669 used a different schema/history; it is retained
as historical evidence rather than credited to this run. Historical neural and margin
models were not retrained. No new leaderboard ranking or medal is established.

## 14. Honest completion estimate

At audit start, approximately **70–75% of the intended deliverable** was complete:
substantial engineering existed, but the central expanded-feature experiment and
cross-notebook proof were missing. After the completed experiments, approximately
**90–95%** is complete, with native execution and verified publication outstanding.
These are judgment-based project-readiness estimates, not measured scientific scores.
A 9.9/10 forecast-quality claim is not supported by the results.

## 15. Employer readiness

The intended finished presentation lets a reviewer trace data → temporal features →
model choices → calibrated probabilities → uncertainty and negative results without
an AWS account. It demonstrates disciplined ML engineering and scientific judgment,
including declining to claim a gain the experiment did not establish. Final readiness
will be confirmed only after the native execution and exact-head checks succeed.

## 16. Highest-value remaining step

Finish the native execution, recovery and publication gates now. For a future accuracy
claim, freeze a compact recipe and evaluate the next genuinely unseen tournament,
with pre-tournament source snapshots and a predeclared scoring population. Repeatedly
tuning on 2022–2025 or adding more unvalidated columns cannot create that evidence.
