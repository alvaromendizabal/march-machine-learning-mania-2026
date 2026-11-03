# From verified bytes to eligible features

**V020 follow-up · reviewed November 3, 2026 · independent March Machine Learning Mania**

Historical features require exact source identity, correct game mapping and evidence that observations were available before prediction. A byte-perfect artifact can still fail those requirements.

## Two completed diagnostics, no new feature admission

V020 completed the two narrowly registered follow-up inspections. It established the previously blocked file's actual format and inspected every row of the previously schema-only Parquet object. This is a completed diagnostic result, **not a successful model experiment or source-debt closure**.

| Target | Complete observation | What it does not establish |
|---|---|---|
| Earlier parser-blocked payload | Comma-delimited CSV; **2,283 records**, **96 columns**, **15,982 physical lines** | Records are not a proven count of unique physical games; format does not prove source or sport identity |
| Earlier schema-only Parquet | **1,629 rows**, **83 columns**, **13 bounded batches**; every column inspected | Reading rows does not establish feature availability before a historical prediction |
| Parquet season field | **2027** for all 1,629 rows | A season label is a candidate population, not an admitted training cohort |
| Parquet source-URL field | **Null in all 1,629 rows**; no provider-host or sport-token candidates | No URL-based provider or sport identity was established |
| Four presence fields | `game_json`, `PBP`, `team_box`, `player_box` are **boolean typed** | They are not the underlying JSON, play-by-play or box-score bodies; truth-value counts were not reported |
| Request crosswalk | All **3,625** original request rows retained; **zero** exact new candidates | No source debt or request debt closed |

Stored event-year histograms deliberately preserve their original representation. `date` and `start_date` each have 636 records in 2026 and 993 in 2027; `game_date_time` and `game_date` each have 637 in 2026 and 992 in 2027. These are **calendar years as stored, without timezone normalization**. The one-record difference is not independently proven to be timezone equivalence. Aware event timestamps and date-only values are not historical feature-availability witnesses.

The original **67 object debts / 3,573 unresolved requests remain open**. Seven tiny archive text members also remain semantically uninspected. There are **zero new historical feature admissions, private model fits, or champion changes**. The 65 other original locations and saved metadata snapshot were not re-read.

## Preserved V019 history: PARTIAL

V019 remains **PARTIAL**. Its history is not rewritten to success by a later repair. All **67 registered body locations** passed complete byte and SHA verification. They represent **54 distinct content identities**, not 67 distinct scientific inputs. Successful receipts survived the partial source-analysis stage. The observations below describe V019 as executed, before V020's follow-up.

| Layer | Observation | Limit |
|---|---:|---|
| Exact body verification | 67 / 67 | Custody, not sport identity or eligibility |
| Unique container analyses completed | 53 | Includes 12 archives and one schema-only Parquet inspection |
| Fully traversed unique JSON containers | 45 | 40 direct JSON containers plus five all-JSON archives |
| Archive members | 45 hashed; 38 JSON traversed; seven tiny text members uninspected | Byte checks are not semantic inspection |
| Then-blocked payload | 4,289,729 bytes; `JSON_SCALAR_SIZE_BOUND` | Format was unestablished in V019; V020 subsequently established CSV grammar |
| Parquet at that stage | 1,629 rows identified from metadata | V019 was schema-only; V020 subsequently inspected all row values |
| Saved metadata snapshot | 90,886 records and receipts | Saved replay, not a fresh cloud census |
| Requests | 3,625 = 3,573 unresolved + 52 prior duplicates | Zero exact matches and debt closures |
| New clock witnesses / model fits | 0 / 0 | No feature admissions or promotion |

A format candidate or timestamp-shaped value is not a proven request join or admissible pregame observation. The schema-2 public record retains every V019 parent field and the separately scoped V018 replay, then adds `latest_followup` for V020.

## Measured resources

