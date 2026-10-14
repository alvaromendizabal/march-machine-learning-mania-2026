# Reproduce a forecast evaluation in seconds

This is a fully executable, **synthetic-only engineering example**. It demonstrates
how a forecast can be produced from time-bounded inputs, evaluated once per physical
game, and accompanied by independently checkable artifact hashes.

It runs offline with Python 3.12 and the standard library. No installation,
credentials, Kaggle account, private model, or data download is required.

## Start here

From the repository root, verify the committed artifacts and run the checks:

```bash
python tools/reproduce_public.py --check
python tools/test_public_reproduction.py
```

To generate a separate output directory:

```bash
python tools/reproduce_public.py --output-dir /tmp/march-public-example
```

The command emits a machine-readable `PASS` or `FAIL`, a UTC completion timestamp,
and elapsed time. Invalid inputs or changed artifacts produce a nonzero exit code.
`--check` never writes files. The example takes less than a second in the reviewed
local environment; this is not an inference-service latency benchmark.

## What the example demonstrates

| Contract | Implementation | Failure covered by the tests |
|---|---|---|
| Temporal input eligibility | Select the latest snapshot at or before each fixed season cutoff | Missing eligible observation; game on/before cutoff; timestamps without explicit UTC |
| Outcome separation | `predict(games, observations, cutoffs)` accepts identity-only game requests | An outcome field inserted into a prediction request is rejected |
| One record per physical game | Deduplicate season, normalized start instant, and unordered team pair; also require unique IDs | A reversed-team duplicate with a different ID is rejected |
| Probability validity | Finite numeric probability in `[0, 1]`; Boolean values are rejected | NaN, infinity, strings, negative values, and values above one |
| Team-swap symmetry | The illustrative rating rule satisfies `P(A>B) + P(B>A) = 1` | Reversing all teams and outcomes preserves Brier, log loss, and AUC |
| Evaluation alignment | Require exactly one binary outcome for every forecast ID | Missing, extra, duplicate, Boolean, and fractional labels |
| Reproducibility | Deterministic seeded fixture; canonical JSON; SHA-256 hashes | Changed or missing artifacts fail the read-only verification |

The input parser rejects duplicate JSON keys and nonfinite JSON constants. It
validates future-dated source records as well as eligible ones, so malformed
records are not silently discarded. All inputs are checked before artifact
generation begins.

The synthetic fixture contains **eight fictional teams, 88 distinct games, and
96 authored rating observations**. Each of four synthetic seasons has two
pre-cutoff snapshots and one deliberately influential post-cutoff snapshot per
team. The selector excludes all **32 post-cutoff observations**. The four seasons
contain 16, 20, 24, and 28 games, making weighting differences visible.

The years in this example are fixture labels. They do not identify historical NCAA
matches, historical validation results, or published competition comparisons.

## Inspect the outputs

| Committed artifact | Contents |
|---|---|
| [synthetic_fixture.json](../examples/public_reproduction/synthetic_fixture.json) | Explicit synthetic marker, seed, season cutoffs, source observations, game identities, and separately stored labels |
| [predictions.json](../examples/public_reproduction/predictions.json) | One probability per physical game, with an unambiguous team orientation |
| [evaluation.json](../examples/public_reproduction/evaluation.json) | Pooled and per-season Brier/log loss/AUC; five-bin reliability table; outcome prevalence |
| [provenance.json](../examples/public_reproduction/provenance.json) | Source-selection audit, selected snapshots, input/output SHA-256 hashes, and generator-code SHA-256 |

The manifest hashes the fixture, predictions, and evaluation. It does not hash
itself; `--check` independently regenerates and compares all four files. The
generator hash changes whenever the implementation changes. Regenerate the
artifacts after an intentional source edit, review the diff, then run `--check`.
Hashes establish consistency with reviewed bytes; they are not an authenticity
signature or evidence of source quality.

## Read the metrics correctly

The prediction rule is an **unfitted illustrative logistic rating transform**:

```text
P(team A wins) = 1 / (1 + 10 ** ((rating_B - rating_A) / 400))
```

No parameters are trained or selected on these outcomes. Labels come from a
separate, deterministically sampled fictional outcome process. The fixture seed
and construction are visible in [the generator](../tools/reproduce_public.py).

For the committed fixture:

| Diagnostic | Value | Interpretation |
|---|---:|---|
| Pooled game-weighted Brier | 0.264192 | Average squared error across all 88 physical games |
| Unweighted mean season Brier | 0.270566 | Average of four season Brier values, regardless of season size |
| Constant 50% reference Brier | 0.250000 | The exact Brier score of predicting 0.5 for every binary outcome |
| Pooled log loss | 0.727850 | Negative log probability assigned to the observed outcome |
| Pooled ROC AUC | 0.550526 | Positive-versus-negative ranking, with half credit for ties |

This arbitrary synthetic example performs worse than the constant 50% reference
on Brier. That result is retained. Its purpose is to make the evaluation and
failure behavior inspectable, not to advertise a favorable score.

The weighted Brier formula is `sum((p - y)²) / number_of_games`. The mean season
Brier gives each season equal weight. Neither is an official competition score
for this fictional dataset. Log loss clips probabilities only for its logarithm
at `1e-15` and `1 - 1e-15`; Brier uses the supplied probabilities unchanged.
AUC is `null` when only one outcome class exists.

Reliability bins are `[0, .2)`, `[.2, .4)`, `[.4, .6)`, `[.6, .8)`, and `[.8, 1]`.
Each reports its count, mean probability, and observed win rate. Empty bins have
`null` means. Expected calibration error weights the absolute bin gaps by sample
count. These small authored samples do not establish real-world calibration.

## Explore a controlled change

Copy `synthetic_fixture.json`, edit a pre-cutoff rating, and pass the copy to
`--fixture`. Keep its `SYNTHETIC_ONLY` marker and schema:

```bash
python tools/reproduce_public.py --fixture /tmp/my-synthetic-fixture.json --output-dir /tmp/my-synthetic-result
python tools/reproduce_public.py --fixture /tmp/my-synthetic-fixture.json --output-dir /tmp/my-synthetic-result --check
```

Changing a post-cutoff rating cannot change predictions. Changing an eligible
rating can. Changing labels can change evaluation, but cannot change predictions.
These are tested information-boundary properties, not merely conventions.

## Relation to the rest of the project

The [Tournament Lab browser demo](public_demo.md) explores how pairwise
probabilities propagate through a bracket. This Python example adds temporal
source admission, physical-game accounting, scoring, and artifact verification.
Their fictional datasets are separate and no numerical parity is claimed.

The public example reproduces its own complete calculation. It **does not
reproduce the private research forecast or a Kaggle submission score**, and it
reveals no proprietary features, model parameters, ensemble recipe, or source
archive. See the [public disclosure](../portfolio/DISCLOSURE.md) for the boundary
between reproducible public artifacts and private research evidence.
