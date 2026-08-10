# LTPP main-grid tooling MVP — pre-result implementation abort, 2026-08-10

## Status

`ABORTED_PRE_RESULT__IMPLEMENTATION_DEFECT`

The approved frozen real-data command was started after the synthetic suite passed, but it stopped while evaluating an unqualified degenerate separator component on the first page. The unguarded ranking diagnostic evaluated `log(aspect / 3.048)` for a non-positive aspect and raised `ValueError: math domain error`.

## What was and was not produced

- No per-date candidate was selected.
- No purple review panel, metrics CSV, result JSON, overlay, crop, control, transform, residual, or registration decision was written.
- The created output directory is retained as the abort location and must not be reused.
- This event does not create a failure date or alter v1/v2 status.

## Mechanical repair

Only the diagnostic ranking value for an already-ineligible `aspect <= 0` component is repaired: it receives the fixed sentinel `10**18`, so it remains ineligible and cannot be selected. No threshold, source input, geometry rule, candidate definition, ranking order for eligible candidates, dependency, or claim boundary changes.

A new unit test constructs the degenerate component and requires fail-closed behavior. The complete synthetic suite is rerun under the repaired source before a newly named real-data run. This is a pre-result implementation repair, not a rerun after observed candidate performance.
