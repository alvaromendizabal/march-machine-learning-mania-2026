# From a coverage total to the next evidence requirement

A single missing-row count cannot explain where acquisition should go next. This project publishes an aggregate qualification frontier: every required edition remains visible, every row belongs to one state, and the result binds the exact current acquisition snapshot.

The latest inspected execution qualified **75 additional women's venue rows**, moving from **27 to 102 of 583**. All previous qualifications were retained. **481 rows remain unresolved**; no edition is complete. These are played-game representation rows, not distinct arenas or a claim of new model performance.

## Inspect the frontier

Run `python tools/review_project.py` from the repository root, then open **outputs/review/index.html** and choose **Remaining evidence**. The review uses Python 3.12 and Node, without private credentials, package installation or network acquisition.

The explorer supports two independent controls:

- **Qualification-state focus** shows editions containing the chosen state and highlights that segment. The other segments remain visible, and each bar retains its full edition denominator.
- **Ordering** switches between chronology and the largest selected count, using unresolved rows when all states are visible. The complete static table always retains all nine editions, including those hidden by the focus.

Native controls, text labels, a polite live explanation and a static data table provide the same information without relying on color. An empty category explicitly preserves the overall unknown count rather than implying completion. The [executed engineering notebook](../portfolio/engineering_review.ipynb) includes the same partition as an interactive Plotly figure and PNG fallback.

## Actual partition

| Edition | Required rows | Qualified | Court qualified; home unresolved | Both dimensions unqualified |
|---|---:|---:|---:|---:|
| 2016 | 63 | 6 | 3 | 54 |
| 2017 | 63 | 15 | 3 | 45 |
| 2018 | 63 | 18 | 0 | 45 |
| 2019 | 63 | 12 | 0 | 51 |
| 2021 | 63 | 0 | 15 | 48 |
| 2022 | 67 | 7 | 0 | 60 |
| 2023 | 67 | 16 | 0 | 51 |
| 2024 | 67 | 9 | 0 | 58 |
| 2025 | 67 | 19 | 0 | 48 |
| **Total** | **583** | **102** | **21** | **460** |

The fourth possible state, home context qualified while court assignment is unresolved, contains zero rows under this **court-first qualification contract**. A row without a qualified court may still have a standalone home witness. “Both dimensions unqualified” does not assert that no useful source facts exist. The frontier describes admitted representation states, not the complete raw-fact inventory.

The 21 rows with qualified court assignments still need defensible home-context evidence; that is not a promise that 21 acquisitions will finish them. The 2021 edition is shown separately because its 15 court-only rows must not become neutral by assumption. Rows without a qualified court also need exact assignment, chronology and identity evidence before the corresponding context qualifies.

## Executable contract

The [public JSON](../portfolio/qualification_frontier.json) carries only allowed fields and aggregate counts. The [validator](../tools/qualification_frontier.py) checks:

1. The declared execution, review date and canonical snapshot digest match the current acquisition snapshot.
2. All nine frozen editions appear exactly once, in order, with their original 63- or 67-row populations.
3. Every count is a nonnegative integer; booleans and floating-point values are rejected.
4. The disjoint states sum to each edition's population and reconcile to the snapshot's qualified and unknown totals.
5. The completed-edition count and court-first semantics agree with the declared contract.
6. No private route, row-level source record or unsupported readiness claim is added to the public schema.

The [failure tests](../tools/test_qualification_frontier.py) change populations without changing their grand total, introduce overlap, claim unknown rows as qualified, alter an otherwise equal-count parent, and probe invalid types and disclosure fields. The [control tests](../tools/test_qualification_frontier.mjs) execute the actual explorer script and check focusing, sorting, empty states, fixed bar denominators and reset behavior.

A digest identifies the published snapshot. It does not authenticate an original publisher or prove historical availability. Public reproduction validates this accounting contract; private return manifests and provider bodies were inspected separately. No full-study readiness or predictive improvement is inferred from coverage.

[Measured execution history](execution_evidence.md) · [Engineering review](engineering_review.md) · [Reproduction boundaries](reproduction_matrix.md)
