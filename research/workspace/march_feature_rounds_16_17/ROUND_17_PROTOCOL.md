# Round 17 — Shot-blocking and free-throw pressure

Design date: 2026-09-12. Manual execution only.

## Hypothesis

Raw block and free-throw rates can reflect both a team's behavior and its opponents. The new representation estimates offense and defense separately, so avoiding blocked shots and producing blocks are distinct effects, as are generating free-throw attempts and suppressing opponents' attempts.

This is not a claim that blocks or free throws are new discoveries. Basic rates already exist in the wider feature bank. The incremental test asks whether jointly adjusting these specific rates for opponents and location improves the fixed consensus-plus-rates reference.

## Four candidates, two families

| Family | Offensive feature (higher favorable) | Defensive feature (higher favorable) | Target before adjustment |
|---|---|---|---|
| Blocked shots | Avoiding blocks beyond opponent expectation | Producing blocks beyond opponent expectation | opponent blocks / own two-point attempts |
| Free-throw pressure | Producing free throws beyond opponent expectation | Limiting opponent attempts beyond expectation | own FTA / own FGA |

For four opponent blocks and 40 two-point attempts, the blocked-shot rate proxy is 0.10. For 20 FTA and 60 FGA, free-throw pressure is 1/3. This is FTA/FGA, not free-throw shooting percentage or a count of fouls. FTA/FGA can exceed one; the continuous ridge model does not impose a binomial interpretation.

The blocked-shot denominator follows a traditional team block-rate convention. The box score does not identify which blocks were against two- versus three-point attempts, so this is not a clean interior/rim rate or actual probability that a two-pointer is blocked. Zero target opportunities with positive target events stop for inspection. Do not invent player height, rim location, or shot-quality information.

Intentional late-game fouling, game state, referee tendencies, and personnel changes are not explicitly controlled. Higher block activity may also change rebounding or foul risks; a positive marginal coefficient is not proof of a causal benefit.

For blocks, offense is sign-negated and defense positive. For free-throw pressure, offense is positive and defense sign-negated. Higher adjusted values always have the favorable convention, not a guaranteed favorable fitted coefficient.

## Source basis and limits

- https://kenpom.com/blog/stats-explained/ — block rate (blocks/opponent 2PA) and free-throw rate conventions.
- https://kenpom.com/blog/offense-vs-defense-free-throw-rate/ — distinction between offensive production and defensive avoidance.
- https://kenpom.com/blog/offense-vs-defense-nonsteal-turnovers/ — relationships among steals, blocks, and other defensive events.

The research motivates decomposing behavior; it does not establish our exact adjustment model or a tournament Brier improvement. Model specification, smoothing, and thresholds below remain fixed hypotheses.

## Fixed experiment and reference

Men's validation seasons: 2022, 2023, 2024, 2025. Training: 2013 through the year before validation, excluding 2020. No 2026 outcomes are used. The inherited played-main-draw label routine excludes First Four matchups and the 2021 Oregon–VCU no-contest. Expected physical training rows: 503, 566, 629, 692; validation rows: 63 each.

The reference contains the same 17 inputs as the completed consensus comparison. It is not the final submitted pooled XGBoost recipe. Do not substitute its Brier for the submitted score. Reuse the four already fitted consensus classifiers after identifier, probability, model-schema, environment, and metric replay checks. Nothing promotes features automatically.

## Opponent and location adjustment

For each target, fit one season-local weighted ridge regression:

    rate_i = intercept + offense[team_i] + defense[opponent_i] + home_effect * home_i
    objective = sum_i weight_i * residual_i**2
                + 20 * sum(offense**2 + defense**2 + home_effect**2)
    weight_i = opportunities_i / mean(opportunities)

Each physical game supplies one observation from each team's perspective. The intercept is unpenalized. Coefficients are signed so higher values are favorable and multiplied by 100. Matchup features are team A minus team B. The model has no tournament-target argument. Rates are descriptive pre-tournament effects, not probabilities, causal effects, or estimates of player availability.

The implementation uses a direct Cholesky solution of the normal equations, not an iterative L-BFGS optimizer. Every accepted solve must be finite and satisfy a relative normal-equation residual no larger than 1e-9. The target's opportunity count also must be at least 50 for each seeded team on each side of the ball, and seeded teams must belong to one connected opponent component. These checks do not prove out-of-sample quality.

The identical underlying raw rates provide four controls. A control is (total events + 100 * contemporaneous league rate) / (total opportunities + 100), with the same favorable sign and per-100 units. This fixed shrinkage is not tuned on tournament results. The opponent adjustment can help or hurt; it is not assumed better than those controls.

