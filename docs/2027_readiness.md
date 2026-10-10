# 2027 readiness: prospective evaluation contract

The project has a confirmed **0.1067095 late-submission Brier score** and substantial historical verification evidence. The next stronger claim requires a forecast frozen **before future outcomes are known**. The October 2026 submission does not establish prospective 2027 performance.

## Current readiness

| Component | Evidence in hand | Still required |
|---|---|---|
| Official game foundation | 42 men's and 29 women's seasons; independent feature replay | Actual incoming-season records |
| Probability artifacts | Accepted v54 forecast, delivered through v93r1; immutable release evidence | Fresh pre-outcome forecast and submission receipt |
| Historical evaluation | Complete 566-game men's cohort; retained control comparisons | A genuinely new prospective evaluation period |
| Supplemental sources | Verified rating/poll inputs and partial original archives | Broad timing-qualified player, availability, BPI, and market inputs |
| Latest source qualification | v128 SOURCE_PARTIAL; 2,258 market rows repaired, 1,075 still missing; no model admission | Exact injury inputs and sufficient timing-qualified historical coverage |
| Operational pipeline | Bounded jobs, self-tests, checkpoints, resume and packaging contracts | Full acquisition-to-freeze rehearsal and actual 2027 execution |

## Preserve separate lifecycle states

Keep the latest accepted late submission, earlier historical controls, experimental forecasts, and source-only pilots distinct. Every artifact must retain its system ID, input/configuration hashes, prediction hash where applicable, population, lifecycle state, and source-timing evidence.

Submission acceptance is an operational fact. Model promotion and prospective validation are scientific claims with additional requirements.

## Make the season transition executable

Audit incoming team identities and aliases, conferences, roster changes, seeds, rankings, player information, publication timestamps, and the official submission schema. Source records must retain the original URL/provider, actual capture time, publisher update time when available, raw checksum, normalized checksum, identity mapping, eligibility, and quarantine reason.

Missing future observations produce `WAITING_FOR_TARGET_DATA` or a source-blocked result. Values are never copied forward merely to make a pipeline complete. A response retrieved today about an old game is not automatically a certified pre-tournament snapshot.

## Rehearse the complete chain

The historical incoming-season rehearsal must execute:

**source acquisition → receipt preservation → normalization and identity mapping → chronology checks → feature construction → training and inference → composition → schema/hash/provenance checks → immutable candidate freeze**

The existing 2026 feature rehearsal covers part of this chain. Full readiness requires the complete chain and then the actual 2027 source state; season parameters alone are insufficient.

## Freeze decisions before outcomes

Declare eligible model families, development and confirmation periods, metric aggregation, promotion rules, calibration/composition rules, and submission policy before the tournament. Keep game-weighted Brier and mean-season Brier separate. Do not tune the frozen decision procedure on the consumed historical benchmark or 2026 outcomes.

Changing a forecast after outcomes creates a new retrospective experiment, not an improved version of the original prospective forecast.

## Exercise failures without losing completed work

Test missing files, invalid identities, corrupt checkpoints, partial coverage, late timestamps, interrupted acquisition/training, resume behavior, candidate schema, duplicate hashes, and submission-action failures. A delivery failure should reuse the frozen forecast instead of retraining it.

## Public review and private implementation

Publish aggregate metrics, source-provenance status, reproduction evidence, research decisions, and readiness contracts. Retain raw archives, exact private features/weights, fitted competition models, row-level forecasts, source-specific mappings, and cloud state privately.

The [benchmark comparison](benchmark_comparison.md), [current research boundary](current_research.md), and [release evidence](../portfolio/release_evidence.json) define what is established today.
