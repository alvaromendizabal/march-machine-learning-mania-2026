# Project working conventions

- Execute changed notebooks and publish their outputs. The owner reviews notebooks;
  routine notebook execution is the maintainer's responsibility.
- Keep a notebook-led Python repository: visible analysis and interpretation in
  canonical notebooks, reusable tested functions in `src/march_mania`.
- Edit canonical filenames in place. Do not add repair, fixed, patched, backup,
  or numbered replacement copies. Git history preserves earlier implementations.
- Use the locked Python environment. Run `scripts/quality.py` and execute the
  current review notebooks before publishing a change.
- Test temporal boundaries, physical-game uniqueness, probability validity,
  team-swap symmetry, failures, checkpoint integrity, and resume behavior.
- Use UTC timestamps, total and task elapsed time, progress, and heartbeats.
  Do not hide meaningful warnings or turn failed tasks into successful records.
- Preserve experiment inputs, source/configuration hashes, predictions, fitted
  models and checkpoints durably. Keep generated model/data binaries outside Git.
- Report official game-weighted Brier and mean season Brier distinctly, alongside
  calibration, log loss, ranking metrics and useful error diagnostics.
- Use documented feature branches and pull requests, and verify checks on the
  exact proposed commit before merging. Report what was actually executed.
- Keep prior evidence labeled by its feature schema. The 2022–2025 benchmark has
  already been consumed. Never describe it as a new untouched holdout.
- Current model families: logistic, histogram boosting, XGBoost and LightGBM.
  Historical PyTorch/TensorFlow and margin results are not current-schema reruns.
- Current review notebooks: 00 through 05. Notebook 04 evaluates the current feature
  and model lineage on the consumed benchmark. Submission generation is an explicit,
  default-off option; routine training and review must not create a Kaggle CSV.
- Final prediction code is `publication/inference.py`; `configs/inference.json` freezes
  pre-2022 development selection. Never tune it on the consumed benchmark or 2026 results.
  Keep historical model lineages distinct. Generation is not an accepted Kaggle upload.
- Notebook publication uses content-verified whole-notebook checkpoints. Never
  resume individual cells without restoring kernel state. Never publish errors
  or unresolved warning outputs. The submission release command audits existing
  prediction bytes; it does not fabricate probabilities or send a Kaggle submission.
