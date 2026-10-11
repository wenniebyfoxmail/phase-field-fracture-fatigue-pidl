# S03-E006-R002 bounded chronology diagnostic

Frozen before inspection: reuse unchanged reviewed `_read_header` at commit
524919b877b85b243b3a18e81af6f50114d193c9, same locked archive. Read no more
than the first six numeric-ID stages, each within the existing 131,072-byte
parser cap. Stop at the first decreasing chronology scalar or any parser error.
No body rows or connection opens. Report the adjacent stage IDs and exact
Decimal values/differences for current_stage_relative_date, cycles and time.

This is an explanatory C0 diagnostic, not another qualification run or a
revised chronology criterion. It distinguishes a cycle counter issue, elapsed
time issue or acquisition-date ordering issue and selects a repair. No
reordering, rounding, tolerance choice or threshold relaxation is evaluated.

R002 completed with no decreasing scalar in its first six stages. The audit's
five distinct-cycle values had initially been mistaken for five accepted stages;
that interpretation is withdrawn.

## S03-E006-R003 extension, frozen before inspection

Continue diagnosis in ascending numeric-ID order up to the first exact
chronology decrease, parser failure or 342 headers (hard cap). Each header uses
the unchanged reviewed parser/cap. Report examined-stage count and only the
first failing adjacent pair's scalar differences. No qualification function
is invoked and no changed criterion is tested. This extension targets the
actual stopped boundary; the first-six-stage limit was insufficient.

R003 result: 16 headers examined; first decrease at stage 21 -> 22.
Relative date: 33360.702789 -> 35010.350529 (+1649.647740).
Cycles: 380353.5 -> 411460.5 (+31107.0).
Time: 117169.35301208496 -> 34068.64939177036 (-83100.70362031460).
Elapsed command wall time: 1.311463459 seconds; process exit 0.
Only time decreases for this pair. Reset/session-clock semantics are unknown.
