# 2027 readiness | prospective evaluation plan

The project now has a mature post-competition research stack, but the next stronger claim must come from **prospective, pre-outcome evidence**.

This document defines the public readiness contract without publishing the private competition implementation.

## 1. Preserve the accepted control and separate research tiers

Keep the accepted submitted control, reconstructed experimental forecasts, and historical replay artifacts as distinct lifecycle states.

For every retained artifact, preserve:

- model / system ID;
- source and data-lineage version;
- immutable prediction hash;
- evaluation population;
- lifecycle state;
- promotion decision;
- source-timing evidence.

Do not let a lower retrospective score silently replace an accepted champion.

## 2. Make season transition an executable contract

Audit every year-specific input route and assumption:

- team identities and aliases;
- conferences;
- rosters / transfers;
- seeds and tournament-selection metadata;
- rankings / ratings;
- player participation / availability;
- external-source publication timing;
- sample-submission / candidate schema.

Require incoming-season inputs to carry provenance and timing evidence.

A missing prerequisite should produce a clear `WAITING_FOR_TARGET_DATA` or source-blocked state rather than silently copying a previous season's value.

## 3. Exercise the full pipeline before outcomes

Use 2026 as a historical incoming-season rehearsal where practical.

The rehearsal should execute:

**source acquisition → raw receipt preservation → normalization → team mapping → chronology checks → feature construction → model training / inference → final composition → schema / hash / provenance validation → immutable candidate freeze**

The goal is to prove that the project can move from newly available data to a frozen candidate without depending on another competitor's prepared file.

## 4. Accumulate prospective source snapshots

When permitted sources become available, retain immutable snapshots before outcomes are known.

Each source record should preserve:

- original URL / provider identity;
- actual capture timestamp;
- publisher update timestamp when available;
- raw-body checksum;
- normalized-table checksum;
- mapping state;
- model eligibility state;
- quarantine reason.

Market, roster, ranking, and player information must remain distinct from postgame updates.

## 5. Predeclare the decision procedure

Before the tournament:

- freeze eligible model families;
- freeze development / confirmation periods;
- freeze the primary metric and exact aggregation;
- freeze promotion / rejection rules;
- freeze calibration / composition rules;
- freeze submission policy.

Changing the system after outcomes are observed creates a new retrospective experiment, not a revision of the original prospective forecast.

## 6. Rehearse operational failure paths

Before the deadline, test:

- missing source files;
- invalid IDs / aliases;
- corrupted checkpoints;
- partial source coverage;
- source timestamps after cutoff;
- interrupted acquisition;
- interrupted training;
- resume behavior;
- candidate schema;
- duplicate candidate hashes;
- submission-action failure.

A delivery failure should not trigger retraining of an already frozen candidate.

## 7. Keep public and private boundaries separate

The public repository should continue to publish:

- aggregate evaluation evidence;
- source-provenance state;
- reproduction status;
- negative-result conclusions;
- operational readiness contracts.

The private AWS workspace should retain:

- raw source archives;
- exact feature formulas;
- fitted models;
- candidate predictions;
- private thresholds / weights;
- source-specific identity logic;
- orchestration state.

## Readiness definition

The project should be called incoming-season ready only after the complete chain is demonstrated end to end on a historical incoming-season rehearsal and then applied prospectively to the actual 2027 source state.

Parameterized functions alone are not sufficient evidence.
