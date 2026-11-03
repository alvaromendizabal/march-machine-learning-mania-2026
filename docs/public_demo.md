# Tournament Lab

**[Open Tournament Lab](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html)** to explore how probability assumptions propagate through an eight-team bracket, then inspect the engineering evidence behind this portfolio.

This public browser application uses real school names with authored synthetic ratings, bracket positions, prices and outcomes. It is separate from the **0.1034347 Kaggle-scored retrospective forecast** described in the [featured result](champion_result.md).

## Choose a review route

The first screen separates the private historical result from the public synthetic calculation. Four keyboard-accessible destinations organize the review: **Overview**, **Scenario lab**, **Engineering evidence** and **Reproduce**. Each is an ordinary in-page link, not an encoded scenario or a new model setting.

- Explore the browser lab for probability propagation, scenario sensitivity and exact export.
- Inspect the [source-readiness summary](source_readiness.md) for the distinction between verified stored bytes, semantic interpretation, clock eligibility and unresolved debt. A completed body verification is not a new eligible feature or successful model.
- Run `python tools/review_project.py` for a credential-free local review, including a separately labeled synthetic chronological training demonstration. This reproduces public engineering contracts, not the private competition model.

The original bracket, team controls, hypothetical-price context, sensitivity, final-opponent paths, scenario sharing and export remain available. Small screens retain an independently scrollable bracket and provide a direct jump to its controls.

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
node tools/test_public_demo_browser.mjs
```

The first two commands execute the actual probability engine and UI handlers with a small dependency-free DOM. The third tests the browser-checker transport and layout contracts with invented fixtures. **None of those commands is a screenshot or a real-renderer pass.**

### Real browser rendering

With an already-installed Chrome or Chromium and Node available, run:

```bash
node tools/check_public_demo_browser.mjs
```

The checker uses Chrome's local debugging pipe, not a network service. It opens the source directly as local files, blocks page HTTP(S) requests, renders desktop (1440px), tablet (768px), mobile (390px) and narrow mobile (320px), and records viewport/full-page screenshots. Assertions cover page overflow, duplicate IDs, resolved in-page links, navigation, the evidence boundary, real controls, first-tab/skip-link behavior, probability conservation and uncaught page errors. Outputs are under **outputs/browser-review/**, including **browser_review.json**. The independently scrollable bracket is deliberate; horizontal overflow of the page is a failure.

Set `CHROME_BIN` only if the existing executable is outside `PATH`. The checker never installs or downloads a browser. A missing browser writes **BLOCKED**, leaves `rendererVerified` false and exits nonzero. Screenshots and a **PASS** are only produced by an actual render; fixture-test success is not substituted. These targeted checks are not a full accessibility conformance certification or manual aesthetic review.

For genuine before/after captures, add `--baseline-ref` followed by an exact nonzero 40-character commit SHA already present in the local clone. Only the original five allowlisted public-demo files are read from that commit. Baseline findings are retained rather than retroactively made to satisfy new navigation requirements. The GitHub workflow runs this check with the runner's existing Chrome and saves screenshots and the JSON report as **public-demo-browser-review**, including on failure. No runtime browser download is performed. CI status must be checked for the actual commit; merely adding the workflow is not evidence that it ran.

Scenario data is authored in [public-demo/data.js](../public-demo/data.js); probability logic is in [engine.js](../public-demo/engine.js). There is no Python fixture-generation step or claim of parity with the private forecasting pipeline.

## Scope of the evidence

| Artifact | What it establishes |
|---|---|
| Browser calculation and JSON export | The synthetic input, parameter choices and computed probabilities |
| Engine tests | Numerical and input-contract checks for the public demonstration |
| UI-handler tests | Controls and exports exercise the actual engine |
| Real-renderer report and screenshots, when executed | Measured desktop/mobile layout and the specific browser interaction checks; not private model quality |
| [Public result audit](../portfolio/reproduce_release.py) | Aggregate score arithmetic, public receipt hashes and disclosures |
| [Confirmed submission receipt](../reports/verified_result/submission_receipt.json) | External acceptance and displayed score of the separate private forecast |

Changing ratings or temperature is interactive exploration. It is not training, a new submission or a fresh validation period. No private model, forecast rows or source archive is included. See the [disclosure](../portfolio/DISCLOSURE.md) and [2027 readiness contract](2027_readiness.md).

## Champions edition

Duke and Michigan are the two featured teams and the default direct matchup. Michigan's 2026 title is factual context linked to the NCAA report in the interface. Ratings and field positions remain authored scenarios; the historical result never enters the probability engine.

The final-path function decomposes title probability into four mutually exclusive opponent contributions. Sensitivity changes only the selected team's current rating and respects the slider's −300..300 range. It is not a confidence interval. Scenario links use a size-bounded, allowlisted JSON schema in the URL fragment; invalid state loads the safe baseline with a visible warning. The JSON export additionally carries scenario inputs, final-opponent paths and local sensitivity.

**Create scenario link** works on the hosted lab; offline users retain JSON export and print. No runtime data request, analytics, account or persistent storage is introduced. URL fragments are not an encryption mechanism; only public controls belong there. [Release acceptance contract](reviewer_contract.md)
