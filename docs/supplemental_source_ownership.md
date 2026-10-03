# Supplemental-source ownership and 2027 readiness

This repository publishes the **state and coverage of supplemental-data ownership**, not the private raw source bodies or competition implementation.

"Owned" means the project independently acquires or reconstructs relevant observations from official/original sources, preserves provenance and timing evidence, and does not depend on another competitor's prepared feature CSV.

## Active modeling scope

- Men: modern competition era, generally 2003+
- Women: modern competition era, generally 2010+
- Narrower source families begin later when the underlying publisher or archive did not exist earlier

## Current ownership matrix

| Source family | Ownership state | Current coverage / evidence | Research state |
|---|---|---|---|
| Official competition data | Official | complete active competition scope | Primary training / validation source |
| Massey ordinals | Official-derived | 7,992 / 7,993 men team-seasons; 100% tournament-team coverage | Active |
| Bart Torvik Time Machine | Independently recreated | 15 men's tournament seasons; 5,268 / 5,304 team-season rows; 1,016 / 1,020 tournament-team rows | Promoted source family |
| AP polling | Independently recreated | 117 rank-complete editions; 95 vote-complete editions | Source validated; several model uses rejected |
| Elo / SRS / Colley / Bradley-Terry | Owned derived | competition-era official-result history | Active / representation-dependent |
| Tournament selection announcements | Independently recreated | 32 NIT + 32 WBIT + 48 WNIT target-season facts | Active source facts |
| ESPN player boxscores | Independently collected | >1.2M mapped pre-cutoff men's player-game rows across 11 seasons | Two scalar proxy representations rejected; raw infrastructure retained |
| Historical championship / first-round market observations | Independently recreated partial | 133 target-season championship-team observations; 57 possible first-round pairs | Useful target-season evidence; insufficient broad historical training coverage |
| Archived ESPN BPI / pregame predictions | Independently recreated partial | archived men's rating/probability vintages plus 16 qualified target-season pregame predictions | Active reconstruction frontier; broad historical coverage incomplete |
| WNCAA NET | Independently recreated partial | multiple women seasons retained; important archive gaps remain | Partial / source-limited |
| NCAA NET men | Partial / incomplete | not yet comprehensive across the clean historical window | Open source gap |
| KenPom | Not independently owned exact | no publisher-exact historical bank | Authorized-only |
| EvanMiya / BPR | Not independently owned exact | no publisher-exact historical bank | Open proprietary gap |
| Historical injury / availability snapshots | Not independently owned exact | participation proxies exist, not medical history | Open / prospective capture preferred |

Machine-readable version: [portfolio/supplemental_source_status_2027.csv](../portfolio/supplemental_source_status_2027.csv).

## Timing standard

Every reconstructed source is evaluated on independent questions:

1. **Raw-source integrity** — can the original bytes/object and checksum be preserved?
2. **Capture chronology** — was the archived/captured observation available before the relevant forecasting cutoff?
3. **Publication semantics** — does the source timestamp or page state actually represent the intended pre-tournament information?
4. **Entity mapping** — does the observation map unambiguously to the official team/player identity?
5. **Model eligibility** — can it enter the declared feature contract without future information?
6. **Predictive transfer** — does a frozen historical policy improve the official metric?

Passing one does not imply passing the others.

## Notable reconstruction results

### Bart Torvik

Historical Time Machine pages were independently collected, mapped to official TeamIDs, stored with source receipts, and evaluated under historical timing rules.

The raw signal was useful but unstable as a broad correction. A reliability/disagreement policy transferred across all three recent confirmation seasons and became part of v26.

### AP polling

The AP archive is now broader than the minimal public-solution use case and includes multiple historical anchor editions plus trajectory metadata.

The reconstruction also uncovered several semantic defects that matter in small-data modeling:

- poll edition numbering;
- current rank versus previous rank;
- rank-complete versus vote-complete observations;
- historical feature-activation boundaries.

The source remains valuable even though several AP-driven model branches did not earn promotion.

### Original-source markets

The project independently recovered target-season championship and possible first-round observations from original historical market responses.

These observations are useful as a source-reconstruction asset, but their limited multi-season coverage prevents the project from presenting them as a broad historical training bank.

Several fixed target-season market transformations were tested and rejected; the source infrastructure remains available for prospective collection.

### Archived ESPN BPI / pregame predictions

The initial historical BPI effort was source/timing blocked. Later archive work recovered genuine original ESPN pages and partial numerical observations.

Current public-safe evidence includes:

- multiple archived men's rating/probability page vintages;
- strict snapshot separation rather than merging incompatible update dates;
- a target-day archived pregame page containing 16 numerical men's BPI matchup forecasts captured before the operational cutoff.

This is **partial recovery**, not a claim of comprehensive historical BPI ownership.

### Player / availability research

Historical pre-cutoff ESPN boxscores were collected and mapped into a large raw player-game bank.

Two owned scalar/continuity representations were tested and rejected. The project therefore retains the raw source infrastructure while avoiding false claims that those features are equivalent to proprietary player-value systems or medical injury data.

## 2027 contract

For future supplemental collection:

- preserve the raw response/object;
- retain original source URL and provider identity;
- retain actual capture timestamp;
- retain source publication/update timestamp when available;
- hash raw and normalized artifacts;
- retain mapping state and ambiguity decisions;
- retain model eligibility state;
- retain quarantine reason;
- leave unavailable future observations as `WAITING_FOR_TARGET_DATA`;
- never copy 2026 values into 2027;
- never turn post-cutoff data into synthetic pre-cutoff history;
- never relabel an owned proxy as an exact proprietary publisher metric.

The project is considered fully incoming-season ready only after the complete acquisition → mapping → feature → fresh train/infer → candidate-freeze chain is exercised end to end.
