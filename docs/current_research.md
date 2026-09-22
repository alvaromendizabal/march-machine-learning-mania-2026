# Current research: scored margin ensemble and women's transfer

Evidence through the women's run on **2026-09-22 at 02:13 UTC**. Open the
[executed case study](../portfolio/current_research.ipynb) for the visual account.

## Achieved scored milestone

Kaggle submission **56447505**, file `march_core75_margin25_candidate.csv`, completed
with both public and private Brier **0.1094899**. Its SHA-256 is
`b3deb57b527450e93682be298bf810275f41d9a7c5056bad6f1b48dd9573bc1c`.
The predecessor scored 0.1098691. The observed improvement is 0.0003792.

The first-place author reports **0.1097454 on 126 games**. The late-submission number
is lower by 0.0002555, but this is not retroactive first place or independent evidence
of prospective superiority. No historical Brier delta is converted into a forecast
of a Kaggle score. The returned Kaggle observation is evidence, not a fresh live API
lookup performed by this publication.

The men's prediction rule is 75% frozen core plus 25% rich margin model, with a fixed
three-seed average. A 66-fit build changed only 2,278 seeded-men matchups in the
132,133-row file. The 129,855 protected lines include every women's prediction.
Only one submission occurred. The scored file is preserved outside this public update.

## Historical mechanism and matched controls

The men's margin model uses the two-feature core plus 31 auxiliary differences.
Binary and signed margin/20 targets share XGBoost squared error, depth-three trees,
regularization, sigmoid calibration and assessment splits. The robustness run used
19, 20 and 21 inner leave-one-season-out folds, three seeds and two targets: 360 fits.
On the same 189 men's main-bracket games, core Brier was 0.1795046214, matched binary
blend 0.1778816298 and margin blend 0.1774648178. Margin improved the core in all
three years and seeds; it beat binary in two of three years. Its historical build-review
decision remains unchanged in evidence.json. The later successful score belongs to
progression.json, rather than being inserted into the historical experiment.

## Women's screening result

Women have a different four-feature core and 28 auxiliary differences, 32 total.
The fixed 25% rich margin blend was the only candidate; the binary-target blend was
a matched control, not an alternative selected after evaluation. No women's Massey
or men-only AP features were invented. The same tree and calibration settings were
used for both targets. Forty-eight fits covered eight outer years and three inner
whole-season folds per target. Training, fitted scaling, early stopping and calibration
excluded each outer assessment year.

| Women: same 504 main-bracket games | Historical Brier |
|---|---:|
| Frozen screening core | 0.1405293026 |
| Matched binary blend | 0.1402266270 |
| Fixed margin blend | 0.1387756863 |

The margin gain is 0.0017536163 against the core and 0.0014509407 over the binary
control; six of eight years improve. Against the retained stronger women reference
on 189 games in 2023–2025, the same screened margin forecasts improve Brier from
0.1292137810 to 0.1282180967 in all three years. This is **not** a fully trained
margin-ensemble result. All eight screening checks passed; the decision is
**FULL_RECIPE_REVIEW**. No 2026 women probabilities or Kaggle score were produced.

## Limitations

Historical years were reused across experiments and hypothesis selection. Outer-year
exclusion prevents direct same-year training, not accumulated validation overfitting.
Inner held-out scores guide early stopping and calibration. Bootstrap support is
conditional on the selected procedure; it is not selection-adjusted proof. Seeds
measure numerical stability, not independent tournament outcomes. The men's late
score motivated the women's hypothesis; no 2026 tournament outcomes enter fitting.

The retained official women's score file is checksum-locked and agrees with frozen
labels. This publication did not independently recover an original official snapshot.
Likewise, returned control-prediction hashes are verified without claiming that every
underlying control model binary was revalidated.

## Provenance and reproducibility

The scored source return has SHA-256
`4034c6f203f3f7b63c4f65ab3d70da6d7fb28170b33995a546135b14202021c6`;
all 36 inventory entries were checked. The women's source return has SHA-256
`dcdafc3cdcc67a886faeeb390177005a28f7c788ab2ae354bff9d7ec494d7403`;
all 20 inventory entries were checked. Historical metrics were independently
recalculated from saved predictions. The score record and exact candidate hash agree.
Source metadata, aggregate year results and checks are retained in
[progression.json](../reports/current_research/progression.json).

GitHub receives the curated notebook, report code, tests, aggregate evidence and
interpretation. AWS retains raw data, current full training source state, caches,
models, per-game artifacts, environments and local modifications. This update is
not an AWS synchronization. Re-executing the public report reproduces aggregates
and figures, not training; hashes do not make omitted private artifacts recoverable.
The earlier 70-submission release and evidence.json are preserved.

## Next boundary

Evaluate the exact women's blend with three seeds and inner leave-one-season-out
training against the retained stronger core and a matched binary-target control.
Passing earns one candidate-build review. A new score test requires a validated
frozen artifact and separate execution authorization; no speculative upload is part
of this publication.

## Attribution

The compact reference is adapted from
[Harrison Horan's first-place writeup](https://github.com/harrisonhoran/kaggle-march-mania-2026-1st-place/blob/main/kagglewriteup.md).
The margin extension is a controlled adaptation, not an exact reproduction of the
winner's full training or calibration. Broader implementation history remains in
[the research index](../research/README.md); all external leading-solution mechanisms
are not claimed to have been recreated merely because this extension worked.
