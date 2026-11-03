# Start here · inspect the engineering, then the result

**Alvaro Mendizabal · independent March Machine Learning Mania**

This is a probability-research system, not just a competition notebook. Ask three questions: what did I build, what can you run, and which conclusions does the evidence support?

## Five-minute employer review

1. **See the product:** [Tournament Lab](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html) turns synthetic assumptions into bracket paths, sensitivity analysis and an analyst brief.
2. **Inspect the ML lifecycle:** [Temporal training](docs/temporal_model_demo.md) fits actual models with train-only preprocessing. [Frozen-model delivery](docs/model_delivery.md) loads the artifacts in an isolated process and reproduces all 198 synthetic forecasts without refitting. Fictional data make both sides inspectable.
3. **Inspect a difficult engineering decision:** [Source-readiness case study](docs/source_readiness.md) explains why verified bytes alone do not admit historical features. A partial result remains partial.
4. **Check the research claim:** [Model card](docs/model_card.md) and [score receipt](docs/champion_result.md) separate retrospective performance from future generalization.

| Hiring lens | Concrete contribution | Review entry |
|---|---|---|
| ML Engineer | Temporal transforms, model evaluation, strict artifact loading, recovery and CI | [Training](tools/temporal_model_demo.py), [pure inference](src/march_mania/public_reference.py), [architecture](docs/architecture.md) |
| Data Scientist | Matched populations, development-only selection, uncertainty and negatives | [Executed engineering notebook](portfolio/engineering_review.ipynb), [protocol](docs/research_protocol.md) |
| AI Engineer | Data contracts, bounded orchestration, reproducible releases and failure delivery | [Recovery tests](tools/test_reliability_demo.py), [source gates](tools/source_readiness.py) |

AI-engineering relevance here is systems engineering for ML, not an unimplemented LLM, agent or RAG capability.

## Ten-minute technical review

From the repository root, with **Python 3.12 and Node**:

```bash
python tools/review_project.py
```

Open **outputs/review/index.html** and its **review.json** companion. No credentials, downloads or package installation are needed. Fourteen checks cover public synthetic training, fresh-process inference, aggregate validators, recovery and browser calculations. Synthetic fits are not counted as private owner research; the artifact-delivery step adds zero fits.

| Question | Evidence |
|---|---|
| Can I inspect an actual fit? | [Training code and tests](docs/temporal_model_demo.md) |
| Does the exported model work without its trainer? | [Model delivery](docs/model_delivery.md), three isolated processes and 198 byte-exact forecasts |
| Can future labels change earlier forecasts? | Temporal mutation tests; [split notebook](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb) |
| What is new versus historical? | [V020 follow-up with preserved V019 history](portfolio/source_readiness.json), separate [V351 replay](portfolio/owner_replay.json) |
| What stays private? | [Reproduction matrix](docs/reproduction_matrix.md) |
| What survives interruption? | [Recovery example](tools/reliability_demo.py) and actual-call-count tests |
| Can public claims be checked? | [Aggregate contracts](tools/source_readiness.py), [publication guard](tools/check_publication.py) |

## Focused examples

**Actual synthetic training:** `python tools/temporal_model_demo.py --out-dir outputs/temporal-demo` generates fictional inputs, fold-fit receipts, predictions, evaluation, a calibration SVG and manifest. [Fixed protocol](docs/temporal_model_demo.md)

**Frozen inference, zero new fits:** `python tools/model_delivery_demo.py demo --out-dir outputs/model-delivery` validates and reloads all three frozen models in fresh isolated processes. Each fold includes the exact model, label-free request, response and checksummed evidence. [Contract and failure cases](docs/model_delivery.md)

**Portable lab:** `python tools/package_public_demo.py`, then open **outputs/public-demo/Tournament_Lab.html**. Deterministic HTML and a five-file ZIP work offline without a server or npm install.

**Browser development:** `python -m http.server 8000`, then visit **http://localhost:8000/public-demo/**. [Demo guide](docs/public_demo.md)

## Full locked-framework review

Python **3.12.13** and dependencies are pinned in **uv.lock**:

```bash
uv sync --locked --group dev
uv run --locked python scripts/quality.py
uv run --locked python -m ipykernel install --user --name march-mania
uv run --locked python scripts/notebook.py --execute --publish
```

Submission generation is default-off. Public framework outputs, private forecasts and synthetic demonstrations retain separate lineages.

| Canonical notebook | Review question |
|---|---|
| [00 — Data audit](notebooks/00_data_audit_and_preparation.ipynb) | Are physical game identities and tables coherent? |
| [01 — Splits and snapshots](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb) | What was knowable before the cutoff? |
| [02 — Feature store](notebooks/02_feature_store_and_diagnostics.ipynb) | How are features and provenance organized? |
| [03 — Model comparison](notebooks/03_model_comparison_and_diagnostics.ipynb) | How are model families compared? |
| [04 — Historical benchmark](notebooks/04_locked_benchmark_and_final_submission.ipynb) | What does the consumed benchmark establish? |
| [05 — Feature research](notebooks/05_feature_research.ipynb) | How are ablations and negative findings recorded? |

The featured **0.1034347 Kaggle Brier** is recorded retrospective submission 57122407. The 925-game study and historical 126-game retrospective are different populations. Synthetic scores establish no NCAA accuracy; the source audit admitted no new historical feature. No new champion or untouched holdout is claimed.

[Review contract](docs/engineering_review.md) · [Source status](docs/source_readiness.md) · [Scope](docs/PROJECT_SCOPE.md) · [Disclosure](portfolio/DISCLOSURE.md)
