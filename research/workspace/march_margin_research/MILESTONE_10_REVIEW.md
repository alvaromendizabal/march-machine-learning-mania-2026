# Milestone 10 — completed recovery and measured feature result

## What the uploaded archive proves

Input: `milestone_10_recovery_return.zip`. All 14 checksums in its integrity ledger
match the files in the uploaded archive. This verifies consistency, not an external
attestation. Its recovery status is `REPORT_COMPLETE`.

Installation accepted 2013/2014 checkpoints. Preparation reused those two rating
fits, completed the remaining five, built five remaining pair tables, and replayed
four references. Evaluation completed eight new classifiers and twelve comparisons.
The report receipt records ten Plotly figures and the saved scientific ZIP.
The logs record preservation checks for repository, raw inputs and upstream caches.

This was executed by the user in SageMaker; it was not newly executed by the
assistant. Receipt timestamps are 2026-09-12 UTC (the evening of September 11 in
America/Los_Angeles). No further BT solver repair is indicated by this archive.

## Brier values extracted from the evaluation log

| Season | Reference | + ability | + ability and uncertainty | Ability delta |
|---|---:|---:|---:|---:|
| 2016 | 0.2128404 | 0.2132414 | 0.2140329 | +0.0004010 |
| 2017 | 0.1733234 | 0.1735861 | 0.1734045 | +0.0002628 |
| 2018 | 0.1990661 | 0.1985560 | 0.1985750 | -0.0005101 |
| 2019 | 0.1732019 | 0.1718494 | 0.1711573 | -0.0013525 |

Primary ability mean delta: **-0.0002997002**; improved **2/4** seasons.
Conditional uncertainty mean delta: **-0.0000158293**; improved **2/4**.
Applying the already-declared −0.0005 / ≥3-of-4 / worst ≤0.003 rule to these logged
values fails for both. This recomputed conclusion is distinguished from reading
`decisions.json`: the full scientific archive was not supplied in this upload.
No feature is promoted. The positive result is successful recovery and a completed
comparison, not a leaderboard breakthrough.

## What remains outside this upload

The recovery ZIP is not the scientific ZIP. It lacks the full calibration,
coefficient, redundancy and per-season scientific tables. It points to:
`$HOME/march_win_strength/reports/milestone_10_return.zip`
SHA-256: `9dcfaf073b72de7105011d45e4cd7f3a42a74ac8c961c449ba053da51bebb86c`.

The next notebook reads that existing file, verifies it and its score grid, and
includes it in the next return archive. No old experiment rerun is needed.
The recovery record's `new_real_data_brier: null` is an unchanged recovery-level
placeholder; it does not erase the twelve actual historical scores present in
its evaluation log. There is still no new 2026 leaderboard score.

## Preservation and next step

Best submitted Brier remains user-reported **0.1222672**; research target
**0.1097454**. No current leaderboard query or new submission was performed.
Neither AWS resources nor GitHub were modified by the assistant in this turn.
The next bounded hypothesis examines margin magnitude and residual influence,
using the unchanged classifier and preserving the completed evidence.
