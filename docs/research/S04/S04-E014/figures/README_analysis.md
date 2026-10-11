# S04-E014 figure reading guide

## Question and evidence

Does unbiased damage-stratified sampling recover the frozen supervised
displacement gate at c20 and c83? The figure reads the two exact R002 monitoring
traces and the final metrics admitted by the fail-closed aggregator.

## Reading order

1. Left: fixed full-field displacement RMS at steps 0, 1000, ..., 10000.
   These points diagnose convergence; only step 10000 votes.
2. Right: final result against the exact S04-E013 seed-7 comparator. The dashed
   line is the absolute `1e-3` gate.

## Interpretation

Both final errors improve by about one third, so damage-aware sampling is a
useful ingredient. Both remain more than three times the absolute gate and fail
the preregistered 50% improvement trigger. The nonmonotonic traces, including a
c83 background-error excursion, show that sampling frequency alone does not
resolve the localized-versus-smooth representation conflict.

Allowed conclusion: reject sampling-only repair and move to one bounded
local/multiscale representation screen that retains the unbiased full-field
objective.

Blocked conclusions: architecture non-representability, four-state/cross-seed
validity, Stage 2 authorization, FEM reproduction, or FEM-teacher qualification.
