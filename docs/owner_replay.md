# Reuse the work. Retain the scientific decision.

**Latest inspected owner execution: V347, October 29, 2026.** Research, science and
lineage completed. Overall status is **PARTIAL** because owned market-source
reconciliation remains incomplete. The [public aggregate record](../portfolio/owner_replay.json)
is deliberately narrower than the private execution evidence.

This is useful engineering evidence even without a new winning model: completed
states were verified and reused, the accepted model survived a negative comparison,
and the return exposed a measurable storage defect to repair.

## Inspect it without credentials

```bash
python tools/review_project.py
```

Open `outputs/review/index.html`. Eleven checks cover the public examples, aggregate
contracts, actual demo controls and deterministic packaging. For just this record:

```bash
python tools/owner_replay.py --check
python -m unittest discover -s tools -p 'test_owner_replay.py' -v
```

These commands use the Python standard library. The complete reviewer also uses
Node for the existing JavaScript demo tests. The [executed engineering notebook](../portfolio/engineering_review.ipynb)
preserves the latest score table and three historical interactive figures with PNG
fallbacks. No private model is fitted or provider queried by this public review.

## What actually ran

| Workstream | State | Observed seconds | Verified result |
| - | - | -: | - |
| Research replay | COMPLETE | 5.159 | 66 fitted operations reused, zero new; 925 matched games across four arms |
| Broader science replay | COMPLETE | 19.119 | 236 fitted operations reused, zero new; its own 112-arm evaluation |
| Historical lineage | SUCCESS | 3.452 | 132 native receipts authenticated; native estimators were not executed |
| Market-source reconciliation | PARTIAL | 784.681 | More request relationships reconciled; no new selections or model admissions |

The two replay fit counts sum to **302**. This does not mean 302 new experiments,
newly acquired games or independent evaluations. The broader science and four-arm
research studies remain separate protocols.

Four return ZIPs total **452,756,526 bytes**. Each is below 150,000,000 bytes.
Their SHA-256 values match the owner execution log. All **5,358 per-part manifested
payload entries** passed exact size, SHA-256 and streaming CRC checks. The logical
index contains **5,351 files**, without missing or duplicate logical payloads.
The public record contains the part and evidence digests; the underlying private
archives are intentionally withheld.

The private audit recalculated all **24 research scorecards** from 3,700 returned
probability/target records with zero discrepancy. The public aggregate checker
validates the resulting accounting and decision. It cannot independently rerun
the withheld per-game calculation or authenticate original publishers.

## The comparison uses the same games

All four arms use the same 925 physical-game population. Development contains
**523 games in 2018, 2019, 2021 and 2022**. The already-exposed later window contains
**402 games in 2023–2025**. There are 3,700 probability records, not 3,700 independent
games. Lower Brier is better.

| Public arm label | Development Brier | Exposed later Brier | Selection consequence |
| - | -: | -: | - |
| Accepted control | 0.170697002771 | 0.167734219705 | Retained |
| Challenger A | 0.172341840795 | 0.163559005976 | Worse on development |
| Challenger B | 0.172312276859 | 0.164983755924 | Worse on development |
| Challenger C | 0.172026223480 | 0.164799768335 | Worse on development |

**Every challenger worsens the declared development Brier.** Lower later-window
loss does not authorize selecting a challenger after viewing that window.
The accepted control remains unchanged, no fresh holdout is claimed, and this run
created no new submission or prospective score.

Generic arm labels protect private composition rules. Per-game errors remain
private, so this publication does not manufacture paired confidence intervals,
significance claims or an exact competitive reproduction recipe. The historical
126-game scored result elsewhere in the repository is a different population;
directly comparing it to these 925 games would be invalid.

## Data readiness depends on the question

The carried source audit reports all **63,657 men's** and **61,298 women's** detailed
regular-season inputs required by the defined **2013–2025 study, excluding 2020**.
V347 confirms that the existing study replays successfully. It did not perform a
new full raw-table census.

