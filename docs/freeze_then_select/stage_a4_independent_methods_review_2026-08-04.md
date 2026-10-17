# Stage A4 independent methods review

Date: 2026-08-04

Reviewer role: read-only independent methods critic.

## Verdict

Conditionally approve a multi-environment synthetic excitation diagnostic, not
a road, PIDL, or causal validation claim.

## Required corrections adopted before execution

- Replace the initial five-environment proposal with eight balanced environments
  so traffic, cold, moisture, and their interactions are not aliased.
- Require raw forcing correlation at most 0.35 before generating damage.
- Use nested environment separation: six selection sections, one internal
  validation section, and one untouched whole-section test per fold.
- Weight environments equally and standardize candidates only inside selection.
- Add oracle frozen, row-matched one-environment, cloned-environment, all-term
  ridge, and true-support-fit controls.
- Audit candidate correlation, effective rank, condition number, and environment
  leverage before interpreting support.
- Require support and forecast gains over row-matched controls; otherwise classify
  any improvement as sample-size or regularization gain rather than excitation
  diversity.

## Hard failure conditions

- Oracle shared-support selection cannot recover the declared support.
- Balanced candidate correlation remains above 0.95 or condition number exceeds
  1e7.
- Any held-out section contributes weak rows, coefficients, thresholds, or model
  choices.
- Multi-environment selection does not beat equal-row one-environment and cloned
  controls.
- Forecast gains exist only after pooling sections.
- All-term ridge matches forecast performance while selected support is unstable.

## Evidence boundary

Passing this diagnostic would show only that designed synthetic excitation can
improve identifiability of the declared candidate library after sparse field
reconstruction. Producer/PIDL and road/FEM evidence remain mandatory for the
active research goal.
