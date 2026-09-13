# NCAA Tournament Probability Forecasting

**Feature-first research · point-in-time validation · reproducible ML engineering**

A notebook-led investigation of NCAA men's and women's tournament win probabilities,
with basketball-informed features, whole-season validation, controlled ablations,
calibration diagnostics, and restartable experiments.

| Reported result | Interpretation |
|---|---|
| **0.1222672 Brier** | Best previously recorded late, retrospective Kaggle submission; not a prospective rank |
| **0.1097454 target** | Historical research target, not an achieved score or guarantee |
| **Feature research remains open** | Negative results are retained; additional features require measured value |

## Start here

- [Two-minute employer walkthrough](docs/employer_walkthrough.md)
- [Scored release and model lineage](reports/final_results/README.md)
- [Research index: implementation, notebooks, protocols, and evidence](research/README.md)
- [Report-only Plotly notebook](portfolio/research_results.ipynb)
- [Consolidation provenance and file hashes](research/provenance/MIGRATION.json)

![Previously observed submission scores](reports/final_results/leaders.png)

## What this project demonstrates

**Domain representation.** Team strength, opponent/context adjustments, shooting,
turnovers, rebounding, ranking systems, temporal changes, and conditional matchups.
Features are evaluated through fixed-reference comparisons, family ablations and
season-level stability; column count alone is not evidence of quality.

**Validation and engineering.** Pre-tournament information cutoffs, earlier-season
training, train-only transformations, game identity checks, team-swap symmetry,
content-addressed checkpoints, explicit stop conditions and UTC progress records.

**Transparent results.** The original scored release is preserved. The research
extension includes both useful and unsuccessful hypotheses and distinguishes
prepared code, user-executed experiments, historical validation, and Kaggle scores.
Previously explored 2022–2025 seasons are not described as untouched tests.

## Read the notebooks

The original executed review notebooks remain in [notebooks/](notebooks/).
Source copies of the AWS research notebooks are indexed in [research/](research/).
These imported source snapshots intentionally omit execution outputs; they are
not claimed to be executed copies. Run their documented workflow in the existing
workspace to generate inline Plotly results and checkpointed evidence.

## One repository

**This is the project's sole publication destination:**
`alvaromendizabal/march-machine-learning-mania-2026`.

Research implementation is now intentionally public at the owner's request.
Earlier split-repository/privacy instructions survive only in historical source
archives and are superseded by [the repository policy](docs/REPOSITORY_POLICY.md).
No new private or portfolio repository should be created by the current workflow.

Raw competition data, credentials, environments and fitted-model binaries are not
Git source. They remain in their original storage. The AWS experiment checkout is
not destructively reset by publication. See [workspace execution](research/EXECUTION.md).

## Limitations and next work

Local Brier scores concern different games and cannot be equated with the Kaggle
score. Repeated experimentation can overfit reused validation seasons. A promising
compact-reference gain still needs assessment against the stronger released recipe.
The next prepared pair is **round 20 (pace/variance context)** and **round 21
(opponent-style responses)**; no new result for either is asserted by this migration.

Existing MIT license and third-party notices remain in place. Competition data is
subject to its own terms. Publication is not a competition submission.
