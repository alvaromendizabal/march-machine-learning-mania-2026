"""Install portfolio documentation and manage submission candidates.

Commands
--------
Install the documentation, CI workflow, configuration, tests, and this
utility as ``scripts/portfolio_release.py``:

    python march_mania_portfolio_upgrade.py install --root . --run

Regenerate the audited submission shortlist later:

    python scripts/portfolio_release.py generate --root . --top 12

Record one observed Kaggle score:

    python scripts/portfolio_release.py record-score --root . \
        --candidate m_primary_w_challenger --score 0.1287654

Import many observed Kaggle scores from one CSV:

    python scripts/portfolio_release.py record-scores-csv --root . \
        --input reports/submission_portfolio/kaggle_scores_import.csv

Generate a targeted challenger-temperature refinement round:

    python scripts/portfolio_release.py refine-challenger --root . \
        --center-m 0.80 --center-w 1.20 --round-name round2

Run the local quality gate:

    python scripts/portfolio_release.py check --root .
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import nbformat
import numpy as np
import pandas as pd
import yaml


EPSILON = 1e-6
CANONICAL_NOTEBOOKS = [
    "00_data_audit_and_preparation.ipynb",
    "01_split_protocol_and_pre_tournament_snapshots.ipynb",
    "02_feature_store_and_diagnostics.ipynb",
    "03_model_comparison_and_diagnostics.ipynb",
    "04_locked_benchmark_and_final_submission.ipynb",
]
PROHIBITED_WORDING = re.compile(
    r"state"
    + r"[_\s-]+"
    + r"of"
    + r"[_\s-]+"
    + r"the"
    + r"[_\s-]+"
    + r"art",
    flags=re.IGNORECASE,
)


README_TEXT = """
# NCAA Tournament Probability Forecasting

A validated end-to-end forecasting system for the 2026 men's and women's
NCAA Division I basketball tournaments. The project converts historical game
results, box scores, ratings, schedules, seeds, conferences, program history,
and matchup interactions into calibrated win probabilities for every possible
2026 matchup.

## Headline result

| Submitted product | Kaggle Brier score | Loss reduction vs. 0.25 |
|---|---:|---:|
| **Challenger** | **0.1299012** | **48.0%** |
| Development blend | 0.1318165 | 47.3% |
| Primary | 0.1421117 | 43.2% |

Lower is better. The challenger reduced Brier loss by **8.6%** relative to the
primary submission.

The challenger is tournament-routed:

- **Men:** pooled-common histogram gradient boosting with rich, seed-aware
  features.
- **Women:** pooled-common XGBoost with rich, seed-aware features.
- **Unseeded hypothetical matchups:** gender-specific seed-free elastic-net
  logistic fallbacks.

## Methodology

- Entire tournament seasons are held out; there is no shuffled game-level
  validation.
- Feature selection, imputation, scaling, tuning, early stopping, calibration,
  and blending are fitted only inside the training boundary.
- Men-only, women-only, pooled, and partial-pooling architectures are compared.
- Logistic regression, histogram boosting, XGBoost, LightGBM, PyTorch,
  TensorFlow, and point-margin models are evaluated under matched folds.
- Matchup reversal is enforced so that `P(A beats B) + P(B beats A) = 1`.
- A locked 2022-2025 benchmark is consumed once under a frozen recipe.
- Long-running work is checkpointed and Stage 2 scoring is batch-resumable.

## Workflow

```mermaid
flowchart LR
    A[Raw Kaggle files] --> B[00 Data audit]
    B --> C[01 Split contract and snapshots]
    C --> D[02 Feature store and diagnostics]
    D --> E[03 Nested model comparison]
    E --> F[04 Locked benchmark and final scoring]
    F --> G[Audited submissions and bracket probabilities]
```

## Canonical notebooks

1. `00_data_audit_and_preparation.ipynb`
2. `01_split_protocol_and_pre_tournament_snapshots.ipynb`
3. `02_feature_store_and_diagnostics.ipynb`
4. `03_model_comparison_and_diagnostics.ipynb`
5. `04_locked_benchmark_and_final_submission.ipynb`

## Documentation

- [Data card](docs/DATA_CARD.md)
- [Validation protocol](docs/VALIDATION_PROTOCOL.md)
- [Results](docs/RESULTS.md)
- [Reproducibility](docs/REPRODUCIBILITY.md)
- [Submission portfolio](docs/SUBMISSION_PORTFOLIO.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)
- [Next model experiments](docs/NEXT_EXPERIMENTS.md)
- [Final model card](reports/final_2026/MODEL_CARD.md)

## One-command candidate and quality workflow

After notebooks 00-04 have completed:

```bat
python scripts\\portfolio_release.py all --root .
```

The command evaluates more than 500 deterministic primary/challenger
combinations, writes a diverse shortlist, creates score and diversity reports,
and runs the repository quality gate. No model retraining occurs.

## Data setup

Download the competition ZIP manually and extract the CSV files directly into:

```text
data/raw/march-machine-learning-mania-2026/
```

Raw data, processed matrices, model caches, model binaries, and complete
submission files are intentionally excluded from Git.

## Scientific status of later submissions

The three original submissions were produced by the frozen notebook 04
workflow. Any candidate generated after observing the 2026 scores is labeled
as post-result sensitivity analysis. It is not presented as an untouched
confirmatory test.

## License

MIT. See [LICENSE](LICENSE).
"""


DATA_CARD_TEXT = """
# Data Card

## Source

The project uses the official Kaggle March Machine Learning Mania 2026 data.
The files cover men's and women's teams, seasons, regular-season and tournament
results, seeds, detailed box scores, cities, conferences, coaches, public
rankings, and bracket structure.

## Prediction unit

Each prediction is identified as:

```text
Season_LowerTeamID_HigherTeamID
```

The target is the probability that the lower-ID team wins. Men's TeamIDs and
women's TeamIDs occupy separate numeric ranges.

## Historical coverage

- Men's compact results begin in 1985.
- Women's compact results begin in 1998.
- Men's detailed box scores begin in 2003.
- Women's detailed box scores begin in 2010.
- Approximately 1.5% of women's detailed games from 2010-2012 are unavailable.
- Expected women's detailed coverage is complete from 2013 forward.
- Public Massey rankings and coaching records are men-only sources.

## Information boundary

Regular-season inputs are restricted to DayNum 132 or earlier, corresponding
to Selection Sunday. Same-season NCAA tournament outcomes are never used to
construct the pre-tournament team snapshot.

## Known limitations

- Tournament labels are sparse relative to the feature universe.
- Data availability differs between the men's and women's tournaments.
- Player injuries, roster continuity, transfers, and market odds are not
  consistently available historically in the competition files.
- Some possession estimates are diagnostic approximations.

## Data quality controls

The pipeline checks unique game keys, score consistency, TeamID and gender
consistency, detailed-versus-compact coverage, shooting constraints,
possession disagreement, matchup orientation, and exact submission order.

## Distribution policy

The repository does not redistribute the raw competition files. Users must
download the data from Kaggle. Raw, interim, and processed data remain local.
"""


VALIDATION_TEXT = """
# Validation Protocol

## Objective

Brier score is the primary objective. Threshold metrics are reported for
interpretation but do not select the final probability model.

## Split unit

An entire NCAA tournament season is indivisible. Games from one tournament
never appear partly in training and partly in validation.

## Development evaluation

Notebook 03 uses matched expanding-window folds:

```text
Train on seasons before 2016 -> validate 2016
Train on seasons before 2017 -> validate 2017
Train on seasons before 2018 -> validate 2018
Train on seasons before 2019 -> validate 2019
Train on seasons before 2021 -> validate 2021
```

The 2020 tournament is absent because it was not played.

## Nested inner folds

Earlier seasons inside each outer training period select missing-value
handling, scaling, features, hyperparameters, boosting rounds, neural training
length, calibration, and ensemble weights. The outer validation tournament
does not select any of those components.

## Architecture comparison

The project compares separate men's and women's models, pooled common-feature
models, partial pooling, direct probability classification, and point-margin
regression followed by calibration. Men-only inputs are not imputed as
artificial women's features.

## Locked benchmark

The 2022-2025 tournaments form a locked benchmark. Notebook 04 evaluates the
frozen recipe using:

1. **Prequential refit:** use only seasons before each benchmark year.
2. **Static block:** fit through 2021 and hold the model fixed.

The benchmark does not reopen feature engineering, model selection, tuning,
calibration-family selection, or blend-weight selection.

## Calibration and symmetry

