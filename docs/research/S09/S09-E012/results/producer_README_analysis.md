# S09-E012 analysis

This is a read-only diagnostic on three frozen exposed-development states.  It
performed no optimiser step, FEM solve, or fresh-holdout access.

Selected exploratory action: `LOCALISATION_AWARE_OBJECTIVE_PROBE`.

The selection follows a frozen minimum-change priority.  It is not an exclusive
causal verdict; all per-state mechanism labels and all matched action candidates
remain in `completion_receipt.json`.

The local observable uses the frozen target-derived mask
`true damage increment > 1e-15`.  It is a diagnostic oracle mask and cannot be
used as an inference or deployment input.  The finite-displacement linearised
responses and exact endpoint observable changes are separate columns in
`observed_endpoint_changes.csv`.

The original 8 wrong and 17 correct pairs are retained.  Control repair and
protection loss are reported together; no subset was selected after inspection.
