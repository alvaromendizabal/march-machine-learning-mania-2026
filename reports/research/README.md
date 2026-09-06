# Research implementation validation

The implementation passes **39 tests**, with **90% line coverage across the four new research modules**. Compilation, lint, formatting and mypy gates pass. The original three reshaping tests remain included.

The synthetic integration test trains 48 fold tasks across both genders, every feature set and both model families; a repeat run reuses all 48 models and all 10 season snapshots. Dedicated tests cover time cutoffs, future-outcome isolation, probability complementarity, missing snapshots, invalid data, corrupted checkpoints, concurrent writers, upload failures, restore checksums, unsafe object paths, ZIP immutability, missing-file diagnostics and notebook structure.

`validation.json` records timings, environment-independent test totals and source hashes. This is implementation evidence. It is not a competition score or evidence of predictive improvement. The official CSVs are still required for the 120-task real-data experiment.

The notebook code cells executed in-process because this host restricts kernel sockets. Its static chart was inspected. CI additionally executes it through a Jupyter kernel. HTML report generation and data contracts are tested; browser visual inspection was blocked by the current browser policy. AWS resource configuration was verified; the first live S3 transfer from Studio remains pending.
