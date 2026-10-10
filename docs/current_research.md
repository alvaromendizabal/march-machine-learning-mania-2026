# Current research boundary

Updated October 10, 2026 UTC. This page supersedes older research snapshots when they describe the current submission state.

## Confirmed result and metric contract

The latest confirmed Kaggle submission, **the v54 forecast delivered through v93r1**, received **0.1067095** in both displayed score fields. It contains **132,133 prediction rows**. The corresponding local 126-game audit is **0.1067095543**; the scored population is 63 men's and 63 women's games.

The official winning score was **0.1097454**. The late submission is **0.0030359 lower (2.77% less Brier loss)**. The competition's March 19 deadline and this project's October 8 submission are different evaluation conditions. This is a retrospective result, not an official rank or prospective victory. See [the complete comparison](benchmark_comparison.md).

| Evidence | Brier | Interpretation |
|---|---:|---|
| Latest accepted late submission, v54 / v93r1 | **0.1067095** | Kaggle-confirmed result |
| Corresponding 126-game audit | **0.1067095543** | Local retrospective audit |
| Women's retained branch, 63 games | **0.0767383172** | Numerical reproduction evidence |
| Earlier owned-data control, v26 | **0.1206458** | Historical submitted control |

The submitted composition adapts the men's probability system and retains the women's reference baseline. Public-method credit, including Harrison Horan's contribution, is preserved. A completed upload establishes submission acceptance; it does not retroactively satisfy every historical promotion gate.

## Separate the evidence types

The project keeps historical development, later-season confirmation, retrospective 2026 scoring, numerical reproduction, and external submission acceptance distinct. The historical benchmark and 2026 outcomes have been inspected repeatedly. Neither is described as a fresh untouched holdout.

The complete men's historical evaluation covers **566 played main-bracket games across nine forecast seasons**, including **189 games in 2023–2025**. Repairing an equal-seed filter restored eight legitimate later-round games after reproducing all 558 saved control predictions.

New model work must beat fixed historical controls across the declared development and confirmation populations, improve each recent confirmation season, and beat the matched static or simpler counterpart where the experiment requires one. A favorable target-year score alone does not qualify a new recipe.

## Verified model and source foundation

- The women's parity check matched **65,703 pairwise probabilities within 1e-4** and all 15 archived member-fit counts and best-iteration receipts.
- Men's matched-input procedure checks reproduced **66 core members** and **66 margin members**, with 31 auxiliary feature columns reconciled.
- The official raw-game foundation contains **13,753 men's team-season rows across 42 seasons** and **9,851 women's rows across 29 seasons**.
- Both teams are present for all **566 historical men's matchup identities**. Performance and schedule features cover all 566; temporal and venue features cover 554, with missingness preserved.
- Men's and women's raw-to-feature outputs were independently replayed; 2026 feature generation was rehearsed as an incoming-season update.

These foundations establish what was built, reconciled and independently replayed. They do not establish complete source parity, a new model gain, or full prospective readiness.

## Latest inspected execution return: v128 source repair

The latest inspected execution return is **v128-owned-source-repair-20261010**, completed **October 10, 2026 at 01:32:58 UTC**, with status **SOURCE_PARTIAL**. All **75 manifested members** were checked against their recorded hashes and sizes.

- **2,258 market-quote rows repaired**; the remaining **1,075 missing rows** stay explicitly missing.
- **Model admission: ineligible.** Exact injury inputs remain missing and the historical gate remains false.
- **Zero model fits, inferences, candidates and submissions.** No new score or model improvement is claimed.
- **Latest confirmed score remains 0.1067095.** Source repair does not promote the existing research composition.

The older v99 package is a dated source-pilot snapshot, not the current execution state. Its historical files and the October 8 release evidence remain unchanged for provenance. The [sanitized execution receipt](../portfolio/latest_execution.json) preserves this return's status, counts and provenance without raw archives, private configuration or cloud paths. Check it with `python tools/summarize_execution.py --check` from the repository root. This is the latest inspected return, not a claim to have inventoried every file on the live AWS workspace.

The normalized player bank includes third-party-derived NCAA records with their own provider identities. These records are not an original ESPN archive. Source ownership, original-response receipts, publication timing and model admission remain separate checks.

## What remains

| Gap | Completion evidence needed |
|---|---|
| Original player histories, availability and injury inputs | Exact required inputs, broad qualified coverage, reliable identities and defensible timing |
| BPI and market histories | Original dated records with sufficient multi-season coverage |
| New complementary signal | Complete historical comparison and matched ablations |
| Legacy source timing | Original-version evidence; numerical parity alone is insufficient |
| Prospective 2027 readiness | Actual incoming inputs and a fresh end-to-end run before outcomes |

The next modeling step follows source qualification and uses a genuinely new representation. Closed recipes are not restarted unchanged. [The reproduction matrix](reproduction_matrix.md) separates completed mechanisms from remaining source gaps; [the readiness contract](2027_readiness.md) defines the future-season claim.
