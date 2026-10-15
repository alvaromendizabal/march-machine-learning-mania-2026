# Tournament Lab · Duke × Michigan

**Alvaro Mendizabal · Machine learning engineering · Sports analytics**

[![Research quality](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml)
[![Public demo](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/public-demo.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/public-demo.yml)
[![Evidence checks](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/current-research.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/current-research.yml)

[![Tournament Lab: Duke and Michigan: 0.1034347 Kaggle Brier, exact bracket scenarios and reproducible engineering.](docs/assets/forecasting-system.svg)](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html)

### 0.1034347 Kaggle Brier. Two marquee teams. Every possible path.

I built an NCAA forecasting research system spanning data qualification, men's and women's probability models, season-forward evaluation and recoverable AWS execution. This repository pairs that work with a **Duke × Michigan interactive lab** and a runnable public engineering example. The public demo is reproducible; the private competition pipeline stays private.

**[Open the Duke × Michigan workbench ↗](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html)** · **[Sports analyst walkthrough](docs/scouting_walkthrough.md)** · **[Three-minute technical review](START_HERE.md)**

## Start with a basketball question

**Duke or Michigan—how does a basketball opinion become a defensible probability?** Michigan is the [2026 NCAA men's champion](https://www.ncaa.com/news/basketball-men/article/2026-04-06/michigan-beats-uconn-wins-2026-mens-basketball-national-championship). Start with either team, adjust its strength, and inspect the matchup, the bracket, the sensitivity and every possible final opponent. Export the complete calculation, create a replayable scenario link, or print an analyst brief.

The school names are real. The demo's ratings, bracket positions, prices and outcomes are **authored synthetic scenarios**, not current NCAA forecasts. No private models or live odds are loaded. [Method and scope](docs/public_demo.md)

## Engineering at a glance

| Capability | Inspectable evidence |
|---|---|
| **14,311 team-season profiles** across men's and women's basketball | [Source-foundation receipt](portfolio/latest_execution.json); distinct season windows and explicit missingness |
| **132,133 matchup probabilities** in the research forecast population | [Evidence map](docs/evidence_map.md); identities, ranges and file integrity checked |
| **Season-aware evaluation** rather than a random-split headline | [Splits notebook](notebooks/01_split_protocol_and_pre_tournament_snapshots.ipynb), [model card](docs/model_card.md) |
| **Public, offline reproducibility** | [Duke lab source](public-demo/), [Python evaluation example](docs/public_reproduction.md), deterministic demo packaging |
| **Recoverable delivery and a protected publication boundary** | [Architecture](docs/architecture.md), [publication checks](tools/check_publication.py), [disclosure](portfolio/DISCLOSURE.md) |

## Featured result: 0.1034347

**Kaggle public and private Brier: 0.1034347 · submission 57122407.** This is a scored retrospective 2026 result, not an offline-only estimate. [Result and evidence](docs/champion_result.md) · [Machine-readable record](reports/champion_result/kaggle_record.json)

The forecast covers **132,133 possible matchups** across men's and women's basketball. Brier measures probability error on scored games, not accuracy; lower is better. The result was obtained after outcomes were available. It is not an official competition victory, prospective validation or a profitability claim.

The public demo reproduces its own probability calculations, not the private competition forecast. Earlier receipts remain in the [historical case study](docs/benchmark_comparison.md); they are not the current headline result.

## What makes the work inspectable

| Public capability | Review it |
|---|---|
| **Duke and Michigan, side by side** | Two live team cards and a default head-to-head comparison |
| **Sensitivity, not false precision** | Perturb one input and see both title probabilities change |
| **Open the path calculation** | Four final-opponent contributions reconcile to the title probability |
| **Reproduce an analyst's exact scenario** | Bounded URL-fragment state, full-precision JSON, printable brief, deterministic offline HTML |
| **Separate research evidence from interface assumptions** | [Model card](docs/model_card.md), [release contract](docs/reviewer_contract.md), automated publication tests |

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
