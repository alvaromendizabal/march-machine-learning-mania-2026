# Public-solution reproduction matrix

This document tracks transferable mechanisms from strong recent March Mania public work. "Recreated" means independently implemented inside this project; it does not mean copied code, copied predictions, or copied feature CSVs.

The repository intentionally avoids score-ranking comparisons. The purpose of this matrix is to show **mechanism coverage and engineering ownership**.

| Public lineage | Mechanism | Current state |
|---|---|---|
| 2023 public work | engineered team statistics + boosting | Recreated / adapted; no promoted gain beyond current accepted system |
| 2023 public work | conference / rolling / margin representations | Recreated / tested |
| 2024 public work | opponent-adjusted offense / defense / pace | Reimplemented; rejected scientifically |
| 2024 public work | margin-based probability modeling | Reimplemented / tested; not promoted |
| 2025 public work | compact engineered boosting system | Recreated / adapted; not promoted |
| 2026 public lineage A | separate-gender modeling | Incorporated |
| 2026 public lineage A | shallow women XGBoost + isotonic calibration | **Numerically reproduced on owned inputs** |
| 2026 public lineage A | AP signal | Source independently recreated; several model uses rejected |
| 2026 public lineage A | player / injury / value information | Exact original publisher inputs not owned; two clean proxies rejected |
| 2026 public lineage B | LR / XGB reference + MOV Elo + Massey | Reimplemented / adapted; used in ranking-correction reconstruction |
| 2026 public lineage C | simple small-data LR / pruning | Recreated / adapted; sparse residual variants rejected |
| 2026 public lineage C | Torvik strength | **Independently recreated and promoted as a source family** |
| 2026 public lineage C | uncertainty / disagreement | **Extended and promoted in v26** |
| 2026 public lineage C | BPI | Partial original-source archive recovery; broad history incomplete |
| 2026 public lineage C | market signal | Partial original-source recovery; limited multi-season coverage |
| 2026 public lineage D | symmetric boosting | Recreated / adapted; rejected |

## Source-equivalent reproduction progress

### Women native branch

The public women mechanism is the strongest numerical reproduction in the project.

Verified:

- all 65,703 target pairwise probabilities match the archived reference within 1e-4;
- the reconstructed 2026 women Brier is 0.0767383172;
- historical member training-row counts and best-iteration receipts match the archived behavior.

The reproduction required restoring several source and implementation details that had been changed in earlier adaptations.

### Men native branch

Historical reconstruction is substantially farther along than the final target forecast.

At the audited grain:

- four historical native-core ingredients match;
- 31 auxiliary margin features match;
- overtime-normalized margin supervision matches;
- AP edition semantics / activation rules match.

The main unresolved parity issues are concentrated in target-season external information that is not yet fully independently owned.

### Official-data reference / ranking branch

The compact official-data reference mechanism and ranking-history correction logic have been independently rebuilt using earlier-season training outputs rather than copied prepared predictions.

The branch improved the post-competition reconstruction frontier, but its historical transfer did not justify automatic promotion.

### Torvik / reliability branch

Torvik Time Machine data is independently owned and has broad historical coverage in the active men's window.

The project's reliability/disagreement extension passed recent confirmation requirements and became part of v26.

## Why the matrix matters

The goal is not to maximize the number of copied public ideas.

Every mechanism is classified by whether the project:

- independently reconstructed the source;
- matched the intended feature semantics;
- reproduced the training target;
- reproduced the inference procedure;
- tested historical transfer;
- preserved an honest promotion lifecycle.

A failed adaptation is not treated as proof that the original mechanism was bad, and a numerical reproduction is not treated as proof of future-season generalization.

## Highest-value remaining mechanism gaps

The important open gaps are now information gaps rather than generic model-family gaps:

- broader original-version BPI / availability history;
- exact target-season player-value / availability information;
- remaining point-in-time NET coverage;
- richer owned roster-role representations with genuinely new information;
- complete incoming-season integration.

Further near-duplicate boosting or calibration sweeps are lower priority until those gaps are addressed.
