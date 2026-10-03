# Post-merge research log

This log summarizes the private AWS research program since the previous public owned-data release. It intentionally excludes private candidate bytes, raw source archives, fitted private models, exact correction weights/gates, credentials, and AWS-local implementation details.

## Public-safe milestone progression

| Milestone | Capability | Result |
|---|---|---|
| v22 | clean owned-only baseline | established the first strict owned/recreated baseline |
| v24 | independent Torvik Time Machine reconstruction | major data/provenance success |
| v26 | reliability-gated Torvik | **promoted; 0.1206458 submitted Brier** |
| v27–v30 | historical BPI / market reconstruction | source/timing limits identified without relaxing chronology |
| v32 | rotation / continuity | rejected |
| v33 | richer player-impact / availability proxy | rejected |
| v34 | dynamic O/D/pace/margin state | rejected; exact 126-game scorer completed |
| v35 | NCAA / WNCAA NET frontier | insufficient historical source coverage for promotion |
| v37–v38 | native women reconstruction attempts | representation differences isolated |
| v39 | complete women historical control repair | exact historical control parity and omitted equal-seed games restored |
| v40 | source recovery + men core/margin study | original championship source and postseason-selection facts recovered |
| v41 | market projection | negative; no promotion |
| v42 | owned historical information bank | 13,607 team-season rows and 2,330 historical matchup rows assembled |
| v43–v44 | AP source semantics / parser repair | 117 rank-complete and 95 vote-complete editions qualified |
| v45 | native women source-equivalent reproduction | **0.0767383172 women Brier; 65,703 pair probabilities reproduced within 1e-4** |
| v46 | native men core / margin reconstruction | 31 auxiliary feature columns reproduced; forecast not promoted |
| v47 | official-data reference + ranking corrections | reconstructed experimental combined Brier improved to **0.1087312** |
| v48 | AP ordinal + overtime-target corrections | historical core ingredients / target definitions matched at audited grain |
| v49 | final-layer study + qualified first-round comparator | strongest reconstructed experimental combined Brier reached **0.1069362** |
| v50 | fixed championship-ratio source substitution | negative; parent preserved |
| v51–v53 | archived ESPN BPI reconstruction | original archived pages recovered; broad historical coverage still incomplete |

## Accepted control versus reconstructed frontier

The accepted submitted owned-data control remains **v26 at 0.1206458 Brier**.

The strongest reconstructed post-competition research forecast is **0.1069362213 Brier** on the same 126-game audit population. It remains **experimental and unsubmitted** because its parent lineage did not satisfy every historical promotion gate.

That distinction is deliberate. The research program tracks two separate questions:

1. *Can the original information and model behavior be independently reconstructed?*
2. *Does the reconstructed system transfer strongly enough to earn prospective trust?*

A favorable answer to the first does not override a weak answer to the second.

## Exact scorer

The 2026 scorer is now complete and reusable downstream of policy freeze:

- 63 / 63 men's games;
- 63 / 63 women's games;
- 126 / 126 combined;
- exact submission-ID alignment;
- exact v26 Brier reproduction: **0.1206458343**.

## Native women reproduction

The most decisive source-equivalent reconstruction is the native women branch.

Verified:

- 65,703 all-pair target probabilities;
- every probability within 1e-4 of the archived reference;
- maximum difference about 4.2e-05;
- mean difference about 2.35e-08;
- 15 / 15 archived member training-row counts and best-iteration receipts matched;
- 2026 women Brier: **0.0767383172**.

This result established that independently owned source reconstruction can recover strong historical model behavior without copied feature artifacts.

## Men feature / target parity work

Subsequent reconstruction isolated multiple implementation mismatches rather than repeatedly retraining approximate versions.

At the audited grain:

- four native historical core ingredients match across 7,981 team-season rows;
- 31 auxiliary historical feature columns match across 2,898 directed rows;
- overtime-normalized margin supervision matches the archived definition;
- AP edition semantics and historical activation rules were repaired.

Remaining target-season differences are concentrated in incomplete external information families rather than unexplained broad feature drift.

## Source reconstruction milestones

### AP

The source bank now contains:

- 117 rank-complete editions;
- 95 vote-complete editions;
- repaired current/previous-rank semantics;
- explicit poll-edition identity;
- separate rank/vote completeness.

Several AP-driven model branches were correctly rejected, but the source itself remains reusable.

### Original markets

The project recovered target-season original historical market responses covering:

- 133 championship-team observations;
- 57 possible first-round pair observations.

These sources are retained as independently reconstructed context, but limited historical breadth prevents them from being presented as a general supervised training bank.

### ESPN BPI archive

Archive reconstruction progressed from an initially blocked source to partial original-source ownership.

The current bank includes:

- archived men's rating pages;
- multiple tournament-probability page vintages;
- snapshot-aware normalization;
- a pre-cutoff target-day page with 16 numerical men's pregame BPI matchup predictions.

Broad historical and women's coverage remain incomplete.

## Negative-result discipline

Several plausible directions were closed after correct execution:

- broad internal-strength expansion;
- recent rotation/continuity;
- richer boxscore player-impact proxies;
- dynamic opponent-adjusted O/D/pace/margin;
- broad correlated blends;
- bracket inversion of championship probabilities;
- fixed championship-ratio source substitution.

A negative experiment is recorded as successful execution with negative scientific evidence, not an engineering failure.

## Current research conclusion

The program has moved from "add more features" toward **source-equivalent information recovery plus prospective validation**.

The highest-value remaining gaps are:

- original-version availability / player-value information;
- broader defensible BPI history;
- remaining official NET history where point-in-time sources exist;
- a complete incoming-season rehearsal that exercises acquisition through candidate freeze.

The next experiments should close one of those capability gaps rather than retune already-rejected 2026 transformations.
