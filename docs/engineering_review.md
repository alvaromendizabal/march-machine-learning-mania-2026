# Evidence behind the forecast

**Alvaro Mendizabal · ML engineering, data systems and applied probability**

The project makes three different kinds of evidence inspectable. They answer different questions and are checked separately.

| Evidence class | What is public | What it establishes |
|---|---|---|
| Historical scored result | Normalized Kaggle record: **0.1034347**, submission 57122407 | Recorded retrospective scoring; no prospective claim or new account query |
| Current acquisition | Allowlisted owner-execution aggregates, reviewed October 26, 2026 | Coverage, residual gaps and processing failures; public checks validate accounting |
| Runnable engineering | Authored synthetic observations, recovery example, forecast/scoring example and bracket engine | Executable contracts on public inputs; no claim of private-pipeline parity |

[Featured score](champion_result.md) · [Aggregate snapshot](../portfolio/acquisition_progress.json) · [Executed notebook](../portfolio/engineering_review.ipynb)

## One command, one review report

From the repository root with Python 3.12 and Node:

```bash
python tools/review_project.py
```

Open **outputs/review/index.html**. Its machine-readable companion is **outputs/review/review.json**. Eight checks execute the synthetic forecast/scoring lab, earlier scored-receipt arithmetic, recovery failure contracts, current aggregate boundaries, execution-history accounting, exact bracket engine, actual UI handlers, and deterministic offline demo packaging. A failed check makes the review fail and retains its log.

No credentials, source download, model artifact or Python package installation is needed. Optional notebook regeneration uses the project's locked development environment. The browser demo still packages exactly five reviewed static source files.

## Current source accounting

The latest authenticated return preserves **133 of 221** originally missing numerical box scores, with no new additions in this execution. **88** remain: 66 unresolved, 10 unverified and 12 quarantined. By season, recovery is 53/103 in 2010, 34/54 in 2011 and 46/64 in 2012. Numerical team-season completeness is **904/1,029**; this is not a historical-admission count. The recovered overlay still has **zero strict historical admissions**.

Venue acquisition completed **80/80** units, verified and reparsed **62** prior bodies, and saved **8 new source bodies**. All **27** prior processing errors were resolved. Qualified women's rows increased from **6 to 27/583**; **556** remain unknown. The 602 men's rows are carried controls. The acquisition milestone succeeded; the complete venue study remains unfinished, with no new model fits or submissions.

These counts come from the supplied execution return, whose **114** manifested members were checked for unique paths, CRC, sizes and SHA-256. This public snapshot withholds raw records and source-specific identity logic. The public validator verifies the aggregate schema and arithmetic; it does not independently authenticate the original publishers.

The [execution evidence ledger](execution_evidence.md) retains both observations and validates their transition. Its interactive report shows numerical recovery, women's venue qualification and historical admission with separate denominators. Added rows and retracted rows are explicit, and the current snapshot must match the final historical observation exactly. Elapsed times describe different workloads and are not presented as a controlled speed benchmark.

## A recovery contract that runs

The public reliability example is written independently from the private research runner. Four synthetic observations deliberately include an eligible timestamp, a late timestamp, an unknown timestamp and a second eligible timestamp.

| Invocation | Qualification calls | Result |
|---|---:|---|
| Uninterrupted cold run | 4 | All units committed |
| Deliberate stop after one unit | 1 | One result retained |
| Resume | 3 | The committed unit is verified and reused |
| Warm repeat | 0 | All four results reused; fingerprints and hashes still checked |

A spy test counts actual calls to qualification; the counter is not merely a count of new file writes. Cold and resumed results must match. Changing an input or corrupting committed content raises an integrity error. Duplicate identities are rejected before writes, a second invocation cannot take an active lock, symlink checkpoints are rejected, and unknown timing stays unknown.

Writes use a temporary file, file synchronization and atomic replacement. These are focused recovery checks, not a claim of a distributed transactional system or protection against a malicious actor who controls both content and its hashes.

## Notebook review

The [engineering review notebook](../portfolio/engineering_review.ipynb) executes four code cells, displays season-level gaps and venue qualification over successive executions, persists two interactive Plotly figures with PNG fallbacks, and executes the recovery demonstration. CI executes the notebook with the locked environment. The six canonical research notebooks remain separate, preserving their modeling and evaluation lineages.

## Questions this project is ready to discuss

- How should a pipeline represent a valid number whose historical availability is unproven?
- Which evidence supports a score, a source acquisition and a model promotion?
- What must be verified before a completed task is reused?
- How should two independent stages preserve useful partial results?
- Why do the same physical-game population and time boundaries matter in an ablation?
- Which parts of a competitive system should be public for review, and which should remain private?

[Architecture](architecture.md) · [Research protocol](research_protocol.md) · [Reproduction matrix](reproduction_matrix.md) · [Model card](model_card.md)
