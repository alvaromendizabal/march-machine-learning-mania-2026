# From a basketball opinion to a testable probability

**A two-minute walkthrough for sports analysts, media collaborators and forecasting teams.**

[Open the Duke workbench](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html) · [Technical evidence](../START_HERE.md)

## 1. Start with Duke—not a guaranteed winner

The demo opens on Duke against UConn in an authored eight-team field. Inspect the direct matchup probability, then Duke's chance of winning the entire field. Those numbers answer different questions: the second includes several games and every possible opponent along the path.

All ratings and bracket positions are illustrative, not a representation of the current season. The names make the scenario familiar without exposing a private forecast.

## 2. Test the story rather than just telling it

Lower Duke's rating by 100 points. The interface recalculates the complete bracket and shows the percentage-point change from the baseline. Then restore Duke and select **Gonzaga surge**. Duke's route can become harder even though Duke's own rating has not changed.

The calculation integrates every possible bracket path under fixed pairwise probabilities. It does not pick winners first and retroactively assign confidence. Exact calculation does not make the assumptions empirically correct.

## 3. Separate an estimate from a price

The analyst panel accepts hypothetical decimal prices for the selected matchup. It normalizes the two implied probabilities to remove the quoted overround and displays the difference from the illustrative model probability. Changing prices never changes the model's bracket output.

That separation is deliberate. A forecast, a market comparison and a profitable decision are three different claims. This demonstration establishes only the first two calculations under synthetic assumptions—not a betting edge, real odds feed or trading strategy.

## 4. Export something another analyst can inspect

The JSON export contains the exact inputs, selected matchup, bracket probabilities, model assumptions and separately labeled price context. A colleague can reproduce the calculation with the public engine. Synthetic scoring examples stay separate from prediction requests; changing their outcome labels does not change the forecasts.

## What the larger project demonstrates

I built source qualification, team-season representation, probabilistic modeling, chronological evaluation and recoverable execution into a research workflow. The published source foundation covers **14,311 team-season profiles** and the research forecast population contains **132,133 within-division matchups**. [Evidence map](evidence_map.md)

The inspected owner research records report **0.1034347 retrospective Brier**; the earlier **0.1067095** result has a directly published Kaggle receipt. These are different evidence classes, not two newly verified live scores. Both belong to post-outcome research, not official competition wins. [Results and limitations](current_research.md)

The private research models are richer than this intentionally small public engine. Their fitted weights, source tables and final forecast rows are not shipped in the browser. The public value is an inspectable example of how I reason about probability, source timing, evaluation and delivery—not a disclosure of the competitive implementation.

## A substantive collaboration conversation

The useful questions are concrete: Which decisions require a probability? What information was available at prediction time? Which failure costs matter? Does a proposed signal improve a frozen baseline on matched future-season games? What needs to be reproduced before a result is trusted?

[Author's GitHub portfolio](https://github.com/alvaromendizabal) · [Engineering case study](employer_walkthrough.md) · [Public/private boundary](../portfolio/DISCLOSURE.md)
