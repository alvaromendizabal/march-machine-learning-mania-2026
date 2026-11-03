# From a fitted model to a verifiable prediction

This public example exercises an important ML engineering boundary: a fitted model
leaves its training process, becomes an explicit artifact, and produces the same
predictions in a fresh inference process. It uses only the repository's fictional
games and already-frozen public reference models. It is not a competition model,
an HTTP service, or a claim of production deployment.

## Reproduce the delivery proof

From the repository root, with Python 3.12:

```bash
python tools/model_delivery_demo.py demo
```

No credentials, network requests, model installation, or new fitting are needed.
The command exports three frozen models, constructs labels-free requests from the
public synthetic features, and checks all 198 probabilities against the existing
reference predictions. It then repeats inference in three isolated Python
processes with site packages disabled. Those temporary process directories
contain neither the training program nor the fixture files or labels.

The output lives under the ignored `outputs/model-delivery/` directory:

| Artifact | Purpose |
| --- | --- |
| `folds/{2024,2025,2026}/model.json` | Closed, versioned JSON model with scaler, ordered features, and training lineage |
| `folds/{2024,2025,2026}/request.json` | Features, game identities, and cutoff clocks; no outcome labels |
| `folds/{2024,2025,2026}/response.json` | Probabilities plus exact model/request SHA-256 identities |
| `receipt.json` | Measured parity and isolated-process evidence, with source pins and explicit synthetic scope |
| `manifest.json` | Byte counts and SHA-256 for exactly the ten payload files; excludes its own hash |

Rerunning the command against an identical completed output verifies every file
without replacing it. An incomplete, changed, extra-file, or symlink-containing
output is rejected. Use `--out-dir outputs/model-delivery-another-review` for a
separate copy. Existing work is never silently refreshed.

For labels-free inference alone, use a model SHA-256 from a separately reviewed
receipt or manifest as the expected pin:

```bash
python tools/model_delivery_demo.py predict \
  --model outputs/model-delivery/folds/2026/model.json \
  --expected-sha256 EXPECTED_MODEL_SHA256 \
  --request outputs/model-delivery/folds/2026/request.json \
  --output outputs/inference-check/prediction-copy.json
```

`EXPECTED_MODEL_SHA256` is a placeholder, not an instruction to trust an arbitrary
model's self-reported hash. The output adapter requires a new file; it will not
overwrite an existing inference response. Keep extra outputs outside the closed
demo directory.

## A narrow, inspectable contract

The reusable [`public_reference.py`](../src/march_mania/public_reference.py) module
has no file, network, fitting, or fixture-loading path. `load_model(raw,
expected_sha256)` returns an immutable reference model. `predict_bytes(model_raw,
expected_sha256, request_raw)` validates the entire request and returns canonical
JSON bytes. It never scores against labels. The
[`CLI adapter`](../tools/model_delivery_demo.py) handles bounded local file I/O.

| Boundary | Enforced behavior |
| --- | --- |
| Artifact identity | An external, lowercase SHA-256 pin must match the complete model bytes before decoding |
| Serialization | Strict UTF-8 JSON; no pickle or dynamic code; duplicate keys, nonfinite numbers, and trailing material rejected |
| Schema | Exact version, synthetic scope, family, ordered features, nested fields, and training lineage; unknown fields rejected |
| Numerics | Exactly three finite coefficients and feature values; positive bounded scales; zero intercept and zero scaler means |
| Temporal eligibility | Training seasons precede the pinned evaluation season; latest training label precedes the authored fit clock; fit precedes forecast; features are available by forecast; forecast is at least 60 minutes before tipoff |
| Identity | Fictional team/game namespaces only; unique game IDs; no training IDs; no duplicate physical matchups, including reversed team order |
| Inference input | Labels and unknown metadata rejected; all rows validated before any response is emitted |
| Bounds | At most 512 request rows, 1 MiB of request JSON, 512 KiB of model JSON, and 2,048 physical training identities |
| Output | Deterministic probabilities and complete model/request pins; no label-dependent metrics or new-fit credit |

The demonstration deliberately uses authored bounds: rating difference ±2,000,
form difference ±6, rest-day difference ±14, coefficient magnitude at most 100,
and scales from `1e-12` through `1e4`. These are finite teaching-contract limits,
not an empirically selected competition recipe. The zero-mean, zero-intercept
model preserves team-swap probability symmetry. Changes to these constraints
require an explicit schema/design change rather than silent feature adaptation.

## What the evidence establishes

The receipt records three exported models, 198 checked predictions, exact
prediction parity, and the measured maximum absolute probability difference.
The fresh-process check is an actual subprocess execution, not a mocked receipt:
`python -I -S` loads only the inference adapter and the public inference module.
The process reports that the trainer and third-party model packages were not
imported. The producer imports the public generator **only to reconstruct the
request features**; it does not refit or rescore the models.

The [`adversarial tests`](../tools/test_model_delivery_demo.py) cover content
tampering, duplicate JSON keys, schema drift, bad numeric values, label injection,
clock and season violations, duplicate physical games, symmetry, source-free
subprocess parity, and preservation of existing output files. Pure inference is
also tested with file and socket operations disabled by test spies.

This is evidence for a reproducible delivery contract, not new basketball
research. The public artifact is intentionally inspectable because its models
and games are synthetic. Private features, original source bodies, research
artifacts, weights, and operational credentials remain outside this repository;
see the [repository policy](REPOSITORY_POLICY.md).

## Limits, not implied guarantees

A hash proves byte identity relative to a trusted pin, not authorship or signing.
The synthetic fit and feature clocks are authored examples, not independently
witnessed provider availability. An isolated subprocess is not a security
sandbox, and finite input checks are not a service availability guarantee. This
example does not implement an authenticated endpoint, rate limiting, deployment,
drift monitoring, or an operational service-level objective. Those concerns and
real pregame feature-clock evidence would need separate designs and verification.
