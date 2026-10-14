# Engineering a verifiable probability forecast

**Alvaro Mendizabal · ML engineering · Data science · Research systems**

## The problem

A tournament predictor must estimate uncertainty across many possible matchups using information that exists at the prediction cutoff. An attractive metric can hide duplicated games, hindsight in source snapshots, or a forecast that cannot be recovered after an interrupted run. I engineered the project around making these failure modes visible.

The work spans source acquisition and qualification, team and matchup features, gender-specific models, probability calibration, historical evaluation and AWS delivery. [System architecture](architecture.md)

## My contribution

| Area | What I built or integrated | Where to inspect it |
|---|---|---|
| Data engineering | Provider identities, chronology checks, raw-to-feature replay, missingness and source receipts | [Source foundation](reproducible_source_foundation.md), [data audit notebook](../notebooks/00_data_audit_and_preparation.ipynb) |
| Probability modeling | Separate men's/women's branches, ranking and strength features, calibrated outputs and controlled composition | [Model comparison](../notebooks/03_model_comparison_and_diagnostics.ipynb), [credited method lineage](benchmark_comparison.md) |
| Evaluation design | Complete physical-game populations, season-based comparisons and separate development/confirmation evidence | [Reproduction matrix](reproduction_matrix.md), [split contracts](../configs/splits.yaml) |
| ML operations | Bounded AWS jobs, checkpoint verification, resume behavior, heartbeats and diagnostic return bundles | [Runtime](../src/march_mania/runtime.py), [failure tests](../tests/test_runtime.py) |
| Review experience | Executed notebooks, a synthetic Python evaluation lab, an interactive bracket demo and aggregate receipt checks | [Start here](../START_HERE.md), [evidence map](evidence_map.md) |

The system builds on credited public methods. Their underlying ideas are not presented as my inventions. The integration, evaluation repairs, source qualification and operational controls are explicit project contributions.

## Measured delivery

The public scoring receipt records **0.1067095 Brier** for a 132,133-row research forecast. The submission occurred after the 2026 tournament and after outcomes were inspected. It is numerically below the published 2026 winning reference, with the unequal evaluation conditions documented in the [comparison](benchmark_comparison.md).

The latest source audit is a separate engineering result: **14,311 team-season profiles**, a recovered **132,133-row forecast**, and **19 manifest members verified**. The run reports 211,716 regular-season games; those raw game records were not included for independent recounting. The private forecast reconstruction remains incomplete. [Latest execution receipt](../portfolio/latest_execution.json)

## Decisions and tradeoffs

**Repair evaluation before interpreting a gain.** An equal-seed filter excluded eight legitimate men's games. I reconciled all 558 saved control predictions before restoring them, creating a 566-game cohort. Otherwise an apparently stronger result could simply reflect a changed denominator.

**Separate numerical parity from information availability.** A model can reproduce probabilities while using a source revision that was unavailable before tipoff. I retain source timing and parity as separate gates. Missing evidence stays missing rather than becoming an assumed pregame observation.

**Preserve stable components while isolating changes.** Matched-input checks reproduced women's probabilities and men's model procedures. This helps distinguish a changed input from an implementation error before crediting a new modeling idea. Causal claims still require matched ablations.

**Retain negative results and completed work.** Several ranking and source integrations improved narrow slices but failed broader historical requirements. Their source assets and diagnostics remained reusable; the rejected recipes did not become approved models. Checkpoints keep a delivery failure from causing unnecessary retraining.

**Publish enough to inspect the engineering.** The public examples expose transparent temporal, identity and scoring contracts. Private fitted models, forecast rows and exact composition rules remain outside this release. Existing public methods retain their license and attribution.

## How to interview this project

- **ML engineer:** trace a corrupt checkpoint or late source timestamp through the failure path; explain the model/feature lineage and artifact freeze.
- **Data scientist:** distinguish game-weighted from season-weighted Brier, explain the complete cohort repair, and separate retrospective improvement from prospective evidence.
- **AI engineer:** discuss typed inputs, observable execution, durable state, controlled publication and reproducible evaluation. This project demonstrates forecasting systems; it makes no claim of being an LLM application.

The [public Python example](public_reproduction.md) gives an interviewer a small executable starting point. The full framework and notebooks provide deeper evidence without requiring access to the private research environment.

## Scope of closeout

This release closes the public portfolio presentation and review path. It does not certify a completed private-model reconstruction or future-season performance. The latest return made no new submission. A prospective claim requires frozen predictions before future outcomes under the [2027 evaluation contract](2027_readiness.md).

[Evidence map](evidence_map.md) · [Architecture](architecture.md) · [Reproduction matrix](reproduction_matrix.md) · [Disclosure](../portfolio/DISCLOSURE.md)
