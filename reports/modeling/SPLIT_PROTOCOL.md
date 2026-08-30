# Frozen Modeling and Validation Protocol

## Forecast boundary

- Target season: 2026
- Feature cutoff: DayNum 132
- Same-season NCAA tournament outcomes are forbidden as predictors.
- Any target/future outcomes found in source files are quarantined.

## Architectures

- Primary: separate men's and women's pipelines
- Mandatory challenger: pooled common-feature model
- Eligible final challenger: partial-pooling prediction blend

## Validation

- Primary: nested expanding-window validation by complete tournament season
- Secondary: LOSO only for public-solution comparability
- Development ends: 2021

## Locked local benchmark

- Seasons: [2022, 2023, 2024, 2025]
- Primary mode: prequential refit with the recipe frozen after 2021
- Sensitivity mode: static target model fit through 2021
- Because the competition is complete and public solution knowledge is available, this is not described as a perfectly blind external test.

## Final 2026 replay

After the full recipe is frozen and the locked-benchmark report is issued, refit the selected system using all eligible labeled tournaments through 2025 and score Stage 2 rows through gender-specific routing.
