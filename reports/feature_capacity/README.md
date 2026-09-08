# How many of the candidate features should reach the estimator?

Completed 2026-09-08 on notebook 02's exact **3,106-candidate matrix**. The hypothesis
was that the fixed 128-feature limit might discard useful signals or retain too much
noise. All limits were declared together before this follow-up ran. The underlying
development seasons had already been explored; this is retrospective evidence.

The study compares 32, 64, 128 and 256 retained inputs with the same train-only
association/redundancy screen, fixed logistic and histogram recipes, and physical games.
There are three routes: men with Massey, men without Massey, and women without Massey.
Women's official coach/ranking sources remain unavailable. Mirroring happens inside
training; each validation game is scored once with symmetric probabilities.

**168 fits were evaluated: 138 newly trained, 30 inherited from verified original
128-input checkpoints.** Template cloning discards learned estimator state. There are
seven OOF years, starting in 2014, and five reported outer seasons: 2016–2019 and 2021.
The nested stream selects capacity by mean-season Brier on strictly earlier OOF
seasons, with at least two such seasons. Ties favor the smaller representation.

| Route / fixed estimator | 32 | 64 | 128 reference | 256 | Forward-selected |
|---|---:|---:|---:|---:|---:|
| Men with Massey / logistic | 0.192095 | 0.203435 | 0.207742 | 0.235234 | 0.192095 |
| Men without Massey / logistic | 0.194492 | 0.201210 | 0.204492 | 0.236982 | 0.194492 |
| Women / logistic | 0.157610 | 0.159531 | 0.171561 | 0.178761 | 0.164711 |
| Men with Massey / histogram | 0.196706 | 0.191393 | 0.192678 | 0.206585 | 0.196706 |
| Men without Massey / histogram | 0.199318 | 0.193887 | 0.195157 | 0.206869 | 0.194984 |
| Women / histogram | 0.167492 | 0.163432 | 0.167173 | 0.166032 | 0.167077 |

Values are mean-season Brier; lower is better. `leaderboard.csv` separately reports
game-weighted Brier, log loss, ROC AUC and calibration error. Every fixed-limit and
nested prediction is retained in `evaluation.csv`; `predictions.csv` also includes
the earlier OOF seasons needed to reconstruct selection.

The forward-selected logistic changes against 128 inputs are **−0.015647** for men
with Massey, **−0.010000** without Massey and **−0.006850** for women. All six nested
comparisons' paired season-bootstrap intervals include zero. The search supplies
exploratory sensitivity evidence, not independent statistical confirmation. Some
fixed-limit contrasts have intervals excluding zero; see `intervals.csv`. No
multiple-comparison correction or causal feature-effect claim is made.

The smaller screens improve the broad logistic fits, but all of these results
remain behind the existing compact development leaders. The experiment gives no
reason to expand the main model beyond 128 retained inputs. It also shows that 128
is not a universal optimum. The current 03/04 recipes are unchanged and their
results retain their original fingerprints; this follow-up is displayed in 02.

No benchmark or 2026 outcomes enter this experiment. In particular, the capacity
was not chosen by testing alternatives on the already-consumed 2022–2025 benchmark.
No submission file was generated.

The second actual execution reused all **168 checkpoints**, repeated **zero fits**
and preserved every estimator file and prediction checksum. A checksum-verified
portable archive contains full models, screening audits, exact source, input matrix
and logs. Upload of this new archive is awaiting a specific storage approval;
it is not described as a completed cloud backup. The earlier feature/model archives
remain verified in S3. Public reports and source/configuration/parent hashes are
validated whenever notebook 02 reads this study.

Reproduction is implemented in `march_mania.publication.capacity`; notebook 02 calls
it in train mode after verifying the upstream feature store. It is part of the
canonical notebook, not a second notebook that the reader must run manually.
