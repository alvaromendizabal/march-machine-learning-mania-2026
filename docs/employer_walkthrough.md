# Employer walkthrough | NCAA forecasting research

## Headline

**Best recorded post-competition Brier: 0.1089408.**

The published 2026 winning benchmark was **0.1097454**, so the recorded result is numerically lower by **0.0008046**, approximately **0.73% lower Brier**. This is a retrospective benchmark result—not an original competition placement or a claim of prospective superiority.

## What I would evaluate as an employer

**Research judgment.** The project began from public leading-solution ideas but did not stop at reproduction. The strongest statistical improvement came from separating two jobs: a compact win-probability core and a richer score-margin ensemble. Multiple plausible alternatives were tested and rejected rather than hidden.

**Controlled iteration.** Historical whole-season assessments, matched controls, fixed blend rules and explicit promotion gates constrained model development. Later post-competition score tests are labeled as such; repeated leaderboard feedback is not presented as an untouched holdout.

**Engineering reliability.** Scored artifacts are checksum-locked. Candidate builders protect unaffected rows byte-for-byte, checkpoint expensive work, validate notebook outputs after reopening, and prevent duplicate uploads after ambiguous responses. The latest scored run made one upload attempt, zero model fits, and passed all eleven stages.

**Evidence-based debugging.** A full market overlay worsened the score, and a Round-1-only overlay worsened it further. Because those candidate changes were disjoint, their Brier contributions could be decomposed algebraically. The isolated championship-futures tier was predicted to score about 0.1089409 before submission and then scored **0.1089408**.

## Model lineage

The strongest statistical model uses XGBoost in two complementary roles: a compact binary-outcome core and a richer score-margin ensemble. The margin representation incorporates efficiency, shooting, possession, rating, schedule and form information. The latest scored artifact adds a fixed championship-futures information tier to selected men’s pairings while preserving the rest of the champion.

The public portfolio communicates the architecture, evidence, controls and achieved results. Current private training implementation, model binaries, exact feature formulas and future competition recipes remain outside this publication.

## Limitations

The 0.1089408 result was obtained after the competition and after iterative research using 2026 feedback. It therefore does not establish what the system would have achieved under the original competition information set, nor does it predict 2027 performance.

The 0.09 figure is a stretch target, not an achieved or published winning score. A genuinely stronger 2027 claim should come from predictions recorded before future outcomes.

See [current research](current_research.md), [2027 readiness](2027_readiness.md), and the [machine-readable milestone](../reports/current_research/latest_score.json).