Calibration uses out-of-fold predictions. Matchups are predicted in both
orientations and symmetrized so that:

```text
P(A beats B) + P(B beats A) = 1
```

## Uncertainty

Comparisons include season-level variability and season-clustered bootstrap
intervals because games within a tournament are dependent.

## Later submissions

Candidates created after observing 2026 scores are labeled post-result
sensitivity analysis and are kept separate from the original locked test.
"""


RESULTS_TEXT = """
# Results

## Submitted products

| Product | Kaggle Brier score | Difference from challenger |
|---|---:|---:|
| **Challenger** | **0.1299012** | — |
| Development blend | 0.1318165 | +0.0019153 |
| Primary | 0.1421117 | +0.0122105 |

The challenger reduced Brier loss by 8.59% relative to the primary and by
1.45% relative to the development blend. Relative to a neutral 0.50 forecast,
the challenger reduced squared probability loss by approximately 48.0%.

## Challenger composition

| Tournament | Architecture | Model | Route |
|---|---|---|---|
| Men | Pooled common-feature | Histogram gradient boosting | Rich seed-aware |
| Women | Pooled common-feature | XGBoost classifier | Rich seed-aware |
| Unseeded rows | Separate by gender | Elastic-net logistic | Rich seed-free |

## Development study

Notebook 03 completed 180 matched tasks across three training contexts, five
held-out seasons, and twelve model families. PyTorch and TensorFlow tabular
MLPs were evaluated alongside linear, boosting, ensemble, and point-margin
systems. Neither neural implementation was the leading individual model under
the matched development folds.

## Locked benchmark

- The men's separate elastic-net primary generalized better than the pooled
  histogram challenger on 2022-2025.
- The women's pooled XGBoost challenger generalized better than the pooled
  seed-logistic primary.
- The development blend had the best combined locked score among the three
  frozen whole-submission products.
- Prequential and static-block rankings were similar.

## Interpretation of the live score

The live score establishes that the joint challenger package was strongest
among the three original submissions. It does not identify whether the men's
histogram model, the women's XGBoost model, or both drove the gain. The first
two later candidates therefore swap the tournament routes independently.

## Reporting discipline

The original notebook 03 development study and notebook 04 locked benchmark
remain unchanged. Later scores are recorded in
`reports/submission_portfolio/kaggle_scores.csv`.
"""


REPRO_TEXT = """
# Reproducibility

## Environment

- Windows 11
- Python 3.12
- Miniforge environment: `ml-modeling`

```bat
conda activate ml-modeling
python --version
python -m pip check
```

## Data placement

Extract the competition CSV files directly into:

```text
data/raw/march-machine-learning-mania-2026/
```

## Canonical execution order

```text
00 -> 01 -> 02 -> 03 -> 04
```

Use the `Python (ml-modeling)` kernel.

## Resume behavior

Notebook 03 stores fold-level tuning, prediction, and explanation checkpoints.
Notebook 04 stores benchmark tasks, final model bundles, and Stage 2 chunks.
Reruns verify hashes before reusing completed work. Generated artifacts remain
local and excluded from Git.

## Generate later submission candidates

```bat
python scripts\\portfolio_release.py generate --root . --top 12
```

The generator reads:

```text
data/processed/locked_benchmark_predictions.parquet
data/processed/stage2_predictions_2026.parquet
```

It does not retrain models.

## Run the quality gate

```bat
python scripts\\portfolio_release.py check --root .
```

## One-command workflow

```bat
python scripts\\portfolio_release.py all --root .
```

## Record a score

```bat
python scripts\\portfolio_release.py record-score ^
  --root . ^
  --candidate m_primary_w_challenger ^
  --score 0.1287654 ^
  --notes "Submitted on Kaggle"
```

## Release verification

```bat
python -m ruff check src tests scripts
python -m pytest -q
python scripts\\repository_release_audit.py --root .
git status
```
"""


SUBMISSION_TEXT = """
# Submission Candidate Portfolio

## Purpose

The original primary, challenger, and development-blend submissions have
already been scored. This workflow exhausts the most useful deterministic
recombinations of those frozen probability streams without model retraining.

## Candidate space

The generator evaluates:

- two tournament-route hybrids;
- a 21 by 21 grid of men's and women's primary weights;
- gender-specific challenger logit scaling;
- gender-specific shrinkage toward 0.5;
- route hybrids combined with logit scaling;
- explicitly labeled edge sensitivities.

More than 500 candidates are evaluated under both prequential and static
historical protocols. Only a diverse audited shortlist is written as complete
132,133-row CSV files.

## Highest-information submissions

1. `m_primary_w_challenger`
2. `m_challenger_w_primary`

Together with the original primary and challenger files, these form a two by
two factorial comparison and reveal which tournament-specific route drove the
improvement.

## Historical prioritization

The robustness score combines prequential macro Brier, static-block macro
Brier, worst gender-season Brier, and disagreement between protocols.

## Candidate diversity

For every candidate, the report records correlation with the challenger,
absolute prediction differences, row counts above difference thresholds,
prediction bounds, and file hashes. Near-duplicates are suppressed from the
default shortlist.

## Commands

```bat
python scripts\\portfolio_release.py generate --root . --top 12
```

```bat
python scripts\\portfolio_release.py record-score ^
  --root . ^
  --candidate CANDIDATE_NAME ^
  --score BRIER_SCORE ^
  --notes "DESCRIPTION"
```

## Submission order

1. Submit the two route hybrids.
2. Submit the leading historically robust blend.
3. Submit the leading temperature variant.
4. Submit the leading shrinkage variant.
5. Submit more only when they add meaningful prediction diversity.

## Scientific labeling

Every new candidate is post-result sensitivity analysis. Do not rewrite the
original locked-benchmark claims after observing another leaderboard score.
"""


CHECKLIST_TEXT = """
# Release Checklist

## Modeling evidence

- [x] Whole-season temporal validation
- [x] Nested model selection and calibration
- [x] Separate, pooled, and partial-pooling architectures
- [x] Linear, tree, neural, ensemble, and point-margin models
- [x] Feature-block ablation
- [x] Matchup symmetry
- [x] Locked 2022-2025 benchmark
- [x] Restartable training and scoring
- [x] Audited 2026 submissions
- [x] Live scores recorded

## Repository quality

- [ ] Five canonical notebooks only
- [ ] Ruff passes
- [ ] Pytest passes
- [ ] CI passes
- [ ] Release audit passes
- [ ] Generated data and caches are not tracked
- [ ] README shows results and methodology
- [ ] Documentation exists and is linked
- [ ] Candidate submissions have hashes and a score log
- [ ] Git working tree is clean
- [ ] Release tag points to the clean commit

## Final commands

```bat
python scripts\\portfolio_release.py all --root .
git status
git add -A
git status
git commit -m "Add portfolio documentation and candidate workflow"
git push origin main
```

After the quality gate passes:

```bat
git tag -a v1.1.0 -m "Portfolio documentation and candidate workflow"
git push origin v1.1.0
```

## External-review test

A reviewer should be able to identify the task, live score, validation design,
model families, final routes, reproducibility path, and limitations within
five minutes of opening the repository.
"""


CI_TEXT = """
name: quality-gate

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - name: Install test dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e .
          python -m pip install pytest ruff nbformat pandas numpy pyyaml plotly
      - name: Ruff
        run: python -m ruff check src tests scripts
      - name: Tests
        run: python -m pytest -q
      - name: Portfolio structure
        run: python scripts/portfolio_release.py check --root . --ci
"""


CITATION_TEXT = """
cff-version: 1.2.0
title: NCAA Tournament Probability Forecasting
type: software
authors:
  - family-names: Mendizabal
    given-names: Alvaro
version: 1.1.0
date-released: 2026-08-31
url: https://github.com/alvaromendizabal/march-machine-learning-mania-2026
repository-code: >-
  https://github.com/alvaromendizabal/march-machine-learning-mania-2026
license: MIT
message: >-
  Please cite this repository and the Kaggle March Machine Learning Mania 2026
  competition when reusing the methodology or software.
"""


CONFIG_TEXT = """
candidate_generation:
  top_n: 12
  primary_weight_grid:
    - 0.00
    - 0.05
    - 0.10
    - 0.15
    - 0.20
    - 0.25
    - 0.30
    - 0.35
    - 0.40
    - 0.45
    - 0.50
    - 0.55
    - 0.60
    - 0.65
    - 0.70
    - 0.75
    - 0.80
    - 0.85
    - 0.90
    - 0.95
    - 1.00
  temperature_grid: [0.80, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20]
  shrinkage_grid: [0.90, 0.95, 0.98, 1.00]
  hybrid_temperature_grid: [0.90, 1.00, 1.10]
  include_risk_candidates: true
  edge_thresholds: [0.01, 0.02, 0.03]
  edge_value: 0.001

