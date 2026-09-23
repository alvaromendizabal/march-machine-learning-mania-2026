# Employer walkthrough | NCAA forecasting research

## Result

The current retained post-competition release scored **0.1089408 Brier**, compared with the published 2026 winning benchmark of **0.1097454**. The numerical difference is **0.0008046**, approximately **0.73% lower Brier**. It is not an original competition placement or proof of future superiority.

Open the [executed case study](../portfolio/current_research.ipynb). It presents the achieved score progression, the rejected market variants, and the protected-row engineering around each score test.

## What to evaluate

**Research progression.** A first-place-derived compact reference was simplified, then complemented with a richer score-margin model. That produced the 0.1094899 release. Later experiments evaluated ranking systems, feature-family removals, alternative objectives, leaf readouts, a reconstructed fourth-place system, and external information. Most were rejected.

**Mechanism isolation.** A broad market overlay scored worse, and a Round-1-only market overlay scored worse still. Because those components were disjoint, the championship-futures component could be isolated exactly. The frozen futures-only candidate then scored **0.1089408**, matching the arithmetic implication of the prior scored components.

**Engineering discipline.** The latest candidate had 132,133 unique IDs in the original order, changed exactly 1,986 approved men’s rows, and preserved the other 130,147 rows byte-for-byte, including all 65,703 women’s rows. The run performed zero model fits and made exactly one upload.

**Judgment under uncertainty.** The winning component was selected using post-competition feedback, so it is development evidence rather than independent validation. The public portfolio makes that limitation visible instead of presenting the score as a prospective result.

## Ownership and 2027

The public repository demonstrates the problem, score progression, validation philosophy, engineering controls, and decisions. The current private implementation, exact feature construction, fitted artifacts, and future competition recipe remain outside the publication.

For 2027, the goal is to preserve the 2026 champion privately and create timestamped forecasts before outcomes. That prospective process is a stronger test of generalization than additional late-score optimization on a completed tournament.
