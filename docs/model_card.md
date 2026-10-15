# Model card · NCAA forecasting research and public demonstration

## Two systems, deliberately separate

| | Private research system | Public Tournament Lab |
|---|---|---|
| Intended use | Research into calibrated NCAA matchup probabilities | Inspectable bracket and hypothetical price mechanics |
| Input | Official competition data and qualified supplemental sources | Real school names with authored synthetic ratings and bracket positions |
| Output | Men's and women's matchup probabilities | Eight-team advancement probabilities and user-selected matchups |
| Evaluation | Historical season-based research and late retrospective scoring | Numerical identities, exhaustive-path reference tests and UI behavior |
| Reproducibility | Requires retained private source/model artifacts | Complete offline browser source and deterministic package |
| Not established | Prospective 2027 superiority or profitability | Real NCAA forecasting skill, calibration or betting edge |

## Data and populations

The published source-foundation receipt covers **8,346 men's team-seasons (2003–2026)** and **5,965 women's team-seasons (2010–2026)**. It reports 211,716 original regular-season games; that raw corpus was not included in the public release for an independent recount. The full 2026 forecast population is 66,430 men's pairs and 65,703 women's pairs. Those pairs are not the same as the smaller played-game population used for scoring.

The [review snapshot](../portfolio/review_snapshot.json) separates the latest inspected model-lineage audit from this earlier source-foundation receipt. Counts from different milestones are not added together.

## Evaluation and leakage controls

Season-forward validation, fitting preprocessing inside training partitions, physical-game identity reconciliation and separate prediction/scoring records are core evaluation contracts. Historical evaluation periods have already been inspected repeatedly. They are not pristine holdouts.

A low late 2026 Brier does not establish prospective superiority. Source ownership and point-in-time validity are distinct: independently retrieving an original source later does not prove those exact values were available before the tournament. The 2027 contract requires an actual pre-outcome source freeze and prospective run.

## Featured Kaggle result

**0.1034347 public/private Brier · submission 57122407** is the scored retrospective research result featured in this release. Its [normalized result record](../reports/champion_result/kaggle_record.json) links the score to retained owner audit evidence and the original forecast identity. This release does not perform a fresh Kaggle account query. Earlier receipts are historical evidence, not the current headline result. [Score context](champion_result.md)

Exact private forecast regeneration, all fitted checkpoint bytes and complete historical source timing remain separate research work. The public demo is fully reproducible within its stated boundary, not a claim that the private pipeline is public.

## Failure modes and limitations

Sparse historical player availability, inconsistent source vintages, changes in team composition, small tournament samples, repeated model selection and cross-season drift can all undermine generalization. The system must abstain from promotion when evidence is inadequate; attractive aggregate performance does not erase a materially weaker season.

The public engine assumes fixed strengths, neutral court, no reseeding and independence of disjoint bracket branches. It is deterministic, not learned from NCAA results. Hypothetical prices are display-only and are not incorporated into its predictions.

## Publication boundary

The demo contains no private predictions, trained competition models, restricted supplemental records, credentials, authenticated URLs or cloud resource identifiers. Existing public historical code retains its original scope and attribution. The publication checks are useful guards, not proof that every secret could be detected automatically. [Disclosure](../portfolio/DISCLOSURE.md)
