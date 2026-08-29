# March Machine Learning Mania 2026

A reproducible local project for auditing, preparing, modeling, calibrating, explaining, and comparing NCAA men's and women's tournament forecasts.

## Project principles

1. Raw Kaggle files are immutable and excluded from Git.
2. Historical features must be built only from information available before each tournament.
3. Tournament outcomes are labels, never same-season inputs.
4. Validation is season-based, with expanding-window evaluation as the primary estimate.
5. Probabilities are evaluated and calibrated for Brier score.
6. Men's and women's models/calibrators are evaluated both separately and jointly.
7. Notebooks are for exploration; reusable logic belongs under `src/march\\\_mania/`.

## Structure

* `data/raw/`: unmodified Kaggle competition files; ignored by Git
* `data/interim/`: canonicalized tables ready for feature engineering; ignored by Git
* `data/processed/`: future model matrices and fold-specific feature stores; ignored by Git
* `notebooks/`: ordered exploratory notebooks
* `src/march\\\_mania/`: reusable loading, reshaping, and validation code
* `tests/`: unit tests for structural transformations
* `configs/`: experiment configuration
* `references/`: supplied starter notebook and data description
* `reports/`: versioned data-quality manifests/audits plus generated figures
* `submissions/`: generated Kaggle files; CSVs ignored by Git

## First run

From Miniforge Prompt:

```bat
conda activate ml-modeling
cd /d "%USERPROFILE%\\\\ML\\\\march-mania-2026"
python -m pip install --upgrade-strategy only-if-needed kaggle pytest ruff pre-commit
python -m pip install -e . --no-deps
python -m pip check
```

\## Local data setup



Download the official competition ZIP manually. Extract all CSV files directly into:



`data/raw/march-machine-learning-mania-2026/`



The CSV files must be directly inside that directory rather than inside an additional nested folder.



Raw and generated datasets are excluded from Git. After extracting the files, start JupyterLab from the repository root:



```bat

jupyter lab

```

Open `notebooks/00\\\_data\\\_audit\\\_and\\\_preparation.ipynb` with the `Python (ml-modeling)` kernel and run all cells.

## What notebook 00 produces

It does not build predictive features. It creates stable structural tables that later feature code can consume:

* `table\\\_inventory.csv`
* `data\\\_manifest.json`
* `raw\\\_data\\\_audit.csv` (small and safe to commit)
* `teams.parquet`
* `seasons.parquet`
* `seeds.parquet`
* `games\\\_compact\\\_canonical.parquet`
* `tournament\\\_targets.parquet`
* `games\\\_detailed\\\_team\\\_long.parquet`
* `team\\\_conferences.parquet`
* `game\\\_cities.parquet`
* `massey\\\_ordinals\\\_men.parquet`
* `submission\\\_matchups.parquet`

## Planned notebook sequence

* `00\\\_data\\\_audit\\\_and\\\_preparation.ipynb`: immutable raw-data audit and canonicalization
* `01\\\_leakage\\\_safe\\\_team\\\_snapshots.ipynb`: pre-tournament team-season feature tables
* `02\\\_baselines\\\_and\\\_validation.ipynb`: seed, Elo, and logistic baselines with season-based folds
* `03\\\_efficiency\\\_and\\\_strength\\\_features.ipynb`: possession, efficiency, schedule, and ranking features
* `04\\\_model\\\_comparison.ipynb`: logistic, XGBoost, LightGBM, and optional neural baselines
* `05\\\_calibration\\\_and\\\_ensemble.ipynb`: OOF calibration, blending, and uncertainty analysis
* `06\\\_explainability.ipynb`: SHAP, permutation importance, PDP/ALE, and stability checks
* `07\\\_submission.ipynb`: final training, Stage 2 matchups, validation, and submission artifact