| Broader evidence family | Have / required | Missing | Unit |
| - | -: | -: | - |
| Original women 2010–2012 missing-box queue | 143 / 221 | 78 | Game rows |
| Women venue court identity | 522 / 583 | 61 | Tournament game rows |
| Women strict home/neutral context | 367 / 583 | 216 | Tournament game rows |
| Exact player team-game joins | 13,622 / 14,228 | 606 | Team-game reconciliations |
| Seeded-team points features | 270 / 272 | 2 | Team-seasons |

These are **carried authenticated scope counts**, not newly recovered rows in
V347. The old women's gaps do not block the defined study. The broader inventory
and future 2027 inputs remain incomplete.

Market inventory contains **17,012,534 selections**, including 16,084,314 men's and
928,220 women's selections. A parser tags 15,259,764 as priced and pregame, but
**zero are admitted to model training**. Selections are quote/outcome records,
not distinct games or bracket-cutoff-certified features. There are **7,768 unknown
owned containers** in the source-closure proof. Of **3,625 candidate requests**, 52
are semantic duplicates and 3,573 remain unresolved; zero are eligible for paid
follow-up and no paid requests or credits were used.

The earlier [October 26 acquisition ledger](execution_evidence.md) and
[qualification frontier](qualification_frontier.md) retain their own definitions,
edition populations and source timing. This later summary lacks the row-level
transition evidence needed to rewrite those panels. Differences between those
dated scopes must not be disguised as a uniform completion percentage.

## The system finding: a compact return must exclude both aliases

The run preserved a **797,517,357-byte** prior return remotely, fully verified the
body and restoration manifest, then released **797,519,872 allocated local bytes**.
Logical file size and filesystem allocation differ. The final observed free disk
after new packaging was **1,229,553,664 bytes**, about 1.23 GB; this is a historical
measurement, not a statement about current free space.

The new review return included **4,960 derived parts totaling 437,817,964 bytes**,
or **96.70%** of its ZIP bytes. Its filter excluded export aliases but missed the
corresponding canonical derived parts. This is a concrete, testable packaging
defect. It identifies approximately 438 MB that need not be copied into every
review return. It does **not** establish that the canonical research data can be
deleted: 4,960 local parts and 6,429 remote parts represent different sets.

The appropriate next implementation should keep one authoritative active catalog,
retain unique scientific states, consolidate inactive byte-identical artifacts
only after verification, preserve a restoration route before releasing originals,
and omit both bulk path families from review returns. A complete filesystem census
and active-writer checks are needed before claiming an amount of additional space
reclaimed. The private runtime implementation is outside this public aggregate
publication; its next owner execution must verify the actual result.

## Runtime observations guide the next change

Core coordinator work took **997.79 seconds**. Recorded start through final return
status took **1,036.23 seconds**, including about 38.44 seconds of final packaging
and verification. The instance exposed **four effective CPUs**, roughly 16 GB RAM
and eight source workers. Mean accounted CPU use was **0.429 cores**, approximately
10.7% of available CPU capacity.

Most elapsed work occurred in odds metadata/inventory, request reconciliation,
derived-part offload and storage bootstrap; model replay took seconds. Progress
boundaries suggest approximately 130 seconds replaying the frozen legacy request
index and approximately 166 seconds in derived-part offload. Those are log-boundary
estimates, not a causal profiler attribution.

The next performance work should remove verified redundant warm scans, fingerprint
completed stages, overlap safe bounded reads, retain a disciplined catalog writer,
and avoid packaging duplicate bulk data. Low CPU alone does not prove every delay
is network-bound. No controlled concurrency benchmark establishes fastest-possible
execution, and timings across different workloads should not be presented as one.

## Publication and licensing boundary

This update adds aggregate values, evidence hashes, a standard-library validator,
failure tests, integrated review output and notebook interpretation. It publishes
no private cloud locations, credentials, raw bodies, licensed feeds, checkpoint
weights, per-game forecast rows, exact private blends or tuned configurations.

The repository's [publication checker](../tools/check_publication.py) checks the
exact changed Git blobs for recognized private artifacts and credential patterns.
The new aggregate schema also rejects unexpected nested fields and private locator
patterns. These are concrete controls with documented limits, not a claim that an
automated scan can recognize every possible secret or licensing issue.

[Current research](current_research.md) · [Engineering review](engineering_review.md)
· [Model card](model_card.md) · [Reproduction levels](reproduction_matrix.md)
