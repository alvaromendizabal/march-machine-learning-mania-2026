# Start here · sports ML with inspectable evidence

**Featured result: 0.1034347 Kaggle public/private Brier · submission 57122407.** [Score and scope](docs/champion_result.md)

Start with the [Duke × Michigan demo](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html), then inspect the [analyst walkthrough](docs/scouting_walkthrough.md) or the [release acceptance contract](docs/reviewer_contract.md). The champions edition adds paired sensitivity, path attribution, scenario replay and print without exposing private forecasting assets.


**A short review path for ML engineers, data scientists and hiring teams.**

I built this project around two questions: are the probabilities useful, and can the evidence behind them be trusted? Start with an executable demonstration, then inspect the research evidence and implementation at the depth you need.

## Three-minute review

For a sports-first introduction, start with the [analyst walkthrough](docs/scouting_walkthrough.md). For use limits and evidence classes, read the [model card](docs/model_card.md).

1. **Explore:** [Tournament Lab](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html) starts with Duke and propagates illustrative team strengths through an eight-team bracket. The calculations are exact under the demo's declared assumptions.
2. **Understand the contribution:** [Engineering case study](docs/employer_walkthrough.md) connects source qualification, forecast construction, evaluation repairs and recoverable execution.
3. **Check the evidence:** [Evidence map](docs/evidence_map.md) identifies the proof and limitation behind each headline result.

## Ten-minute technical review

From the repository root, with **Python 3.12 and Node**:

```bash
python tools/review_project.py
```

Open **outputs/review/index.html** for the executed checks and current evidence. **outputs/review/review.json** preserves the results and source hashes. This standard-library review needs no credentials, package installation or downloads. [Engineering review contract](docs/engineering_review.md)

| Question | Start with |
|---|---|
| How is outcome leakage prevented? | [Synthetic forecast example](docs/public_reproduction.md), [split notebook](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb) |
| What did the author contribute? | [Engineering case study](docs/employer_walkthrough.md), [method attribution](docs/benchmark_comparison.md#method-lineage-and-additional-work) |
| What was actually delivered? | [Featured scored record](reports/champion_result/kaggle_record.json), [latest owner replay](portfolio/owner_replay.json) |
| What is reproducible? | [Reproduction matrix](docs/reproduction_matrix.md), [executed engineering notebook](portfolio/engineering_review.ipynb) |
| What happens after interruption? | [Runnable recovery example](tools/reliability_demo.py), [actual computation tests](tools/test_reliability_demo.py) |
| Which evidence blocks the next qualification? | [Qualification frontier](docs/qualification_frontier.md), [partition validator](tools/qualification_frontier.py) |

The **October 30 V350 owner replay (Pacific)** reused 302 fitted operations with zero new fits on the same 925-game study. The accepted control remains selected. Odds reconciliation improved 34.37%, while total time grew 31.93% with consolidation work. Source unknowns fell to 71; all 3,482 new selections came from current endpoints and add no historical training coverage. Cleanup released 366,530,560 allocated bytes and moved 472 notebook/HTML files; protected references remain separate. The [latest replay review](docs/owner_replay.md) distinguishes the 578,227-file home census from complete duplicate/feature diagnostics and records eleven recent outcomes: zero SUCCESS, seven PARTIAL and four STOPPED. Completed phases do not become overall success; incomplete history keeps all-time totals unknown.

The **October 26 acquisition snapshot** reports **133/221 numerical candidates**, **88 remaining**, and **102/583** qualified women's venue rows, up from 27. All prior qualifications were retained; **481** women's rows remain unresolved. The new frontier distinguishes 21 court-qualified rows lacking home context from 460 rows with both dimensions unqualified. These owner-run aggregates are separate from the scored forecast and synthetic examples. The [execution ledger](docs/execution_evidence.md) preserves the history, while the [frontier explorer](docs/qualification_frontier.md) makes the next evidence requirements inspectable.

## A portable, offline demo

Run `python tools/package_public_demo.py`, then open **outputs/public-demo/Tournament_Lab.html** directly. Packaging verifies the public boundary first and produces deterministic HTML, a five-file ZIP and content hashes. No server, credentials or npm install is required for the packaged browser demo.

## Browser demo locally

```bash
python -m http.server 8000
```

Open **http://localhost:8000/public-demo/**. The static demo needs no build step. Check its engine and actual UI handlers with `node tools/test_public_demo_engine.mjs` and `node tools/test_public_demo.mjs`. [Demo guide](docs/public_demo.md)

[Maintained scope and publication boundary](docs/PROJECT_SCOPE.md) distinguish the active framework from retired one-time report copies.

## Full framework review

Python **3.12.13** and the project dependencies are locked in `uv.lock`:

```bash
uv sync --locked --group dev
uv run --locked python scripts/quality.py
uv run --locked python -m ipykernel install --user --name march-mania
uv run --locked python scripts/notebook.py --execute --publish
```

Default review mode reads published aggregate evidence. Submission generation is default-off. Public framework outputs and private forecasts retain separate lineages.

| Notebook | Review question |
|---|---|
| [00 — Data audit](notebooks/00_data_audit_and_preparation.ipynb) | Are tables and physical game identities coherent? |
| [01 — Splits and snapshots](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb) | What was available at the prediction cutoff? |
| [02 — Feature store](notebooks/02_feature_store_and_diagnostics.ipynb) | How are features and provenance organized? |
| [03 — Model comparison](notebooks/03_model_comparison_and_diagnostics.ipynb) | How are model families compared? |
| [04 — Historical benchmark](notebooks/04_locked_benchmark_and_final_submission.ipynb) | What does the consumed benchmark establish? |
| [05 — Feature research](notebooks/05_feature_research.ipynb) | How are hypotheses, ablations and failures recorded? |

These six notebooks document public-framework lineages. [Verified result](portfolio/verified_result.ipynb) documents the separate receipted retrospective submission. Historical research notebooks preserve dated experiments; they do not supersede [current evidence](docs/current_research.md).

## Read the results correctly

The featured scored result is **0.1034347 Kaggle Brier, submission 57122407**. [Result and evidence](docs/champion_result.md). Older receipts remain archival records; the demonstration's synthetic scores establish no NCAA performance. Prospective evaluation requires a forecast frozen before future outcomes. [Evaluation disclosure](portfolio/DISCLOSURE.md)
