# T2 Failure Seal and Diagnostic Plan

**Goal:** Preserve and publish the original T2 coupled fixed-point failure, then diagnose its c5/s4 iterate dynamics without changing the sealed production result.

**Architecture:** A Python evidence builder copies only T2-owned artifacts into a create-once dossier, binds the predecessor by terminal/authentication hashes, emits strict machine-readable failure and identity receipts, and inventories every copied byte. Large MATLAB shards are tracked with Git LFS. D-T2 is a separate c5-only diagnostic producer; any later stabilized solver is a new experiment identity and never replaces original T2.

## Non-negotiable boundaries

- Original T2 classification is `FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4`.
- Keep the fixed-point threshold at `1e-3` and the stagger cap at 1000.
- Do not classify the failure as Newton failure.
- Do not modify or overwrite P0, P0R, T1, or T2 outputs and legacy receipts.
- Do not launch the serial-chain T3.
- Run no more than one MATLAB/FEM experiment at a time.
- Monitoring energy is auxiliary only; it is not a fatigue-consistent objective.

## Task 1: Seal and publish original T2 failure

1. Write failing unit tests for selected-file closure, create-once behavior, exact SHA inventory, failure classification, identity binding, and exclusion of the duplicated T1 evidence tree.
2. Implement the external evidence builder with strict JSON reads and copy-then-rehash verification.
3. Build the real dossier from `C:\q4diag\toy-road-t2-production-7c56ff3-run1`.
4. Verify the 1000-row c5/s4 trace, four completed cycle shards, terminal error, source/runtime/input hashes, and predecessor hashes.
5. Track large `.mat` files with Git LFS, commit, push, and verify the exact remote ref.

## Task 2: Minimal D-T2 diagnostic

1. Add tests for a diagnostic-only observer that records full damage iterates without altering the update operator.
2. Add a separately named c5-only runner that stops after c5/s4 and records `d_k`, `delta_d_k`, active sets, process-zone summaries, and fatigue-consistent objective components.
3. Recheck that no MATLAB/FEM process exists, then execute exactly one D-T2 run.
4. Classify negative-eigenvalue oscillation, near-periodic switching, or nonperiodic noncontraction from adjacent and lagged iterate geometry.

## Task 3: Sibling contract and stabilized-T2 design

1. Re-seal the family graph as P0/P0R qualification with T1, original-failed T2, and T3 as siblings; the receipt carries no production authorization.
2. Keep T3 pending a separate one-shot authorization.
3. Define fixed `omega=0.5` and safeguarded Aitken as separately identified c5-only stabilized experiments using the original four gates and thresholds.
4. Permit a full stabilized trajectory only after c5/s4 passes; require matched stabilized-numerics checks for P0/T1/T3 before using stabilized T2 in training data.
