# Toy-Road P0 Repeatability Producer

This handoff implements the approved v2.1 producer contract. It is a synthetic
FEM transfer workflow, not real-road validation.

The production order is `P0 -> P0R -> T1 -> T2 -> T3`, with terminal validation
after every case. P0/P0R form one producer qualification pair and are not two
independent training or LOTO trajectories.

`finalize_toy_road_family_package.m` closes one completed case package using
its execution lock, c5 receipt, contract, and canonical attempt record. It
writes a no-clobber terminal manifest, sorted checksums, and validation summary.

Preflight receipts are explicitly non-authorizing. No production case may run
without a later, separate execution authorization.

The launcher locks both the Python executable path and its SHA-256 before every
Python protocol invocation. Immediately before the MATLAB call it rechecks the
producer Git HEAD, clean status, and source manifest.

`new_toy_road_p0_one_shot_wrapper.ps1` is run only after a source commit is
sealed. It generates an external wrapper fixed to that commit and to
`P0_parent`; the wrapper rejects preflight receipts and requires a separate
`P0_PARENT_EXECUTION_AUTHORIZED` record. The authorization must also attest the
dedicated-producer controls in `DEDICATED_PRODUCER_POLICY.json`. Generating the
wrapper does not authorize or start FEM.

## D1 Runtime Diagnostic

The D1 runtime probe has scope `diagnostic_only_non_authorizing`. It records
runtime identity predicates and must finish with zero FEM cycles. A complete
PASS or FAIL package contains exactly ten files; `D1_SHA256SUMS.txt` validates
exactly nine peer files and never hashes itself. A launcher-level crash may
instead leave the declared partial package headed by
`D1_LAUNCHER_RECOVERY.json`.

Phase A ends at a reviewed `pre_matlab_candidate_commit`. Neither its static
tests nor any D1 diagnostic receipt authorizes production: D1 does not
authorize P0, P0R, T1, T2, or T3.
