# Public-solution reproduction matrix

This document tracks transferable mechanisms from strong recent March Mania solutions. "Recreated" means independently implemented inside this project; it does not mean copied code or copied feature CSVs.

| Competition lineage | Mechanism | Current state |
|---|---|---|
| 2023 strong public work | engineered team statistics + boosting | Recreated/adapted; no promoted gain beyond v26 |
| 2023 | conference / rolling / margin features | Recreated/tested |
| 2024 top work | opponent-adjusted offense/defense/pace | Reimplemented in v34; **rejected** |
| 2024 | margin-based probability modeling | Reimplemented/tested; not promoted |
| 2025 top work | compact engineered XGBoost-style system | Recreated/adapted; not promoted |
| 2026 first-place lineage | separate-gender modeling | Incorporated |
| 2026 first-place lineage | AP signal | Source independently recreated; model branch rejected |
| 2026 first-place lineage | player/injury/value information | Exact proprietary inputs not owned; two clean proxies rejected |
| 2026 second-place lineage | LR/XGB + MOV Elo + Massey | Reimplemented/adapted; not promoted |
| 2026 third-place lineage | simple small-data LR / pruning | Recreated/adapted; sparse residual variants rejected |
| 2026 third-place lineage | Torvik strength | **Independently recreated and promoted** |
| 2026 third-place lineage | uncertainty / disagreement | **Extended and promoted in v26** |
| 2026 third-place lineage | BPI | Historical source/timing blocked |
| 2026 third-place lineage | market signal | Historical timestamped source blocked |
| 2026 fourth-place lineage | symmetric boosting | Recreated/adapted; rejected |

## Current gap

The strongest legitimate 2027-ready system is still v26 at **0.1206458 Brier**. The gap to the ~0.09 research target is **0.0306458**.

The current evidence argues against adding more models from the same high-correlation internal feature families. New work should introduce a materially different source or representation.

## Next source frontier

The immediate next private milestone is independent NCAA NET/WNCAA NET reconstruction from official/archived NCAA pages, including rank, WAB, quadrant, road, and neutral context when those fields are actually available.

Promotion still requires historical transfer before any 2026 audit.
