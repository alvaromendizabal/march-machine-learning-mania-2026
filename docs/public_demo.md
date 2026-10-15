# Tournament Lab

**[Open Duke × Michigan](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html)** to explore how probability assumptions propagate through an eight-team bracket.

This public browser application uses real school names with authored synthetic ratings, bracket positions, prices and outcomes. It is separate from the **0.1034347 Kaggle-scored retrospective forecast** described in the [featured result](champion_result.md).

## Try it in two minutes

1. Start with the **Baseline** preset. Inspect each team's probability of reaching the semifinal, final and championship.
2. Select a team and adjust its rating by up to 300 points. Watch uncertainty propagate through both sides of its possible path.
3. Increase or decrease the temperature. Higher values pull pairwise probabilities toward 50%; lower values make rating differences more decisive.
4. Compare two teams directly, then switch to **Even** or **Gonzaga surge**. Bracket placement and pairwise strength answer different questions.
5. Export the calculation, then inspect its assumptions and optional synthetic scoring diagnostics in the JSON.

The bracket displays possible entrants and probabilities. It does not invent a realized set of winners.

## What actually runs

The authored fixture contains **eight real school names with synthetic ratings**, ratings from **1460 to 1720**, and fixed first-round pairings **1–8, 4–5, 2–7, 3–6**. The matchup rule is:

```text
P(A beats B) = 1 / (1 + 10 ** ((rating_B - rating_A) / temperature))
```

Temperature defaults to **400** and can be adjusted from **100 to 800**. No ratings or temperature are fitted to data.

The engine uses **exact dynamic programming**: it combines each team's probability of arriving at a bracket node with the probabilities of every possible opponent. It sums all tournament paths under fixed pairwise probabilities and independent game outcomes. This is not a Monte Carlo estimate. “Exact” describes the calculation, not calibration or realism of its assumptions.

The exported JSON includes a separate **16-outcome authored synthetic sample** with Brier loss, log loss and a five-bin diagnostic. These diagnostics are export-only; the visible interface focuses on bracket and matchup probabilities. Outcome labels are supplied to scoring, separately from identity-only prediction requests. The sample is small and constructed; its metrics are not an untouched holdout, a calibration guarantee or evidence about NCAA performance.

## Duke × Michigan and price context

Duke is the default selected team and Michigan the default direct opponent. Both have dedicated feature cards and controls. The field also contains UConn, Houston, Florida, Arizona, North Carolina and Gonzaga. Their numbered positions are fictional eight-team bracket slots, **not actual NCAA seeds**. No school endorsement is implied.

The Duke headline and baseline difference come from the same exact bracket engine as the table. The price panel accepts hypothetical decimal prices greater than 1 and no greater than 1000. With quoted prices dA and dB, its normalized market probability is `(1/dA) / ((1/dA) + (1/dB))`. It reports the overround and model-minus-market difference. These display-only inputs never alter matchup or bracket forecasts. Invalid prices hide stale price results; a valid bracket can still be exported with null price context.

## Deterministic standalone build

Run `python tools/package_public_demo.py`. Open **outputs/public-demo/Tournament_Lab.html** without a server. The identical source also produces a five-file ZIP and SHA-256 manifest. The generator checks the static publication boundary and uses fixed ZIP metadata, so unchanged source produces unchanged output bytes. The public demonstration—not the private trained forecasting system—is fully reproduced.

## Run locally

The application is static HTML, CSS and JavaScript with no dependencies, credentials, backend or model download. From the repository root:

```bash
python -m http.server 8000
```

Open **http://localhost:8000/public-demo/**. The local server only serves files; calculations run in the browser.

Check the numerical engine and actual UI handlers with Node:

```bash
node tools/test_public_demo_engine.mjs
node tools/test_public_demo.mjs
```

Scenario data is authored in [public-demo/data.js](../public-demo/data.js); probability logic is in [engine.js](../public-demo/engine.js). There is no Python fixture-generation step or claim of parity with the private forecasting pipeline.

## Scope of the evidence

| Artifact | What it establishes |
|---|---|
| Browser calculation and JSON export | The synthetic input, parameter choices and computed probabilities |
| Engine tests | Numerical and input-contract checks for the public demonstration |
| UI-handler tests | Controls and exports exercise the actual engine |
| [Public result audit](../portfolio/reproduce_release.py) | Aggregate score arithmetic, public receipt hashes and disclosures |
| [Confirmed submission receipt](../reports/verified_result/submission_receipt.json) | External acceptance and displayed score of the separate private forecast |

Changing ratings or temperature is interactive exploration. It is not training, a new submission or a fresh validation period. No private model, forecast rows or source archive is included. See the [disclosure](../portfolio/DISCLOSURE.md) and [2027 readiness contract](2027_readiness.md).

## Champions edition

Duke and Michigan are the two featured teams and the default direct matchup. Michigan's 2026 title is factual context linked to the NCAA report in the interface. Ratings and field positions remain authored scenarios; the historical result never enters the probability engine.

The new final-path function decomposes title probability into four mutually exclusive opponent contributions. Sensitivity changes only the selected team's current rating and respects the slider's −300..300 range. It is not a confidence interval. Scenario links use a size-bounded, allowlisted JSON schema in the URL fragment; invalid state loads the safe baseline with a visible warning. The JSON export additionally carries scenario inputs, final-opponent paths and local sensitivity.

**Create scenario link** works on the hosted lab; offline users retain JSON export and print. No runtime data request, analytics, account or persistent storage is introduced. URL fragments are not an encryption mechanism; only public controls belong there. [Release acceptance contract](reviewer_contract.md)
