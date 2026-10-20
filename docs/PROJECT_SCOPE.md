# What this repository maintains

**NCAA probability forecasting, with independent evaluation and a runnable public reference.**

The [featured scored artifact](champion_result.md), the historical public framework,
and the authored bracket demonstration have distinct identities. A successful
public example is not a reproduction of a private competition score.

| Review path | Maintained components | Evidence boundary |
|---|---|---|
| Featured delivery | `portfolio/reproduce_release.py`, the scored receipt and acceptance checks | Recorded retrospective result; not a prospective win-rate claim |
| Forecasting framework | `src/march_mania/`, the six canonical notebooks and their consumed aggregate inputs | Training-only features, season-forward comparisons and recoverable execution |
| Interactive analysis | `public-demo/`, public reproduction, packaging and browser tests | Authored team strengths and scenarios, not live odds or forecasts |
| Ongoing research | Existing private AWS workspace, data and checkpoint lineages | Not closed, restarted or synchronized by repository presentation changes |

## What was retired from the current tree

Unreferenced legacy feature-engineering/final-export report copies, an unused large
feature-audit export, an obsolete model-recipe duplicate, one-time consolidation
scripts, and completed branch-specific publication jobs are not part of this
maintained review. Two old model-comparison CSVs remain because the canonical
notebook and protocol actually consume or cite them. Essential baseline comparisons,
negative outcomes, attribution, fitted-reference code and active test gates remain.
Git history preserves retired material without advertising it as the current system.

## Reproduce without private assets

Start with [the technical walkthrough](../START_HERE.md) and
[public reproduction](public_reproduction.md). The full framework uses the pinned
Python environment and retains its original tests, type/lint gates, native notebook
execution, score-ledger checks and independent browser evaluation. The repository
hygiene check also verifies Markdown links inside notebooks and rejects tracked
runtime caches and temporary run handoffs.

Private models, exact tuned recipes, licensed source records, secrets and raw
forecast arrays are not added by this publication. AWS is still the scientific
execution environment. Do not reset a running workspace or delete its checkpoints
to make a GitHub directory smaller.
