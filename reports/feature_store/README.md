# Measured feature-store evidence

The first rebuilt-store benchmark completed 400 chronological model folds on
eight official CSV files. `run.json` records source/data hashes, runtime versions,
the original run duration, and checksums for the evidence tables in this folder.
The manifest's Git commit is the base revision before this working-tree change;
its per-file SHA-256 values identify the exact implementation used for the run.

All 3,894 seed/strength/compact-full control forecasts match the original AWS
notebook 05 run exactly, with maximum absolute probability difference 0.0.

| Candidate | Mean season Brier | Difference from strength | Exploratory 95% season interval |
|---|---:|---:|---|
| Men: strength + adjusted Four Factors, logistic | 0.188058 | -0.003210 | [-0.006760, 0.001261] |
| Women: strength + dynamic Elo, logistic | 0.143597 | -0.000711 | [-0.004123, 0.002322] |

Both intervals include zero. Feature/model comparisons use previously examined
development seasons, so these are research candidates, not promoted models or
independent evidence of a future medal. The full feature set is not the winner.
The earlier men's system still reports a stronger 0.180669; original forecasts
are required for exact paired reconciliation.

Massey ranks, the Stage 2 sample, player availability and roster minutes were
absent from the available eight-file snapshot. The first two are handled by the
full Kaggle downloader and will enable additional artifacts after the Studio run.
Player information requires a separate historical, timestamped source.

Review rendered notebook 02 for static charts, or the archived run's `report.html`
for interactive charts. Original raw files, model binaries and per-task
checkpoints belong in private project storage, not this public repository.
