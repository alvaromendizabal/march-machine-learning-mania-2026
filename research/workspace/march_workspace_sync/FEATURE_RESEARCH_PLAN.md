# Feature engineering reopened: evidence-driven rounds

## Objective and score contract

Current submitted Brier: **0.1222672**. Historical target: **0.1097454**. The gap is **0.0125218**, approximately **10.24%** of the current score. Lower is better. These values are not comparable to every historical-validation number: populations, aggregation and available information must match. No new experiment has been run by the synchronization kit.

The published winner reports 0.1097454 over 126 games. Its reported historical raw Brier was 0.1850 for men and 0.1390 for women, with different cross-validation and calibration conventions. This is a useful warning against demanding 0.1097454 on a different collection of historical seasons. Its historical and realized-tournament results differ substantially; our target remains serious, but it is not a guarantee or a universal cross-validation threshold.

The repository labels the September 9 release complete. That describes the archived release, not a conclusion that all plausible feature research has been exhausted. New research should preserve the old release, avoid rewriting its score history, and proceed in a separate reviewed branch after setup.

## What is already present

The committed feature-store documentation states that the 3,106 candidates already include opponent-adjusted offense/defense, adjusted Four Factors, residual form, venue and opponent-strength context, distribution tails, multiple windows, Bayesian shooting quantities, pace, Elo and margin Elo, target histories, antisymmetric matchup interactions, coach histories and conference strength. A separate study adds 840 ranking definitions. Retention caps of 32, 64, 128 and 256 have already been compared; broadening to 256 generally hurt.

Therefore, “add Four Factors,” “try Elo,” “add rolling averages,” “add coaches,” or “generate 1,000 more columns” are not adequate new experiments. Each proposal below must identify the exact existing feature names, the actual fitted columns, earlier ablations and the mechanism it changes.

A consequential existing assumption is screening by training-only point-biserial association, pruning near-duplicates and retaining at most 128 inputs. That is leakage-conscious, but univariate screening can miss features that matter conditionally. This is a hypothesis about the representation and screening procedure—not proof that it explains the score gap. A compact, explicitly retained family can be tested against the same fixed estimator before tuning model algorithms.

