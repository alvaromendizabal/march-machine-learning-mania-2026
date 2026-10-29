# Portfolio review: freshness, scientific decisions and storage evidence

## Audited baseline

**Repository:** `alvaromendizabal/march-machine-learning-mania-2026`, an independent project. **Baseline main:** `f26469a4f93e0aeb91b795c0e569c512636af284`. Review date: October 29, 2026. No open pull requests or active repository path-sharing constraints were observed at the start of this change. The branch was unprotected and the ruleset inventory was empty. No Sports Edge Lab repository or AWS workload is modified by this public update.

All five check runs on that exact main commit were successful: research quality, notebook publication, current-research verification, browser demo and source/navigation hygiene. This update does not claim to repair a failing baseline CI system. It adds substantive evidence checks to a working pipeline.

The baseline one-command public review also passed all ten of its local checks. The repository already contains an interactive scenario lab, six canonical research notebooks, additional portfolio notebooks, an executed public reproduction, model cards, source histories, a qualification explorer and extensive tests. These are preserved.

## Scoring method and limits

These are editorial assessments, not measured tests. Each dimension uses the same 0–10 anchors: 0 means absent; 5 means present with significant gaps; 8 means strong, inspectable evidence with material limits; 9 means comprehensive and currently verified; 9.9 requires exceptional execution with only negligible remaining gaps. All twelve dimensions have equal weight. The 9.9 target is a goal, not an earned result.

The AFTER column is deliberately **NOT VERIFIED** in this baseline artifact. An after score requires the proposed head to pass its checks, a permitted merge, and verification of the resulting main commit. Local readiness does not supply those facts. The pull request and final release report carry those exact-head receipts.

| Dimension | Before /10 | Verified after /10 | Target | Baseline evidence and remaining gap |
| - | -: | - | -: | - |
| Technical architecture and engineering depth | 8.5 | NOT VERIFIED | 9.9 | [Modular pipeline, checkpoint recovery and independent review commands](architecture.md). One authoritative active workspace and measured warm-path optimization remain runtime work. |
| Scientific rigor, leakage prevention and evaluation | 8.8 | NOT VERIFIED | 9.9 | [Chronological contracts, paired cohorts and explicit consumed benchmark](research_protocol.md). No prospective 2027 evidence; public paired uncertainty is constrained by private errors. |
| ML breadth and feature engineering | 8.4 | NOT VERIFIED | 9.9 | [Four current model families, ablations and historical lineage distinctions](model_card.md). Further feature admissions require qualified sources and predeclared comparisons. |
| Data provenance and reliability | 7.9 | NOT VERIFIED | 9.9 | [Source ledgers, digest-bound history and explicit qualification frontier](execution_evidence.md). Latest owner state was absent from the public landing pages; broader coverage remains incomplete. |
| Reproducibility and documentation | 8.5 | NOT VERIFIED | 9.9 | [One-command public demo, locked environment and executed notebooks](public_reproduction.md). Public examples and private competitive replay have intentionally different scopes. |
| Testing, CI/CD and merge safety | 8.8 | NOT VERIFIED | 9.9 | [Five checks passed on the audited main; pinned Actions and exact-head publication guard](../.github/workflows/ci.yml). Main is unprotected; required review/check enforcement depends on owner repository settings. |
| Security, privacy, licenses and protected IP | 8.6 | NOT VERIFIED | 9.9 | [Changed-blob publication scan, aggregate schemas and explicit disclosure](../portfolio/DISCLOSURE.md). Pattern scans cannot prove every license entitlement or recognize every private value. |
| Interactive UX and accessibility | 8.5 | NOT VERIFIED | 9.9 | [Keyboard-oriented static lab, scenario controls and qualification explorer](public_demo.md). No independent assistive-technology audit; latest run was not surfaced in existing review. |
| Visual design and professional polish | 8.6 | NOT VERIFIED | 9.9 | [Coherent responsive workbench and persisted notebook figures](studio.md). Freshness and scope needed clearer hierarchy across owner observations. |
| Five-minute employer review experience | 8.2 | NOT VERIFIED | 9.9 | [Clear author, result, review paths and runnable report](../START_HERE.md). Top-level latest-status narrative lagged the actual owner run. |
| Four-project consistency and maintainability | 8.3 | NOT VERIFIED | 9.9 | [Independent repository conventions, canonical filenames and shared public contracts](REPOSITORY_POLICY.md). Score applies to maintainability of this independent repo; no cross-repository audit was performed. |
| Hiring relevance for ML Engineer, AI Engineer and Data Scientist | 8.7 | NOT VERIFIED | 9.9 | [Inspectable modeling, data systems, negative results and reliability work](employer_walkthrough.md). Fresh run accounting and explicit quantitative systems diagnosis needed a public review path. |
| **Equal-weight overall mean** | **8.483** | **NOT VERIFIED** | **9.9** | Independent-repository assessment; no fabricated four-project comparison. |

