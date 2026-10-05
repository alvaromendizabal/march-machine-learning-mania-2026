# Start here | employer review guide

This repository is a curated ML research case study. The public surface is intentionally narrower than the private AWS research workspace: it exposes the data contracts, validation design, model evidence, tests, notebooks, and aggregate results needed to evaluate the work without publishing a turnkey competition implementation.

## 30-second review

Read the [README](README.md).

The key signals are:

- exact Brier-score evaluation on a 126-game audit;
- independently recreated external-data sources with chronology and provenance controls;
- numerical reproduction of 65,703 women's pairwise probabilities within 1e-4;
- men's core and margin model-procedure parity on matched inputs;
- a complete 566-game historical men's evaluation bank;
- AWS/SageMaker execution with checkpoints, telemetry, manifests, and cost controls;
- explicit rejection of experiments that improve one slice but fail broader validation.

## 3-minute review

1. [Employer walkthrough](docs/employer_walkthrough.md)
2. [System architecture](docs/architecture.md)
3. [Current research boundary](docs/current_research.md)

These three documents explain what was built, how evidence is separated by lifecycle state, and what is intentionally public versus private.

## 10-minute technical review

Open the six canonical notebooks in order:

1. [00 · Data audit and preparation](notebooks/00_data_audit_and_preparation.ipynb)
2. [01 · Split protocol and pre-tournament snapshots](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb)
3. [02 · Feature store and diagnostics](notebooks/02_feature_store_and_diagnostics.ipynb)
4. [03 · Model comparison and diagnostics](notebooks/03_model_comparison_and_diagnostics.ipynb)
5. [04 · Locked benchmark and final inference](notebooks/04_locked_benchmark_and_final_submission.ipynb)
6. [05 · Feature research](notebooks/05_feature_research.ipynb)

Then inspect:

- [Supplemental-source ownership](docs/supplemental_source_ownership.md)
- [Public-solution reproduction matrix](docs/reproduction_matrix.md)
- [Aggregate research portfolio](portfolio/README.md)

## Deep technical review

| Area | Purpose |
|---|---|
| `src/march_mania/` | reusable data, feature, modeling, runtime, and publication modules |
| `tests/` | correctness, leakage, publication, recovery, and model-contract tests |
| `configs/` | explicit modeling and publication configuration |
| `notebooks/` | canonical executed research narrative |
| `reports/` | committed aggregate evidence used by publication checks |
| `portfolio/` | employer-facing aggregate notebooks and machine-readable summaries |
| `docs/` | architecture, research boundaries, source ownership, and reproduction state |
| `references/` | official/reference material retained only when relevant to the public project |

Historical scratch work, migration snapshots, duplicate workspaces, and obsolete starter material are intentionally absent from the current tree. Git history preserves them.

## Public reproducibility check

After installing the locked environment:

```bash
uv sync --locked --group dev
uv run --locked python -m march_mania.publication.portfolio_contract
```

The check verifies that the public score boundary, historical-control counts, source-coverage evidence, milestone ledgers, README links, canonical notebook set, and curated employer narrative remain internally consistent.

The full CI suite additionally compiles, lints, formats, type-checks, tests, re-executes notebooks, and verifies publication artifacts.

## Public/private contract

Published:

- aggregate metrics and exact evaluation populations;
- source coverage and provenance state;
- feature/model reproduction evidence;
- validation rules and lifecycle decisions;
- negative experiment conclusions;
- canonical notebooks, tests, and engineering architecture.

Not published:

- row-level private forecasts;
- raw supplemental source archives;
- fitted private competition models;
- exact private correction rules, thresholds, or weights;
- private source-identity logic;
- credentials or AWS-local orchestration state.

That boundary keeps the project technically reviewable while preserving competitive implementation details.