| Measurement | V019 original audit | V020 two-target follow-up |
|---|---:|---:|
| S3 HEAD / GET calls | 69 / 69 | 2 / 2 |
| Identity-service calls | 1 | 1 |
| Observed SDK retries | 0 | 0 |
| Verified stored bytes | 187,256,496, including saved metadata | 4,423,048, exactly two bodies |
| Registered source-body bytes | 148,994,102, subset of the total | 4,423,048 |
| Source-audit-only time | 69.363149288 seconds | 0.857078101 seconds |
| Body time before packaging | 78.816266397 seconds | 11.079313356 seconds |
| Return packaging time | 0.606110172 seconds | 0.616731249 seconds |
| Total including packaging | 79.509194911 seconds | 11.786151602 seconds |
| Peak process RSS before packaging | 882,536 KiB | 1,154,084 KiB |
| CPU visibility | Four logical / affinity CPUs | Four logical / affinity CPUs |
| Free disk before packaging | 1,406,443,520 bytes | 1,245,544,448 bytes |
| Free disk after packaging | 1,327,349,760 bytes | 1,165,094,912 bytes |
| Provider calls / purchases / cloud writes / listings | Zero | Zero |
| Monetary cost | **UNKNOWN**, not measured | **UNKNOWN**, not measured |

V020 observed five HTTP attempts: one identity-service call, two HEADs and two complete conditional GETs. The two bodies were read sequentially; four visible CPUs do not mean four source workers. No raw local mirror was retained. These are per-execution scopes, not cumulative acquisition totals.

Packaging time, final total and final free disk come from the matching post-write live log, not the earlier sealed archive. Source-audit time excludes parent authentication and packaging. Low free disk motivates remote bulk storage; it does not authorize deletion of research history. Cost is unknown, not zero.

## The matched study is not a new holdout

V018 completed a zero-fit replay on **925 identical targets**, with **218 common feature-bearing games** and **707 control fallbacks**. Development has 523 games; the already-exposed later window has 402. Public arm labels omit private configurations.

| Frozen arm | Brier, all 925 | Log loss, all 925 |
|---|---:|---:|
| Accepted control | 0.16940939326558535 | 0.504349701696621 |
| Reference arm | 0.16762873051435492 | 0.4972804843645902 |
| Candidate A | 0.16758810464578947 | 0.4972281959983217 |
| Candidate B | 0.16764848874668442 | 0.4973564428498034 |

All paired descriptive intervals from **1,024 season-block resamples, seed 10010**, include zero. Both candidate families passed **zero of five** development screens. **Six of 44 First Four games** have features, below the 20-game reporting threshold. Control remains selected. Public aggregates cannot reproduce paired intervals independently without withheld per-game rows.

The historical 126-game retrospective and separately recorded Kaggle submission are different populations. No newly verified Brier below 0.102, blind holdout, competition victory or future profitability is established.

## Remaining source coverage

- Existing 60-minute men's market history: **6,765 edges**, seasons **2021–2025** only. Men's 2018/2019 and all women's corresponding coverage remain zero.
- CollegeBasketballData: **15,028 men's exact game joins**, **15,027 paired-stat games**, **14,704 nonempty-line games**, but no newly admitted historical pregame clock witnesses.
- Provider completeness and freshness cannot be claimed from this audit.

## Next decision: no repeated source read

Both registered source diagnostics are complete. Another GET of the same bytes is not justified by the result. The next bounded task is **offline evidence qualification and frozen public-model delivery parity**: retain exact source and request identities, preserve unknown eligibility masks, check frozen inference contracts, and keep engineering verification separate from scientific evidence. This requires no new source, provider or cloud read and no new private scientific fit.

Source identity, exact request/game linkage and pre-cutoff availability remain prerequisites. All-null URLs and 2027 season candidates do not repair older market-clock gaps. Shared storage does not establish sport identity; football is not basketball.

Only evidence-proven inputs can enter a later preregistered season-forward batch: frozen cutoff, train-only transforms and encodings, earlier-development selection and labeled exposed-later monitoring. Completed model fits are not repeated to repair source interpretation or packaging.

## Reproduction and disclosure

[source_readiness.json](../portfolio/source_readiness.json) feeds an [allowlist validator](../tools/source_readiness.py) and [adversarial tests](../tools/test_source_readiness.py). Unknown fields fail at every nesting level, including year histograms. Checks reject altered frozen metrics, invented closure, admissions or fits, misreported columns, implicit timezone conversion, private predictions, boolean-as-count errors and scope changes. These validate the published aggregate contract, not original provider bodies. Private cloud locations, bodies, competitive recipes and row-level forecasts stay withheld.

[Architecture](architecture.md) · [Model card](model_card.md) · [Public training](temporal_model_demo.md) · [Historical V351 comparison](owner_replay.md)
