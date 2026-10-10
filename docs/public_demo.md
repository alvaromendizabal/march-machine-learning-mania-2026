# Tournament Lab

**[Open Tournament Lab](https://alvaro-tournament-lab.tartmacaw2.chatgpt.site)** to explore how probability assumptions propagate through an eight-team bracket.

This public browser application uses fictional teams and authored data. It is separate from the **0.1067095 late research submission** described in the [result comparison](benchmark_comparison.md).

## Try it in two minutes

1. Start with the **Rated** preset. Inspect each team's probability of reaching the semifinal, final and championship.
2. Select a team and adjust its rating by up to 300 points. Watch uncertainty propagate through both sides of its possible path.
3. Increase or decrease the temperature. Higher values pull pairwise probabilities toward 50%; lower values make rating differences more decisive.
4. Compare two teams directly, then switch to **Even** or **Challenger**. Bracket placement and pairwise strength answer different questions.
5. Export the calculation, then inspect its assumptions and optional synthetic scoring diagnostics in the JSON.

The bracket displays possible entrants and probabilities. It does not invent a realized set of winners.

## What actually runs

The authored fixture contains **eight fictional teams**, ratings from **1460 to 1720**, and fixed first-round pairings **1–8, 4–5, 2–7, 3–6**. The matchup rule is:

```text
P(A beats B) = 1 / (1 + 10 ** ((rating_B - rating_A) / temperature))
```

Temperature defaults to **400** and can be adjusted from **100 to 800**. No ratings or temperature are fitted to data.

The engine uses **exact dynamic programming**: it combines each team's probability of arriving at a bracket node with the probabilities of every possible opponent. It sums all tournament paths under fixed pairwise probabilities and independent game outcomes. This is not a Monte Carlo estimate. “Exact” describes the calculation, not calibration or realism of its assumptions.

The exported JSON includes a separate **16-outcome authored synthetic sample** with Brier loss, log loss and a five-bin diagnostic. These diagnostics are export-only; the visible interface focuses on bracket and matchup probabilities. Outcome labels are supplied to scoring, separately from identity-only prediction requests. The sample is small and constructed; its metrics are not an untouched holdout, a calibration guarantee or evidence about NCAA performance.

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

Fixture data is authored in [public-demo/data.js](../public-demo/data.js); probability logic is in [engine.js](../public-demo/engine.js). There is no Python fixture-generation step or claim of parity with the private forecasting pipeline.

## Scope of the evidence

| Artifact | What it establishes |
|---|---|
| Browser calculation and JSON export | The synthetic input, parameter choices and computed probabilities |
| Engine tests | Numerical and input-contract checks for the public demonstration |
| UI-handler tests | Controls and exports exercise the actual engine |
| [Public result audit](../portfolio/reproduce_release.py) | Aggregate score arithmetic, public receipt hashes and disclosures |
| [Confirmed submission receipt](../reports/verified_result/submission_receipt.json) | External acceptance and displayed score of the separate private forecast |

Changing ratings or temperature is interactive exploration. It is not training, a new submission or a fresh validation period. No private model, forecast rows or source archive is included. See the [disclosure](../portfolio/DISCLOSURE.md) and [2027 readiness contract](2027_readiness.md).
