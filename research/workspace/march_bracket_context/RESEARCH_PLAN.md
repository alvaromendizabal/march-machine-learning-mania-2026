# Round 09 research protocol — announced-bracket eligibility

## Evidence-led pivot

Round 08’s primary mechanism-given-rates comparison failed for men and women. Preserve it; no hyperparameter retuning or feature inflation is justified by those results. This round investigates information outside the compact reference’s regular-season team statistics: the women’s first-/second-round hosting policy conditional on the announced bracket.

The domain-source claims below come from official NCAA and university publications. The exact feature equations and experiment gate are **our hypotheses**, not conclusions asserted by those publications. No external data is downloaded at execution time. Raw seed tables already present in the verified Kaggle snapshot supply the actual inputs.

## Primary-source basis

1. NCAA, June 30, 2014: the 2015 move to the top 16 seeds hosting early rounds; neutral regional sites return in 2015. https://www.ncaa.org/news/2014/6/30/division-i-women-s-basketball-committee-seeks-cost-savings-for-championship.aspx
2. NCAA, December 16, 2015: 2016 first/second rounds at top-16 home courts and retention of that format; field announcement precedes the tournament. https://www.ncaa.org/news/2015/12/16/committee-decides-women-s-basketball-championship-dates
3. Charlotte Athletics, February 14, 2019 (before field announcement): an approved alternative hosting arrangement for South Carolina; eligibility is not equivalent to playing at the usual home venue. https://charlotte49ers.com/news/2019/2/14/general-charlottes-halton-arena-pegged-as-possible-ncaa-site
4. South Carolina Athletics, March 18, 2019 (before first round): fourth seed, opening group and Charlotte location announced. https://gamecocksonline.com/news/2019/03/18/womens-basketball-gamecocks-open-ncaa-tournament-with-belmont/
5. Stanford Athletics, March 19, 2017 (after first round): confirms Stanford could not host because of a gymnastics event. This is **limitation evidence only**, not an as-of feature input and not an override. https://gostanford.com/news/2017/03/19/cardinal-at-k-state

No result, score, team name, arena, location or site override from those articles is placed into the feature arrays. A later verified-venue study would require a complete, historically dated hosting map—not selective exceptions inferred from outcomes.

## Exact information contract

The prediction timestamp is after the field is announced and before the first NCAA game. Regular-season statistics are frozen through day 132. Complete women's 64-team seed panels are required. Supported seasons: 2013–2019 only. Women's later play-ins, 2021 centralized arrangements, and 2026 inference are not supported by this code and fail closed rather than extrapolating silently.

The four pod seed groups in each region are {1,16,8,9}, {4,13,5,12}, {3,14,6,11}, {2,15,7,10}. Within-pod potential opponents can meet in the first two rounds without needing to know who actually survives. A non-top-four team is not asserted to be at home merely for appearing in a host's pod. Two regions with the same numerical pod are different pods.

For each season we construct all 64 choose 2 = 2,016 pairs before attaching target outcomes. Actual tournament pairs are used later to score predictions. The feature constructor accepts matchup keys only and rejects y, WLoc, DayNum, CityID and score columns. Seed data and base snapshots are independently verified against their archived SHA-256 identities.

## Features

Let `q(A) = I(seed(A) ≤ 4)`, `P(A,B) = I(same region AND same four-team pod)`, and `E = I(2015 ≤ season ≤ 2019)`.

**Existing control:** `S = q(A) − q(B)`. This ordinary nonlinear seed transformation is not a novel claim. The original 16 inputs already contain numerical seed difference, strength, schedule, margin, adjusted offense/defense and simple shooting profiles. S tests top-four status beyond linear seed difference.

**New candidate 1:** `H = E × P(A,B) × S`. This is signed **seed-derived hosting eligibility**, not an observed home/away flag. It is zero for nonpod pairs, nonhosts, and prepolicy seasons. A zero before 2015 means this particular policy feature is inapplicable; older games are not being labeled neutral.

