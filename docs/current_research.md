# Current evidence and evaluation boundaries

## Achieved score

The current release is Kaggle submission **56447505**, recorded COMPLETE with both
public and private Brier **0.1094899**. Its filename and SHA-256 are retained in
[progression.json](../reports/current_research/progression.json). The preceding
release scored 0.1098691. The published first-place author's benchmark is 0.1097454;
the new late score is numerically lower by 0.0002555.

No prospective rank, medal, prize, or statistical superiority claim follows from
that comparison. The winner's result was an original competition submission; this
project's improvement was evaluated after the competition and subsequent research.

## Latest women's robustness

The latest run assessed the same **189 main-bracket games across 2023–2025**:

| System | Brier |
|---|---:|
| Frozen reference | 0.1292137810 |
| Matched win/loss-target ensemble | 0.1289932952 |
| Margin-target ensemble | 0.1283061209 |

The margin ensemble gains **0.0009076601** over the reference and **0.0006871744** over
the matched target control. It improves the reference in all three years and across
all three predeclared random repeats. It beats the binary control in two of three
years, not all three. The all-tournament gain, including play-ins, is 0.0010450845;
that is a different population from the main-bracket comparison.

All seven predeclared robustness gates passed. The run completed 234 model fits,
78 regression tests and its executed notebook in 53.43 seconds overall. No additional
Kaggle submission occurred. The next decision is a frozen candidate build and one
controlled score test—not an automatic weight or feature search.

## What the evaluation controls

Each outer assessment year was excluded from fitting, early stopping and calibration.
Earlier whole seasons supply inner omissions; learned transformations are fit inside
training partitions. Margin and binary targets have matched representations and
training settings. Fixed ensemble choices and averaging every predeclared repeat
prevent selecting a favorable weight or seed after inspection.

These controls do not remove accumulated selection on reused years. The same seasons
informed earlier research, including the screen that selected this proposal. Inner
held-out scores guide both early stopping and calibration. Conditional bootstrap
results concern the retained forecasts, not selection-adjusted certainty about 2027.
The positive matched-target average also does not establish a statistically certain
objective advantage from only three years.

## Provenance and publication scope

The latest source is `march_women_margin_robustness_return_20260922T025311309011Z-567.zip`.
The publication records its checksum and the source notebook's identity in
[milestone.json](../reports/current_research/milestone.json). All 23 inventory entries
were verified and aggregate Brier independently recomputed from saved predictions.
The source notebook has 11 completed code cells and seven Plotly/image-output pairs.
This public case study is a distinct, curated aggregate report.

No new full training code, model binaries, exact feature formulas, calibration
implementation or parameter recipe is added by this publication. Existing public
source and historical licenses remain unchanged. A readable methodology explanation
is evidence of professional judgment, not a grant of confidentiality over public history.
The private AWS training state is not synchronized by the publication workflow.

The compact reference is credited to
[Harrison Horan's first-place writeup](https://github.com/harrisonhoran/kaggle-march-mania-2026-1st-place/blob/main/kagglewriteup.md).
Original aggregate evidence and prior releases remain intact for honest chronology.
