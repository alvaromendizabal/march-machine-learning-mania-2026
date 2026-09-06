# Notebook 02: feature store and evidence

The canonical notebook is `notebooks/02_feature_store_and_diagnostics.ipynb`.
Its implementation lives in importable, tested modules. The historical notebook
remains recoverable from Git commit `2791d6b`; it is not duplicated under a
different filename. Historical model and submission results remain available.

## What the first benchmark established

AWS run `b0ca1fe8efba1b73a689623d9ae3e6c79de9ff3a1c925a9967e74bce9ae0049d`
completed 120 model folds in 31.545 seconds on official data. Its input hashes
and result tables are recorded in `reports/research/run.json`.

| Fixed logistic model | Men: mean season Brier | Women: mean season Brier |
|---|---:|---:|
| Seed | 0.200158 | 0.151179 |
| Strength | 0.191268 | 0.144308 |
| Full 25-feature compact candidate | 0.192310 | 0.153326 |

The added compact features did not improve the strength baseline. The men's
older, richer system reports 0.180669; its saved game-level forecasts are needed
for an exact paired comparison. The women's older best reports 0.148684.
These are retrospective development results, not Kaggle submission scores.
The original feature store already proposed hundreds of correlated features;
feature count is not evidence of predictive value.

## New feature contract

| Family | Statistical definition and intended information |
|---|---|
| Strength/core | Preserve the seed, home-adjusted ridge margin, schedule, box-rate and compact interaction controls |
| Adjusted efficiency | Separate offensive and defensive effects per 100 shared possessions; full-season and 30-day weighted fits |
| Adjusted Four Factors | Separate team and opponent effects on effective shooting, turnover avoidance, offensive rebounding and free-throw rate; include home effect |
| Form | Opponent-adjusted residual dispersion, downside tail, recent residual and shrunk road/neutral residual; schedule spread, strong-opponent performance, shrunk close-game rate and rest |
| Shooting | Beta-binomial posterior mean and standard deviation for two-point, three-point and free-throw shooting, on offense and defense; contemporaneous league prior equivalent to 100 attempts |
| Tempo | Possessions per 40 minutes, pace variation, three-point scoring dependence, possession disagreement and reliable-box-score coverage |
| Dynamic | Standard and capped margin-weighted Elo; 65% annual carryover; simultaneous daily updates; change during the final 30 days |
| History | Prior five seasons' NCAA wins, appearances and shrunk seed strength; current-season NCAA labels excluded |
| Rankings | Latest pre-cutoff ordinal per team/system, 14-day staleness limit, consensus, disagreement, vendor count, age and momentum from matched vendors |
| Interactions | Strength conditioned on pace, shooting uncertainty and three-point dependence; cross-team shooting and offense/defense products |

The registry contains 80 features, of which five require men's Massey data.
Missing sources are explicit. The runner never invents women's external ranks,
injuries, player minutes, roster continuity or unavailable player statistics.
Those require licensed historical data with publication timestamps before they
can enter this protocol. Formulas and constants are in `advanced_features.py`;
`feature_registry.csv` records source, family, transformation, cutoff and parity.

Shared possessions average both box-score estimates. Pace accounts for overtime.
Adjusted ratings exclude games whose possession estimates disagree by more than
10%; coverage is retained as a feature and diagnostic. Higher adjusted offense
and defense are better; turnover targets use turnover avoidance. Sparse shooting
and situational estimates shrink toward declared priors rather than becoming
unstable raw percentages.

## Temporal evaluation

- Build snapshots for 2013–2026, excluding the canceled 2020 tournament.
- Fit and score ablations only on 2016, 2017, 2018, 2019 and 2021, training on
  earlier seasons with at least three prior seasons. Outcomes from 2022 onward
  never enter this benchmark's training, selection or reported metrics.
- All regular-season snapshots use DayNum <= 132. Pre-tournament seeds are
  permitted; this contract is not suitable for predictions made before seeding.
- NCAA labels are joined only after feature-only matchup construction. Strictly
  prior NCAA outcomes are permitted in program-history features.
