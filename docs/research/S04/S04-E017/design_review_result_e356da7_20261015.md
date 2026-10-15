# S04-E017 v1 independent design review result

Date: 2026-10-15. Reviewed commit: `e356da7`. Reviewer: existing read-only
method-review chat `01a12d15-9b60-7280-8248-18386d6ef741`.

The exact outbound review request was shown to and approved by the user before
it was sent once. The reviewer returned **NEEDS REVISION**. This was a design
review only: it did not authorize implementation, training, confirmation access
or a producer Run.

Accepted direction:

- use the minimal L0-versus-I0 comparison before GradNorm/PCGrad;
- retain close total parameter counts and whole-Umax holdouts.

Required changes before re-review:

1. remove the invalid derivation of corrected mean `f` from corrected mean
   history;
2. limit Q to a transformed relative configuration comparison and report
   physical-scale, C1-20 and zero-Delta B0 diagnostics;
3. freeze paired-seed aggregation, near-zero denominator, missing-run, numeric
   tie and invalid-I0 branches without dropping failed seeds;
4. specify channel bounds/monotonic fields, controlling tolerance and tests for
   reachability, zero Delta and violation detection;
5. state that matched total parameters do not match per-task capacity, compute
   or optimisation, and freeze sample/update/selection semantics and costs;
6. position S04-E017 relative to the concurrent single-channel physical-raw
   proposal rather than calling both the unique next step.

Revision v2 is contained in `experiment.md`. No re-review request has been sent;
any new outbound message requires a new exact user approval.
