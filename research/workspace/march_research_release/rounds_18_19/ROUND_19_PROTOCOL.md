# Round 19: Three-point and free-throw scoring-source dependence

 ## Hypotheses prepared before the new results
 Family A: 3 × made three-pointers / total points. Family B: Made free throws / total points. For each family, estimate one offensive-team effect and one defensive-opponent effect from legal same-season regular-season games, including a home/away indicator. Four matchup differences are the candidates. The four corresponding unadjusted offensive/allowed rates are controls, not novel discoveries.

 The question is whether opponent/location adjustment adds value beyond those ordinary rates and the existing 17-input consensus reference. These concepts have analogues in the broader feature bank; this is a controlled representation test, not a claim that rebounds, assists or points distribution were previously unknown.

 ## Sources versus implementation choices
 Established rate definitions and opponent-adjustment rationale: 
 https://kenpom.com/blog/stats-explained/
https://kenpom.com/blog/ratings-glossary/

 The particular weighted linear adjustment, prior sizes, inference from box-score columns and evaluation recipe are proposed implementation choices, not reproduced vendor ratings or proven predictive improvements. The round19 point-source formulas also follow direct scoring arithmetic (3 points for a made three-pointer and 1 per made free throw); no paid API, scraped player data or unverified venue source is needed.

 ## Exact fitting contract
 For game orientation i, y_i = events_i / opportunities_i. Fit
 `sum_i w_i * (y_i - intercept - offense_team_i - opponent_effect_i - home_coefficient*home_i)^2 + 20 * ||penalized coefficients||^2`, with w_i = opportunities_i / mean(opportunities).
 Intercept is unpenalized. The sign of offense is increasing target share; defense is negative of the opponent coefficient, so positive means lower allowed share. These signs are not performance labels. Use a direct Cholesky solve, maximum 500 teams, residual-certificate tolerance 1e-9, positive finite parameters, and minimum 50 relevant opportunities for seeded offense and defense. Unadjusted controls use 100 opportunity-equivalents of the same legal season's league prior. Weights are an experimental opportunity emphasis, not a claim to reproduce KenPom's weighting.

 Zero-opportunity observations are excluded only for the relevant target when event count is also zero; nonzero events with zero opportunities stop. Round18 stops if assists exceed field goals. Round19 requires score = 2*FGM + FGM3 + FTM and positive total points. No clipping repairs invalid counts.

 ## Boundaries
 Use regular-season games through day132 for 2013–2019 and 2021–2025; no 2020 or 2026 labels. Construct all seeded pairs before attaching tournament outcomes. Existing label logic excludes First Four using paired seed codes and the 2021 no-contest. Training seasons precede the validation season. Learned tournament preprocessing is training-only. Matchup features reverse sign under team swap.

 ## Fixed comparisons / resources
 Men, 2022–2025. Six recipes: reference17; ratecontrol21; familyA23; familyB23; both25; duplicated-rate-control25. Twenty new logistic classifiers, four replayed references, 24 season-local rate fits (two per twelve seasons), twelve snapshots, ten planned inline Plotly figures. Logistic C=0.1, no intercept, mirrored orientations and physical-game weighting remain unchanged. No automatic search or ensemble.

 Primary: `adjustment_given_rates`; supporting conditional family tests and `both_given_duplicate`. Consider follow-up only for mean delta≤−0.0005, improvements in≥3/4 seasons, worst deterioration≤+0.003 and mean delta vs duplicate<0. None is a significance test. Do not select the most favorable secondary contrast as a substitute for the primary. No result from the other new round affects formulas or selection.

 ## Limits / limitations
 All-season audit120 seconds (zero fits), smoke90, smoke replay90, remaining preparation300, evaluation180, reporting120. Two threads; 6GiB worker RSS guard. Actual runtime/cost unmeasured. Known sources and checkpoints must exist; no rebuild or download on missing inputs. Scoring shares are compositional: more of one source implies less of another. They conflate attempt mix and accuracy and are not pure causal dependence, talent or efficiency measures. Free-throw mix can reflect intentional fouling/game state.

 Years are already-used exploratory history; four season clusters cannot provide strong uncertainty calibration and repeated selection can overfit. A positive compact-reference result must transfer to the stronger production recipe before a submission claim. No candidate gain, test success or runtime is claimed before user execution.