known_kaggle_scores:
  challenger: 0.1299012
  development_blend: 0.1318165
  primary: 0.1421117
score_observed_at_utc: "2026-08-31T00:00:00Z"
"""


TEST_TEXT = """
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "portfolio_release.py"
SPEC = importlib.util.spec_from_file_location("portfolio_release", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_temperature_preserves_symmetry() -> None:
    probability = np.array([0.1, 0.25, 0.6, 0.9])
    forward = MODULE.temperature_scale(probability, 1.15)
    reverse = MODULE.temperature_scale(1.0 - probability, 1.15)
    np.testing.assert_allclose(forward + reverse, 1.0, atol=1e-12)


def test_shrinkage_preserves_symmetry() -> None:
    probability = np.array([0.05, 0.3, 0.7, 0.95])
    forward = MODULE.shrink_to_half(probability, 0.93)
    reverse = MODULE.shrink_to_half(1.0 - probability, 0.93)
    np.testing.assert_allclose(forward + reverse, 1.0, atol=1e-12)


def test_gender_hybrid_uses_expected_streams() -> None:
    frame = pd.DataFrame(
        {
            "Gender": ["M", "W"],
            "primary": [0.2, 0.3],
            "challenger": [0.8, 0.7],
            "development_blend": [0.5, 0.5],
        }
    )
    specification = MODULE.CandidateSpec(
        name="m_primary_w_challenger",
        family="gender_hybrid",
        m_primary_weight=1.0,
        w_primary_weight=0.0,
    )
    prediction = MODULE.candidate_prediction(
        frame,
        specification,
        primary_column="primary",
        challenger_column="challenger",
        blend_column="development_blend",
    )
    np.testing.assert_allclose(prediction, [0.2, 0.7])


def test_gender_parser_uses_team_id_ranges() -> None:
    ids = pd.Series(["2026_1101_1102", "2026_3101_3102"])
    assert MODULE.parse_gender(ids).tolist() == ["M", "W"]
"""


SCORE_LOG_TEXT = """
Candidate,KaggleBrier,ObservedAtUTC,Notes
challenger,0.1299012,2026-08-31T00:00:00Z,Observed score supplied by author.
development_blend,0.1318165,2026-08-31T00:00:00Z,Observed score supplied by author.
primary,0.1421117,2026-08-31T00:00:00Z,Observed score supplied by author.
"""


NEXT_EXPERIMENTS_TEXT = r'''
# Next Model Experiments

## Governance

Notebooks 03 and 04 define the completed version-1 experiment. Their
development decisions, locked benchmark, and original 2026 submissions remain
unchanged. Any new model trained after observing the 2026 scores belongs to a
new, explicitly post-result research track.

## Priority 1: Multi-seed challenger bagging

Refit the existing men's histogram-boosting and women's XGBoost challenger
procedures across several deterministic seeds while keeping features,
hyperparameter ranges, folds, and calibration rules fixed. Average the
probabilities across seeds.

Promotion gate:

- lower macro season Brier under the full rolling-origin backtest;
- no material worsening in worst-season Brier;
- stable calibration by tournament;
- meaningful prediction diversity versus the current challenger.

## Priority 2: Point-margin ensemble

Train a strongly regularized XGBoost or LightGBM regressor on tournament point
margin, then convert out-of-fold margins to probabilities with a smooth,
symmetric calibrator. Margin targets distinguish one-point wins from large
wins and can provide complementary signal to direct classification.

Promotion gate:

- improvement under identical temporal folds;
- calibrator fitted only on out-of-fold margin predictions;
- stable tails and no extreme-probability collapse.

## Priority 3: Gender-specific constrained stacking

Use historical out-of-fold predictions from:

- elastic-net logistic regression;
- histogram gradient boosting;
- XGBoost;
- LightGBM;
- point-margin regression;
- one bounded neural model.

Fit nonnegative weights separately for men and women, constrain each set of
weights to sum to one, and penalize concentration. The neural model earns
weight only when its errors are genuinely complementary.

## Priority 4: Season-model averaging

Retain one model per historical held-out season and average all legal
season-model predictions for the target year. This reduces variance and
creates diversity without expanding feature dimensionality.

## Priority 5: Historically versioned external information

Potential high-value additions include:

- opponent-adjusted efficiency from an external rating provider;
- returning minutes and returning production;
- roster and transfer continuity;
- injuries known before the submission deadline;
- player-level talent or recruiting composites;
- travel distance, time-zone change, and altitude;
- historically available market-implied probabilities.

Every source requires an as-of timestamp and historical backfill. Current
values must never be joined retrospectively into older seasons.

## Runtime limits

New experiments should retain:

- one model at a time;
- float32 matrices;
- bounded feature caps;
- histogram-based tree training;
- checkpointed folds and seeds;
- restartable candidate-level artifacts;
- no unrestricted hyperparameter sweeps.

## Final standard for a new version

A version-2 model is promoted only when it improves rolling-origin evidence,
maintains calibration and worst-season behavior, passes the same leakage and
symmetry tests, and is frozen before a future prospective tournament.
'''


TEMPLATES = {
    "README.md": README_TEXT,
    "docs/DATA_CARD.md": DATA_CARD_TEXT,
    "docs/VALIDATION_PROTOCOL.md": VALIDATION_TEXT,
    "docs/RESULTS.md": RESULTS_TEXT,
    "docs/REPRODUCIBILITY.md": REPRO_TEXT,
    "docs/SUBMISSION_PORTFOLIO.md": SUBMISSION_TEXT,
    "docs/RELEASE_CHECKLIST.md": CHECKLIST_TEXT,
    "docs/NEXT_EXPERIMENTS.md": NEXT_EXPERIMENTS_TEXT,
    ".github/workflows/ci.yml": CI_TEXT,
    "CITATION.cff": CITATION_TEXT,
    "configs/submission_portfolio.yaml": CONFIG_TEXT,
    "tests/test_portfolio_release.py": TEST_TEXT,
    "reports/submission_portfolio/kaggle_scores.csv": SCORE_LOG_TEXT,
    "docs/assets/.gitkeep": "",
}


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    family: str
    source: str | None = None
    m_primary_weight: float = 0.0
    w_primary_weight: float = 0.0
    m_temperature: float = 1.0
    w_temperature: float = 1.0
    m_shrinkage: float = 1.0
    w_shrinkage: float = 1.0
    edge_threshold: float | None = None
    edge_value: float = 0.001
    risk_profile: str = "standard"
    rationale: str = ""

    def signature(self) -> tuple[Any, ...]:
        return (
            self.source,
            round(self.m_primary_weight, 8),
            round(self.w_primary_weight, 8),
            round(self.m_temperature, 8),
            round(self.w_temperature, 8),
            round(self.m_shrinkage, 8),
            round(self.w_shrinkage, 8),
            self.edge_threshold,
            round(self.edge_value, 8),
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def atomic_json(path: Path, payload: Any) -> None:
    atomic_text(path, json.dumps(payload, indent=2, default=str))


def atomic_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_parquet(path)


def clip_probability(values: Any) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), EPSILON, 1.0 - EPSILON)


def temperature_scale(probability: Any, multiplier: float) -> np.ndarray:
    probability = clip_probability(probability)
    logits = np.log(probability / (1.0 - probability))
    return clip_probability(
        1.0 / (1.0 + np.exp(-float(multiplier) * logits))
    )


def shrink_to_half(probability: Any, factor: float) -> np.ndarray:
    probability = clip_probability(probability)
    return clip_probability(0.5 + float(factor) * (probability - 0.5))


def edge_adjust(
    probability: Any,
    threshold: float | None,
    edge_value: float,
) -> np.ndarray:
    output = clip_probability(probability).copy()
    if threshold is None:
        return output
    output[output <= float(threshold)] = float(edge_value)
    output[output >= 1.0 - float(threshold)] = 1.0 - float(edge_value)
    return clip_probability(output)


def parse_gender(ids: pd.Series) -> pd.Series:
    team_one = ids.astype(str).str.split("_", expand=True)[1].astype(int)
    return pd.Series(
        np.where(team_one < 3000, "M", "W"),
        index=ids.index,
    )


def transform_streams(
    gender: Any,
    primary: Any,
    challenger: Any,
    specification: CandidateSpec,
) -> np.ndarray:
    gender = np.asarray(gender, dtype=str)
    primary = clip_probability(primary)
    challenger = clip_probability(challenger)
    output = np.empty(len(primary), dtype=float)

    settings = [
        (
            "M",
            specification.m_primary_weight,
            specification.m_temperature,
            specification.m_shrinkage,
        ),
        (
            "W",
            specification.w_primary_weight,
            specification.w_temperature,
            specification.w_shrinkage,
        ),
    ]
    for label, weight, temperature, shrinkage in settings:
        mask = gender == label
        if not np.any(mask):
            continue
        blended = (
            float(weight) * primary[mask]
            + (1.0 - float(weight)) * challenger[mask]
        )
        transformed = temperature_scale(blended, float(temperature))
        transformed = shrink_to_half(transformed, float(shrinkage))
        output[mask] = edge_adjust(
            transformed,
            specification.edge_threshold,
            specification.edge_value,
        )
    return clip_probability(output)


def candidate_prediction(
    frame: pd.DataFrame,
    specification: CandidateSpec,
    *,
    primary_column: str,
    challenger_column: str,
    blend_column: str | None,
) -> np.ndarray:
    if specification.source is not None:
        mapping = {
            "primary": primary_column,
            "challenger": challenger_column,
            "development_blend": blend_column,
        }
        column = mapping[specification.source]
        if column is None or column not in frame.columns:
            raise KeyError(
                f"Source column for {specification.source!r} is unavailable."
            )
        return clip_probability(frame[column])
    return transform_streams(
        frame["Gender"],
        frame[primary_column],
        frame[challenger_column],
        specification,
    )


def add_candidate(
    records: dict[tuple[Any, ...], CandidateSpec],
    specification: CandidateSpec,
) -> None:
    signature = specification.signature()
    if signature not in records:
        records[signature] = specification


def build_candidate_specs(config: dict[str, Any]) -> list[CandidateSpec]:
    records: dict[tuple[Any, ...], CandidateSpec] = {}

    exact = [
        CandidateSpec(
            name="primary",
            family="existing",
            source="primary",
            rationale="Previously submitted primary stream.",
        ),
        CandidateSpec(
            name="challenger",
            family="existing",
            source="challenger",
            rationale="Previously submitted challenger stream.",
        ),
        CandidateSpec(
            name="development_blend",
            family="existing",
            source="development_blend",
            rationale="Previously submitted development-frozen blend.",
        ),
        CandidateSpec(
            name="m_primary_w_challenger",
            family="gender_hybrid",
            m_primary_weight=1.0,
            w_primary_weight=0.0,
            rationale=(
                "Men's primary with women's challenger; highest-information "
                "tournament-route hybrid."
            ),
        ),
        CandidateSpec(
            name="m_challenger_w_primary",
            family="gender_hybrid",
            m_primary_weight=0.0,
            w_primary_weight=1.0,
            rationale=(
                "Factorial counterpart used to isolate each tournament route."
            ),
        ),
    ]
    for specification in exact:
        add_candidate(records, specification)

    weights = [float(value) for value in config["primary_weight_grid"]]
    for men_weight in weights:
        for women_weight in weights:
            name = (
                f"blend_mprimary_{int(round(men_weight * 100)):03d}_"
                f"wprimary_{int(round(women_weight * 100)):03d}"
            )
            add_candidate(
                records,
                CandidateSpec(
                    name=name,
                    family="gender_weight_grid",
                    m_primary_weight=men_weight,
                    w_primary_weight=women_weight,
                    rationale="Gender-specific convex primary/challenger blend.",
                ),
            )

    temperatures = [float(value) for value in config["temperature_grid"]]
    for men_value in temperatures:
        for women_value in temperatures:
            name = (
                f"challenger_temperature_m_{men_value:.2f}_"
                f"w_{women_value:.2f}"
            ).replace(".", "p")
            add_candidate(
                records,
                CandidateSpec(
                    name=name,
                    family="challenger_temperature",
                    m_temperature=men_value,
                    w_temperature=women_value,
                    rationale="Gender-specific symmetric logit scaling.",
                ),
            )

    shrinkages = [float(value) for value in config["shrinkage_grid"]]
    for men_value in shrinkages:
        for women_value in shrinkages:
            name = (
                f"challenger_shrink_m_{men_value:.2f}_w_{women_value:.2f}"
            ).replace(".", "p")
            add_candidate(
                records,
                CandidateSpec(
                    name=name,
                    family="challenger_shrinkage",
                    m_shrinkage=men_value,
                    w_shrinkage=women_value,
                    rationale="Gender-specific shrinkage toward 0.5.",
                ),
            )

    hybrid_values = [
        float(value) for value in config["hybrid_temperature_grid"]
    ]
    bases = [
        ("mprimary_wchallenger", 1.0, 0.0),
        ("mchallenger_wprimary", 0.0, 1.0),
        ("challenger", 0.0, 0.0),
    ]
    for base_name, men_weight, women_weight in bases:
        for men_value in hybrid_values:
            for women_value in hybrid_values:
                name = (
                    f"{base_name}_temperature_m_{men_value:.2f}_"
                    f"w_{women_value:.2f}"
                ).replace(".", "p")
                add_candidate(
                    records,
                    CandidateSpec(
                        name=name,
                        family="hybrid_temperature",
                        m_primary_weight=men_weight,
                        w_primary_weight=women_weight,
                        m_temperature=men_value,
                        w_temperature=women_value,
                        rationale="Route hybrid with symmetric logit scaling.",
                    ),
                )

    if bool(config.get("include_risk_candidates", True)):
        for threshold in config["edge_thresholds"]:
            name = f"challenger_edge_{float(threshold):.3f}".replace(".", "p")
            add_candidate(
                records,
                CandidateSpec(
                    name=name,
                    family="edge_adjustment",
                    edge_threshold=float(threshold),
                    edge_value=float(config["edge_value"]),
                    risk_profile="risk_seeking",
                    rationale="Explicitly labeled high-variance sensitivity.",
                ),
            )

    return sorted(records.values(), key=lambda item: (item.family, item.name))


def load_stage2(path: Path) -> pd.DataFrame:
    frame = read_frame(path).copy()
    required = {"ID", "PredPrimary", "PredChallenger", "PredBlend"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise KeyError(f"Stage 2 artifact is missing columns: {missing}")
    if "Gender" not in frame.columns:
        frame["Gender"] = parse_gender(frame["ID"])
    if not frame["ID"].is_unique:
        raise AssertionError("Stage 2 IDs are not unique.")
    return frame.reset_index(drop=True)


def load_benchmark(path: Path) -> pd.DataFrame:
    frame = read_frame(path)
    required = {
        "Protocol",
        "Gender",
        "Season",
        "TargetKey",
        "Team1Win",
        "Role",
        "Prediction",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise KeyError(f"Benchmark artifact is missing columns: {missing}")

    index_columns = [
        "Protocol",
        "Gender",
        "Season",
        "TargetKey",
        "Team1Win",
    ]
    pivot = (
        frame.loc[
            frame["Role"].isin(
                ["primary", "challenger", "development_blend"]
            ),
            [*index_columns, "Role", "Prediction"],
        ]
        .pivot_table(
            index=index_columns,
            columns="Role",
            values="Prediction",
            aggfunc="first",
        )
        .reset_index()
    )
    pivot.columns.name = None
    roles = {"primary", "challenger", "development_blend"}
    missing_roles = sorted(roles.difference(pivot.columns))
    if missing_roles:
        raise KeyError(f"Benchmark artifact is missing roles: {missing_roles}")
    return pivot


def evaluate_candidate(
    benchmark: pd.DataFrame,
    specification: CandidateSpec,
) -> dict[str, float]:
    prediction = candidate_prediction(
        benchmark,
        specification,
        primary_column="primary",
        challenger_column="challenger",
        blend_column="development_blend",
    )
    scored = benchmark[
        ["Protocol", "Gender", "Season", "Team1Win"]
    ].copy()
    scored["SquaredError"] = (
        prediction - scored["Team1Win"].to_numpy(dtype=float)
    ) ** 2
    grouped = (
        scored.groupby(
            ["Protocol", "Gender", "Season"],
            observed=True,
        )["SquaredError"]
        .mean()
        .reset_index()
    )

    output: dict[str, float] = {}
    protocols = [
        ("prequential_refit", "Prequential"),
        ("static_block", "Static"),
    ]
    for protocol, prefix in protocols:
        game_rows = scored.loc[scored["Protocol"].eq(protocol)]
        season_rows = grouped.loc[grouped["Protocol"].eq(protocol)]
        output[f"{prefix}GameBrier"] = float(
            game_rows["SquaredError"].mean()
        )
        output[f"{prefix}MacroBrier"] = float(
            season_rows["SquaredError"].mean()
        )
        output[f"{prefix}WorstGenderSeasonBrier"] = float(
            season_rows["SquaredError"].max()
        )
        for gender in ("M", "W"):
            gender_rows = season_rows.loc[
                season_rows["Gender"].eq(gender)
            ]
            output[f"{prefix}{gender}MacroBrier"] = float(
                gender_rows["SquaredError"].mean()
            )

    output["ProtocolGap"] = abs(
        output["PrequentialMacroBrier"] - output["StaticMacroBrier"]
    )
    output["RobustHistoricalScore"] = (
        0.55 * output["PrequentialMacroBrier"]
        + 0.25 * output["StaticMacroBrier"]
        + 0.15 * output["PrequentialWorstGenderSeasonBrier"]
        + 0.05 * output["ProtocolGap"]
    )
    return output


def diversity_metrics(
    reference: np.ndarray,
    candidate: np.ndarray,
) -> dict[str, float | int]:
    difference = np.abs(candidate - reference)
    return {
        "CorrelationWithChallenger": float(
            np.corrcoef(reference, candidate)[0, 1]
        ),
        "MeanAbsoluteDifference": float(difference.mean()),
        "P95AbsoluteDifference": float(np.quantile(difference, 0.95)),
        "MaximumAbsoluteDifference": float(difference.max()),
        "RowsDifferentBy002": int(np.sum(difference >= 0.02)),
        "RowsDifferentBy005": int(np.sum(difference >= 0.05)),
    }


def load_config(root: Path) -> dict[str, Any]:
    path = root / "configs" / "submission_portfolio.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_score_log(root: Path, config: dict[str, Any]) -> pd.DataFrame:
    path = root / "reports" / "submission_portfolio" / "kaggle_scores.csv"
    configured = pd.DataFrame(
        [
            {
                "Candidate": name,
                "KaggleBrier": float(score),
                "ObservedAtUTC": config.get("score_observed_at_utc", ""),
                "Notes": "Observed score supplied by project author.",
            }
            for name, score in config["known_kaggle_scores"].items()
        ]
    )
    if path.exists():
        existing = pd.read_csv(path)
        configured = pd.concat([existing, configured], ignore_index=True)
        configured = configured.drop_duplicates("Candidate", keep="first")
    atomic_csv(path, configured)
    return configured


def build_catalog(
    stage2: pd.DataFrame,
    benchmark: pd.DataFrame,
    specifications: list[CandidateSpec],
    scores: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    score_map = (
        scores.set_index("Candidate")["KaggleBrier"].to_dict()
        if not scores.empty
        else {}
    )
    reference = stage2["PredChallenger"].to_numpy(dtype=float)
    predictions: dict[str, np.ndarray] = {}
    records: list[dict[str, Any]] = []

    for order, specification in enumerate(specifications, start=1):
        probability = candidate_prediction(
            stage2,
            specification,
            primary_column="PredPrimary",
            challenger_column="PredChallenger",
            blend_column="PredBlend",
        )
        predictions[specification.name] = probability
        records.append(
            {
                "Candidate": specification.name,
                "Family": specification.family,
                "RiskProfile": specification.risk_profile,
                "Rationale": specification.rationale,
                "KaggleBrier": score_map.get(
                    specification.name,
                    np.nan,
                ),
                **asdict(specification),
                **evaluate_candidate(benchmark, specification),
                **diversity_metrics(reference, probability),
                "CatalogOrder": order,
                "ScientificStatus": "post_result_sensitivity",
            }
        )

    catalog = pd.DataFrame(records).sort_values(
        ["RobustHistoricalScore", "RiskProfile", "Candidate"]
    )
    catalog["HistoricalRank"] = np.arange(1, len(catalog) + 1)
    return catalog.reset_index(drop=True), predictions


def select_shortlist(
    catalog: pd.DataFrame,
    predictions: dict[str, np.ndarray],
    top_n: int,
) -> pd.DataFrame:
    selected = [
        "m_primary_w_challenger",
        "m_challenger_w_primary",
    ]
    exact_duplicate_names = {
        "blend_mprimary_000_wprimary_000",
        "blend_mprimary_100_wprimary_100",
    }
    eligible = catalog.loc[
        ~catalog["Candidate"].isin(
            [
                "primary",
                "challenger",
                "development_blend",
                *selected,
                *exact_duplicate_names,
            ]
        )
        & catalog["RiskProfile"].eq("standard")
        & catalog["MeanAbsoluteDifference"].ge(0.0005)
    ].copy()

    family_best = (
        eligible.sort_values("RobustHistoricalScore")
        .groupby("Family", observed=True)
        .head(1)
    )
    for name in family_best["Candidate"]:
        if len(selected) >= top_n:
            break
        selected.append(str(name))

    for name in eligible.sort_values("RobustHistoricalScore")["Candidate"]:
        if len(selected) >= top_n:
            break
        name = str(name)
        if name in selected:
            continue
        probability = predictions[name]
        duplicate = False
        for prior in selected:
            difference = float(
                np.abs(probability - predictions[prior]).mean()
            )
            correlation = float(
                np.corrcoef(probability, predictions[prior])[0, 1]
            )
            if difference < 0.0005 and correlation > 0.999995:
                duplicate = True
                break
        if not duplicate:
            selected.append(name)

    if len(selected) < top_n:
        for name in eligible["Candidate"]:
            name = str(name)
            if len(selected) >= top_n:
                break
            if name not in selected:
                selected.append(name)

    output = catalog.set_index("Candidate").loc[selected].reset_index()
    output.insert(
        0,
        "SubmissionPriority",
        np.arange(1, len(output) + 1),
    )
    return output


def safe_slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()[:90]


def write_submissions(
    root: Path,
    stage2: pd.DataFrame,
    shortlist: pd.DataFrame,
    predictions: dict[str, np.ndarray],
) -> pd.DataFrame:
    output_dir = root / "submissions"
    output_dir.mkdir(parents=True, exist_ok=True)
    ids = stage2["ID"].astype(str).reset_index(drop=True)
    records: list[dict[str, Any]] = []

    for row in shortlist.itertuples(index=False):
        name = str(row.Candidate)
        priority = int(row.SubmissionPriority)
        filename = (
            f"submission_2026_candidate_{priority:02d}_"
            f"{safe_slug(name)}.csv"
        )
        path = output_dir / filename
        submission = pd.DataFrame(
            {
                "ID": ids,
                "Pred": clip_probability(predictions[name]),
            }
        )
        if not submission["ID"].equals(ids):
            raise AssertionError("Submission order changed.")
        if not submission["ID"].is_unique:
            raise AssertionError("Submission IDs are not unique.")
        atomic_csv(path, submission)
        records.append(
            {
                "SubmissionPriority": priority,
                "Candidate": name,
                "Path": str(path.relative_to(root)),
                "Rows": len(submission),
                "MinimumPrediction": float(submission["Pred"].min()),
                "MaximumPrediction": float(submission["Pred"].max()),
                "MeanPrediction": float(submission["Pred"].mean()),
                "SHA256": sha256_file(path),
                "GeneratedAtUTC": utc_now(),
                "Status": "ready_to_submit",
            }
        )
    return pd.DataFrame(records)


def write_plot(root: Path, catalog: pd.DataFrame) -> str | None:
    try:
        import plotly.express as px
    except Exception:
        return None

    figure = px.scatter(
        catalog,
        x="MeanAbsoluteDifference",
        y="RobustHistoricalScore",
        color="Family",
        symbol="RiskProfile",
        hover_name="Candidate",
        hover_data=[
            "PrequentialMacroBrier",
            "StaticMacroBrier",
            "PrequentialMMacroBrier",
            "PrequentialWMacroBrier",
            "CorrelationWithChallenger",
            "KaggleBrier",
        ],
        title=(
            "Candidate trade-off: historical robustness versus "
            "difference from challenger"
        ),
        labels={
            "MeanAbsoluteDifference": "Mean absolute difference",
            "RobustHistoricalScore": "Historical score (lower is better)",
        },
        height=750,
    )
    path = (
        root
        / "reports"
        / "submission_portfolio"
        / "candidate_tradeoff.html"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(path, include_plotlyjs="cdn", full_html=True)
    return str(path.relative_to(root))


def write_candidate_reports(
    root: Path,
    catalog: pd.DataFrame,
    shortlist: pd.DataFrame,
    manifest: pd.DataFrame,
    plot_path: str | None,
) -> None:
    report_dir = root / "reports" / "submission_portfolio"
    atomic_csv(report_dir / "candidate_catalog.csv", catalog)
    atomic_csv(report_dir / "shortlist.csv", shortlist)
    atomic_csv(report_dir / "submission_manifest.csv", manifest)

    diversity_columns = [
        "Candidate",
        "Family",
        "CorrelationWithChallenger",
        "MeanAbsoluteDifference",
        "P95AbsoluteDifference",
        "MaximumAbsoluteDifference",
        "RowsDifferentBy002",
        "RowsDifferentBy005",
    ]
    atomic_csv(
        report_dir / "prediction_diversity.csv",
        catalog[diversity_columns],
    )

    columns = [
        "SubmissionPriority",
        "Candidate",
        "Family",
        "PrequentialMacroBrier",
        "StaticMacroBrier",
        "RobustHistoricalScore",
        "MeanAbsoluteDifference",
        "CorrelationWithChallenger",
    ]
    report = f"""
# Generated Submission Shortlist

Generated: {utc_now()}

Every new candidate is post-result sensitivity analysis. No model was
retrained.

{shortlist[columns].to_markdown(index=False)}

Interactive report: {plot_path or "Plotly unavailable."}
"""
    atomic_text(report_dir / "README.md", report.strip() + "\n")
    atomic_json(
        report_dir / "generation_summary.json",
        {
            "status": "complete",
            "generated_at_utc": utc_now(),
            "catalog_candidates": int(len(catalog)),
            "shortlisted_candidates": int(len(shortlist)),
            "submission_files": int(len(manifest)),
            "scientific_status": "post_result_sensitivity",
            "plot": plot_path,
        },
    )


def install(root: Path, *, run_after: bool) -> int:
    root = root.resolve()
    notebook_names = sorted(
        path.name for path in (root / "notebooks").glob("*.ipynb")
    )
    if notebook_names != CANONICAL_NOTEBOOKS:
        raise RuntimeError(
            f"Expected exactly {CANONICAL_NOTEBOOKS}; found {notebook_names}."
        )

    for relative, content in TEMPLATES.items():
        destination = root / relative
        if (
            relative.endswith("kaggle_scores.csv")
            and destination.exists()
        ):
            continue
        atomic_text(destination, content.strip() + "\n")

    installed_script = root / "scripts" / "portfolio_release.py"
    installed_script.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).resolve(), installed_script)

    gitignore = root / ".gitignore"
    current = (
        gitignore.read_text(encoding="utf-8")
        if gitignore.exists()
        else ""
    )
    additions = [
        "data/model_cache/",
        "models/",
        "outputs/",
        "submissions/*.csv",
    ]
    missing = [line for line in additions if line not in current]
    if missing:
        updated = current.rstrip()
        updated += "\n\n# Generated project artifacts\n"
        updated += "\n".join(missing) + "\n"
        atomic_text(gitignore, updated)

    print("Documentation, CI, configuration, tests, and utility installed.")
    print("Notebooks 00-04 were not modified.")

    if run_after:
        status = generate(
            root,
            top_n=None,
            stage2_path=None,
            benchmark_path=None,
        )
        if status != 0:
            return status
        return check(root, ci=False)
    return 0


def load_paths(
    root: Path,
    stage2_path: Path | None,
    benchmark_path: Path | None,
) -> tuple[Path, Path]:
    stage2 = stage2_path or (
        root
        / "data"
        / "processed"
        / "stage2_predictions_2026.parquet"
    )
    benchmark = benchmark_path or (
        root
        / "data"
        / "processed"
        / "locked_benchmark_predictions.parquet"
    )
    return stage2, benchmark


def generate(
    root: Path,
    *,
    top_n: int | None,
    stage2_path: Path | None,
    benchmark_path: Path | None,
) -> int:
    root = root.resolve()
    config = yaml.safe_load(
        (
            root / "configs" / "submission_portfolio.yaml"
        ).read_text(encoding="utf-8")
    )
    generation = config["candidate_generation"]
    top_n = int(top_n or generation["top_n"])
    stage_path, benchmark_file = load_paths(
        root,
        stage2_path,
        benchmark_path,
    )
    stage2 = load_stage2(stage_path)
    benchmark = load_benchmark(benchmark_file)
    scores = load_score_log(root, config)
    specifications = build_candidate_specs(generation)
    catalog, predictions = build_catalog(
        stage2,
        benchmark,
        specifications,
        scores,
    )
    shortlist = select_shortlist(catalog, predictions, top_n)
    manifest = write_submissions(
        root,
        stage2,
        shortlist,
        predictions,
    )
    plot_path = write_plot(root, catalog)
    write_candidate_reports(
        root,
        catalog,
        shortlist,
        manifest,
        plot_path,
    )

    print(f"Candidates evaluated: {len(catalog):,}")
    print(f"Submission files written: {len(manifest):,}")
    print(
        shortlist[
            ["SubmissionPriority", "Candidate"]
        ].to_string(index=False)
    )
    return 0


def record_score(
    root: Path,
    candidate: str,
    score: float,
    notes: str,
) -> int:
    path = (
        root
        / "reports"
        / "submission_portfolio"
        / "kaggle_scores.csv"
    )
    if path.exists():
        frame = pd.read_csv(path)
    else:
        frame = pd.DataFrame(
            columns=[
                "Candidate",
                "KaggleBrier",
                "ObservedAtUTC",
                "Notes",
            ]
        )
    new_row = pd.DataFrame(
        [
            {
                "Candidate": candidate,
                "KaggleBrier": float(score),
                "ObservedAtUTC": utc_now(),
                "Notes": notes,
            }
        ]
    )
    frame = pd.concat(
        [frame.loc[~frame["Candidate"].eq(candidate)], new_row],
        ignore_index=True,
    )
    frame = frame.sort_values(
        "KaggleBrier",
        na_position="last",
    )
    atomic_csv(path, frame)
    print(frame.to_string(index=False))
    return 0


def record_scores_csv(
    root: Path,
    input_path: Path,
) -> int:
    """Merge a batch of observed Kaggle scores into the permanent ledger."""
    path = (
        root
        / "reports"
        / "submission_portfolio"
        / "kaggle_scores.csv"
    )
    incoming_path = (
        input_path
        if input_path.is_absolute()
        else root / input_path
    )
    incoming = pd.read_csv(incoming_path)
    required = {"Candidate", "KaggleBrier"}
    missing = sorted(required.difference(incoming.columns))
    if missing:
        raise KeyError(
            f"Score import is missing required columns: {missing}"
        )

    incoming = incoming.copy()
    incoming["Candidate"] = incoming["Candidate"].astype(str)
    incoming["KaggleBrier"] = pd.to_numeric(
        incoming["KaggleBrier"],
        errors="coerce",
    )
    incoming = incoming.loc[
        incoming["KaggleBrier"].notna()
    ].copy()
    if incoming.empty:
        raise ValueError(
            "The score import contains no nonblank Kaggle scores."
        )
    if not incoming["KaggleBrier"].between(0.0, 1.0).all():
        raise ValueError("Every Kaggle Brier score must be between 0 and 1.")

    if "ObservedAtUTC" not in incoming.columns:
        incoming["ObservedAtUTC"] = utc_now()
    else:
        incoming["ObservedAtUTC"] = incoming[
            "ObservedAtUTC"
        ].fillna(utc_now())
    if "Notes" not in incoming.columns:
        incoming["Notes"] = ""
    else:
        incoming["Notes"] = incoming["Notes"].fillna("")

    incoming = incoming[
        ["Candidate", "KaggleBrier", "ObservedAtUTC", "Notes"]
    ].drop_duplicates("Candidate", keep="last")

    if path.exists():
        existing = pd.read_csv(path)
    else:
        existing = pd.DataFrame(columns=incoming.columns)

    combined = pd.concat(
        [
            existing.loc[
                ~existing["Candidate"].isin(incoming["Candidate"])
            ],
            incoming,
        ],
        ignore_index=True,
    ).sort_values(
        ["KaggleBrier", "Candidate"],
        na_position="last",
    )
    atomic_csv(path, combined)

    print(
        f"Imported {len(incoming):,} scores from "
        f"{incoming_path}."
    )
    print(f"Score ledger: {path}")
    print(combined.to_string(index=False))
    return 0


def _inclusive_float_grid(
    minimum: float,
    maximum: float,
    step: float,
) -> list[float]:
    if step <= 0:
        raise ValueError("Grid step must be positive.")
    if maximum < minimum:
        raise ValueError("Grid maximum must be at least the minimum.")
    count = int(round((maximum - minimum) / step))
    values = [
        round(minimum + index * step, 10)
        for index in range(count + 1)
    ]
    if values[-1] < maximum - 1e-9:
        values.append(round(maximum, 10))
    return sorted(set(values))


def _temperature_candidate(
    men_value: float,
    women_value: float,
    *,
    rationale: str,
) -> CandidateSpec:
    name = (
        f"challenger_temperature_m_{men_value:.3f}_"
        f"w_{women_value:.3f}"
    ).replace(".", "p")
    return CandidateSpec(
        name=name,
        family="challenger_temperature_refinement",
        m_primary_weight=0.0,
        w_primary_weight=0.0,
        m_temperature=float(men_value),
        w_temperature=float(women_value),
        rationale=rationale,
    )


def build_refinement_specs(
    *,
    center_m: float,
    center_w: float,
    m_min: float,
    m_max: float,
    w_min: float,
    w_max: float,
    coarse_step: float,
    local_step: float,
    local_radius: float,
) -> list[CandidateSpec]:
    """Create coordinate slices plus a dense local two-dimensional grid."""
    specifications: dict[tuple[Any, ...], CandidateSpec] = {}

    men_axis = _inclusive_float_grid(m_min, m_max, coarse_step)
    women_axis = _inclusive_float_grid(w_min, w_max, coarse_step)

    for men_value in men_axis:
        candidate = _temperature_candidate(
            men_value,
            center_w,
            rationale=(
                "Men's temperature coordinate slice around the current "
                "best challenger transformation."
            ),
        )
        specifications[candidate.signature()] = candidate

    for women_value in women_axis:
        candidate = _temperature_candidate(
            center_m,
            women_value,
            rationale=(
                "Women's temperature coordinate slice around the current "
                "best challenger transformation."
            ),
        )
        specifications[candidate.signature()] = candidate

    local_m = _inclusive_float_grid(
        max(0.05, center_m - local_radius),
        center_m + local_radius,
        local_step,
    )
    local_w = _inclusive_float_grid(
        max(0.05, center_w - local_radius),
        center_w + local_radius,
        local_step,
    )
    for men_value in local_m:
        for women_value in local_w:
            candidate = _temperature_candidate(
                men_value,
                women_value,
                rationale=(
                    "Dense local challenger-temperature refinement around "
                    "the current best observed pair."
                ),
            )
            specifications[candidate.signature()] = candidate

    return sorted(
        specifications.values(),
        key=lambda item: (
            abs(item.m_temperature - center_m)
            + abs(item.w_temperature - center_w),
            item.m_temperature,
            item.w_temperature,
        ),
    )


def generate_refinement(
    root: Path,
    *,
    center_m: float,
    center_w: float,
    m_min: float,
    m_max: float,
    w_min: float,
    w_max: float,
    coarse_step: float,
    local_step: float,
    local_radius: float,
    top_n: int,
    round_name: str,
    stage2_path: Path | None,
    benchmark_path: Path | None,
    include_scored: bool,
) -> int:
    """Generate a focused, restartable round around a temperature winner."""
    root = root.resolve()
    config = load_config(root)
    stage_path, benchmark_file = load_paths(
        root,
        stage2_path,
        benchmark_path,
    )
    stage2 = load_stage2(stage_path)
    benchmark = load_benchmark(benchmark_file)
    scores = load_score_log(root, config)

    specifications = build_refinement_specs(
        center_m=center_m,
        center_w=center_w,
        m_min=m_min,
        m_max=m_max,
        w_min=w_min,
        w_max=w_max,
        coarse_step=coarse_step,
        local_step=local_step,
        local_radius=local_radius,
    )
    catalog, predictions = build_catalog(
        stage2,
        benchmark,
        specifications,
        scores,
    )

    if not include_scored:
        scored_pairs: set[tuple[float, float]] = set()
        pattern = re.compile(
            r"^challenger_temperature_m_([0-9]+p[0-9]+)_"
            r"w_([0-9]+p[0-9]+)$"
        )
        for candidate_name in scores["Candidate"].astype(str):
            match = pattern.match(candidate_name)
            if match is None:
                continue
            scored_pairs.add(
                (
                    round(float(match.group(1).replace("p", ".")), 6),
                    round(float(match.group(2).replace("p", ".")), 6),
                )
            )
        pair_keys = list(
            zip(
                catalog["m_temperature"].round(6),
                catalog["w_temperature"].round(6),
                strict=True,
            )
        )
        catalog = catalog.loc[
            [
                pair not in scored_pairs
                for pair in pair_keys
            ]
        ].copy()

    if catalog.empty:
        raise RuntimeError(
            "No unscored refinement candidates remain for this grid."
        )

    catalog = catalog.sort_values(
        [
            "RobustHistoricalScore",
            "PrequentialWorstGenderSeasonBrier",
            "Candidate",
        ]
    ).reset_index(drop=True)
    selected = catalog.head(
        len(catalog) if top_n <= 0 else min(top_n, len(catalog))
    ).copy()
    selected.insert(
        0,
        "SubmissionPriority",
        np.arange(1, len(selected) + 1),
    )

    slug = safe_slug(round_name)
    output_dir = root / "submissions" / f"refinement_{slug}"
    output_dir.mkdir(parents=True, exist_ok=True)
    ids = stage2["ID"].astype(str).reset_index(drop=True)
    manifest_records: list[dict[str, Any]] = []

    for row in selected.itertuples(index=False):
        candidate = str(row.Candidate)
        priority = int(row.SubmissionPriority)
        path = (
            output_dir
            / (
                f"submission_2026_refinement_{slug}_{priority:02d}_"
                f"{safe_slug(candidate)}.csv"
            )
        )
        submission = pd.DataFrame(
            {
                "ID": ids,
                "Pred": clip_probability(predictions[candidate]),
            }
        )
        if not submission["ID"].equals(ids):
            raise AssertionError("Submission row order changed.")
        if not submission["ID"].is_unique:
            raise AssertionError("Submission IDs are not unique.")
        if not np.isfinite(submission["Pred"]).all():
            raise AssertionError("Submission contains nonfinite predictions.")
        if not submission["Pred"].between(0.0, 1.0).all():
            raise AssertionError("Submission probabilities are out of range.")
        atomic_csv(path, submission)
        manifest_records.append(
            {
                "SubmissionPriority": priority,
                "Candidate": candidate,
                "MenTemperature": float(row.m_temperature),
                "WomenTemperature": float(row.w_temperature),
                "HistoricalRobustnessScore": float(
                    row.RobustHistoricalScore
                ),
                "PrequentialMacroBrier": float(
                    row.PrequentialMacroBrier
                ),
                "StaticMacroBrier": float(row.StaticMacroBrier),
                "MeanAbsoluteDifference": float(
                    row.MeanAbsoluteDifference
                ),
                "CorrelationWithChallenger": float(
                    row.CorrelationWithChallenger
                ),
                "Path": str(path.relative_to(root)),
                "Rows": int(len(submission)),
                "SHA256": sha256_file(path),
                "Status": "ready_to_submit",
            }
        )

    report_dir = root / "reports" / "submission_portfolio"
    report_dir.mkdir(parents=True, exist_ok=True)
    manifest = pd.DataFrame(manifest_records)
    atomic_csv(
        report_dir / f"refinement_{slug}_catalog.csv",
        catalog,
    )
    atomic_csv(
        report_dir / f"refinement_{slug}_manifest.csv",
        manifest,
    )
    score_template = manifest[
        [
            "SubmissionPriority",
            "Candidate",
            "MenTemperature",
            "WomenTemperature",
            "Path",
        ]
    ].copy()
    score_template["KaggleBrier"] = np.nan
    score_template["ObservedAtUTC"] = ""
    score_template["Notes"] = (
        f"Post-result challenger-temperature refinement: {round_name}"
    )
    atomic_csv(
        report_dir / f"refinement_{slug}_score_template.csv",
        score_template,
    )

    try:
        import plotly.express as px

        heatmap = catalog.pivot_table(
            index="m_temperature",
            columns="w_temperature",
            values="RobustHistoricalScore",
            aggfunc="first",
        )
        figure = px.imshow(
            heatmap,
            aspect="auto",
            labels={
                "x": "Women's logit multiplier",
                "y": "Men's logit multiplier",
                "color": "Historical robustness score",
            },
            title=(
                "Challenger-temperature refinement: historical robustness"
            ),
        )
        figure.write_html(
            report_dir / f"refinement_{slug}_heatmap.html",
            include_plotlyjs="cdn",
            full_html=True,
        )
    except Exception as exc:
        print(f"Plotly heatmap was skipped: {exc!r}")

    print(
        f"Refinement round '{round_name}' created "
        f"{len(manifest):,} submission files."
    )
    print(f"Submission folder: {output_dir}")
    print(
        manifest[
            [
                "SubmissionPriority",
                "Candidate",
                "MenTemperature",
                "WomenTemperature",
                "HistoricalRobustnessScore",
                "Path",
            ]
        ].to_string(index=False)
    )
    print(
        "After submitting, enter scores in: "
        f"{report_dir / f'refinement_{slug}_score_template.csv'}"
    )
    return 0


def validate_notebooks(root: Path) -> list[str]:
    names = sorted(
        path.name for path in (root / "notebooks").glob("*.ipynb")
    )
    if names != CANONICAL_NOTEBOOKS:
        raise AssertionError(
            f"Expected {CANONICAL_NOTEBOOKS}; found {names}."
        )
    for name in names:
        path = root / "notebooks" / name
        nbformat.validate(nbformat.read(str(path), as_version=4))
    return names


def scan_wording(root: Path) -> list[str]:
    suffixes = {
        ".md",
        ".py",
        ".yml",
        ".yaml",
        ".json",
        ".toml",
        ".ipynb",
    }
    ignored = {
        ".git",
        "data",
        "models",
        "submissions",
        ".ipynb_checkpoints",
    }
    matches: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        relative = path.relative_to(root)
        if set(relative.parts[:-1]).intersection(ignored):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if PROHIBITED_WORDING.search(text):
            matches.append(str(relative))
    return sorted(set(matches))


def run_command(command: list[str], root: Path) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": command,
        "returncode": int(result.returncode),
        "stdout": result.stdout[-12000:],
        "stderr": result.stderr[-12000:],
    }


def check(root: Path, *, ci: bool) -> int:
    required = [
        "README.md",
        "LICENSE",
        "CITATION.cff",
        ".github/workflows/ci.yml",
        "docs/DATA_CARD.md",
        "docs/VALIDATION_PROTOCOL.md",
        "docs/RESULTS.md",
        "docs/REPRODUCIBILITY.md",
        "docs/SUBMISSION_PORTFOLIO.md",
        "docs/RELEASE_CHECKLIST.md",
        "docs/NEXT_EXPERIMENTS.md",
    ]
    records: list[dict[str, Any]] = []
    for relative in required:
        records.append(
            {
                "Check": f"Required file: {relative}",
                "Passed": (root / relative).exists(),
                "Details": relative,
            }
        )

    try:
        names = validate_notebooks(root)
        records.append(
            {
                "Check": "Canonical notebooks validate",
                "Passed": True,
                "Details": names,
            }
        )
    except Exception as exc:
        records.append(
            {
                "Check": "Canonical notebooks validate",
                "Passed": False,
                "Details": repr(exc),
            }
        )

    wording = scan_wording(root)
    records.append(
        {
            "Check": "Promotional wording absent",
            "Passed": not wording,
            "Details": wording,
        }
    )

    commands = [
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "src",
            "tests",
            "scripts",
        ],
        [sys.executable, "-m", "pytest", "-q"],
    ]
    audit = root / "scripts" / "repository_release_audit.py"
    if audit.exists():
        commands.append(
            [sys.executable, str(audit), "--root", "."]
        )

    for command in commands:
        result = run_command(command, root)
        records.append(
            {
                "Check": " ".join(command),
                "Passed": result["returncode"] == 0,
                "Details": result,
            }
        )

    if not ci:
        summary = (
            root
            / "reports"
            / "submission_portfolio"
            / "generation_summary.json"
        )
        records.append(
            {
                "Check": "Submission portfolio generated",
                "Passed": summary.exists(),
                "Details": str(summary),
            }
        )

    table = pd.DataFrame(records)
    failed = table.loc[~table["Passed"]]
    report_dir = root / "reports" / "repository_release"
    atomic_csv(
        report_dir / "portfolio_quality_gate.csv",
        table.assign(
            Details=table["Details"].map(
                lambda value: json.dumps(value, default=str)
            )
        ),
    )
    atomic_json(
        report_dir / "portfolio_quality_gate.json",
        {
            "status": "PASS" if failed.empty else "FAIL",
            "generated_at_utc": utc_now(),
            "ci_mode": ci,
            "failed_checks": failed["Check"].tolist(),
            "records": records,
        },
    )
    print(table[["Check", "Passed"]].to_string(index=False))
    status = "PASS" if failed.empty else "FAIL"
    print(f"Portfolio quality gate: {status}")
    return 0 if failed.empty else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    install_parser = commands.add_parser("install")
    install_parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
    )
    install_parser.add_argument("--run", action="store_true")

    generate_parser = commands.add_parser("generate")
    generate_parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
    )
    generate_parser.add_argument("--top", type=int, default=None)
    generate_parser.add_argument("--stage2-path", type=Path)
    generate_parser.add_argument("--benchmark-path", type=Path)

    record_parser = commands.add_parser("record-score")
    record_parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
    )
    record_parser.add_argument("--candidate", required=True)
    record_parser.add_argument("--score", type=float, required=True)
    record_parser.add_argument("--notes", default="")

    record_csv_parser = commands.add_parser("record-scores-csv")
    record_csv_parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
    )
    record_csv_parser.add_argument(
        "--input",
        type=Path,
        required=True,
    )

    refine_parser = commands.add_parser("refine-challenger")
    refine_parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
    )
    refine_parser.add_argument("--center-m", type=float, default=0.80)
    refine_parser.add_argument("--center-w", type=float, default=1.20)
    refine_parser.add_argument("--m-min", type=float, default=0.60)
    refine_parser.add_argument("--m-max", type=float, default=1.00)
    refine_parser.add_argument("--w-min", type=float, default=1.00)
    refine_parser.add_argument("--w-max", type=float, default=1.40)
    refine_parser.add_argument("--coarse-step", type=float, default=0.05)
    refine_parser.add_argument("--local-step", type=float, default=0.025)
    refine_parser.add_argument("--local-radius", type=float, default=0.05)
    refine_parser.add_argument("--top", type=int, default=30)
    refine_parser.add_argument("--round-name", default="round2")
    refine_parser.add_argument("--stage2-path", type=Path)
    refine_parser.add_argument("--benchmark-path", type=Path)
    refine_parser.add_argument(
        "--include-scored",
        action="store_true",
    )

    check_parser = commands.add_parser("check")
    check_parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
    )
    check_parser.add_argument("--ci", action="store_true")

    all_parser = commands.add_parser("all")
    all_parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
    )
    all_parser.add_argument("--top", type=int, default=None)
    all_parser.add_argument("--stage2-path", type=Path)
    all_parser.add_argument("--benchmark-path", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    root = arguments.root.resolve()

    if arguments.command == "install":
        return install(root, run_after=arguments.run)
    if arguments.command == "generate":
        return generate(
            root,
            top_n=arguments.top,
            stage2_path=arguments.stage2_path,
            benchmark_path=arguments.benchmark_path,
        )
    if arguments.command == "record-score":
        return record_score(
            root,
            arguments.candidate,
            arguments.score,
            arguments.notes,
        )
    if arguments.command == "record-scores-csv":
        return record_scores_csv(
            root,
            arguments.input,
        )
    if arguments.command == "refine-challenger":
        return generate_refinement(
            root,
            center_m=arguments.center_m,
            center_w=arguments.center_w,
            m_min=arguments.m_min,
            m_max=arguments.m_max,
            w_min=arguments.w_min,
            w_max=arguments.w_max,
            coarse_step=arguments.coarse_step,
            local_step=arguments.local_step,
            local_radius=arguments.local_radius,
            top_n=arguments.top,
            round_name=arguments.round_name,
            stage2_path=arguments.stage2_path,
            benchmark_path=arguments.benchmark_path,
            include_scored=arguments.include_scored,
        )
    if arguments.command == "check":
        return check(root, ci=arguments.ci)
    if arguments.command == "all":
        status = generate(
            root,
            top_n=arguments.top,
            stage2_path=arguments.stage2_path,
            benchmark_path=arguments.benchmark_path,
        )
        if status:
            return status
        return check(root, ci=False)
    raise KeyError(arguments.command)


if __name__ == "__main__":
    raise SystemExit(main())