## Six fixed configurations

| Recipe | Inputs | Purpose |
|---|---:|---|
| reference | 17 | Verified existing consensus reference |
| rates | 21 | Reference plus four unadjusted controls |
| family A | 23 | Rates plus two adjusted family-A effects |
| family B | 23 | Rates plus two adjusted family-B effects |
| both | 25 | Rates plus all four adjusted effects |
| duplicate_control | 25 | Rates plus one exact copy of each raw-rate input |

The duplicate columns contain no new information and are not counted as new candidates. They probe sensitivity to coefficient allocation under fixed L2 regularization; they are not a complete causal identification test.

The classifier remains logistic regression C=0.1, no intercept, mirrored orientations, per-physical-game weighting, and train-only RMS scaling. Only training-constant columns may be removed. No rescreening fills vacated slots. No algorithm search, calibration sweep, ensemble, or cross-round selection is performed.

## Comparisons and decision rule

Primary: `adjustment_given_rates` = Brier(both) - Brier(rates).
Other rows show each adjusted family added alone, each added to the other, raw rates versus reference, and `both_given_duplicate`.

Consider production transfer only when the primary mean is <= -0.0005, at least three of four seasons improve, the worst deterioration is <= +0.003, and the mean delta versus the duplicate control is negative. Otherwise `DO_NOT_PROMOTE`. These are resource-allocation rules, not significance thresholds. Do not replace a failed primary with a favorable secondary result.

Report Brier per physical game and mean across seasons; game-weighted and equal-season means are both retained. Log loss, calibration, coefficients, support, and correlations are secondary diagnostics. A 2,000-replicate fixed-seed bootstrap resamples whole seasons, not individual mirrored observations. Its four-cluster percentile interval is exploratory, with no multiple-testing correction, and must not be described as strong confirmatory inference.

## Information availability and leakage assumptions

Feature builders see only legal same-season regular-season box scores through day 132. Known tournament seeds define possible matchups and remain part of the pre-existing reference; no realized tournament round, location, win, score, or outcome is a candidate input. Late regular-season data are allowed at the declared post-selection prediction timestamp. This is not a pregame evaluation of earlier regular-season games.

Predetermined alpha, exposure threshold, and formulas do not use held-out tournament labels. All tournament-supervised preprocessing and fitting occur on earlier seasons. The same-season league prior and opponent estimates use only already observed regular-season data. Historical CSV revisions cannot be ruled out from the provided snapshot alone.

All evaluation years have already been consumed by this project. These are further exploratory feature investigations, not untouched tests or proof of beating 0.1097454. Nothing here changes the reported 0.1222672 submission.

## Bounded work and restartability

Twelve seasons, two target fits each: at most 24 new rate-model fits, 12 new feature tables, 20 new tournament classifiers, four reference replays. Old rating models and raw files are never rebuilt or modified. A 2013-only smoke stage fits two targets and creates one table; its immediate replay must do zero new fits. Remaining preparation needs 22 target fits and 11 tables. Individual fits and tables have content-verified completion manifests. An intentional synthetic interrupted-smoke test is included in the user-run suite.

Stage ceilings: smoke 90 seconds per invocation, preparation 300, evaluation 180, reporting 120. Two BLAS/OpenMP threads, worker RSS guard 6 GiB, minimum free output disk 256 MiB. These limits are not measured runtime estimates or billing caps. The worker is stopped when a guard is exceeded; already sealed outputs survive. No automatic repeated retry.

## Visual evidence and return package

Ten standalone Plotly figures are displayed with explicit `fig.show()` calls: prior negative findings; exposure support; raw-versus-adjusted defensive profile; all six Brier curves; primary deltas; duplicate-control deltas; family effects; training-only overlap; calibration; coefficient stability. Numerical and observation support tables are displayed beside the charts. The scientific archive/HTML is saved before inline rendering. No Jinja2-dependent DataFrame styling is used.

Aggregate reports, diagnostics, parameter manifest, executed-test receipt, and available runtime telemetry are returned. Raw rows, models, individual predictions, and private edited notebooks are excluded. Source and data hashes bind each run; changed artifacts stop rather than being silently reused.

## Status

Prepared code with static review only. No tests, notebooks, experiment functions, rating fits, or tournament models have been executed by ChatGPT. The supplied tests and execution stages must pass in the user's environment before numerical or performance claims can be made.

## Method documentation

- https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.Ridge.html — ridge objective and penalties; the custom weighted design above is a declared implementation choice.
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.cho_solve.html — linear system solve from a Cholesky factor.
- https://www.jmlr.org/papers/v11/cawley10a.html — model-selection overfitting under repeated validation reuse.
