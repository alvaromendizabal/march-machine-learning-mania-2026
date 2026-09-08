# Feature research: what the expanded bank actually adds

The completed experiment generated **3,106 candidates**, **9,200 team snapshots** and
132,133 official-template feature rows. It ran **1,050 temporal ablation fits** on
2016–2019 and 2021. The template table contains features, not submission probabilities.

The bank consists of 124 existing signals, 2,944 distribution/venue/opponent/trajectory/
peer candidates, 26 official coach-history signals and 12 conference-context signals.
All 20 full-bank fits retained 128 inputs. Across those fits, **251 distinct features**
were retained at least once; there is no globally selected 251-column model. Across
all ablations, 1,674,530 candidate decisions included 1,585,764 rejections.

## Measured results

| Fixed recipe | Men: mean season Brier | Women: mean season Brier |
|---|---:|---:|
| Strength logistic | 0.191268 | 0.144308 |
| Original-bank logistic | 0.217966 | 0.167989 |
| Expanded-bank logistic | 0.207742 | 0.171561 |
| Original-bank histogram boosting | 0.196503 | 0.161895 |
| Expanded-bank histogram boosting | 0.192678 | 0.167173 |
| Lowest observed logistic block | 0.187608 · rankings | 0.143331 · conference |

Game-weighted Brier for the last row is 0.187544 for men and 0.143331 for women.
The `baseline_124` control uses the original bank under the current fitting protocol;
its women's route has 101 eligible inputs after removing all 23 Massey-derived columns.
These fixed-recipe minima are exploratory feature comparisons. Notebook 03 separately
selects blocks and regularization using earlier OOF predictions.

## What to retain from the experiment

The broader bank improves the men's original-bank fits but does not beat the compact
ranking logistic model. It worsens the women's full-bank fits. More columns alone are
not a reliable route to a stronger tournament forecast.

In the expanded men's non-Massey bank, retaining coach features changes mean-season
Brier by **−0.010429** for logistic regression and **−0.006302** for histogram boosting.
The respective paired season-bootstrap intervals are [−0.031271, 0.009248] and
[−0.014599, 0.002199]. These are conditional pipeline effects: removing a family also
reruns screening and changes which other inputs occupy the 128-feature capacity.

Adding Massey to the full bank changes histogram Brier by **−0.002479** but logistic
Brier by **+0.003250**. Target encodings contribute smaller, model-dependent changes.
Women's conference logistic improves the strength baseline by **−0.000976**, with
interval [−0.005378, 0.004480]. None of these intervals establishes a reliable benefit
across future tournaments. Five seasons and many comparisons limit the conclusions.

## Availability and temporal safeguards

Every active men's team has legal Massey and coach coverage in 2013–2026. Legal ranking
editions end at day 128 in these seasons, before the day-132 snapshot cutoff. The full
raw-season coverage table also identifies earlier unavailable and incomplete periods.
Women's Massey and coach tables are absent; their ablations correctly leave forecasts
unchanged. Both populations have season-specific conference membership.

Target histories use strictly earlier seasons, a fixed Beta(10,10) prior, a three-season
half-life and a five-season window. Coach performance uses earlier games assigned to
the coach's actual intervals. Conference context uses pre-cutoff regular-season games
and that season's membership. Future-outcome, cold-start, realignment, order-invariance
and team-swap tests enforce the relevant boundaries.

`run.json` binds the results to exact data/configuration/source hashes and a verified
private archive. Public tables expose scores, coverage, rejection counts and retention.
The complete per-candidate audit and every fitted model remain in the archive. The
successful resumed attempt took 1,563.702 seconds; this excludes its earlier disk-limited
attempt. Resource telemetry from the restricted process namespace is not a RAM estimate.
