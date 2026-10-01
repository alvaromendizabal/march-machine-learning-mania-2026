# Current result and evaluation boundaries

## Canonical research boundary

The current AWS-reproduced post-competition system scores **0.1033437336 Brier** on the complete 126-game 2026 men's + women's cohort. The published 2026 winning benchmark is **0.1097454**.

The numerical comparison is favorable, but the timing matters: this is **post-competition, benchmark-informed research**, not an original competition placement or a prospective generalization claim.

The active stretch target is **0.0900000**, leaving **0.0133437336** absolute Brier.

A separate agreement-gated candidate scores **0.1027974461** in local replay. It is not promoted here because canonical AWS reproduction is still pending.

## Score progression since the previous public release

| Research milestone | Complete-cohort Brier | Public interpretation |
|---|---:|---|
| Previous retained boundary | 0.1051853186 | Post-competition reference |
| Owned external-consensus correction | 0.1043512820 | First stable improvement from independently reconstructed external context |
| Dated-Torvik residual | 0.1042218008 | Historical gate passed, but final gain was below the promotion requirement |
| **Uncertainty-gated dated-Torvik correction** | **0.1033437336** | AWS-reproduced current research boundary |
| Agreement-gated candidate | 0.1027974461 | Local replay only; canonical run pending |

Lower is better. Scores are retrospective research evaluations on the known 2026 outcomes and must not be represented as original leaderboard results.

## Supplemental-source program

The project now treats public winning solutions primarily as **mechanism and source inventories**, not as files to copy.

### Independently owned / reconstructed

- competition-era AP polling observations and trajectory summaries;
- dated BartTorvik snapshots and trajectory state;
- game-specific ESPN predictor/BPI context;
- multi-provider no-vig market context;
- regular-season venue, conference, and coach-history summaries;
- historical player-game data supporting owned player-value and participation proxies;
- direct competition-derived Elo/SRS/Colley/Massey-style strength systems.

### Partial or substitute-only

- coach PASE: a chronological analogue exists; exact numeric parity is not claimed;
- player value: owned substitutes exist; exact EvanMiya/BPR parity is not claimed;
- availability: participation proxies exist; they are not medical injury labels;
- preseason strength: owned Torvik trajectories exist; they are not relabeled KenPom.

### Explicit remaining gaps

- authorized exact historical KenPom where access is not independently available;
- exact proprietary EvanMiya/BPR values;
- complete contemporaneous historical injury/availability snapshots;
- independently reconstructed WNCAA NET history suitable for a strict point-in-time pipeline.

## Source timing and leakage boundary

A reconstructed historical source can be useful without being prospectively certified.

The project distinguishes:

1. **receipt integrity** — current bytes match a captured source/recipe;
2. **cutoff eligibility** — the observation is dated before the modeled forecast cutoff;
3. **historical publication provenance** — evidence that the same observation existed before the original forecast;
4. **predictive evidence** — a frozen matched comparison improves its declared assessment window.

A checksum alone is not a leakage claim. Retrospective sources without original publication proof remain labeled retrospective.

## Major negative findings since the previous release

Several plausible mechanisms were deliberately closed rather than continuously retuned:

- owned preseason trajectory + coach history;
- two owned player-value/availability representations;
- generic public-solution LR/XGBoost replacements;
- AP-enhanced first-place-style boosting;
- historical season-level BPI whose endpoint returned post-cutoff/final state;
- sparse/pruned LR residual correction;
- broad robust rating consensus;
- unconditional dated-Torvik correction whose final gain was below the frozen promotion margin.

The pattern is consistent: **recent/development gains are insufficient unless transfer remains stable across the untouched confirmation seasons and the final complete-cohort audit.**

## Why the current system improved

The strongest gain does not come from replacing the full model. It comes from **selective men-only residual correction** on rows where the retained system historically showed sufficient uncertainty, while protecting strong first-round and women's predictions.

This is reported at a high level only. Exact private gating rules, weights, row-level corrections, and production artifacts are intentionally not public.

## Active modeling scope

New supplemental reconstruction/modeling is bounded to:

- **men 2003+**
- **women 2010+**

Older cached material may remain for provenance but is not an active modeling target.

## 2027 state

The prospective layer is designed to capture real source timing rather than recreate it after the tournament:

- raw observations first;
- capture timestamps and SHA-256 receipts;
- normalization/mapping as separate steps;
- source-level waiting states for unpublished 2027 inputs;
- no copy-forward of 2026 values;
- no automatic promotion of a new source into production features.

The next defensible generalization claim requires a genuinely future tournament scored under a frozen pre-outcome protocol.