- Fit imputation/scaling on each training fold. Mirror training games only after
  splitting, and score one physical validation game in lower-TeamID orientation.
- The same two fixed model recipes as notebook 05 isolate feature effects.
  Evaluate single-family additions, the full set and every drop-one ablation.
  There are 400 folds without rankings and 420 with men's rankings.
- Brier is the official metric. Compare macro-season Brier and game-weighted
  Brier; inspect log loss, AUC, average precision, calibration bins and ECE.
  Precision/recall/F1 use a fixed 0.5 threshold and lower-TeamID as positive.
- Paired uncertainty resamples whole seasons. Five seasons and many comparisons
  make these intervals diagnostic; choosing the lowest observed result is not
  independent evidence of improvement. No model is automatically promoted.

## Run in the existing AWS Studio terminal

```bash
git pull --ff-only
python3 scripts/bootstrap.py
.venv/bin/march-data --output data/kaggle \
  --s3 s3://sagemaker-march-mania-560403859723-us-west-2/data
.venv/bin/march-features --raw data/kaggle/raw \
  --output outputs/feature_store \
  --s3 s3://sagemaker-march-mania-560403859723-us-west-2/feature-store
.venv/bin/python scripts/notebook.py --execute
```

The downloader uses Kaggle authentication already configured in that runtime.
If it reports an authentication failure, run `.venv/bin/kaggle auth login` there.
Accept the competition's data terms through Kaggle if your account has not done
so. Do not paste tokens into notebooks, command arguments, Git or chat.

The downloader follows every listing page and freezes the file list, sizes and
release timestamps. It downloads every official file, including the sample
submission, instead of extracting only the eight compact-run inputs. Kaggle's
client performs identity-checked HTTP-range resumption when the server supports
it. A completed file gets a checksum checkpoint. ZIP responses undergo name,
size and CRC checks. Repeating the command reuses completed files.

Snapshots and model folds commit their checkpoints after output hashes are
recorded. UTC events include total elapsed seconds, task timing and heartbeats.
S3 uploads retry through the SDK; an unsuccessful upload fails explicitly and
the next run retries it without refitting a completed task. The completion
summary is uploaded last. EBS retains stopped-space work; versioned private S3
retains an independent copy. An unfinished estimator restarts its fit.

Use the exact same commands to resume. Changed source, data, dependencies or
configuration require a new output directory; historical experiments are never
overwritten. A fresh Kaggle release likewise belongs in a new data directory.
No repeated repair notebooks or alternate implementation filenames are created.

## Review and downstream handoff

Open canonical notebook 02 and choose **Run All**. It reads completed local
results or the recorded Git evidence, and identifies the source. Open the
standalone `outputs/feature_store/report.html` for interactive charts. The notebook
execution command also writes rendered copies under `outputs/validation`.

Artifacts include team snapshots, historical matchups, a feature registry,
source coverage, missingness, every out-of-fold forecast, metrics, ablation
intervals, models and hashes. If the official Stage 2 sample is present,
`submission_features.parquet` preserves its exact row order and identifies
seeded/unseeded routes. It contains features, not final predictions.

Notebook 03's historical implementation still consumes its original feature
contract. The next stage is to migrate its nested chronological tuning and
calibration to this new schema, compare old/new forecasts on identical IDs, and
freeze the submission recipe. Do not feed the new store silently into the old
schema or submit an ablation winner selected on these same seasons.

The official 2026 deadline was March 19, 2026. A new 2026 file is a retrospective
or late-submission exercise, not a route to a new medal in that completed event.
The next live competition requires its own official files, rules and deadline.

Sources: [Kaggle competition](https://www.kaggle.com/competitions/march-machine-learning-mania-2026),
[official Kaggle authentication](https://github.com/Kaggle/kaggle-cli/blob/main/docs/README.md),
[official download commands](https://github.com/Kaggle/kaggle-cli/blob/main/docs/competitions.md),
[probability calibration](https://scikit-learn.org/stable/modules/calibration.html).
