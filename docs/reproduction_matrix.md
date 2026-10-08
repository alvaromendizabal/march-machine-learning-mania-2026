# Reproduction matrix

This project studies transferable mechanisms from public NCAA forecasting work, including Harrison Horan's credited methods, and distinguishes implementation ownership from source ownership. Reproduction means independently checking a mechanism or reconstructing its behavior; it does not imply that every underlying source is original, timing-certified, or publicly redistributable.

The current result is the **confirmed v54 late submission delivered through v93r1 at 0.1067095 Brier**. Submission acceptance is separate from historical model promotion. See the [benchmark comparison](benchmark_comparison.md) and [release evidence](../portfolio/release_evidence.json).

| Mechanism or source family | Demonstrated result | Remaining boundary |
|---|---|---|
| Separate men's/women's modeling | Incorporated in the submitted composition | Gains are not attributed causally without matched ablations |
| Women's compact XGBoost/calibration branch | 65,703 pair probabilities reproduced within 1e-4; historical fit receipts matched | Submitted composition retains the women's reference baseline; reproduction is not a claim of inventing that method |
| Men's core model procedure | 66 members reproduce archived iterations and same-input predictions | Matched-input parity does not establish source timing |
| Men's margin procedure | 66 members reproduce iterations and calibration slopes; 31 auxiliary features reconciled | Raw-margin target contract retained after re-audit |
| Official-data reference and ranking branch | Independently rebuilt and adapted in the men's probability system | Historical transfer remains a separate gate |
| Torvik Time Machine | Historical snapshots independently reconstructed | Provider attribution and timing remain attached to each source |
| AP polling | Editions, rank semantics, and activation boundaries reconstructed | Several fixed model integrations failed validation |
| Official raw-game features | 42 men's and 29 women's seasons; independent replay | Descriptive feature coverage is not evidence of a predictive gain |
| Derived NCAA player-box bank | Historical identity, coverage, and model-contract work retained | Not relabeled as original ESPN data or an original-owned player archive |
| Original ESPN boxscores | v99 package delivered for a 60-game, 20-group qualification pilot | Owner return pending; broad history and availability semantics unproven |
| BPI and market information | Partial original-source recovery | Broad dated history remains incomplete |
| Publisher advancement probabilities | Complete 68-team fields reconstructed for 2025 and 2026 | Fixed blending recipe rejected; source success did not imply model success |

## Independent validation repairs

The men's historical evaluation now contains **566 played main-bracket games across nine forecast seasons**. An equal-seed filter had excluded eight legitimate later-round games. The repaired implementation reproduced all **558 saved control predictions** before restoring those games.

Other reconciled contracts include team-order symmetry, AP edition semantics, historical source activation, the original margin target, and raw-object versus aggregate-file identity. Each repair addresses a different failure mode; no single parity check substitutes for the others.

## What negative experiments established

Mirrored training and exact-date AP integration improved recent confirmation aggregates but worsened development results. They did not earn promotion. Reconstructed opponent-adjusted features, sparse residual variants, and fixed publisher blends likewise remain recorded according to their own evidence.

The earlier player experiments used different banks and masks. A qualified ten-season representation and the later nine-season cached bank must not be treated as one identical dataset. In particular, the later player recipe was source-inconclusive under its minimum training coverage, so it is not described as a complete valid-negative experiment.

A lineup-stint pilot stopped before fitting because the producer's interval semantics did not establish continuous player exposure. The project retained the records without inventing missing time or calling the result adjusted plus-minus.

## Reproducibility levels

| Level | What a reviewer should expect |
|---|---|
| Public review | Aggregate score comparison, metric checks, provenance boundaries, architecture, and documented reproduction procedures |
| Private artifact replay | Exact saved inputs, configurations, predictions, model receipts, and checkpoints |
| Source-to-feature replay | Rebuilt normalized tables from retained raw source objects |
| Fresh-season reproduction | Newly acquired season inputs through a frozen candidate before outcomes |

The [public notebook](../portfolio/verified_result.ipynb) and [audit CLI](../portfolio/reproduce_release.py) reproduce aggregate release checks. They do not rerun private training or recreate the private prediction rows.

Private artifact and source-to-feature replay have substantial evidence, with scope varying by source and model family. Fresh-season reproduction remains an explicit [2027 readiness requirement](2027_readiness.md). Private weights, detailed correction logic, fitted competition artifacts, and row-level private forecasts are withheld.
