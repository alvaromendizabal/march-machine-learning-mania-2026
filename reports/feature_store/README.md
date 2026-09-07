# Feature-store evidence

The current run uses the exact 35-file Kaggle download recorded on 2026-09-07.
It builds 124 features, 9,200 team snapshots and all 132,133 official Stage 2
matchup rows. It evaluates 660 model folds on 2016–2019 and 2021, with men's
Massey coverage included. `run.json` records source/data/environment hashes and
checksums for every published aggregate evidence file.

The prior 104-feature experiment remains in private S3 under fingerprint
`554cee2384b92a822f973e415054bce2d2fca3df68a4efcaf6bd11c4e8e24c69`.
All 18,878 comparable control forecasts reproduce exactly (maximum probability
difference 0.0). Full/drop-one models change because their feature sets change.

| Logistic candidate | Men: mean season Brier | Women: mean season Brier |
|---|---:|---:|
| Strength baseline | 0.191268 | 0.144308 |
| Add ball control | 0.190589 | 0.145600 |
| Add schedule context | 0.191737 | 0.147245 |
| Add scoring shape | 0.193138 | 0.145602 |
| Best observed existing family | 0.187602 (rankings) | 0.143597 (dynamic Elo) |

The men's ball-control delta is -0.000679, with a paired season-bootstrap 95%
interval [-0.011127, 0.010139]. It is exploratory evidence, not an established
improvement. The all-feature logistic model is worse than the compact baseline.
No new final model or submission recipe is promoted from this experiment.

The Git feature-usage table includes the full block for both model families.
Every per-candidate and per-fold audit is retained in the private run archive.
