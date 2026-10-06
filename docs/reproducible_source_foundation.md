# Reproducible official-data foundation

## Why this milestone exists

The project had already reproduced important model behavior, but source ownership and repeatable feature construction remained separate engineering questions.

The latest AWS milestone therefore focused on a narrower claim:

> Given only owned official game files and pinned source receipts, rebuild broad historical features, preserve missingness, prove chronology boundaries, and reproduce the resulting feature banks independently.

It intentionally performed **zero forecasting-model fits**.

## Aggregate result

| Evidence | Men | Women |
|---|---:|---:|
| Raw seasons discovered | 42 | 29 |
| Team-season rows rebuilt | 13,753 | 9,851 |
| Incoming 2026 rows | 365 | 363 |

For the complete 566-game historical men's evaluation bank:

- both teams are available for **566 / 566** games;
- performance features are complete for **566 / 566**;
- schedule features are complete for **566 / 566**;
- temporal / venue features are complete for **554 / 566**.

Missing values remain explicit. They are not replaced with future values or publisher-specific estimates.

## What is independently rebuilt

The public feature contract contains transparent descriptive families: scoring and margin; boxscore possession estimates; offensive / defensive / net efficiency; shooting, turnover, rebounding, and free-throw factors; opponent record and opponent efficiency context; recent form; home / road / neutral splits; close-game results; and rest intervals.

These names describe project-owned formulas. They are not relabeled proprietary metrics.

## Reproducibility evidence

The milestone verifies raw-file hashes, compact / detailed consistency, team coverage, cutoff rules, explicit missingness, future / post-cutoff poison resistance, season-prefix invariance, 2026-as-incoming feature generation, content-addressed caching, and separate-process raw-to-feature replay.

Men's and women's saved feature outputs matched their independent replays.

## Source boundaries

The project distinguishes official / owned inputs, independently recreated external sources, late reconstructed data, and quarantined data.

A recent reconstructed-lineup study illustrates that boundary. The source was preserved, but modeling stopped before fitting when its interval semantics did not match the runner's exposure assumption.

## What this does not prove

This milestone does not show that the new descriptive features improve forecasting performance.

It does not certify every private supplemental source, reproduce the complete private model recipe, or establish full future-season readiness.

Those are separate gates.

## Next research question

The next modeling study uses this foundation to test whether strictly pregame regular-season supervision learns matchup information that transfers to tournament games.

The experiment must pass historical development and confirmation requirements before any target-year audit.
