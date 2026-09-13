# Code provenance

`frozen/shot_features.py` and `frozen/research_workflow.py` are byte-identical copies of the user's earlier research-kit reference implementations. `frozen/ranking_features_round12.py` is the byte-identical previous ranking implementation used for definition-parity tests, not a module that launches prior experiments. Their expected hashes are in `constraints.json`.

The new reference builder calls only the existing compact margin and standard shooting/efficiency components. It does not change the original reference formula or call failed residual/profile features. The new label loader explicitly supports the later-era main-draw population and excludes 2026. No project repository source is imported or modified.

Synthetic fixtures in `tests/` change source/data/Git pins only inside isolated temporary copies. They do not alter production constraints in this kit and are not competition-performance evidence.
