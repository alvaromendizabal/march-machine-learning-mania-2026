# Current research boundary

## Metric contract

Primary metric: **Brier score** on NCAA tournament win probabilities. Lower is better.

The project keeps three evaluation concepts separate:

1. historical development / confirmation;
2. the exact 126-game 2026 audit;
3. externally submitted scores.

A lower retrospective 2026 score does not automatically become the accepted champion.

## Accepted system

The accepted owned/recreated control remains **v26**:

| Population | Games | Brier |
|---|---:|---:|
| Men | 63 | 0.1445997537 |
| Women | 63 | 0.0966919150 |
| Combined | 126 | **0.1206458343** |

The late/post-competition submission score is **0.1206458**.

v26 combines official competition data, independently recreated Bart Torvik history, and a frozen reliability/disagreement policy that improved all three recent confirmation seasons before the final audit.

## Strongest reconstructed experimental frontier

The strongest current post-competition reconstruction scores:

- combined: **0.1069362213**
- men: **0.1371341254**
- women: **0.0767383172**
- evaluation population: **63 men + 63 women = 126 games**
- lifecycle: **EXPERIMENTAL**
- submitted: **no**
- promoted: **no**

The lower score is retained as research evidence, not promoted as the accepted system, because its parent lineage did not pass every historical transfer gate and repeated 2026 analysis has consumed the tournament as development information.

That distinction is intentional: the repository separates *what can be reconstructed retrospectively* from *what has earned prospective trust*.

## Native women numerical reproduction

The clearest reconstruction success is the women’s native branch.

The rebuilt source-equivalent pipeline:

- generated all **65,703** pairwise women probabilities;
- matched the archived reference within **1e-4** for every row;
- had maximum absolute prediction difference of roughly **4.2e-05**;
- had mean absolute difference of roughly **2.35e-08**;
- matched all 15 archived member training-row counts and best-iteration receipts;
- scored **0.0767383172 Brier** on the 63 scored women’s games.

This branch uses owned / independently recreated inputs and demonstrates that strong historical behavior can be recovered without copying another competitor's prepared feature table.

## Men’s reproduction status

The historical men reconstruction has also progressed materially.

Verified at the audited grain:

- all four native historical core ingredients match across **7,981 team-season rows** within numerical tolerance;
- all **31 auxiliary margin features** match across **2,898 directed historical rows**;
- the overtime-normalized margin target matches the archived definition;
- AP edition semantics and historical activation rules were repaired.

Remaining target-season differences are tied to still-incomplete source families such as exact historical availability/player-value information and corrected target postseason-membership identities.

## Supplemental-source frontier

Current independently recreated / owned source families include:

- Bart Torvik Time Machine;
- AP polling history;
- official-derived Elo / SRS / Colley / Bradley-Terry / efficiency / pace / recency;
- Massey ordinals;
- original postseason-selection announcements;
- historical player boxscore infrastructure;
- partial original-source market history;
- partial archived ESPN BPI / pregame prediction history.

The project does not relabel substitutes as proprietary publisher metrics.

## Closed or rejected directions

Correctly executed negative experiments include:

- broad owned internal-strength expansion;
- simple rotation / continuity;
- richer boxscore player-impact proxies;
- dynamic opponent-adjusted offense / defense / pace / margin;
- several broad market transformations;
- repeated blending of highly correlated weaker branches.

These results remain part of the scientific record because they reduce repeated spending on low-information directions.

## 2027 boundary

A large part of the pipeline is season-parameterized, but the complete incoming-season chain is not yet called finished.

The final readiness test must execute:

**source acquisition → raw receipt preservation → mapping → chronology checks → feature generation → fresh training/inference → final candidate freeze → schema/hash/provenance validation**

using an incoming-season contract without borrowing prepared feature artifacts.

Missing future observations remain `WAITING_FOR_TARGET_DATA`; 2026 values are never renamed as 2027 data.
