# Milestone 08 — completed result and next decision

Source: the user's `milestone_08_return.zip`, SHA-256 **0d26571d26db56b0ca72bee8170b39f84f822478c5f66eec58fabe0d8646da5d**. Its return_integrity.json hashes were checked against all listed members. These are real returned experiment results, not synthetic validation scores.

## Outcome

The declared primary comparison was `mechanism_given_rates`: anchor plus direct-rate controls plus four nonlinear possession candidates, minus anchor plus direct-rate controls.

| Population | Mean primary Brier change | Improved seasons | Worst deterioration | Saved decision |
|---|---:|---:|---:|---|
| Men | +0.0004202204733369727 | 1 / 4 | +0.0019930640782214737 | DO_NOT_EXPAND_AUTOMATICALLY |
| Women | +0.0005932187159539762 | 0 / 4 | +0.0010245982793215258 | DO_NOT_EXPAND_AUTOMATICALLY |

Negative changes favor inclusion. Do not promote the nonlinear family under this tested compact logistic recipe. This is not proof that every possession-based representation fails.

The men's **ordinary-rate control** improved its mean versus the 16-input reference by −0.001239893615748229, with improvement in 3/4 seasons. However, its 2017 deterioration was +0.0062071104995331805. That is a separate, unstable observation, not evidence the nonlinear candidates succeeded. The women's direct-rate addition worsened its mean by +0.0044459670321423603.

## Execution and preservation

The resumed run reports **21 new classifiers, four local checkpoint reuses, seven upstream reference replays, 32 total comparisons and zero rating fits**. Including the four classifiers already completed before the compatibility correction, the experiment comprises 25 newly fitted classifiers plus seven reused references. The report records repository, raw-data, upstream-cache and AWS-resource changes as false. It records no new leaderboard score or GitHub update.

Last reported submitted Brier: **0.1222672**. Research target: **0.1097454**. Neither number was measured anew by milestone 08.

## Decision

Leave the failed nonlinear possession family's expansion stopped. Test a different mechanism: women's announced-bracket hosting eligibility. This is not another transformation of box-score shooting efficiency. An ordinary top-four-seed indicator is retained as a separate control, so a gain is not mistaken for merely adding nonlinear seed status.

The new experiment is a narrow **eligibility-proxy** test, not a confirmed-venue dataset or proof of home advantage. Verified archived venue/hosting exceptions, travel, later-era validation and production-recipe transfer remain separate work. There is no basis to guarantee a leaderboard record.