### Role-specific baseline ratings

| Role | Before /10 | Verified after | Why |
| - | -: | - | - |
| Machine Learning Engineer | 8.7 | NOT VERIFIED | Substantial feature/model/evaluation code, chronological tests, recoverable execution; private reproduction and source qualification remain scoped. |
| AI Engineer | 8.4 | NOT VERIFIED | Modular orchestration, tooling, APIs, recovery and CI are concrete; no unimplemented LLM or autonomous-agent capability is claimed. |
| Data Scientist | 8.8 | NOT VERIFIED | Matched comparisons, timing boundaries, calibration and honest retrospective labels; prospective validation remains future work. |

## Ten highest-impact remaining weaknesses

1. **Public freshness:** the main landing page called the October 26 acquisition record latest while October 29 replay evidence existed. Addressed by the new latest-run panel and dated historical labels.
2. **Study versus project readiness:** a successful scoped replay could be mistaken for complete broader data. Addressed by explicit study inputs, residual units and incomplete market admissions.
3. **Selection after exposure:** later-window improvements invite accidental promotion. Addressed by a tested development-based retained-control decision with the consumed-window label.
4. **Return storage overhead:** canonical derived parts slipped past a filter that excluded their export aliases. The public case study quantifies the defect; runtime repair and owner validation remain separate private work.
5. **Unproven performance ceiling:** configured worker counts did not establish optimal throughput. The new review reports CPU, workstream and packaging observations without promising maximum speed.
6. **Fragmented active runtime state:** versioned work roots can accumulate repeated outputs. The public report identifies one authoritative catalog and verified consolidation as acceptance criteria; it does not claim cleanup has run.
7. **Incomplete market-source qualification:** millions of selections are not model-ready games. No new training admission or paid acquisition is inferred from inventory size.
8. **Private-versus-public reproducibility:** competitive inputs and exact composition rules cannot be distributed. The allowlisted record, validator and executed notebook provide useful aggregate review without claiming private-pipeline parity.
9. **No enforced branch protection:** the owner repository had no active ruleset. The workflow still verifies exact heads; repository enforcement is an owner settings decision outside this scoped content update.
10. **No prospective season result or independent accessibility certification:** neither a polished demo nor a retrospective score establishes those outcomes. They remain explicit follow-up work.

## Focused implementation and acceptance criteria

The change has one integration owner in this independent repository. It edits existing README/review/demo surfaces in place and adds one stable aggregate record, one validator, meaningful failure tests and a scoped case study. It does not replace the existing research framework or create fictitious multi-project tracks.

| Improvement | Owned paths | Acceptance evidence |
| - | - | - |
| Latest public owner record | `portfolio/owner_replay.json`, `tools/owner_replay.py` | Strict nested allowlist; matched physical-game arithmetic; consumed-window and promotion guards; explicit data and storage units |
| Scientific/disclosure regression coverage | `tools/test_owner_replay.py`, `scripts/quality.py` | Reject overlap, count confusion, nonfinite metrics, unqualified promotion, oversize/duplicate parts, private fields, incomplete-inventory purchases |
| Existing review experience | `tools/review_project.py`, `tools/review_template.html`, `portfolio/engineering_review.ipynb` | Eleven-check public review; real clean-kernel execution with persisted table and existing figures; mobile/desktop rendering |
| Clear latest-versus-history boundary | `README.md`, `START_HERE.md`, `docs/current_research.md`, `public-demo/index.html`, portfolio/docs review pages | Current V347 result appears first; October 26 source ledger retains its exact denominator and date |
| Evidence-rich engineering case study | `docs/owner_replay.md` | Scope-qualified negative result, observed system bottleneck, exact storage accounting and remaining gaps |

## Public reproduction and protected material

Run `python tools/review_project.py` from a checkout with Python 3.12 and Node. The public review performs no paid requests or cloud access. Optional notebook generation uses the locked environment. The actual competitive research run depends on authorized private inputs and is not a public credential-free reproduction.

The new public record was generated through an explicit allowlist rather than copying private summaries. It contains no cloud bucket or object paths, credentials, raw source rows, per-game forecasts, weights, tuned blend parameters or private feature recipes. The changed-blob publication check and nested-schema tests provide concrete checks; neither substitutes for all possible licensing review. No newly redistributed third-party dataset is part of this change.

## What would justify the remaining increase

After merge, verify exact-head and final-main checks before assigning an AFTER score. Remaining advances should earn credit through measurable work: source closure and justified admissions; restoration-tested consolidation; controlled warm-path/concurrency benchmarks; a genuinely prospective 2027 run; and an independent accessibility review. Generic presentation polish cannot erase those scientific or operational gaps.

[Latest owner result](owner_replay.md) · [Review contract](engineering_review.md) · [Evidence map](evidence_map.md)
