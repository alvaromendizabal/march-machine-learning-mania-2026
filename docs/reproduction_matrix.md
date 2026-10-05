# Public-solution reproduction matrix

This document tracks transferable mechanisms from strong recent March Mania public work. "Recreated" means independently implemented inside this project; it does not mean copied code, copied predictions, or copied feature CSVs.

The repository intentionally emphasizes **mechanism coverage and engineering ownership**, not leaderboard imitation.

| Public lineage | Mechanism | Current state |
|---|---|---|
| 2023 public work | engineered team statistics + boosting | Recreated / adapted; no promoted gain beyond accepted system |
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

Verified:

- all 65,703 target pairwise probabilities match the archived reference within 1e-4;
- reconstructed 2026 women Brier is 0.0767383172;
- historical member training-row counts and best-iteration receipts match archived behavior.

### Men native branch

Model-procedure reconstruction is now substantially complete on matched inputs.

Verified:

- all 66 core members reproduce archived best iterations and same-input predictions;
- all 66 margin members reproduce best iterations and calibration slopes;
- 31 auxiliary margin features were reconciled;
- the original margin-target contract was corrected after re-audit;
- AP edition semantics / activation rules were repaired.

The remaining parity questions are concentrated in external information families rather than broad model-procedure drift.

### Official-data reference / ranking branch

The compact official-data reference mechanism and ranking-history correction logic have been independently rebuilt using earlier-season training outputs rather than copied prepared predictions.

This branch contributed to the reconstructed experimental frontier, while historical transfer gates prevented automatic promotion.

### Torvik / reliability branch

Torvik Time Machine data is independently owned with broad historical coverage in the active men's window.

The project's reliability / disagreement extension passed the declared recent confirmation requirements and became part of v26.

## Additional reconstruction findings

### Complete historical cohort

The men's historical evaluation bank now covers 566 played main-bracket games across nine forecast seasons.

An equal-seed filtering defect had removed eight legitimate later-round games. The repaired control reproduced all 558 saved historical predictions before restoring those omissions.

### Original publisher bracket fields

Complete 68-team men's advancement-probability fields were independently reconstructed for 2025 and 2026.

The source reconstruction succeeded; the fixed model integration was rejected. The source therefore remains an owned research asset without being promoted as a forecasting component.

### Pair-exchange and exact-date AP studies

Both studies produced favorable recent-confirmation behavior but failed development gates. They are retained as negative scientific evidence rather than promoted selectively.

## Why the matrix matters

Every mechanism is evaluated by whether the project independently reconstructed the source, matched feature semantics, reproduced the training target, reproduced inference behavior, tested historical transfer, and preserved an honest promotion lifecycle.

A failed adaptation is not proof that the original mechanism was bad, and a numerical reproduction is not proof of future-season generalization.

## Important remaining mechanism gaps

- broader original-version availability / player-value history;
- broader BPI and timestamp-qualified market history;
- remaining point-in-time NET coverage;
- stronger owned roster-role representations;
- complete incoming-season integration.

The current private study evaluates calibration with strictly earlier-season held-out predictions. No result is claimed publicly until the AWS evidence exists.
