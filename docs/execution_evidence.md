# Evidence that survives the next execution

An acquisition pipeline needs to explain what changed, what was retained and what remains unknown. A total alone cannot distinguish new work from a replay, and a successful process does not establish complete scientific coverage.

The public [execution ledger](../portfolio/execution_history.json) preserves three published observations: an earlier partial acquisition, successful reconciliation, and expanded acquisition. The [current snapshot](../portfolio/acquisition_progress.json) must equal the ledger's final observation exactly. These are owner-execution aggregates; the underlying private return manifests were inspected separately.

## The measured transition

| Measure | v324 | v325 | v326 · latest inspected |
|---|---:|---:|---:|
| Recovered numerical boxes | 133/221 | 133/221 | 133/221 |
| Historically admitted recovered boxes | 0/133 | 0/133 | 0/133 |
| Qualified women's venue rows | 6/583 | 27/583 | 102/583 |
| Dated court assignments | 12 | 28 | 38 |
| Qualified home-context pods | 2 | 9 | 35 |
| Source-processing errors | 27 | 0 | 0 |
| Acquisition units completed | 72/72 | 80/80 | 107/107 |

The v325 execution resolved all 27 prior processing errors and added 21 qualifications. The latest v326 execution then captured **27 new bodies**, verified **70 prior unique bodies**, and **reused 64 of 71 prior analyses while reparsing seven**. No prior capture was downloaded again. It retained all 27 prior qualified rows and added **75**, leaving **481** unresolved. The earlier 27 error resolutions are not counted again.

Elapsed times were 665.9, 229.2 and 153.2 seconds, respectively. The work scopes differ, so these are observations rather than a controlled speed benchmark. All three executions produced zero model fits, submissions and strict historical admissions. The latest source stage performed cached conflict diagnosis with zero fresh HTTP requests and zero box additions; its successful diagnostic completion is separate from closing the 88-record numerical gap.

## Reproduce the accounting

```bash
python tools/review_project.py
```

Open **outputs/review/index.html**. The evidence explorer switches between women's venue qualification, numerical box recovery and historical admission. Each view retains its denominator and unknown population. Keyboard-operable controls, a live text explanation and a static data table preserve the meaning without relying on bar length or color.

The report is self-contained and runs offline. **outputs/review/review.json** contains the same observations, derived deltas and content digests. No credential, provider request, model fit or private adapter is required. The [executed notebook](../portfolio/engineering_review.ipynb) includes the venue history as an interactive chart and a PNG fallback. The [qualification frontier](qualification_frontier.md) adds an edition-level partition of the remaining evidence requirements, bound to this exact current snapshot.

## Contract and failure behavior

The [validator](../tools/evidence_history.py) rejects duplicate or reordered execution identities, mismatched transition parents, changes to the declared populations, double-counted box additions, unexplained qualification loss, retractions larger than the prior population, unverified reparsing and overclaimed error resolution. A successful acquisition cannot conceal processing errors, and a completed acquisition milestone must finish its planned units.

Explicit retractions are supported because evidence may later be invalidated. The equation is prior qualified rows + additions − retractions = current qualified rows. The validator does not require every metric to increase; it requires changes to be explained.

Strict JSON loading rejects duplicate keys and nonfinite values. An exact field allowlist prevents additional private fields from being silently accepted. Published observation digests identify content; they do not authenticate a withheld publisher or prove when a historical source first existed. The [failure tests](../tools/test_evidence_history.py) exercise corrupted copies of the public records and a valid explicit-retraction example.

## Why there is no single completion percentage

Numerical recovery, timestamp eligibility, venue representation, original-matrix reproduction, scientific evaluation and prospective operation have different populations and acceptance criteria. Combining them into one percentage would hide the unfinished gates. The public report exposes those differences and makes its narrower engineering claims executable.

[Engineering review](engineering_review.md) · [Current research](current_research.md) · [Reproduction matrix](reproduction_matrix.md) · [Publication boundary](../portfolio/DISCLOSURE.md)
