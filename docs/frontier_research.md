# Research frontier and leading-solution reproduction matrix

## Competitive boundary

| Boundary | Brier |
|---|---:|
| Published 2026 winner | 0.1097454 |
| Retained private post-competition system | **0.1051853** |
| Stretch target | 0.0900000 |
| Remaining absolute reduction | **0.0151853** |

This is post-competition benchmark-informed research, not an original leaderboard placement.

## Leading-solution mechanism matrix

| Public mechanism / research family | Current status | Evidence / decision |
|---|---|---|
| Compact statistical tournament reference | **Adapted / validated** | Strong compact control remains part of the research framework. |
| Score-margin supervision | **Adapted / validated** | Produced useful complementary signal in earlier scored work. |
| 2025 engineered strength / quality concepts | **Adapted** | Reimplemented with official data; manual game overrides are not treated as transferable methodology. |
| 2025 fourth-place-style margin / leaf / calibration ideas | **Recreated / rejected** | Did not establish stable confirmation improvement. |
| 2026 first-place seed / opponent-quality / strength concepts | **Adapted** | Core statistical ideas implemented; contemporaneous injury and proprietary player value remain incomplete. |
| 2026 second-place LR + boosting matchup framing | **Adapted** | Multiple matched logistic/boosting reconstructions completed under chronological validation. |
| Chronological OOF ensemble weighting | **Recreated / rejected** | Experts were too correlated; learned weighting underperformed the retained system. |
| Corrected player-impact exposure | **Recreated / rejected** | Development gain did not transfer to confirmation. |
| Shot-context / shooting-style features | **Reconstructed / rejected for tournament transfer** | Improved held-out regular-season prediction but not tournament confirmation. |
| Possession / lineup representation | **Reconstructed / fixed formulation closed** | Large source layer validated; first holdout formulation did not satisfy its gate and tournament coverage was insufficient. |
| Cross-season player-origin context | **Reconstructed / rejected** | Improved all three recent years but failed development gate. |
| Residual-source fusion | **Reconstructed / rejected narrowly** | Development passed; recent confirmation +0.0004496 missed +0.0005 gate. |
| Joint origin + shot 33-feature model | **Reconstructed / rejected** | Recent confirmation improved; development regressed. |
| Roster size / role geometry | **Reconstructed / blocked** | 125,657 historical roster records built; one early fold lacked the fixed minimum training count. |
| 2027 preseason reference forecasts | **Operational** | 99 men's + 366 women's frozen research priors. |
| Point-in-time injury / availability signal | **Missing frontier** | High-value gap; retrospective proxies are not treated as equivalent. |
| Strong women-specific external/player value | **Missing frontier** | Material prospective information gap. |
| Fully point-in-time external ratings / consensus markets | **Incomplete frontier** | Several historical source families remain provenance-limited or unavailable. |

The matrix is intentionally conservative. A mechanism is not labeled recreated because a similar feature exists somewhere in the repository.

## What the post-release evidence says

### 1. More features are not automatically more transferable

The shot-context system improved held-out regular-season prediction but did not improve the tournament correction. Domain transfer is now an explicit gate rather than an assumption.

### 2. Recent-year gains are not enough

Cross-season player-origin features and the joint 33-feature representation both looked stronger in 2023–2025 but failed their earlier development criteria. The project retains the original gate rather than rewriting it after seeing recent scores.

### 3. Complementarity exists, but it still needs stable signal

The newer correction streams are much less correlated than the earlier raw model family. Residual fusion nearly passed, missing its confirmation threshold by about 0.0000504. That is evidence of complementarity, not evidence that the current combination should be promoted.

### 4. Data engineering has become a first-class research asset

The private AWS workspace now contains multiple independently checked observation layers: advanced team/player context, daily pregame states, possession/lineup data, cross-season player history, roster attributes, schedules, and prospective 2027 captures. The challenge has shifted from simply acquiring more rows to proving that new information survives point-in-time validation.

## Current data/provenance frontier

A scoped registry contains **4,318 hashed CSV paths**, with **903 paths matching discovered reconstruction receipts**. The remaining paths include raw inputs, generated outputs, duplicated contents, and files without discovered reconstruction recipes. The registry does not turn unknown provenance into verified provenance.

The highest-value missing inputs remain:

1. contemporaneous injury / availability history;
2. stronger women-specific external/player-value signal;
3. historically verifiable predeadline external strength systems;
4. broader market consensus with point-in-time capture;
5. future-season data frozen prospectively rather than reconstructed after outcomes.

## Current private next step

The roster-geometry dataset is reconstructed but its first model run was blocked by a single cold-start fold. The next private experiment keeps the 80-game minimum, preserves every assessment game, leaves the unavailable fold unchanged, and tests the remaining trainable folds under the same historical gates.

No public claim is made until that experiment is actually scored.

## Public/private boundary

This document publishes research questions, aggregate evidence, validation logic, and negative results. It does not publish raw datasets, candidate prediction bytes, fitted private models, exact production feature formulas, source-specific identity logic, credentials, or AWS-only competitive implementation details.
