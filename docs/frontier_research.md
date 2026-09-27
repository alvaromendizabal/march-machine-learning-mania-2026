# Research frontier and leading-solution reproduction matrix

## Competitive boundary

| Boundary | Brier |
|---|---:|
| Published 2026 winner | 0.1097454 |
| Retained private post-competition system | **0.1051853** |
| Stretch target | 0.0900000 |
| Remaining absolute reduction | **0.0151853** |

This is post-competition benchmark-informed research, not an original leaderboard placement.

## Leading-solution reproduction matrix

| Public mechanism | Current status | Evidence / decision |
|---|---|---|
| Compact statistical tournament reference | **Adapted / validated** | Strong compact benchmark retained in the research stack. |
| Score-margin supervision | **Adapted / validated** | Produced complementary signal in prior scored research. |
| 2025 first-place engineered strength / quality concepts | **Adapted** | Reimplemented with official data; game-specific manual overrides are not treated as transferable methodology. |
| 2025 fourth-place-style margin / robust / leaf ideas | **Recreated / rejected** | Did not establish stable confirmation improvement. |
| 2026 first-place seed / opponent-quality / strength concepts | **Adapted** | Core mechanisms implemented; contemporaneous injury / proprietary player value remains incomplete. |
| 2026 second-place matchup-difference LR + XGBoost framing | **Adapted** | 31-feature independent chronological reconstruction completed; latest 78-fit ensemble rejected. |
| Chronological OOF ensemble weighting | **Recreated / rejected** | Past-only learned weights did not beat equal blending historically and were far behind the retained 2026 system. |
| Player rotation / continuity proxies | **Recreated / rejected as correction** | Large player-history reconstruction completed; corrections did not transfer. |
| Championship-title market transformations | **Recreated / rejected** | Direct retrospective corrections worsened 2026 Brier. |
| Direct game-market correction | **Reconstructed partially / rejected** | Source coverage was incomplete; available men’s correction worsened Brier. |
| Prospective 2027 schedule capture | **Operational** | Men’s and women’s target-season schedules are captured raw-first; completed games remain unavailable at current capture. |
| Injury / player-availability signal | **Blocked / not yet implemented prospectively** | Requires timestamped, competition-compliant source history. |
| Strong women-specific external ratings / player value | **Missing frontier** | Highest-value information gap for women. |
| Genuinely complementary representations | **Missing frontier** | Latest three experts show residual correlations around 0.956–0.975. |

The matrix is intentionally conservative. An idea is not called “recreated” because a similar feature exists somewhere in the codebase.

## Latest structural result: complementarity is the bottleneck

The latest milestone rebuilt a clean historical forecast bank from raw official files and trained three fixed expert families per gender. It created **78 model checkpoints** and **26 annual blend checkpoints**.

The chronological blend scored **0.1638382** historically versus **0.1634288** for the equal blend. On the complete frozen 2026 replay, it scored **0.1281818** versus **0.1051853** for the retained system.

The most important diagnostic is the residual-correlation matrix: pairwise correlations among the three reconstructed experts are roughly **0.956–0.975**. Learned weighting cannot manufacture complementary information when models make nearly the same mistakes.

This closes a credible direction. The next frontier should add signal, not another weighting layer.

## What should move the metric next

1. **Prospective player availability / injury context.** The published top systems benefited from player-level availability information that our prospectively valid dataset does not yet possess.
2. **Women-specific external signal.** The women’s retained component is strong; richer external/player-value data is a clearer capability gap than another generic model family.
3. **Complementarity-first representation research.** Candidate models should earn ensemble inclusion based on out-of-time residual diversity and standalone calibration, not model count.
4. **2027 prospective evaluation.** Freeze source identities, cutoffs, model states, and predictions before target outcomes so future evidence supports a genuinely stronger generalization claim.

## Public/private boundary

The public repository exposes aggregate methodology, validation logic, negative results, and the research roadmap. Raw datasets, source snapshots, model binaries, private predictions, exact production feature formulas, credentials, and AWS-only research state remain private.