Sources: [feature-store implementation contract](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/docs/feature_store.md), [published release and limitations](https://github.com/alvaromendizabal/march-machine-learning-mania-2026/blob/84b8fb36644a6558beded6dad84f5645ea4405d3/README.md).

## First investigation after setup: representation and selection audit

**Question:** Are high-value compact domain signals absent from the data, missing from the candidate bank, or discarded before they reach the fitted model?

Read the actual feature registry, per-model `feature_usage.csv`, `screening_summary.csv`, `selection_stability.csv`, `fold.json` and matched-game predictions where available. The committed docs locate public evidence under `reports/feature_store`; the private artifacts may be in versioned `outputs` or S3 and must be verified before reuse. Do not refit merely because a path is missing. Restore the exact hash-pinned archive only when needed and permitted.

Create a family × sex × season evidence table with these distinct statuses: source unavailable; raw source available; feature implemented; passes availability tests; excluded by training coverage; excluded by screening; retained; positive/neutral/negative ablation; stability unresolved. Add the source/configuration fingerprint and dataset snapshot to every row.

The first bounded experiment, only after that table and the preflight are valid, should compare the **same fixed estimator** on a compact anchor versus anchor + one specifically defined missing/underrepresented family. Candidate count alone is not progress.

## Research rounds, in priority order

| Round | Exact investigation | Availability and leakage gate | Required comparison |
|---|---|---|---|
| 1 | **Compact winner-inspired representation:** seed difference, continuous strength, quality-win/resume strength; women's rim-protection signal. Distinguish these definitions from our current quartile-opponent, conference and ball-control summaries | Seeds/selected tournament fields are available only after the declared selection deadline. Seed-derived opponent-quality summaries must be removed in the seed-free route | Anchor vs each incremental compact family vs their small combined representation. Preserve the same physical games and fixed estimator; compare forced-family inclusion with the current screen |
| 2 | **Schedule/resume beyond win totals:** field-strength-weighted wins and losses, quality win opportunities, wins above a schedule-specific expectation, seed-versus-strength discrepancy | Build opponent ratings and thresholds from legal pre-cutoff games. Fit any expected-performance or seed mapping only on earlier/inner training seasons. Secondary tournament selection availability must be documented | Existing schedule family vs genuinely different opportunity-adjusted representation. Separate resume information from raw win rate and seed |
| 3 | **Matchup interactions and uncertainty:** pace × strength gap, shooting-volume/variance × strength gap, offensive-rebound vs opponent defensive-rebound mismatch, turnover-pressure vs ball-security mismatch, interior scoring vs rim protection | Existing Four Factors/ball-control features must be audited first. Interaction formulas must respect swap symmetry; no actual tournament round/venue inferred from post-deadline results | Anchor + one small mechanism-based interaction block, with and without marginal screening. Drop-one-family ablations; include uncertainty/effective sample support |
| 4 | **Dynamic, robust strength estimation:** opponent-adjusted residual trends and strength uncertainty, not unadjusted recent-win streaks; compare bounded recency/robust-loss variants against existing ridge/Elo | All games at/before cutoff; rating hyperparameters chosen in inner temporal folds. Do not substitute final-season ranking data | Existing strength representation vs one changed estimator of latent strength, fixed downstream model. Recency is not assumed useful; winner reported it did not help their solution |
| 5 | **Roster and availability:** lost player-value × expected minutes, continuity, starter experience, concentrated usage and return-from-absence effects | Current official snapshot does not supply injuries/rosters/minutes. Require permitted, archived pre-deadline player data, provenance and credible historical coverage. Never backfill past seasons with today's roster/health information | Source-coverage and name-resolution audit before fitting. A 2026-only scenario is explicitly not a season-stable historical feature validation; missing history is not zero injury burden |
| 6 | **External expert information and remaining gaps:** genuine pre-cutoff efficiency values, early-season priors, women's comparable expert signals, and eligible market-derived strength where permitted | Verify competition and source terms, timestamps, licensing and complete forecast availability. Massey ordinal ranks are not the underlying efficiency values. Later-round betting lines are not available for a pre-tournament all-pairs forecast | Baseline vs incremental source contribution on common coverage. No automatic purchase, scraping or use of retrospective values |

The ranking of these rounds is a research decision based on the inspected documentation, not an assertion that they will improve the score. Some ingredients are already present and may prove redundant. Reject duplication after checking the actual formulas and prior evidence.

## Why these are plausible rather than arbitrary

The 2026 winner's write-up identifies seed differences, a custom net-efficiency rating, quality wins, men's injury deductions and an extra women's blocks feature. It used a very small final representation, separate men's/women's models and post-processing. Its manually adjusted rating, leave-one-season-out protocol, calibration and edge sharpening should not be copied uncritically or represented as the same methodology as our forward-only validation. A winning realized score does not isolate the causal contribution of each feature.

Ken Pomeroy's explanations motivate opponent/venue-adjusted offensive and defensive efficiency, tempo and the Four Factors. These concepts already exist in our bank, so improvement must come from a materially different representation, source, adjustment, uncertainty treatment or interaction—not renaming them. Academic analysis of Four Factors documents nonlinear relationships and dependence on the other factors; that supports testing specific interactions but does not prove that they improve NCAA tournament predictions.

Sources:
- [2026 winner's original write-up](https://github.com/harrisonhoran/kaggle-march-mania-2026-1st-place/blob/main/kagglewriteup.md).
- [KenPom ratings explanation](https://kenpom.com/blog/ratings-explanation/).
- [KenPom Four Factors explanations](https://kenpom.com/blog/stats-explained/).
- [KenPom glossary](https://kenpom.com/blog/ratings-glossary/).
- [Poropudas and Halme, Dean Oliver's Four Factors Revisited, 2023](https://arxiv.org/abs/2305.13032). NBA examples motivate mechanisms; transfer to NCAA is a hypothesis, not established evidence.

This is an initial source-grounded research agenda, not a completed exhaustive literature review. Additional primary-source investigation belongs at the start of each round.

## Evaluation contract

Use one physical game exactly once for scoring. Mirror training examples only with consistent labels and keep both orientations in the same season split. Report game-weighted Brier using `(p - y)^2`, with 0/1 coding, and separate men's/women's and per-season results. Keep the current mean-season selection metric alongside the game-weighted official aggregation; do not switch selection criteria after seeing results.

Scalers, imputers, screening, learned ratings/mappings, target encodings, hyperparameters and calibration must follow the specified temporal training boundaries. Same-season regular results may build a pre-tournament snapshot only when every contributing game precedes its cutoff. Rankings require publication cutoffs and source edition checks. Seeds and field-selection summaries need their own declared availability contract; they cannot be smuggled into the seed-free path.

The 2016–2019/2021 development seasons and 2022–2025 benchmark have already been explored. The 2026 submission scores are also consumed. Reusing them is retrospective research, not a new untouched holdout. Freeze a prospective future evaluation when one becomes available, while continuing legitimate historical representation research now. Keep a complete experiment ledger to expose repeated selection.

For each challenger save matched predictions, per-game losses, per-season metrics, family definitions, kept/dropped columns, coverage, fitted preprocessing, source/data/config hashes and a decision. Report paired season-block uncertainty descriptively and disclose the small number of seasons and repeated exploration.

## Bounded execution gates for later experiments

These are proposed **caps**, not measured runtimes or blanket cloud-spend authorizations. No experiment below runs from this kit.

| Gate | Scope | Stop condition and receipt |
|---|---|---|
| Unit/synthetic | Availability, swap invariance, schema, mirror grouping, deterministic hashes, checkpoint reuse | Any failure: fix the cause; no fitting |
| Feature smoke | A small subset of legal pre-cutoff games/teams | Missing prerequisites, implausible units or unexplained coverage loss: stop and save diagnostics |
| Pilot | One predeclared historical season, compact anchor + one family, fixed estimators, single CPU process | 5-minute cap per task and 15-minute total pilot cap initially. Stop on failure or clear domination; save each completed fit. One season is a debugging gate, not acceptance evidence |
| Representative study | Only after pilot passes; predeclared multiple seasons and separate sexes | Maximum 30 minutes per approved stage, persistent per-task checkpoints; no uncontrolled parallel sweep |
| Promotion decision | Add-family + drop-family ablations, stability, coverage and calibration review | Tentative useful-gain threshold: pooled Brier improvement of 0.001, broadly positive season signs and no unexplained severe regressions. Predeclare and sensitivity-check this threshold; it is a heuristic, not statistical significance |

If an apparently useful family is weak marginally but plausible conditionally, test a tiny predeclared interaction block or a change in screening, not a blind increase in the candidate cap. Keep model algorithms fixed during representation attribution. Ensembles remain a later, separately attributable investigation.

## Mandatory milestone record

Every substantial stage records: hypothesis; attempted/completed work; passes; failures/negative findings; actual metrics and evaluation population; saved hashes/checkpoints; GitHub state; methodological lesson; next highest-value experiment; and why more computation is warranted. An activity log alone is not a result. No skipped or failed experiment counts as a validated family.

Do not declare feature engineering exhausted until major high-value families are explicitly accounted for as tested, redundant, unsupported by evidence, unavailable under the time/rules contract, or infeasible within the agreed budget. “Unavailable” is a data limitation, not a negative predictive finding.
