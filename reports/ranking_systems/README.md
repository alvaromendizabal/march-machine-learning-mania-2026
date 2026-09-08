# Does individual-system information improve the ranking consensus?

Completed 2026-09-08 under the [declared protocol](../../docs/ranking_systems.md).
The official source supplies **105 systems known in legal 2003–2012 snapshots**.
Eight definitions per system produce **840 additional candidates**. The combined
arm contains those 840 plus the 19 existing compact consensus candidates. Across
the main bank and this separate study, **3,946 distinct candidate definitions**
have now been investigated; the notebook 03 input remains the original 3,106 bank.

**112 fits were evaluated: 92 fresh fits and 20 verified original controls.**
Seven OOF years support forward-only representation selection for the five outer
seasons. Every outer arm covers the same 334 men's physical games. Women have no
official ordinal table and are not given fabricated system inputs.

| Representation | Logistic: mean season Brier | Histogram: mean season Brier |
|---|---:|---:|
| Strength without Massey | 0.191268 | 0.200485 |
| Compact consensus control | 0.187608 | 0.189798 |
| Individual levels | 0.186924 | 0.196201 |
| Deviations from consensus | 0.198198 | 0.195027 |
| Matched-system momentum | 0.191060 | 0.194011 |
| Availability | 0.189269 | 0.190405 |
| Combined | 0.186924 | 0.196201 |
| Eight-component embedding | 0.188223 | 0.192718 |
| Forward-selected representation | 0.195240 | 0.189887 |

Lower is better. Game-weighted Brier, log loss, ROC AUC and calibration error are
separately recorded in `leaderboard.csv`. The nominal best fixed logistic arm has
game-weighted Brier **0.186891** and ROC AUC **0.793759**. It is not a newly validated
final model: the fixed-arm comparison is retrospective and the forward selector
does not reproduce its advantage.

Individual levels change logistic mean-season Brier by **−0.000684**, with a paired
95% season-bootstrap interval **[−0.006008, 0.003298]**. Their improvement is driven
by 2021; three of the five season comparisons are unfavorable. The histogram effect is **+0.006403 [−0.005991, 0.019733]**. The combined
screen retains exactly the same columns and produces identical predictions to
levels: other families do not survive alongside the strongest level candidates.

The forward-selected logistic stream worsens by **+0.007632 [0.002134, 0.013908]**.
Earlier OOF seasons choose momentum for 2016/2017 and availability for later folds;
that choice fails to generalize. Histogram selection chooses availability for 2016
and then the consensus, changing Brier by only **+0.000089**. Deviations hurt fixed
logistic in every outer season; the eight-component embedding also fails to help
either estimator on average. The histogram embedding interval excludes zero on the
unfavorable side. Intervals are exploratory and unadjusted for multiple comparisons.

In the ten combined outer fits, **8,400 additional-candidate screening decisions**
produce **160 retentions and 8,240 rejections**. Each fit retains 16 additions, and
**22 distinct additional columns** survive across those fits; **818 of the 840**
are never retained in this combined outer comparison. All 22 are system-specific
logits. Stable examples include DOK, CNG, MOR, LMC, EBP, DOL, WLK, STH, SAG, RTH, POM
and WIL, each selected in all five seasons by both recipes. These are selection
frequencies, not independent evidence of each system's predictive value.

Across all arms and OOF fits, the audit records **31,336 input decisions**. Embedded
inputs are explicitly labeled separately from screened retention; hundreds of PCA
source columns never count as hundreds of fitted model dimensions. Missing,
constant, redundant-to-base, redundant-to-addition and capacity rejections remain
auditable. The full audit is retained with the private run; counts and stability
are public. The no-Massey and consensus controls preserve their original predictions.

All **112 saved models** reloaded and reproduced their forecasts with maximum
absolute error **0.0**. An independent calculation reproduced all **18 leaderboard
rows**. A second actual run reused **113 checkpoints** (matrix plus 112 fits),
started zero new tasks and preserved every model and prediction checksum.

**Decision: retain the compact consensus; do not promote this addition or retune
the final model around its nominal winning fixed arm.** This closes a concrete
gap in the official-data feature search. Together with the broad-family ablations
and retained-capacity experiment, the evidence supports diminishing returns from
more variations of the same inputs. It does not prove that untested, independently
informative player data would be useless. No 2022–2026 labels or submission file
are used, and notebook 03/04 results retain their existing lineage.


The 49,337,694-byte archive is verified in versioned S3 storage. Its exact-version
fresh download was consumed by the canonical `study_stage` restoration path,
reusing all 113 tasks without fitting and reproducing the model/prediction hashes.
Notebook 02 now restores both follow-ups before running them in train mode on a
fresh checkout; changed source/configuration delegates a new run instead of
restoring stale results. The verified upstream feature archive and raw inputs
remain explicit dependencies. See [the validation receipt](../validation/ranking_systems.json).


The source passed **228 automated tests** and native execution of **all six notebooks,
42 code cells**. The second notebook pass reused all six verified checkpoints with
no warning/error outputs. The exact source checkout, executed notebook hashes,
coverage scope and cloud recovery evidence are recorded in the validation receipt.
