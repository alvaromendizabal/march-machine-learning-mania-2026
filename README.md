# NCAA tournament forecasting

**Alvaro Mendizabal · Machine learning engineering · Applied data science**

[![Research quality](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml)
[![Evidence checks](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/current-research.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/current-research.yml)
[![Public demo](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/public-demo.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/public-demo.yml)

![Forecasting systems: 14,311 team-season profiles, 132,133 validated matchup probabilities, and a reproducible public review.](docs/assets/forecasting-system.svg)

I build probability forecasts whose inputs, evaluation and delivery can be inspected. This project brings together temporal data engineering, separate men's and women's modeling, calibration, and recoverable AWS execution. The public repository demonstrates the engineering with runnable examples, executed notebooks, tests and carefully scoped research evidence.

**[Try Tournament Lab](https://alvaro-tournament-lab.tartmacaw2.chatgpt.site)** · **[Three-minute review](START_HERE.md)** · **[Engineering case study](docs/employer_walkthrough.md)** · **[Architecture](docs/architecture.md)**

## What I built

| Engineering outcome | Evidence | Why it matters |
|---|---|---|
| **14,311 team-season profiles** across men's and women's basketball | [Latest source audit](portfolio/latest_execution.json) | Reusable feature construction with explicit source and season boundaries |
| **132,133 validated matchup probabilities** in a recovered artifact | [Execution verification](portfolio/latest_execution.json) | Complete identities, valid probability ranges and checksum-verified recovery |
| **566 historical men's games**, including eight restored equal-seed games | [Evaluation repairs](docs/reproduction_matrix.md) | Difficult matchups remain in the evaluation denominator |
| **A Kaggle-recorded research forecast** with a published receipt | [Measured result](docs/benchmark_comparison.md) | Connects a concrete forecast artifact to an external scoring record |
| **Public, executable engineering examples** | [Synthetic evaluation lab](docs/public_reproduction.md) · [Browser demo](docs/public_demo.md) | Review the reasoning and failure handling without credentials or private data |

The latest source audit reports **211,716 official regular-season games** and verifies 19 manifested files. Its profile and probability counts were independently checked in the supplied return. The raw game corpus was not included for independent recounting. These source results are separate from the scored forecast; they do not establish its causal improvement.

## Run it in one minute

Python 3.12, standard library only; no credentials, GPU, model download or external dataset:

```bash
git clone https://github.com/alvaromendizabal/march-machine-learning-mania-2026.git
cd march-machine-learning-mania-2026
python tools/reproduce_public.py --check
python portfolio/reproduce_release.py --check
python tools/summarize_execution.py --check
```

The first command rebuilds a **synthetic forecast-and-evaluation example** and checks its saved artifacts. The other two verify published aggregate evidence. The example demonstrates cutoff selection, one row per physical game, team-swap symmetry, Brier/log loss and reliability diagnostics. It does not reproduce the private competition forecast. [Inputs, outputs and failure cases](docs/public_reproduction.md)

For the full framework, use the [locked Python environment and six review notebooks](START_HERE.md#full-framework-review). For a visual introduction, [Tournament Lab](docs/public_demo.md) lets you change fictional ratings and inspect exact bracket advancement probabilities.

## Results with a clear scope

The published receipt records **0.1067095 Brier** for a **late, retrospective 2026 submission**, submitted after outcomes had been inspected. It is numerically below the published 2026 winning reference; it is not an official competition victory or evidence of prospective superiority. [Receipt, comparison and attribution](docs/benchmark_comparison.md)

That receipt is the public scored case study, not a claim that it is the newest or strongest private experiment. The latest inspected return, **v170, October 14, 2026 UTC**, completes a source-reconstruction audit and recovers an existing forecast. It produces **no new candidate or submission**, and the full private model replay remains incomplete. [Current evidence boundary](docs/current_research.md)

## Decisions worth reviewing

- **Evaluate full populations.** Reconcile identities before calculating improvements; report game-weighted and mean-season Brier separately.
- **Qualify information before modeling.** Treat event time, publisher time and retrieval time as different facts. Preserve missingness when original timing cannot be proved.
- **Make research recoverable.** Use manifest checks, bounded jobs, checkpoints, heartbeats and failure artifacts to preserve completed AWS work.
- **Keep negative results.** A promising recent slice does not override a failed historical gate. [Research decisions](docs/employer_walkthrough.md#decisions-and-tradeoffs)

[Reviewer evidence map](docs/evidence_map.md) · [Source lineage](docs/reproducible_source_foundation.md) · [Public/private boundary](portfolio/DISCLOSURE.md) · [Contributing](CONTRIBUTING.md)

**Stack:** Python · pandas · scikit-learn · XGBoost · LightGBM · Plotly · AWS SageMaker · GitHub Actions.

**Author:** [Alvaro Mendizabal](https://github.com/alvaromendizabal) · [MIT license](LICENSE)
