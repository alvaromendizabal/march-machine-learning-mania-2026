# From a basketball opinion to a testable probability

**A two-minute walkthrough for sports analysts, media collaborators and forecasting teams.**

[Open Duke × Michigan](https://raw.githack.com/alvaromendizabal/march-machine-learning-mania-2026/main/public-demo/index.html) · [Technical evidence](../START_HERE.md)

## 1. Start with Duke and the champions

The demo opens on Duke against Michigan, the 2026 NCAA men's champion, in an authored eight-team field. The two start at equal illustrative ratings; real championship history does not set the model outcome. Inspect the direct matchup probability, then Duke's chance of winning the entire field. Those numbers answer different questions: the second includes several games and every possible opponent along the path.

All ratings and bracket positions are illustrative, not a representation of the current season. The names make the scenario familiar without exposing a private forecast.

## 2. Test the story rather than just telling it

Lower Duke's rating by 100 points. The interface recalculates the complete bracket and shows the percentage-point change from the baseline. Then restore Duke and select **Gonzaga surge**. Duke's route can become harder even though Duke's own rating has not changed.

The calculation integrates every possible bracket path under fixed pairwise probabilities. It does not pick winners first and retroactively assign confidence. Exact calculation does not make the assumptions empirically correct.

## 3. Separate an estimate from a price

The analyst panel accepts hypothetical decimal prices for the selected matchup. It normalizes the two implied probabilities to remove the quoted overround and displays the difference from the illustrative model probability. Changing prices never changes the model's bracket output.

That separation is deliberate. A forecast, a market comparison and a profitable decision are three different claims. This demonstration establishes only the first two calculations under synthetic assumptions—not a betting edge, real odds feed or trading strategy.

## 4. Explain the path, then hand off the scenario

Select **Explore Michigan** or **Explore Duke**. The sensitivity rows show how a local rating change moves both teams' title probabilities. The path panel decomposes the selected team's title chance into its four possible final opponents; those contributions sum to the displayed title chance. No path is chosen in advance.

Create a scenario URL to reproduce the same controls on another browser, or print the analyst brief. The link contains only bounded public scenario parameters in its fragment. It carries no private weights, external data, account state or forecast tables.

### Export something another analyst can inspect

The JSON export contains the exact inputs, selected matchup, bracket probabilities, model assumptions and separately labeled price context. A colleague can reproduce the calculation with the public engine. Synthetic scoring examples stay separate from prediction requests; changing their outcome labels does not change the forecasts.

## What the larger project demonstrates

I built source qualification, team-season representation, probabilistic modeling, chronological evaluation and recoverable execution into a research workflow. The published source foundation covers **14,311 team-season profiles** and the research forecast population contains **132,133 within-division matchups**. [Evidence map](evidence_map.md)

**0.1034347 public/private Kaggle Brier, submission 57122407**, is the featured scored research result. It is retrospective, not an official competition win or a prospective forecast. [Result record and scope](champion_result.md)

The private research models are richer than this intentionally small public engine. Their fitted weights, source tables and final forecast rows are not shipped in the browser. The public value is an inspectable example of how I reason about probability, source timing, evaluation and delivery—not a disclosure of the competitive implementation.

## A substantive collaboration conversation

The useful questions are concrete: Which decisions require a probability? What information was available at prediction time? Which failure costs matter? Does a proposed signal improve a frozen baseline on matched future-season games? What needs to be reproduced before a result is trusted?

[Author's GitHub portfolio](https://github.com/alvaromendizabal) · [Engineering case study](employer_walkthrough.md) · [Public/private boundary](../portfolio/DISCLOSURE.md)
