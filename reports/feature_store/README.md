# Notebook 02 evidence

The current 104-feature contract completed **480 real-data folds in 111.622
seconds** using the eight official CSVs preserved from the verified Studio run.
Massey and the official sample were unavailable. Tests exercise their integration
with synthetic data; synthetic performance is never reported as Kaggle evidence.

The files here are checksummed in `run.json`. `feature_usage.csv` is a compact
view of the full-feature logistic models; the independent S3 archive contains
all folds, every fitted estimator and the complete feature-use audit. The archive
also contains raw inputs, source files, dependency lock and task checkpoints.

A full restoration reused all **510 tasks**, with **zero refits**, in 13.732
seconds. Each saved model's actual feature dimension and ordered column list are
checked against its feature audit in integration tests. Pytest treats warnings
as errors. Both review notebooks execute in the GitHub CI kernel gate.

The fixed strength control is reproduced on 3,894 matched forecasts within
3.2e-15 probability tolerance. Seed target encoding slightly improved men's
mean-season Brier (0.191268 to 0.190539), with a bootstrap interval crossing zero;
it was weaker than the Four Factors candidate. Team encoding hurt both genders,
and seed encoding did not improve women. No candidate is promoted automatically.
Massey's real-data benefit has not been measured by this run.

`manifest.git_commit` identifies the base checkout at run start. The benchmark
ran on the feature branch's working implementation before its publication commit;
per-file `manifest.inputs.source` hashes identify the exact evaluated code.
The previous experiment and archive remain linked from `run.json` and retained
in Git history. Do not compare its full-block score with the current full block
as though they contained identical features.
