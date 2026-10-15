# Tournament Lab · NCAA probability forecasting

**Alvaro Mendizabal · Machine learning engineering · Sports analytics**

[![Research quality](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml)
[![Public demo](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/public-demo.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/public-demo.yml)
[![Evidence checks](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/current-research.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/current-research.yml)

[![Tournament Lab: Duke matchup scenarios, exact bracket probabilities and inspectable ML engineering.](docs/assets/forecasting-system.svg)](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html)

### A strong team is not a certain winner. Build the probabilities—and the evidence behind them.

I built an NCAA forecasting research system spanning data qualification, men's and women's probability models, season-forward evaluation and recoverable AWS execution. This repository pairs that work with a **Duke-centered interactive lab** and a runnable public engineering example. The public demo is reproducible; the private competition pipeline stays private.

**[Open the Duke workbench ↗](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html)** · **[Sports analyst walkthrough](docs/scouting_walkthrough.md)** · **[Three-minute technical review](START_HERE.md)**

## Start with a basketball question

**How much should a change in Duke's strength move its matchup probability—and its chance of winning a bracket?** Adjust the field, compare Duke with UConn, then inspect every possible tournament path. Enter hypothetical prices to separate a probability estimate from a no-vig market comparison. Export the inputs and full-precision calculation.

The school names are real. The demo's ratings, bracket positions, prices and outcomes are **authored synthetic scenarios**, not current NCAA forecasts. No private models or live odds are loaded. [Method and scope](docs/public_demo.md)

## Engineering at a glance

| Capability | Inspectable evidence |
|---|---|
| **14,311 team-season profiles** across men's and women's basketball | [Source-foundation receipt](portfolio/latest_execution.json); distinct season windows and explicit missingness |
| **132,133 matchup probabilities** in the research forecast population | [Evidence map](docs/evidence_map.md); identities, ranges and file integrity checked |
| **Season-aware evaluation** rather than a random-split headline | [Splits notebook](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb), [model card](docs/model_card.md) |
| **Public, offline reproducibility** | [Duke lab source](public-demo/), [Python evaluation example](docs/public_reproduction.md), deterministic demo packaging |
| **Recoverable delivery and a protected publication boundary** | [Architecture](docs/architecture.md), [publication checks](tools/check_publication.py), [disclosure](portfolio/DISCLOSURE.md) |

## Results, with evidence attached

| Result | Evidence class | What it means |
|---|---|---|
| **0.1034347 Brier** | [Owner execution record](portfolio/review_snapshot.json) | Best recorded source-rebuilt retrospective result in the inspected October research evidence; not a fresh Kaggle receipt in this release |
| **0.1067095 Brier** | [Published Kaggle receipt](reports/verified_result/submission_receipt.json) | Directly inspectable earlier late-submission case study |
| **Public browser and Python demos** | Synthetic test fixtures | Demonstrate mechanics and engineering, not NCAA predictive performance |

Brier is probability error, not accuracy; lower is better. These 2026 research results were obtained **after outcomes were available**. They are not official competition wins, evidence of betting profitability or prospective performance. The public package does not regenerate the private scored forecasts. [Full evidence boundaries](docs/current_research.md)

## Reproduce the public work

Python 3.12 and Node are enough for the lightweight review; no credentials, cloud account or model download:

```bash
git clone https://github.com/alvaromendizabal/march-machine-learning-mania-2026.git
cd march-machine-learning-mania-2026
python tools/reproduce_public.py --check
python portfolio/reproduce_release.py --check
node tools/test_public_demo_engine.mjs
node tools/test_public_demo.mjs
python tools/package_public_demo.py
```

Open **outputs/public-demo/Tournament_Lab.html** directly in a browser. The packager creates a deterministic self-contained HTML file and a five-file ZIP after checking the public boundary. The same browser calculation runs entirely offline. [Full setup and locked-environment checks](START_HERE.md)

## Review the work behind the interface

[Engineering case study](docs/employer_walkthrough.md) · [Model card](docs/model_card.md) · [Architecture](docs/architecture.md) · [Six executed research notebooks](START_HERE.md#full-framework-review) · [Data provenance](docs/reproducible_source_foundation.md) · [2027 evaluation contract](docs/2027_readiness.md)

**Stack:** Python, pandas, scikit-learn, XGBoost, LightGBM, Plotly, AWS SageMaker, GitHub Actions; dependency-free browser demonstration.

**Author:** [Alvaro Mendizabal](https://github.com/alvaromendizabal) · [MIT license](LICENSE) · [Method attribution and disclosure](portfolio/DISCLOSURE.md)
