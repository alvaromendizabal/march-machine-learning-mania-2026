# Existing AWS execution paths

Keep the current `march-mania-dev` space and its original scientific checkout.
The consolidator uses a separate local clone of THIS SAME repository for safe
publication; it does not create another GitHub repository or reset the experiment
checkout. Source snapshot equality is recorded in the migration manifest. The
original experiment checkout remains pinned because existing checkpoints validate
its source, environment and data identity.

Run the existing next pair from `$HOME/march_next_steps/rounds_20_21` with
`$HOME/march-machine-learning-mania-2026/.venv/bin/python`.
Use `run_tests.py`, then notebook 20, then notebook 21; keep all `private_runs`.
They retain the documented cutoff, fixed features and reused validation years.

A fresh clone contains archived implementation, not raw data or fitted caches.
It is not a claim that all notebooks can run without restoring their documented
inputs. Do not execute two-repository publication scripts from archived folders.
