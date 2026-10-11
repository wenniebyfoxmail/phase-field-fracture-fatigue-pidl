# Next repair: qualify a task-relevant progression index

Status: proposed, not executed or qualified.

E006 repaired the observed commented-header grammar. Its frozen gate still
failed because `time` decreased at a diagnostic stage pair where cycles and
acquisition-relative date increased. Timer-reset semantics remain unknown.

The next bounded question is whether the complete sequence can support a
cycle-indexed observation-only crack-length task. For that task, a finite,
consistent cycle counter and acquisition ordering are necessary; monotonicity
of every available sensor clock is not automatically necessary. This rationale
must be reviewed before adopting a new admission rule after E006's result.

Smallest test: all 342 bounded headers, retain original stage-ID order, check
exact cycle and acquisition-date consistency, required field/schema coverage,
and report `time` decreases as separate diagnostics. No silent reordering,
session joining, imputation or removal of stages. If cycle/date ordering also
fails, locate the first pair and stop admission. Any segmentation/session repair
would need explicit evidence, not an assumed timer-reset explanation.

Preserve component coverage independently: parsed-header count, complete-field
count, filename/header-match count, schema-valid count and chronology-check
count. Upstream components can pass completely even if a later component fails.
Keep partial versus whole-sequence results explicit.

If admitted, design a separate chronological prediction evaluation with
origin-time-only inputs, crack-length target and persistence/secant comparator.
Repeated stages belong to one specimen; do not claim independent-specimen or
road generalisation. DCPD crack length and DIC observations are not phase-field
labels. No model training or phase-field/material fit is part of admission.