**New candidate 2:** `V = H × 10 / sqrt(margin_sd(A)^2 + margin_sd(B)^2 + 1)`. The neutral-point floor and factor 10 are fixed numerical conventions. V asks whether a structural hosting advantage has different probability impact in higher- versus lower-variability matchups. It is not calibrated probability uncertainty and is not estimated from validation outcomes.

Every feature negates under team swapping. Every pair's context is deterministic from the declared as-of inputs. Missing seeds, duplicated identities, impossible fields, seed/snapshot disagreement and invalid variability stop the run. No actual venue is imputed.

## Comparison design

Women only. Four validation years: 2016, 2017, 2018, 2019. Training uses strictly earlier years from 2013. Reference recipe remains frozen: C=0.1 logistic regression, no intercept, deterministic mirrored training orientations with total weight one per physical game, training-only RMS scaling, constant-column removal only. No rebalanced feature selection, model search, temperature search or ensemble.

| Arm | Inputs | Role |
|---|---:|---|
| anchor | 16 | Replay existing reference |
| seed_status | 17 | Reference + S |
| host_context | 18 | Reference + S + H |
| host_context_scaled | 19 | Reference + S + H + V |

Primary Brier contrast: **host_context_scaled − seed_status**. Secondary contrasts: status versus anchor, H given status, V given H. Because the input sets remain fixed, component removals do not replace features through reselection. Contributions remain model-conditional, not causal estimates.

Four cached anchors are verified from native JSON models and exact prediction keys. Optional missing historical log_loss is recalculated from verified predictions; inconsistent stored diagnostics are errors. Twelve new challengers maximum; no new rating-model fits. Seven women’s base snapshots reused. Seven small bracket feature tables built and content-addressed; repeat runs reuse them.

## Gate and limits

Consider a separate confirmed-venue/later-era study only if mean primary delta ≤ −0.0005, at least 3/4 primary folds improve and the worst delta ≤ +0.003. This is not a significance threshold. The gate starts nothing automatically and does not promote a feature. The secondary unscaled hypothesis is reported as secondary, not substituted as the primary after inspection.

Stage hard ceilings: preparation 180 s, evaluation 180 s, report 120 s. Per-stage exclusive lock, subprocess-group cancellation, 15 s heartbeat. Limits are not instance billing caps. Persist every completed table/fit independently. Refuse missing/corrupt upstream artifacts; never rebuild the previous research bank implicitly.

## Interpretive risks

* These are repeatedly consumed historical seasons, not untouched validation. No leaderboard record or future performance is promised.
* 2016 has only 2015 as a policy-era training season; support counts by fold are mandatory. Broader venue history may need a separately verified dataset.
* Eligibility confounds seeding, bracket stage and expected hosting. The S control reduces one obvious alternative explanation but cannot prove a causal home effect.
* Known venue exceptions mean some eligible teams did not play at their normal home court. No selective venue edits are made after seeing Brier.
* The fitted logistic is a diagnostic reference, not the submitted pooled XGBoost/conference model. Any useful signal must survive a fixed production transfer and suitable later-era check before claiming submission improvement.
* The men's ordinary-rate gain from round 08 is recorded as a separate unstable finding. This women's experiment neither promotes nor erases it.

## Research still open

Do not declare the feature space mature from this narrow round. The next high-value source-backed extensions include a complete as-of women's host/site dataset, actual preannounced travel context, verified roster/availability history, and production-input lineage. Individual rating-system levels/deviations and PCA were already investigated in the repository; repeating them should first consult their saved results. Further additions must change an identifiable signal or test, not merely add columns.

Successful artifacts: native-JSON model checkpoints; all-pairs context tables; measured metrics, fixed-set ablations, gate and cohort diagnostics; 10 Plotly charts and self-contained HTML; a small privacy-scoped return archive. Return `reports/milestone_09_return.zip` and stop here.
