# Tournament Lab

**Alvaro Mendizabal · ML engineering · Applied data science · Reliable AI systems**

[![Research quality](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/ci.yml)
[![Public demo](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/public-demo.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/public-demo.yml)
[![Evidence checks](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/current-research.yml/badge.svg)](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/actions/workflows/current-research.yml)

[![Tournament Lab: probability, provenance and recovery. Inspectable engineering behind a forecast.](docs/assets/forecasting-system.svg)](START_HERE.md)

## A forecast is only as useful as the evidence behind it.

I built a basketball probability-research system connecting **source qualification, chronological ML, probability evaluation and recoverable cloud execution**. This independent March Machine Learning Mania project exposes the engineering decisions—not just a leaderboard number.

**[Explore the interactive lab ↗](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html)** · **[Five-minute engineering review](START_HERE.md)** · **[Train](docs/temporal_model_demo.md) → [Freeze, load and infer](docs/model_delivery.md) → [Verify the evidence](docs/evidence_bundle.md)**

| Engineering question | Inspectable evidence | Important boundary |
|---|---|---|
| Can you build and evaluate an ML pipeline? | [Actual temporal training](tools/temporal_model_demo.py), train-only transforms, probability diagnostics and deterministic artifacts | Fictional data, not NCAA performance |
| Can you deliver a model outside the training process? | [Strict artifact loader](src/march_mania/public_reference.py), isolated label-free inference, exact parity and tamper tests | Local inference contract; not a deployed service or production SLA |
| Can someone else audit the execution after the runner is gone? | [Offline evidence verifier](docs/evidence_bundle.md): exact source tree, retained notebook bodies, dependency hashes and closed artifact manifest | Externally pinned run and bytes; integrity is not authorship or prospective validation |
| Can you prevent leakage and resist misleading gains? | [925-game matched replay](docs/source_readiness.md#the-matched-study-is-not-a-new-holdout), development screens and unchanged control | Later labels were already exposed; no score-selected promotion |
| Can you own data and production reliability? | [Source audit](docs/source_readiness.md), [interrupt/resume/corruption tests](tools/test_reliability_demo.py), immutable evidence and failure returns | 67 bodies verified; identity and eligibility remain unresolved |
| Can you communicate a model as a product? | Bracket propagation, sensitivity, path attribution, scenario replay and printable briefs | Browser ratings, prices and outcomes are authored synthetic scenarios |

## Run the public review

From a checkout with **Python 3.12 and Node**, no credentials or package installation:

```bash
python tools/review_project.py
```

Open **outputs/review/index.html**. Fifteen checks cover actual synthetic ML training, frozen-artifact inference, source contracts, evidence-bundle rejection cases, recovery, evidence arithmetic, browser calculations and offline packaging. **review.json** records results and source hashes. Contract tests are not presented as an audit of a real CI run. [Setup and reproduction levels](START_HERE.md#ten-minute-technical-review)

For training alone:

```bash
python tools/temporal_model_demo.py --out-dir outputs/temporal-demo
```

This fits regularized logistic models on expanding prior-season windows. Scaling is learned from training rows only; future outcomes cannot alter earlier forecasts. The fixed protocol and tests are public, independent of the private competitive model.

For **inference without refitting**, run `python tools/model_delivery_demo.py demo --out-dir outputs/model-delivery`. Three isolated Python processes load the frozen artifacts and reproduce all 198 synthetic forecasts exactly. The inference module has no dependency on the trainer. Its closed contract rejects altered artifacts, outcome fields, repeated physical games, invalid clocks and nonfinite values. [Artifact and request schemas](docs/model_delivery.md)

For **verification without executing downloaded code**, use the [CI evidence-bundle walkthrough](docs/evidence_bundle.md). The standard-library verifier checks the downloaded bundle against an independently retained binding, reconstructs its Git tree, and follows each notebook checkpoint and runtime receipt to exact retained bodies. It rejects missing or extra files and mismatched dependencies. This closes a real earlier retention gap: a receipt named a five-cell notebook whose generated body had not been included in the CI archive.

## Results, with their denominators

| Evidence | What it establishes | What it does not establish |
|---|---|---|
| **0.1034347 Kaggle Brier** | [Recorded retrospective score](docs/champion_result.md), submission 57122407 | Prospective performance, an official competition win or profitability |
| **132,133 possible-matchup probabilities** | [Normalized submission record](reports/champion_result/kaggle_record.json) | 132,133 scored games |
| **925 matched games / 218 common feature games** | [V018 study](portfolio/source_readiness.json): control Brier 0.1694094; candidate A 0.1675881 | A selected replacement or new holdout; every paired interval includes zero |
| **67/67 bodies verified / zero admissions** | [V019 source audit](docs/source_readiness.md), 54 distinct content identities | Complete provider acquisition, closed debt or proven pregame clocks |
| **2/2 targeted format diagnostics completed** | [V020 follow-up](docs/source_readiness.md): 2,283 CSV records and 1,629 Parquet rows | Source identity, unique basketball-game counts or historical feature eligibility |
| **67 object / 3,625 request masks audited offline** | [V021 qualification](docs/source_readiness.md): all registered rows retained; 198 frozen public synthetic responses matched | Completeness masks are not debt closure; public inference is not private-model parity |

The 925-game study, historical 126-game retrospective and Kaggle receipt are **different populations**, not equivalent tests. Control remains unchanged.

## Architecture: qualify before you learn

```mermaid
flowchart TD
    A[Source observations] --> B{Identity and timing proven?}
    B -->|Yes| C[Train-only feature pipeline]
    B -->|No or unknown| D[Retained evidence and explicit gaps]
    C --> E[Earlier-season model selection]
    E --> F[Frozen policy and predictions]
    F --> G[Later-season observation]
    G --> H[Matched evaluation and release evidence]
```

[Architecture](docs/architecture.md) · [Evaluation protocol](docs/research_protocol.md) · [Model card](docs/model_card.md) · [Attribution](docs/benchmark_comparison.md#method-lineage-and-additional-work)

## Latest owner evidence · reviewed November 3, 2026

**V021 completed all six offline stages, with zero new source requests, private fits or historical admissions.** It qualified the existing evidence for 67 object locations and all 3,625 original request rows. The 47/54 complete content masks and 60/67 complete location masks describe interpretation coverage, not proven source identity or feature eligibility. Three frozen public synthetic models reproduced 198 label-free responses exactly in process; that is separate from the public fresh-process demonstration.

V020's two earlier format diagnostics remain complete: 2,283 CSV records and 1,629 Parquet rows. Every Parquet season value is a 2027 candidate and every game JSON URL is null. Event dates and boolean presence flags are not feature-availability witnesses or underlying data bodies.

V019's original **PARTIAL** record is unchanged: 67 bodies verified, 54 distinct content identities and a 90,886-record saved metadata snapshot—not a fresh listing. Seven tiny archive text members remain semantically uninspected. V020's successful format scans produced **zero exact request matches, debt closures or historical feature-clock witnesses**. The original **67 objects / 3,573 unresolved requests** remain unresolved. [Measured resources and blockers](docs/source_readiness.md)

The [V351 systems comparison](docs/owner_replay.md) and [October 26 acquisition snapshot](portfolio/acquisition_progress.json) remain dated historical records, not relabeled latest results.

## Publicly reproducible. Privately bounded.

The public tree contains the maintained Python framework, six canonical executed notebooks, an actually trained synthetic example, portable inference and evidence-verification contracts, browser calculations, tests, CI and aggregate evidence. Private provider bodies, cloud locations, competitive weights, exact blend recipes and row-level competitive forecasts stay withheld. [Reproduction matrix](docs/reproduction_matrix.md) · [Disclosure](portfolio/DISCLOSURE.md) · [Publication guard](tools/check_publication.py)

**Stack:** Python, pandas, scikit-learn, XGBoost, LightGBM, Plotly, AWS SageMaker and GitHub Actions. Portable examples have dependency-free paths. No LLM or generative-AI capability is claimed for this forecasting project.

**Author:** [Alvaro Mendizabal](https://github.com/alvaromendizabal) · [MIT license](LICENSE) · [Technical review rubric](docs/portfolio_review.md)
