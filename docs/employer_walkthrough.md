# Employer walkthrough | NCAA forecasting research

## Start here

Open the [frontier notebook](../portfolio/frontier_research.ipynb). It is the current employer-facing view of the project: the verified **0.1051853** post-competition boundary, the chronological reconstruction, the rejected ensemble, the residual-correlation diagnosis, and the prospective 2027 data state.

## Result and framing

The retained private system scores **0.1051853 Brier** on the full 126-game 2026 cohort. The published 2026 winner scored **0.1097454**. The private research result is numerically lower, but all of this work is post-competition and informed by public benchmarks, so it is presented as an applied ML research case study rather than an original placement.

The target is **0.09**, leaving **0.0151853** absolute Brier.

## What to evaluate

**1. Validation design.** The latest model history is reconstructed with explicit forecast-year boundaries. Each model and scaler sees only earlier tournament labels, and annual blend weights use only earlier out-of-time predictions. The 2026 outcomes enter only after all forecasts are frozen.

**2. Negative-result discipline.** The latest 78-fit ensemble did not pass promotion. It is published because it answers an important question: the candidate experts are too correlated to close the gap through smarter weighting alone.

**3. Data engineering.** The private AWS workspace contains official competition data, rich team-state reconstruction, player-history tables, external-source captures, feature receipts, hashes, and resumable checkpoints. Public GitHub contains reviewed aggregate evidence rather than raw competitive artifacts.

**4. Reproduction rigor.** Mechanisms from 2025 and 2026 public solutions are classified individually as adapted, validated, rejected, blocked, or missing. The project does not claim exact reproduction when external/proprietary inputs are absent.

**5. Prospective readiness.** The 2027 collector has already captured 1,629 men’s and 2,280 women’s schedule records. Zero completed games is represented as a waiting state; future competition mappings and deadlines are not guessed.

**6. Engineering quality.** The latest run completed in ~44 seconds on CPU, passed 53 self-tests, produced 78 model checkpoints and 26 blend checkpoints, retained six Plotly figures after notebook reopen, and preserved a full return bundle with cost and provenance evidence.

## Latest research decision

Retain **0.1051853**. Do not spend another round tuning a highly correlated team-level ensemble. The highest-value next capabilities are prospectively valid player availability/injury context, stronger women-specific external/player-value information, and representations that demonstrate genuinely different residual structure before blending.

## Public/private boundary

The repository intentionally does not publish private prediction CSVs, model binaries, raw external snapshots, credentials, exact production formulas, or the canonical AWS workspace. The public portfolio is designed to make the research process, engineering decisions, and evaluation rigor assessable without distributing the active competition system.
