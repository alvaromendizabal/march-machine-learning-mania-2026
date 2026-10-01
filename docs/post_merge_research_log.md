# Post-merge research log | September 28 – October 1, 2026

This log summarizes major private AWS milestones completed after PR #34. It publishes aggregate evidence only; private implementation, raw data, predictions, and production weights remain excluded.

## Research timeline

| Milestone | Status | Aggregate evidence | Decision |
|---|---|---|---|
| Supplemental operational release | Completed | 96,531 corroborated games; 19,006 team profiles; 9,652 dated rating rows | Retain data infrastructure |
| Owned preseason trajectory + coach history | Rejected | Development +0.0002100; confirmation -0.0009346 | Retain data, close correction |
| Owned player-value / availability v1 | Rejected | Development +0.0017768; confirmation -0.0004962 | Retain data, close v1 |
| Owned box-value / availability v2 | Rejected | Development -0.0010510; confirmation -0.0012728 | Close proxy family |
| ESPN external-consensus reconstruction | Promoted research | Full 126-game Brier 0.1043513 | New research baseline |
| Public-solution frontier comparison | Rejected | Generic replacement regressed complete 2026 audit | Keep external-consensus baseline |
| AP archive reconstruction | Completed | 16,530 ranked rows; full required recent coverage; 100% mapped | Source ownership milestone |
| AP-enhanced first-place-style model | Rejected | Development improved; confirmation regressed | Retain AP data, close model |
| Season-level ESPN BPI archive | Timing blocked | Historical endpoint state updated after tournament cutoffs | Archive only; prospective 2027 capture |
| Sparse/pruned LR residual | Rejected | Development +0.00286; confirmation -0.00246 | Close sparse-LR residual |
| Robust rating consensus | Rejected | Historical gate passed; complete 2026 audit worsened | Close broad consensus correction |
| Dated-Torvik residual | Rejected by final gate | Complete audit 0.1042218; gain below frozen promotion margin | Retain mechanism evidence |
| **Uncertainty-gated dated-Torvik correction** | **Promoted research** | **AWS-reproduced Brier 0.1033437** | **Current canonical research boundary** |
| Agreement-gated correction | Pending canonical run | Local replay 0.1027974 | Do not promote until canonical AWS reproduction |

Positive gain means lower Brier relative to the matched reference.

## Data ownership milestones

### AP polling

Competition-era weekly AP observations are independently collected and mapped. Public modeling consumes bounded pre-tournament summaries and trajectories rather than a competitor-provided frozen feature CSV.

### Dated BartTorvik

The private archive contains **9,652 dated observations across 27 editions**. Cutoff eligibility is explicit. Undated/final/post-cutoff observations are retained as provenance but are not automatically treated as forecast-time features.

### External game context

Game-specific ESPN predictor/BPI and sportsbook-provider information are normalized into owned representations. Historical retrospective source timing and prospective 2027 capture are documented separately.

### Player context

The project reconstructed **1,210,609 pre-cutoff player-game rows** and **53,808 player source/profile rows**. Derived player-value/participation features are intentionally called owned proxies, not EvanMiya BPR or medical injury labels.

## Validation lessons

**Broad replacement repeatedly underperformed selective correction.** Several full-model public-solution reproductions looked promising in development but failed 2026 transfer.

**Source ownership and model usefulness are separate milestones.** AP reconstruction succeeded even though the tested AP-enhanced boosting correction was rejected.

**Timing can block a source independently of engineering.** Season-level ESPN BPI existed historically, but endpoint updates occurred after the relevant tournament cutoffs; the project archived the source and refused to treat it as pre-tournament history.

**Small-data corrections require strong restraint.** The strongest retained gain came from a narrow correction to historically uncertain men's cases while protecting already strong rows.

## Engineering lessons

- engineering failure, source/timing block, and scientific rejection are separate states;
- cached acquisition is reused across corrected runs instead of redownloading expensive history;
- every candidate is deterministically reconstructed before a final audit;
- late reporting failures resume from model/prediction checkpoints;
- private runners are integrity checked and hard bounded on memory/runtime;
- promotion can be wired to a guarded submission action without making submission success part of model correctness.

## 2027 prospective state

The private 2027 pipeline remains waiting-state driven. Unpublished target-season inputs do not cause false failures and are not copied from 2026. The intended next source milestone is prospectively captured roster/availability context plus stronger women-specific external ratings under real timestamps.
