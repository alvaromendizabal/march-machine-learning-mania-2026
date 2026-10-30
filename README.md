# Tournament Lab

**Alvaro Mendizabal · Machine learning engineering · Applied data science**

[![Research quality](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml)
[![Public demo](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/public-demo.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/public-demo.yml)
[![Evidence checks](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/current-research.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/current-research.yml)

[![Tournament Lab: probability, provenance and recovery. Inspectable engineering behind a forecast.](docs/assets/forecasting-system.svg)](START_HERE.md)

## A probability is only useful when its evidence holds up.

I built an NCAA forecasting research system across **data qualification, men's and women's probability models, chronological evaluation and recoverable AWS execution**. This repository makes the work inspectable: a basketball scenario lab, six executed research notebooks, a public evaluation pipeline, and an independently authored recovery example that stops, resumes and rejects corrupted state.

**[Explore Duke × Michigan ↗](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html)** · **[Review the engineering](START_HERE.md)** · **[Inspect current evidence](docs/engineering_review.md)**

| Result | Evidence and interpretation |
|---|---|
| **0.1034347 Kaggle Brier** | [Recorded public/private score](docs/champion_result.md), submission 57122407. Retrospective 2026 research; prospective performance is unproven. |
| **132,133 possible-matchup probabilities** | [Normalized result record](reports/champion_result/kaggle_record.json), with separate men's and women's populations. These are forecast rows, not scored games. |
| **302 fitted operations reused; 925 matched games** | [Latest owner replay](docs/owner_replay.md). Zero new fits; accepted control retained after all three challengers worsened development Brier. |
| **Completed work survives and verifies** | [Runnable reliability example](tools/reliability_demo.py): exact resume, zero qualification recomputation on a warm run and corrupt-checkpoint rejection on synthetic inputs. |

## Review it in one command

From a checkout, with **Python 3.12 and Node**:

```bash
python tools/review_project.py
```

Open **outputs/review/index.html**. Eleven checks execute the public forecast and scoring example, historical receipt arithmetic, recovery tests, current aggregate checks, owner replay and storage accounting, execution-history and qualification-frontier contracts, explorer controls, bracket engine and UI handlers, and deterministic offline demo packaging. Inspect progress across runs, then focus the remaining evidence by edition and qualification state. The report needs **no credentials, cloud account, private data or package installation**. [Setup and review contract](START_HERE.md#ten-minute-technical-review)

The public examples reproduce their own calculations. Competitive forecasting recipes, learned weights, private source banks and row-level forecasts remain private. [Reproduction levels](docs/reproduction_matrix.md) · [Publication boundary](portfolio/DISCLOSURE.md)

## Three ways to inspect the work

| Review path | What it demonstrates | Start here |
|---|---|---|
| **Applied modeling** | Separate men's/women's branches, calibration, season-forward evaluation, matched comparisons and negative results | [Model card](docs/model_card.md) · [Model-comparison notebook](notebooks/03_model_comparison_and_diagnostics.ipynb) |
| **Data and ML systems** | Source identities, timing boundaries, explicit missingness, content verification, independent stages and durable recovery | [Engineering case study](docs/employer_walkthrough.md) · [Executed engineering review](portfolio/engineering_review.ipynb) |
| **Product communication** | Duke–Michigan scenarios, exact bracket propagation, sensitivity, path attribution, scenario replay and printable briefs | [Interactive lab](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html) · [Analyst walkthrough](docs/scouting_walkthrough.md) |

## From source to decision

```mermaid
flowchart TD
    A[Source observations] --> B{Identity and timing qualify?}
    B -->|Yes| C[Versioned features]
    B -->|No or unknown| D[Retained evidence and explicit gaps]
    C --> E[Season-forward model comparison]
    E --> F{Declared evaluation passes?}
    F -->|Yes| G[Versioned forecast artifact]
    F -->|No| H[Retained negative result]
    G --> I[Independent integrity and delivery checks]
```

[Architecture](docs/architecture.md) · [Evaluation protocol](docs/research_protocol.md) · [Source ownership](docs/supplemental_source_ownership.md)

## Latest verified owner run · October 29, 2026 (Pacific)

**V348 completed the research, science and lineage stages; market-source reconciliation remains PARTIAL.** It reused **66 research and 236 science fitted operations**, with **zero new fits or submissions**. The matched study has **925 physical games** and **3,700 probability rows across four arms**. All three challengers worsened the predeclared development Brier, so the accepted control remains selected. The later window was already examined and is not a fresh holdout. [Matched results and runtime evidence](docs/owner_replay.md)

The next measured run reduced elapsed time from **17m 16s to 9m 11s**, odds GET responses by **85.78%**, and the review return from **452.76 MB to 10.32 MB**. Verified cleanup released **1.492 GB of allocated disk**, leaving **2.572 GB free** after packaging. All **396 manifest entries** passed verification. These sequential owner observations preserve the same scientific result; they are not a controlled concurrency benchmark. Source closure remains open, and all historical folders have not been removed.

**Do we have the data?** The defined 2013–2025 study has its required detailed-game inputs. Broader coverage is incomplete: 78 old women's boxes, venue/context and player-join gaps remain; **17,012,534 market selections have zero model-training admissions**. Source objects, selection records and eligible games are separate units. [Allowlisted aggregate record](portfolio/owner_replay.json) · [Executed engineering review](portfolio/engineering_review.ipynb)

The [October 26 acquisition snapshot](portfolio/acquisition_progress.json), [execution ledger](docs/execution_evidence.md) and [qualification frontier](docs/qualification_frontier.md) retain their own dated populations and rules. They are historical evidence, not a relabeled census from the latest replay.

## What the scored result establishes

**0.1034347** is the recorded Kaggle public/private Brier for the featured retrospective submission. Lower Brier indicates lower probability error on scored games. Outcomes were already available; the score does not establish an official competition victory, untouched validation, accuracy percentage or profitability. The demo's ratings, bracket positions, prices and outcomes are authored synthetic scenarios, separate from the scored forecast.

Earlier scored receipts and method attribution remain in the [historical comparison](docs/benchmark_comparison.md). The [2027 evaluation contract](docs/2027_readiness.md) defines what future evidence must establish.

**Stack:** Python, pandas, scikit-learn, XGBoost, LightGBM, Plotly, AWS SageMaker, GitHub Actions and dependency-free browser calculations.

**Author:** [Alvaro Mendizabal](https://github.com/alvaromendizabal) · [MIT license](LICENSE) · [Attribution and disclosure](portfolio/DISCLOSURE.md)
