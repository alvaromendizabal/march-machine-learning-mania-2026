# Employer walkthrough | NCAA forecasting research

## Start here

Open the [frontier research notebook](../portfolio/frontier_research.ipynb). It is the current employer-facing view of the project: the **0.1072824** retained post-competition boundary, the chronology-safe residual-family study, the frozen unscored challenger, the provenance controls, and the remaining gap to 0.09.

The earlier [scored component case study](../portfolio/current_research.ipynb) remains useful historical evidence for how the 0.1089408 public release was isolated. It is no longer the current private score boundary.

## Result

The strongest retained private post-competition release is **0.1072824 Brier**, compared with the published 2026 winning benchmark of **0.1097454**. The numerical difference is **0.0024630**, about **2.24% lower Brier**. This is not an original competition placement or proof of prospective superiority.

The active stretch target is **0.09**, leaving **0.0172824** absolute Brier to close. The project therefore treats the remaining work as a frontier research problem rather than a polishing exercise.

## What to evaluate

**Research judgment.** The latest residual study did not simply choose the configuration with the largest average gain. The full residual panel improved the historical mean more, but violated a predeclared worst-season guardrail. A smaller, more stable representation was selected instead. This is the kind of tradeoff that matters when models must generalize across tournament seasons.

**Validation design.** Configuration selection was season-grouped and used only tournament outcomes through 2025. The 2026 tournament outcome was prohibited. Market/futures inputs were also excluded from residual training and model selection. The resulting candidate is therefore a test of a new statistical representation rather than a leaderboard-tuned market variant.

**Engineering discipline.** The frozen challenger changes only 2,278 approved men's rows and preserves 129,855 rows byte-for-byte, including every women's row. It passed schema, ordering, numerical, formula, preservation, and notebook checks. Candidate construction made no submission.

**Provenance honesty.** The project explicitly distinguishes independently rebuilt transformations from historical observations whose original pre-deadline capture cannot be proven. The 2026 futures layer is retained only as a retrospective fixed component. For 2027, raw-first collectors, immutable source timestamps, stale-season quarantine, and cutoff-aware freezing are the standard.

**Cloud engineering.** The research program uses a private AWS/SageMaker workspace for active experiments and public GitHub for reviewed evidence. The 2027 data layer already operates scheduled collectors for Kalshi, ESPN, and BartTorvik, while refusing invalid target-season data rather than silently filling gaps.

**Frontier awareness.** The repository now includes an explicit leading-solution reproduction matrix. It shows what was recreated and validated, what was adapted, what failed, what is blocked by unavailable point-in-time data, and what remains missing. The next planned capabilities—women-specific reconstruction, roster/availability signals, and a heterogeneous OOF ensemble—come directly from that gap analysis.

## Ownership and public/private boundary

The public repository demonstrates the problem, score progression, validation philosophy, top-solution adaptation, engineering controls, negative results, provenance limitations, and prospective research plan.

The active private implementation, current candidate bytes, fitted model artifacts, detailed production feature formulas, private data, and source-specific competitive recipes remain outside the public release. That separation keeps the portfolio technically rich without turning an evolving competition system into a public reproduction kit.
