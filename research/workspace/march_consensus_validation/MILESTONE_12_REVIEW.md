# Milestone 12 — Actual results and next decision

Source: the user's `milestone_12_return.zip`. Twenty files covered by the return-integrity manifest were independently hashed and matched. All values below are from the supplied results, not from the synthetic tests of the next kit.

| Men’s season | Reference Brier | + consensus Brier | Consensus change | Pairwise-family change beyond consensus |
|---|---:|---:|---:|---:|
| 2016 | 0.2128404 | 0.2119065 | −0.0009338 | −0.0031369 |
| 2017 | 0.1733234 | 0.1719935 | −0.0013299 | +0.0081501 |
| 2018 | 0.1990661 | 0.1994409 | +0.0003748 | +0.0005160 |
| 2019 | 0.1732019 | 0.1714087 | −0.0017932 | −0.0010743 |

## Ten-part milestone review
1. **Attempted:** Two shared-system ranking features, with an established consensus control and fixed logistic classifier.
2. **Completed:** Seven legal publication panels, seven matchup matrices, 20 scored historical comparisons.
3. **Passed:** Technical completion, data/source/upstream preservation, original reference replays; the separate consensus-control gate.
4. **Failed/underperformed:** The new pairwise family worsened mean Brier **+0.0011137347**, improved 2/4 years, worst deterioration **+0.0081500886**. Its primary gate failed.
5. **Actual metric:** Consensus alone improved mean Brier **−0.0009205404**, improved 3/4 years, worst deterioration **+0.0003747942**. Mean scores: reference **0.1896079406**, plus consensus **0.1886874002**. Those are men’s 2016–2019 exploratory main-draw results, not 2026 leaderboard scores.
6. **Saved work:** The returned summary records completed metrics, diagnostics, report integrity, and the fingerprint `374348cf553aca8e932ef6d6f56244a6ebcac7cbb2ab36cf66bc17a2d0acef12`. Sixteen new classifiers, four upstream replays, zero rating fits in that experiment.
7. **GitHub:** The returned summary says `github_updated: false`. No new commit or merge is made by this response or the next kit. This is not a fresh check of remote branch status.
8. **Learned:** The established consensus control is worth testing beyond the old years; adding the paired-ranking representation is not supported by its primary comparison. These are separate claims.
9. **Next highest-value step:** Repeat only reference versus reference-plus-consensus on 2022–2025, unchanged. No failed pairwise additions and no novel-feature claim.
10. **Compute justification:** Eight classifiers and ten compact-reference ridge fits yield a later-era test, with seven old matrices and four old consensus models reused. This is preferable to another variant selected against the same 2016–2019 outcomes.

The 2022–2025 years are already used project history; they are not newly untouched tests. Source revisions and broad project selection remain limitations. No result establishes that the whole leaderboard gap is due to features or that the target can be guaranteed.
