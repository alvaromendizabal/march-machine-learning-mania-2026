# Current research boundary

## Metric contract

Primary metric: **Brier score** on NCAA tournament win probabilities. Lower is better.

The project keeps four evaluation concepts separate:

1. historical development;
2. later-season confirmation;
3. the exact 126-game 2026 audit;
4. externally submitted scores.

A lower retrospective 2026 score does not automatically become the accepted champion.

## Accepted system

The accepted owned/recreated control remains **v26**:

| Population | Games | Brier |
|---|---:|---:|
| Men | 63 | 0.1445997537 |
| Women | 63 | 0.0966919150 |
| Combined | 126 | **0.1206458343** |

The late/post-competition submission score is **0.1206458**.

## Strongest reconstructed experimental frontier

The strongest current post-competition reconstruction scores:

- combined: **0.1067095543**
- men: **0.1366807914**
- women: **0.0767383172**
- evaluation population: **63 men + 63 women = 126 games**
- lifecycle: **EXPERIMENTAL**
- submitted: **no**
- promoted: **no**

This result comes from the reconstructed women branch, independently rebuilt ranking/reference components, qualified original-source first-round information, and a fixed source-composition policy.

It remains research evidence because its upstream historical promotion requirements were not all satisfied and 2026 has been repeatedly inspected.

## Native women numerical reproduction

The rebuilt source-equivalent women pipeline:

- generated all **65,703** pairwise target probabilities;
- matched the archived reference within **1e-4** for every row;
- had maximum absolute difference of roughly **4.2e-05**;
- had mean absolute difference of roughly **2.35e-08**;
- matched all 15 archived member training-row counts and best-iteration receipts;
- scored **0.0767383172 Brier** on the 63 scored women's games.

## Men's reproduction status

Verified:

- all **66 core members** match archived best iterations and same-input predictions at numerical precision;
- all **66 margin members** match archived best iterations and calibration slopes, with only negligible same-input prediction differences;
- all **31 auxiliary historical feature columns** were reconciled;
- the original margin-branch target contract was re-audited and uses raw final-score margin; an earlier overtime-normalized equivalence claim was withdrawn;
- AP semantics and historical activation boundaries were repaired.

The remaining uncertainty is concentrated in source and representation families rather than broad unexplained model drift.

## Complete historical men's control

The historical evaluation bank now covers **566 played main-bracket games across nine forecast seasons**.

The original implementation had excluded every equal-numbered-seed matchup, which removed legitimate later-round games. The repaired evaluation:

- reproduced all **558** previously saved control predictions;
- restored **8** legitimate omitted games;
- yields a complete **189-game 2023–2025 confirmation population**.

A matched training correction was also tested and rejected because it did not improve robustly enough across development and confirmation.

## Recent matched experiments

### Pair-exchange / mirrored training

A fixed mirrored-training primary improved the 2023–2025 confirmation Brier from **0.1812860970 to 0.1773597347**, improving all three confirmation seasons.

Development deteriorated from **0.1838583627 to 0.1846847370**, so the experiment failed its predeclared gate and did not proceed to target-year inference.

### Exact-date AP refresh

A broader exact-date AP primary improved confirmation from **0.1812860970 to 0.1792712182** but worsened development to **0.1865589852**.

The source reconstruction remains useful; the fixed model integration was rejected.

### Original publisher probability tables

Complete 68-team men's advancement-probability fields were independently recovered for both 2025 and 2026.

The fixed probability-blending policy was rejected after it failed to improve robustly. The source assets remain useful as dated, independently owned information rather than a promoted model component.

## Supplemental-source frontier

Current independently recreated / owned source families include Bart Torvik Time Machine, AP polling history, official-derived ratings, Massey ordinals, postseason-selection announcements, historical player boxscore infrastructure, partial market / BPI archives, and original publisher bracket probability tables for 2025 and 2026.

The project does not relabel owned substitutes as proprietary publisher metrics.

## Current research question

The next private study uses **strictly earlier-season held-out predictions for calibration**, separating base-model training from calibration selection.

This is staged as a new research question; no public performance result is claimed yet.

## Incoming-season boundary

A large part of the pipeline is season-parameterized, but the complete incoming-season chain is not called finished.

The final readiness test must execute:

**source acquisition → raw receipt preservation → mapping → chronology checks → feature generation → fresh training / inference → final candidate freeze → schema / hash / provenance validation**

without borrowing prepared feature artifacts.

Unavailable future observations remain WAITING_FOR_TARGET_DATA; values are never copied forward from a prior season.
