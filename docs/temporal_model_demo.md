# A small learning system you can inspect

This public example actually learns model coefficients, forecasts later fictional seasons, and evaluates its frozen predictions. It runs using the Python standard library, without credentials or source downloads. It is an independently authored teaching implementation—not the private competition recipe, a reproduction of NCAA forecasts, or another owner research invocation.

The existing [rating/scoring example](../tools/reproduce_public.py) remains unchanged and unfitted. This example adds a separate, genuinely trained path.

## Run it

From the repository root:

```bash
python tools/temporal_model_demo.py --check
```

The command reconstructs the fictional fixture, fits three models, generates predictions, computes metrics, and compares all six committed artifact files byte for byte. A mismatch fails without rewriting evidence. To regenerate deliberately, omit `--check`; to experiment without replacing the reference artifacts, pass `--out-dir outputs/temporal-experiment` and an explicit `--seed`.

The [one-command employer review](engineering_review.md) also reruns the three fits, validates the committed example, and executes its adversarial contract tests. The [executed engineering notebook](../portfolio/engineering_review.ipynb) trains in a real Jupyter kernel and preserves its tables, calibration chart and static fallback.

## What is fitted

The seed-2026 fixture contains 12 fictional teams playing one round robin in each of six authored seasons, 2021–2026: **396 distinct physical games**. Each team-season has three dated observations. The latest observation is deliberately after the forecast cutoff and is excluded; 72 late observations cannot become pregame features.

Three transparent teaching features are differences in fictional rating, form and rest days. Features use the latest observation published at or before that season's forecast cutoff. The model must finish fitting before the forecast; the forecast is at least one hour before the game. Earlier-season labels must be available strictly before fitting. These are authored simulation clocks, not evidence of historical provider availability.

| Forecast season | Earlier training seasons | Physical training games | Physical evaluation games |
|---|---|---:|---:|
| 2024 | 2021–2023 | 198 | 66 |
| 2025 | 2021–2024 | 264 | 66 |
| 2026 | 2021–2025 | 330 | 66 |

Each fold fits a scaler **only on its training population** and then performs 250 full-batch gradient steps for L2-regularized logistic regression. The fixed learning rate is 0.12 and L2 coefficient is 0.04. The minimized objective is mean binary cross entropy plus `0.04 / 2 × sum(weight²)`. No evaluation-season tuning, model search, calibration fit or early stopping occurs.

Every training game is represented by its original and team-swapped orientation, each with weight one half. The scaler is fitted on that symmetric population: its mean is zero and population standard deviation is the square root of the mean squared original feature. Zero-variance features use a scale of one. A zero intercept and symmetric features ensure `P(A beats B) = 1 − P(B beats A)` within floating-point tolerance. Mirroring does not double the physical-game denominator.

Prediction accepts feature rows, not outcomes. The code serializes all predictions and records their SHA-256 before evaluation labels enter scoring. Content pins establish reproducibility of the artifact, not a trusted historical forecast time. Fitted coefficients, scaler parameters and training identities are deliberately public because they belong only to this fictional fixture.

## Reference output: synthetic only

The three expanding-window folds produce **198 out-of-season synthetic predictions**, three actual synthetic fits, **zero owner research fits**, zero private artifacts and zero network requests.

| Diagnostic | Seed-2026 authored fixture |
|---|---:|
| Game-weighted Brier | 0.17836297204902107 |
| Game-weighted log loss | 0.5332119916892536 |
| Accuracy, ties receiving half credit | 0.7070707070707071 |
| ROC-AUC | 0.8087928153717627 |
| Constant-50% reference Brier | 0.25 |

Log loss clips probabilities to `[1e-15, 1 − 1e-15]`. ROC-AUC uses pairwise ranking with half credit for tied scores. Five fixed-width reliability bins retain their counts and mean predictions; empty bins have null rates. Expected calibration error is explicitly a bin-dependent diagnostic, not a proof of calibration. Game-weighted and unweighted mean-season Brier are reported separately; the reference fixture has equal fold sizes, so these happen to agree.

The fixture is small and generated from known latent structure. Predictability is designed into this teaching exercise. Its scores demonstrate that the implementation runs; they say nothing about NCAA performance, future competition results, private-model parity or profitability.

## Inspect the artifacts

The [example directory](../examples/temporal_model_demo/) contains:

| File | Evidence |
|---|---|
| `synthetic_fixture.json` | Complete fictional observations, games, labels and cutoff clocks |
| `synthetic_fits.json` | Three fitted coefficient/scaler sets, training identities, input pins and optimizer receipts |
| `predictions.json` | Frozen synthetic predictions, explicitly scoped and prefixed `synthetic_` |
| `evaluation.json` | Fold populations, per-season and pooled metrics, reliability bins, teaching protocol and evidence boundaries |
| `calibration.svg` | Deterministic accessible static reliability plot |
| `manifest.json` | Exact bytes/SHA-256 for the five payloads, generator and protocol pins; excludes its own hash |

The source hash is part of the manifest. Editing the generator—even a formatting change—requires explicit regeneration. Exact-byte reproducibility is verified in the project's locked Python 3.12 environment. Floating-point math can vary across Python/platform implementations; do not silently refresh reference bytes to conceal a mismatch.

## Contracts that fail closed

Run the focused suite with `python -m unittest discover -s tools -p 'test_temporal_model_demo.py'`. Its 32 tests cover:

- Three actual fitted folds, changed coefficients and decreased training objective, with fixture fits separated from research accounting.
- Train-only scaling, no evaluation-label influence on fitting, no evaluation-feature influence on an earlier fit, and no current-season training rows.
- Late/missing observations, forecast and fit boundaries, labels unavailable at fit time, and UTC comparisons using parsed instants rather than lexical strings.
- Duplicate IDs, reversed-team physical duplicates, conflicting source observations, team-order symmetry and distinct physical-game weighting.
- Nonfinite or boolean numeric inputs, malformed clocks, invalid probabilities, unsupported scopes, zero-variance features and missing/bad labels.
- Independent metric reference calculations, tie handling, clipping, calibration-bin closure, output pins and deterministic reruns.
- Read-only `--check` failure on tampering and syntactically valid, accessible SVG output.

Tests themselves run extra synthetic fits; they are not additional research invocations and are not folded into the three-fold demonstration counter.

[Source](../tools/temporal_model_demo.py) · [Tests](../tools/test_temporal_model_demo.py) · [Public/private boundary](REPOSITORY_POLICY.md) · [Current source readiness](source_readiness.md)
