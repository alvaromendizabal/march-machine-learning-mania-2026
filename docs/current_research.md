# Current research status and evaluation boundaries

## Recorded best

The current recorded post-competition best is submission **56479241**, filename
`march_champion_bpi_futures_only_men.csv`, with public and private Brier
**0.1089408** and SHA-256
`b10aeddf304ca6f5e2c6f749ce4a792210ac554f6a99bb6d8b68aeabbfe110d9`.

The preceding champion scored **0.1094899**. The published 2026 winning benchmark is
**0.1097454**. The current artifact is therefore numerically lower by **0.0008046**.
These are post-competition comparisons; no original placement or prize claim follows.

## What changed

The 0.1094899 statistical champion combined a compact men’s win-probability core with a
richer score-margin ensemble. The latest scored artifact preserves that champion except
for **1,986 men’s pairings** receiving a fixed BPI championship-futures information tier.

The final file contains **132,133 rows**. Exactly **130,147 rows** remain protected,
including all **65,703 women’s rows**. The scored run performed zero model fits and one
upload attempt.

## Why this component was tested

A prior full market overlay changed 2,018 rows and scored 0.1098037. A separately frozen
Round-1-only overlay changed 32 of those rows and scored 0.1103527. Those 32 rows were
identical in both candidates, leaving 1,986 disjoint futures-only changes.

Because Brier is additive over scored games, the isolated component’s rounded score could
be inferred algebraically before upload:

`futures_only = incumbent + full_overlay - round1_only`

The implied interval was approximately **0.10894075–0.10894105**. The subsequent recorded
score was **0.1089408**, consistent with that decomposition.

## Research limitations

The component isolation used two post-competition leaderboard scores. The component
probabilities and fixed weight existed before those scores were observed, but choosing
which disjoint component to retain is still post-hoc model selection. The result is useful
for retrospective research and portfolio evidence, not independent confirmation or a
forecast of 2027 performance.

The published competition winner scored 0.1097454; **0.09 is an unachieved stretch target**.
Reaching 0.09 from 0.1089408 requires another 0.0189408 absolute reduction, roughly 17.4%.

Repeatedly used historical seasons and post-competition score feedback are consumed
development information. Future evidence should use immutable, timestamped pregame
snapshots and predictions frozen before outcomes.

## Public/private boundary

GitHub is the curated employer-facing evidence layer. AWS retains the evolving private
training implementation, fitted models, feature details, checkpoints, data and experiment
state. This update intentionally does not publish a retraining kit for the current system.

Previously published source and license grants remain in repository history and are not
made confidential by this policy.
