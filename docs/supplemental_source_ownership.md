> **Ownership clarification, October 8, 2026:** historical player archive counts below include third-party-derived NCAA records. They are not newly certified original ESPN data. The exact v81 cache bank is awaiting a corrected audit, and the v99 original ESPN pilot is delivered but has no returned owner result at this snapshot. See [current research](current_research.md).

# Supplemental-source ownership and incoming-season readiness

This repository publishes the **state and coverage of supplemental-data ownership**, not private raw source bodies or the competition implementation.

"Owned" means the project independently acquires or reconstructs relevant observations from official / original sources, preserves provenance and timing evidence, and does not depend on another competitor's prepared feature CSV.

## Active modeling scope

- Men: modern competition era, generally 2003+
- Women: modern competition era, generally 2010+
- Narrower source families begin later when the publisher or archive did not exist earlier

## Current ownership matrix

| Source family | Ownership state | Current coverage / evidence | Research state |
|---|---|---|---|
| Official competition data | Official | raw census: 42 men's seasons / 13,753 team-seasons and 29 women's seasons / 9,851 team-seasons | Primary training / validation source; v76 raw-to-feature replay verified |
| Massey ordinals | Official-derived | 7,992 / 7,993 men team-seasons; complete tournament-team coverage | Active |
| Bart Torvik Time Machine | Independently recreated | 15 men's tournament seasons; 5,268 / 5,304 team-season rows; 1,016 / 1,020 tournament-team rows | Promoted source family |
| AP polling | Independently recreated | 117 rank-complete editions; 95 vote-complete editions | Source validated; several model uses rejected |
| Elo / SRS / Colley / Bradley-Terry | Owned derived | competition-era official-result history | Active / representation-dependent |
| Tournament selection announcements | Independently recreated | 32 NIT + 32 WBIT + 48 WNIT target-season facts | Active source facts |
| ESPN player boxscores | Independently collected | >1.2M mapped pre-cutoff men's player-game rows in the broader archive; later qualified modeling bank retained 1,036,477 rows with 541 / 566 eligible historical matchups | Several proxy / role representations rejected; raw and identity infrastructure retained |
| Historical championship / first-round market observations | Independently recreated partial | 133 target-season championship-team observations; 57 possible first-round pairs | Useful target-season evidence; insufficient broad historical training coverage |
| Archived ESPN BPI / pregame predictions | Independently recreated partial | men's archived rating / probability vintages plus 16 qualified target-season pregame predictions | Active reconstruction frontier; broad historical / women's coverage incomplete |
| Original publisher bracket probability tables | Independently recreated partial | complete 68-team men's fields for 2025 and 2026 | Source validated; fixed blend experiments rejected |
| WNCAA NET | Independently recreated partial | multiple women seasons retained; important archive gaps remain | Partial / source-limited |
| NCAA NET men | Partial / incomplete | not comprehensive across clean historical window | Open source gap |
| KenPom | Not independently owned exact | no publisher-exact historical bank | Authorized-only |
| EvanMiya / BPR | Not independently owned exact | no publisher-exact historical bank | Open proprietary gap |
| Historical injury / availability snapshots | Not independently owned exact | participation proxies exist, not medical history | Open / prospective capture preferred |
| Reconstructed ten-player matchup stints | Independently downloaded reconstruction, not original event-state history | three late historical files were audited; interval semantics were incompatible with the first modeling contract | Quarantined from modeling pending original event/substitution reconstruction |

Machine-readable version: [portfolio/supplemental_source_status_2027.csv](../portfolio/supplemental_source_status_2027.csv).

## Timing standard

Every reconstructed source is evaluated on independent questions:

1. **Raw-source integrity** — can the original bytes / object and checksum be preserved?
2. **Capture chronology** — was the observation available before the relevant forecasting cutoff?
3. **Publication semantics** — does the source timestamp / page state represent the intended pre-tournament information?
4. **Entity mapping** — does the observation map unambiguously to the official identity?
5. **Model eligibility** — can it enter the declared feature contract without future information?
6. **Predictive transfer** — does a frozen historical policy improve the official metric?

Passing one does not imply passing the others.

## Official raw-game foundation

The latest source milestone independently rebuilds public-safe descriptive features from official compact and detailed game records rather than prepared feature tables.

Current evidence includes:

- 13,753 men’s team-season rows and 9,851 women’s team-season rows in the raw census;
- 566 / 566 historical men’s matchup identities with both teams present;
- 566 / 566 complete performance and schedule feature pairs;
- 554 / 566 complete temporal / venue pairs, with missingness retained explicitly;
- separate-process raw-to-feature replay for both genders;
- a 2026-as-incoming feature rehearsal;
- chronology poisoning and season-prefix invariance checks.

This is a source/feature reproducibility result, not a forecasting promotion.

## Notable reconstruction results

### Bart Torvik

Historical Time Machine pages were independently collected, mapped to official TeamIDs, stored with source receipts, and evaluated under historical timing rules.

A later source-receipt audit rebuilt the incumbent snapshot from pinned season files and showed that the changed consolidated aggregate was numerically equivalent at model-input precision. This replaced a fragile compressed-file identity assumption with receipt-based verification.

### AP polling

The AP archive includes exact selected editions and richer rank / ballot context.

The reconstruction uncovered important semantic defects: poll-edition numbering, current rank versus previous rank, rank-complete versus ballot-complete observations, historical feature-activation boundaries, and nearest-edition versus exact-anchor behavior.

The source remains valuable even though multiple AP-driven model policies were rejected.

### Original markets and BPI

The project independently recovered target-season historical market responses and archived ESPN pages.

Public-safe evidence includes 133 championship-team observations, 57 possible first-round pair observations, multiple archived men's rating / probability vintages, and 16 qualified target-season pregame BPI matchup forecasts.

Coverage remains too narrow to describe this as a general historical supervised-data bank.

### Original publisher bracket probabilities

Complete 68-team men's probability fields were recovered for 2025 and 2026 from dated original source material.

The source reconstruction passed structural and probability-consistency checks. The fixed forecasting blends did not earn promotion, so the source is retained without overstating its model value.

### Player / availability research

Historical pre-cutoff ESPN boxscores were collected and mapped into a large raw player-game bank.

Two owned scalar / continuity representations were tested and rejected. The project therefore keeps the raw infrastructure while avoiding claims that those features equal proprietary player-value systems or medical injury data.

## Incoming-season contract

For future supplemental collection:

- preserve the raw response / object;
- retain original source URL and provider identity;
- retain actual capture timestamp;
- retain source publication / update timestamp when available;
- hash raw and normalized artifacts;
- retain mapping state and ambiguity decisions;
- retain model eligibility state;
- retain quarantine reason;
- leave unavailable future observations as WAITING_FOR_TARGET_DATA;
- never copy prior-season values into the incoming season;
- never turn post-cutoff data into synthetic pre-cutoff history;
- never relabel an owned proxy as an exact proprietary publisher metric.

The project is considered fully incoming-season ready only after the complete acquisition → mapping → feature → fresh train/infer → immutable-candidate chain is exercised end to end.
