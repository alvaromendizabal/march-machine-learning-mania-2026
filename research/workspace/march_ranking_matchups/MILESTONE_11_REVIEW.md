# Milestone 11 — verified current state

Basis: the user-uploaded `milestone_11_return.zip`, not generated benchmark data.
All 21 members listed in its integrity manifest match their recorded SHA-256 values.

| Configuration | Mean Brier change vs reference | Seasons improved |
|---|---:|---:|
| anchor_huber | -0.0001987299 | 1/4 |
| anchor_compressed | -0.0004379670 | 3/4 |
| anchor_both | -0.0005018549 | 2/4 |

The primary `huber_given_anchor` failed the expansion gate. The declared secondary `compression_given_huber` also failed (mean −0.0003031250, 3/4 improved). The nominal compression-only comparison must not replace the primary claim. No margin-feature promotion follows.

Completed: 14 new regular-season rating fits, seven matchup tables, 12 new tournament classifiers and four prior reference replays. No execution error remains in the supplied report. Source, raw inputs and upstream artifacts are recorded as unchanged.

The nested milestone 10 scientific archive is present and has the expected digest. This review does not refit either study.

No new leaderboard score was measured. Submitted Brier remains the user-reported 0.1222672; 0.1097454 remains a target, not a guaranteed outcome.

Next design: restore an established ordinal-consensus control to the compact manual reference, then test two matched-system pair summaries beyond it. This is not rerunning the prior 840-feature ranking study or pretending ranking consensus is new to the repository.
