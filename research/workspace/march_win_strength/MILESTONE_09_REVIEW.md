# Milestone 09 · Verified review

This review uses only the uploaded `milestone_09_return.zip`. All 18 hashes in its `return_integrity.json` matched. These are reported historical metrics, not independently rerun predictions in this chat.

## Actual primary result

| Season | Seed-status control | Bracket + scaled eligibility | Change |
|---|---:|---:|---:|
| 2016 | 0.1633963 | 0.1661827 | +0.0027864 |
| 2017 | 0.1315294 | 0.1304291 | -0.0011003 |
| 2018 | 0.1529060 | 0.1520691 | -0.0008369 |
| 2019 | 0.1471766 | 0.1479359 | +0.0007592 |

Mean primary Brier change: **+0.0004021**. Improved seasons: **2/4**. Gate: **DO_NOT_EXPAND_AUTOMATICALLY**. Positive changes are worse.

Completed: **16 comparisons**, **12 new classifier fits**, **4 verified reference replays**, **0 new rating-model fits**. `summary.json` reports COMPLETE and unchanged repository/raw/upstream artifacts. No leaderboard score was produced; no GitHub update was performed.

## Methodological conclusion

Do not promote or automatically expand the bracket-eligibility representation under this tested fixed recipe. Improvement in two seasons does not satisfy the predeclared three-season rule. This result does not establish that actual home-court information is useless; this was a seed-derived eligibility proxy, not a complete confirmed-venue feature.

## Next increment

Stop that expansion. Investigate men's joint schedule-adjusted win-loss ability, independently of margins, with approximate pair-rating uncertainty as a conditional second feature. Reuse all existing reference fits; keep the tournament classifier unchanged. This is a different representation hypothesis, not a claim of a new algorithmic invention or a promised score gain.

The research space is not declared mature. Repeated historical exploration, limited tournament training samples and differences from the final production recipe remain important limitations.
