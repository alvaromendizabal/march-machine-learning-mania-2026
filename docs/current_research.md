# Current research boundary

## Current owned/recreated champion

The current **2027-ready owned/recreated champion** is **v26**, with a late/post-competition Kaggle Brier of **0.1206458**.

An independently reconstructed 126-game scorer reproduces the result at **0.1206458343253354**.

| Population | Games | Brier |
|---|---:|---:|
| Men | 63 | 0.1445997537 |
| Women | 63 | 0.0966919150 |
| Combined | 126 | 0.1206458343 |

Lower is better.

The research target remains **0.0900000**, a gap of **0.0306458343** from the current owned champion.

## Historical score context

Earlier post-competition research reached lower retrospective scores, including a 0.1033437 broader-data boundary and a 0.1027974 replay candidate. Those results remain useful historical evidence, but they are **not the current 2027 ownership boundary** because some external inputs were not independently recreated under the stricter source contract now used by the project.

This distinction prevents a lower historical number from being misrepresented as a repeatable 2027 system.

## What v26 adds

v26 combines:
- official competition data;
- independently recreated Bart Torvik Time Machine history;
- the clean owned baseline;
- a frozen reliability/disagreement gate selected before 2026 audit.

The Torvik reliability rule improved all three recent confirmation seasons before the final 2026 audit and was promoted without post-hoc 2026 tuning.

## Exact scorer

The exact 2026 scorer is now complete:
- 63/63 men's games;
- 63/63 women's games;
- 126/126 combined;
- exact submission-ID alignment;
- exact Brier reproduction of the v26 Kaggle score.

The scorer is downstream of policy selection. It is used only after a policy is frozen.

## Closed directions

The following representations were tested and rejected under frozen validation:
- broad owned internal-strength expansion;
- simple recent rotation/continuity;
- richer boxscore player-impact/availability;
- dynamic opponent-adjusted offense/defense/pace/margin;
- repeated broad blending among highly correlated weak branches.

Historical ESPN BPI and timestamped market reconstruction were source/timing blocked rather than converted into leakage-prone inputs.

## Current open frontier

The next material external-data question is independently reconstructed NCAA NET/WNCAA NET history. The goal is to own the source, preserve timing/provenance, and test whether official NET/WAB/quadrant information is complementary to v26.

No promotion is allowed from source availability alone. A source must also pass frozen historical transfer.
