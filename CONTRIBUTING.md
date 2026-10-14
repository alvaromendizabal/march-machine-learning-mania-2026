# Contributing

The public repository supports review of forecasting methods, validation contracts, synthetic examples and aggregate research evidence. Changes should improve one of those public surfaces while preserving each experiment's original scope.

## Development

Use Python 3.12.13 and `uv sync --locked --group dev`. Follow [AGENTS.md](AGENTS.md) for notebook and evidence conventions. Run `uv run --locked python scripts/quality.py`; execute changed notebooks and the six canonical review notebooks before publishing. The lightweight [review path](START_HERE.md) requires only Python's standard library.

## A useful pull request

Explain the problem, resulting behavior, evidence and limitations. Link the relevant tests or executed notebook. For evaluation changes, specify the population, season boundaries, metric aggregation and whether outcomes were previously inspected. Do not silently change a frozen historical control or promote a failed experiment.

## Publication checks

Run `python tools/check_publication.py --staged` before committing. CI checks the proposed changes against the base commit. The guard catches common accidental private artifacts and suspicious content; it supplements human review, not a guarantee of confidentiality.

Do not add competition prediction rows, source-return archives, runner executables, cloud credentials, private configurations or fitted models. Author synthetic fixtures for public examples and label them explicitly. Existing public code remains under its established license. New supplemental source data needs provenance and redistribution review before publication.

The project accepts changes through feature branches and pull requests with passing checks on the exact proposed commit. [Architecture](docs/architecture.md) · [Evidence map](docs/evidence_map.md) · [Disclosure](portfolio/DISCLOSURE.md)
