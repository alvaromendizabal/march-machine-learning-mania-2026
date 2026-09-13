# Review of the uploaded milestone 06

## Observed, not inferred

Original upload: `milestone_06_return.zip`. The values below are copied from its metrics and summary. No round-07 experiment has been run on the user’s data.

| Population | Season | Configuration | Brier | Delta vs anchor |
|---|---:|---|---:|---:|
| M | 2017 | anchor | 0.1733234 | +0.0000000 |
| M | 2017 | anchor_level | 0.1713579 | -0.0019655 |
| M | 2017 | anchor_change | 0.1748314 | +0.0015081 |
| M | 2017 | anchor_both | 0.1718584 | -0.0014650 |
| M | 2019 | anchor | 0.1732019 | +0.0000000 |
| M | 2019 | anchor_level | 0.1744629 | +0.0012609 |
| M | 2019 | anchor_change | 0.1728251 | -0.0003768 |
| M | 2019 | anchor_both | 0.1735579 | +0.0003560 |
| W | 2017 | anchor | 0.1309463 | +0.0000000 |
| W | 2017 | anchor_level | 0.1277010 | -0.0032453 |
| W | 2017 | anchor_change | 0.1267309 | -0.0042154 |
| W | 2017 | anchor_both | 0.1244092 | -0.0065371 |
| W | 2019 | anchor | 0.1462544 | +0.0000000 |
| W | 2019 | anchor_level | 0.1540589 | +0.0078044 |
| W | 2019 | anchor_change | 0.1460340 | -0.0002204 |
| W | 2019 | anchor_both | 0.1522309 | +0.0059765 |

## Decision supported by the result

Only women’s `anchor_change` improved in both discovery years and met the previous gate. Its mean delta was -0.002217873565227735. The 2019 change-only Brier gain was small; log loss moved in the wrong direction. Men’s results and the level additions were inconsistent across the two years.

**Next:** test the same two women’s change features on 2016/2018 using completed snapshots and reference models. These extra seasons remain previously-used project history. No broad expansion or automatic promotion is warranted.

## Execution record from the returned summary

The completed round made 14 early-rating fits and 13 new classifiers, replayed 3 earlier classifiers, and reused 14 base snapshots. The summary reports source, raw and upstream preservation and no GitHub/AWS resource modification. No new leaderboard result was recorded.

## Source files

`evidence/metrics.csv`, `evidence/decisions.json`, `evidence/summary.json`, `evidence/manifest.json`. These are extracted bytes from the uploaded report. The decision above is our interpretation; the report itself marks the women’s change family `CONSIDER_UNCHANGED_REPLICATION`.
