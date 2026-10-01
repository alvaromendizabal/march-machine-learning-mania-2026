# Supplemental-source ownership and 2027 readiness

This document summarizes which external inputs used or discussed by leading public March Mania solutions are independently reconstructed in the private research system.

It is an **ownership/provenance matrix**, not a public dump of the source data. Raw third-party observations, exact private feature formulas, candidate predictions, credentials, and source-specific identity maps are intentionally excluded.

## Active historical scope

New reconstruction/modeling is bounded to:

- **Men: 2003+**
- **Women: 2010+**

Narrower sources may begin later. Earlier cached observations can remain as inert provenance but are not an active modeling target.

## Current status

| Source family | State | Public boundary |
|---|---|---|
| AP polling | Owned | Weekly observations mapped independently; pre-tournament summaries/trajectory available |
| Dated BartTorvik | Owned | 9,652 dated observations across 27 editions with explicit cutoff eligibility |
| ESPN game-specific predictor/BPI | Owned partial | Useful game context captured; retrospective original publication timing is not always independently certified |
| Multi-provider market context | Owned substitute | Provider-level no-vig summaries; private raw quotes not published |
| Venue/context | Owned | Observed context only; not relabeled as publisher-adjusted venue ratings |
| Coach performance | Owned analogue | Past-only coach-history signal; exact external PASE parity not claimed |
| Player value/availability | Owned proxy | Derived from player-game/participation history; not relabeled BPR or injury diagnosis |
| Season-level ESPN BPI | Timing blocked historically | Historical endpoint state was updated after tournament cutoff; retained only as archive/prospective reference |
| WNCAA NET | Open gap | Independent point-in-time reconstruction remains a priority |
| Exact KenPom | Authorized-only | No fabricated parity |
| Exact EvanMiya/BPR | Open proprietary gap | Owned substitutes exist but are named separately |
| Historical medical injury context | Open gap | 2027 prospective capture preferred to retrospective relabeling |

Machine-readable version: [portfolio/supplemental_source_ownership.csv](../portfolio/supplemental_source_ownership.csv).

## What "owned" means here

Owned does **not** mean ownership of a third party's intellectual property. It means the research pipeline can independently acquire/normalize the relevant public observations or reconstruct a separately named analogue without relying on another competitor's prepared feature CSV.

## Timing standard

The project keeps four ideas separate:

1. **capture integrity** — bytes/checksums/receipts are stable;
2. **forecast cutoff eligibility** — an observation is dated early enough to enter the model;
3. **original historical publication proof** — evidence the historical observation was actually published before that old forecast;
4. **predictive transfer** — a frozen model rule improves development and confirmation under its declared protocol.

A source can pass integrity and fail timing. A source can pass timing and fail predictive transfer.

## 2027 prospective contract

For future data, the goal is stronger provenance than retrospective reconstruction:

- capture raw source responses before transformation;
- store real capture timestamps and checksums;
- preserve source IDs and mapping status;
- separate acquisition from feature eligibility;
- leave unpublished sources in **WAITING_FOR_TARGET_DATA**;
- never copy 2026 values into 2027 as placeholders;
- promote a source only after both engineering and historical/prospective validation gates pass.

The highest-value remaining data work is women-specific external rating parity and prospectively captured roster/availability context.
