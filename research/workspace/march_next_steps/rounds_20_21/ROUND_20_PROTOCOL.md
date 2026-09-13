# Round 20 — Pace and shot-variance context

**Status: prepared, unexecuted.** Four hypotheses, two families; no empirically optimal constants claimed. Data and target: pre-tournament men's matchup win probability; evaluation Brier on played main draws in 2022–2025. All evaluation years were previously explored. No claim of fresh confirmation or leaderboard performance.

## Why this investigation
Earlier rounds mainly added team-effect differences. Here symmetric context multiplies the existing antisymmetric strength/consensus gap. Under a rough independent-scoring-opportunities picture, accumulated mean and variation scale differently as opportunities increase. This motivates a *hypothesis* that pace and scoring variability modify how a strength gap translates to a probability. NBA scoring studies support considering stochastic scoring and heterogeneous ability; they do not validate this NCAA formula or prove independence of possessions.

Pace/variance concepts already exist in the broader repository. This is a controlled alternate representation, not a claim that these concepts are wholly new.

## Inputs and definitions
Only current-season regular-season detailed games with DayNum ≤132. Shared possessions are the average of `FGA − OR + TO + .475 FTA` for both sides. Tempo is possessions ×40/(40+5NumOT). League context includes all legal teams, not just tournament teams; no future edition/outcome is used.

Pool attempts by team. Define three-attempt share q, two-point accuracy p2 and three-point accuracy p3 using fixed 50-attempt priors from the same known league totals. Half-event safeguards keep the priors finite in tiny fixtures. This is descriptive season-local shrinkage, not training on tournament outcomes.

Field-goal scoring variance proxy:
`E=2(1−q)p2 + 3q p3`
`V=4(1−q)p2 + 9q p3 − E²`.
It models a categorical 0/2/3 field-goal outcome. It excludes free throws, turnovers, rebounding chains, shot dependence and game-state variance; it is not a full possession or score forecast.

Controls (team A−B): mean tempo, tempo SD, three-attempt share, V. These are not counted as new discoveries.

## Four candidates
Let D be the already-cached margin-strength difference and R the existing ranking-consensus-logit difference. For symmetric pair mean tempo T and league team-mean tempo T0, set u=√(T/T0)−1. For pair mean V and league team-mean V0, set v=√(V0/V)−1.

- Pace family: D×u and R×u.
- Variance family: D×v and R×v.

All four negate under team swap. Equal strength gaps yield zero interaction. League-average context yields zero contextual increment. Square-root scaling is fixed before the run, a scientific hypothesis rather than calibration.

## Experiment and safeguards
Six fixed configurations: reference17, controls21, either family23, both25, duplicate-controls25. The four duplicate columns repeat the descriptive controls, not new information. Primary `context_given_controls`; duplicate sensitivity `both_given_duplicate`; conditional add/drop comparisons keep all other columns fixed. Classifier settings unchanged from the verified consensus reference. No tuning, selection, new rating fit or ensemble. Twelve feature snapshots; four baseline classifier replays; twenty new classifiers maximum.

Preflight all years → 2013 smoke → replay proves zero new construction → remaining snapshots → comparisons → preserved report. Input disagreements, nonfinite profiles and <10 detailed games per seeded team stop. Future games/labels never enter construction; no 2026 labels. Same snapshot is valid for that season's pre-tournament forecast, not a pregame backtest of its constituent regular-season games.

Retain as a transfer candidate only if mean delta ≤−.0005, ≥3/4 years improve, worst delta≤+.003, and negative mean versus duplicate controls. This rule is not significance. Four-season bootstrap and leave-one-season-out summaries are descriptive; repeated research and small cluster count limit inference. No automatic promotion.

## Sources and limits
- Gabel & Redner, Random Walk Picture of Basketball Scoring (2011), NBA study: https://arxiv.org/abs/1109.2825 . Motivation only; not an NCAA benchmark or proof of our formulas.
- Pomeroy, Stats Explained: https://kenpom.com/blog/stats-explained/ . Possession and rate definitions.
- Frozen local `consensus_reference.py` / `research_workflow.py`: exact baseline and chronology. Prior scoring/variance experiments remain in the project's negative-evidence ledger.
