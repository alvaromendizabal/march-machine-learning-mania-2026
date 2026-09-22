# Current research: margin supervision as a complementary forecast

Evidence through **2026-09-21 23:50 UTC**. Main entry point:
[executed case study](../portfolio/current_research.ipynb).

## Contract and mechanism

The retained men's core uses seed difference and Harry-rating difference. The
auxiliary representation adds 31 existing feature differences (ratings, schedule,
efficiency, shooting, possession and form). The controlled comparison uses the
same 33 inputs for signed binary outcomes and signed point margins divided by 20.
Both targets use XGBoost squared error, depth 3, learning rate 0.03, at most 1,200
trees and 75-round early stopping. The complete publication policy is recorded
in `method` within the [evidence file](../reports/current_research/evidence.json).

For outer years 2023, 2024 and 2025, only earlier tournament seasons enter training.
Each earlier season is left out in turn: 19, 20 and 21 inner folds. Three seeds and
two targets produce **(19 + 20 + 21) × 3 × 2 = 360 fits**. A common zero-intercept
sigmoid calibration method is fitted on pooled inner held-out scores; calibrated
per-model forecasts are averaged over folds and then seeds. The final rule is
**0.75 × frozen stronger core + 0.25 × auxiliary probability**.

The reference core is not refitted. The richer margin ensemble is not an exact
reproduction of the competition winner's hyperparameters or calibration. Margin
supervision and this fixed blending experiment are tested adaptations, not a
claim to own another author's method or replicate every winning component.

## Results and decision

| Historical men: 189 main-bracket games | Brier |
|---|---:|
| Frozen stronger core | 0.1795046214 |
| 25% rich binary-target blend | 0.1778816298 |
| 25% rich margin-target blend | 0.1774648178 |

The margin blend gains **0.0020398036** against the core and **0.0004168120** against
the matched binary blend. It improves the core in all three years and for all
three seeds. Margin beats binary in two years; binary is better in 2025.
All-tournament improvement, including play-ins, is **0.0016179283**. It is not the
same evaluation population as the main-bracket table.

All seven predeclared checks passed. These require at least 0.0005 gain against
the stronger core, at least 0.00025 gain over the matched target control, at least
two improving years, nonnegative aggregate results for every seed, an all-tournament
guard, worst-season guard and conditional bootstrap support. The decision remains
**CANDIDATE_BUILD_REVIEW**. No 2026 challenger file or new Kaggle score was produced.

## Why negative results are included

The report compares five procedures on the same eight-year, 503-game men's screen:
full feature union, residual PCA, nested subset selection, frozen-core feature
correction, and the fixed rich margin blend. The first four were rejected. The
margin screen justified the later fuller-ensemble check, not an immediate submission.
The women's subset branch was stopped after a predefined worst-season violation;
its four-season partial evaluation is not plotted as an eight-season result.

## Limitations that affect interpretation

2023–2025 were already used in project development. The margin proposal was
selected from an earlier four-proposal screen on overlapping years. Outer-year
exclusion prevents direct same-year fitting, but does not reverse accumulated
validation selection. Bootstrap estimates are conditional on the chosen model
and three reused seasons; they are not selection-adjusted confidence in a future
competition result. Inner held-out scores guide both early stopping and calibration.
Averaging three seeds measures numerical stability, not three independent tournaments.

The incumbent's 0.1098691 score is a recorded late Kaggle submission. Harrison
Horan's writeup reports the 0.1097454 first-place benchmark on 126 games. The
0.0001237 difference is a numerical reference, not an original rank claim or
proof of exact scoring-scope equivalence. No historical Brier improvement is
converted into a predicted Kaggle score.

## Provenance and publication boundaries

The latest source is `march_margin_robustness_return_20260921T234907325480Z-561.zip`,
SHA-256 `4b1f034521a2a81a9b84f5f3d2720949e0d63cfe898740bfee400978e1d6a8ab`.
Its 21 inventory entries were checked, and main-bracket Brier was independently
recalculated from saved predictions before publication. The original AWS notebook
has seven Plotly outputs and seven image fallbacks. Its SHA-256 is recorded in
the evidence JSON; this curated six-chart report is a different notebook.

The JSON preserves aggregate results, source archive hashes, source notebook
identity, the late-submission identifier and prediction-file checksum. This is
an auditable publication extract, not a claim that hashes alone enable recovery
of the private source files. The underlying archives remain in the owner's records.

**GitHub receives:** portable report code, a clean-kernel executed notebook,
aggregate evidence, figures, tests and interpretation. Existing repository
implementation and historical release evidence remain intact.

**AWS retains:** complete current training sources and local modifications, raw
competition records, feature caches, per-game predictions, model binaries,
checkpoint directories, local configuration and environments. This curated
publication does not pretend to synchronize all of those files. Full training
reproduction needs those authorized inputs and the retained source state.
The report reproduces its own published analyses using only committed aggregates.

## Attribution and missing mechanisms

The compact core is adapted from [Harrison Horan's first-place writeup](https://github.com/harrisonhoran/kaggle-march-mania-2026-1st-place/blob/main/kagglewriteup.md).
Existing broader research is indexed in [research/README.md](../research/README.md).
External market/player information and every other top-solution mechanism have
not been reproduced merely because this target ablation passed. This publication
makes no claim of comprehensive top-solution reconstruction.

## Next modeling boundary

Freeze one candidate using the retained policy; verify temporal inputs, probability
ranges, template ordering, unique IDs, exact women/protected-row invariance and
checkpoint lineage. Only after those checks should one separately authorized
submission test the candidate. Publication itself does not train, deploy or submit.
