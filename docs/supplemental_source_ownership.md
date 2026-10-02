# Supplemental-source ownership and 2027 readiness

This repository publishes the **state** of supplemental data ownership, not the private data itself.

"Owned" here means the pipeline independently acquires or reconstructs the relevant public observations from official/original sources, preserving provenance and timing, rather than relying on another competitor's prepared feature CSV.

## Active modeling scope

- Men: modern competition era, generally 2003+
- Women: modern competition era, generally 2010+
- Narrower sources start later when the publisher/source did not exist earlier

## Ownership matrix

| Source family | Ownership state | Research state | Public boundary |
|---|---|---|---|
| Official competition data | Official | Active | Primary training/validation source |
| AP polling | Independently recreated | Tested; model branch rejected | Source remains legitimate |
| Bart Torvik Time Machine | Independently recreated | **Promoted in v26** | Current strongest supplemental source |
| Massey ordinals | Official-derived | Active | Chronology-safe legal editions |
| Elo / SRS / Colley / Bradley-Terry | Owned derived | Active / partially rejected | Derived from official results |
| ESPN player boxscores | Independently collected | Two tested representations rejected | Retained for prospective 2027 capture |
| WNCAA NET | Independently recreated partial | Open source gap | 2021–2024 retained; 2025 missing; 2026 requires durable canonicalization |
| NCAA NET men | Not yet comprehensively owned | Open gap | Next source frontier |
| ESPN historical season BPI | Timing/source blocked | Blocked | Prospective 2027 only |
| Historical timestamped market odds | Source blocked | Blocked | Prospective 2027 only |
| KenPom | Not independently owned exact | Authorized-only | No fabricated parity |
| EvanMiya / BPR | Not independently owned exact | Open proprietary gap | Owned substitutes are named separately |
| Historical injury snapshots | Not independently owned | Open gap | Prospective 2027 capture preferred |

Machine-readable version: [portfolio/supplemental_source_status_2027.csv](../portfolio/supplemental_source_status_2027.csv).

## Timing standard

Each reconstructed source is evaluated on four independent questions:

1. **Capture integrity** — can the source bytes and normalized representation be reproduced?
2. **Historical timing** — did the observation exist before the relevant tournament/prediction cutoff?
3. **Model eligibility** — does the row map cleanly to the competition entity/time contract?
4. **Predictive transfer** — does a frozen historical policy improve the official metric?

Passing one does not imply passing the others.

## Examples

### Bart Torvik
The project reconstructed historical Time Machine observations from the upstream source, mapped them to official TeamIDs, preserved receipts, and then tested them historically. The raw signal was useful but unstable; a disagreement/reliability gate transferred across recent seasons and became the current champion.

### ESPN BPI
Historical source material was explored, but the defensible pre-cutoff archive path was not adequate. The project preserved the collector idea for prospective 2027 capture instead of using final/postseason values retrospectively.

### Historical markets
Event discovery and provider-level odds mechanics were reconstructed, but timestamped pre-deadline history was not available at sufficient coverage. The historical branch was closed rather than backfilled with closing lines.

### Player availability
Pre-cutoff ESPN boxscores were captured and tested through two owned representations. Neither transferred strongly enough to promote. The raw infrastructure remains useful for prospectively timestamped 2027 participation/availability.

## 2027 contract

For future source collection:
- retain the raw response/object;
- retain source URL and provider identity;
- retain actual capture timestamp;
- retain source publication timestamp when available;
- hash raw and normalized artifacts;
- retain mapping state;
- retain model eligibility state;
- retain quarantine reason;
- leave unavailable future sources as WAITING_FOR_TARGET_DATA;
- never copy 2026 values into 2027;
- never convert post-cutoff data into synthetic pre-cutoff history.
