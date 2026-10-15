# Public release acceptance contract

This page describes testable behavior, not a self-awarded quality score.

## Sports and result identity

Duke and Michigan are both in the public fixture and featured by dedicated controls. Michigan is identified as the 2026 NCAA men's champion, with an original NCAA report linked beside that claim. The default matchup is Duke–Michigan. Authored ratings and field slots remain separate from factual championship history.

The featured research result is **0.1034347 public/private Kaggle Brier**, submission **57122407**. The normalized record states its provenance and retrospective scope. No release step rewrites older Kaggle receipts or claims a fresh account query.

## Numerical invariants

The eight-team bracket integrates all 128 possible complete outcomes under fixed pairwise probabilities. Every matchup is symmetric on team swap; the title probabilities sum to one. Each selected team's four final-opponent contributions sum to its title probability. Sensitivity perturbs one team's rating at a time and preserves all other inputs. Market prices remain display-only.

## Reproducible handoff

Identical source produces byte-identical HTML and ZIP artifacts. Exported JSON carries full precision, scope and input settings. A bounded, allowlisted scenario link reproduces the same result. Malformed, oversized, unknown-team or out-of-range states fail visibly and cannot introduce external model inputs.

## Usability and failure behavior

Both featured controls, all selectors and sliders work by keyboard. Invalid matchup or numeric input does not leave stale results masquerading as current output. The bracket scrolls inside its own narrow-screen region. Print produces an analyst brief. Motion preferences are respected.

## Publication boundary

Only five reviewed static source files enter the standalone demo package. Adjacent private files are excluded; unexpected files inside the public package fail validation. No runtime network requests, authentication, analytics or private research artifacts are required. New public paths are reviewed by the publication checker and the proposed commit's CI gates before merge.

## Evidence that remains separate

This publication is not a new Kaggle submission or new scientific experiment. It cannot establish prospective model accuracy, profitability, a recruiter's response or completed private-model reconstruction. [Model card](model_card.md) · [Reproduction commands](../README.md#reproduce-the-public-work)
