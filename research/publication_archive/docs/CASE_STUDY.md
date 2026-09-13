# Case study: representation quality under temporal validation

## Objective
Estimate the probability that the lower-ID team wins an NCAA tournament matchup. The research objective is the Brier score, with log loss, calibration, subgroup errors and stability used as diagnostics.

## Design
Season-local inputs obey pre-tournament cutoffs. Each historical tournament is predicted using earlier tournament labels. Men's and women's populations are assessed separately when appropriate. Rating estimators use pre-cutoff regular-season observations, not the tournament outcomes they help forecast.

## Investigation strategy
The experiments study team strength, shooting, record quality, temporal change, possession mechanics, bracket context, ranking consensus and opponent adjustment. Family additions and removals keep other inputs fixed. Duplicate-input controls flag sensitivity to regularization rather than proving new information.

## Engineering decisions
Runs are divided into schema audits, small smoke tests, verified resumption, bounded preparation, evaluation and report export. Native model representations and checksum manifests support reuse. Later-stage exceptions do not erase accepted earlier work. Data inconsistencies are recorded rather than silently recoded as plausible values.

A recent example separated a data-quality stop from a packaging failure: the turnover experiment stopped because some credited steals exceeded the opposing turnover count; the independent blocks/free-throw experiment completed. The combined ZIP failed because it required both experiments. A revised collector accepts partial evidence without calling missing work complete.

## Measured conclusion
Ranking consensus gave a small later-era improvement for the compact reference. The more complicated representations frequently did not generalize consistently. This is an important negative result: computational activity and feature count are not substitutes for evidence.

## Limitations and next gate
The validation seasons and competition results have already informed earlier development. The posted late-submission best is retrospectively selected, not an untouched prospective assessment. A compact-reference improvement must be transferred into the stronger production recipe before it supports a production claim. Data coverage, availability and licensing constrain external/player-level features.

## Contribution and disclosure
Project research and engineering are presented by Alvaro Mendizabal. AI-assisted code preparation is followed by user-controlled execution and inspection. Tests are claimed passed only when an execution artifact supports that statement. This public case study is not the private training implementation.
