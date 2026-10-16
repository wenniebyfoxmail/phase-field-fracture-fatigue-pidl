# S09-E008 producer-provenance return recheck — 2026-10-16

## Question

Has Windows-FEM Request 32 returned enough exact-source evidence to decide
whether the Stage-0A input state is sufficient for the sealed U0.125 s00-to-s04
transition?

## Locations checked

- all fetched branches of the shared repository, including the dedicated
  Request 32 branch and `windows_fem_outbox.md`;
- the standard Mac handoff folder `~/Downloads/_pidl_handoff_v2/`;
- the local OneDrive GRIPHFiTH tree;
- the Request 31 read-only audit and derived-snapshot records already copied to
  the shared repository.

## Findings

No direct Request 32 response was found. In particular, there is no returned
variable-classification table, exact solver/update source, or exact run
provenance folder for
`hard5_u0125_stage0b_f24eff2a79b64cc3a6538dd4f18f71ae`.

Two nearby evidence packages were found and checked without opening new
scientific arrays:

1. `hard5_synthetic_dic_peak6_export_20260927_v1` is from clean source commit
   `53ce560b6d20b336d6ec92ccf56ed2b230e804ce`, not the sealed S09-E008 commit
   `862992a60edc7f59335365beacb5c71fc8592a7a`. It contains six event-bracketing
   peak states rather than the 73-cycle six-state trajectory. Its README limits
   it to synthetic-DIC qualification and qualitative transition diagnostics and
   explicitly excludes model training and forecasting claims.
2. `stage2a_qualification_20260930` is bound to the correct source commit and
   the same AMOR and fatigue binary hashes, but it contains only the
   `c0001_s04` state. Its frozen purpose is format/Q4 qualification, and its
   contract states that it does not qualify the corrected Stage-2 producer,
   continuation or restart. It cannot establish s00-to-s04 Markov-state
   sufficiency.

Request 31 records confirm the exact commit, native Q4 identity, binary hashes,
and the timing distinction between `s00 pre_cycle_committed`, `s04
post_history_commit`, and `s05 post_history_commit`. The copied derived
snapshots contain launch overlays and tests, but not the parent solver source
needed to trace every carried and reconstructed variable.

## Decision

`STATE_SUFFICIENCY_BLOCKED` remains the correct status. The nearby packages may
support identity and timing cross-checks; neither is a substitute for Request
32. No scientific payload was decoded, no training was started, and no new FEM
run is justified.

The remaining minimum return is now sharply bounded to:

- exact existing provenance for the sealed U0.125 run;
- exact s00 construction, staggered solve, history-update and exporter source;
- a source-line-traced classification of each advance variable as physical
  carried state, prescribed/frozen context, causally reconstructible value or
  solver initial guess;
- an explicit smallest-missing-item result if the payload is not state
  sufficient.

Until that return is available, the permitted local route is limited to
synthetic/in-memory P0/P1 code and deterministic tests. Scientific decode,
normaliser freezing from real fields, P1 training and Stage 0B remain closed.

## Later resolution on the same date

The user authorised direct SSH instead of a GitHub request. Read-only access to
`CITPC12` found the exact run, provenance and exact-commit source snapshot.
State sufficiency is now qualified as recorded in
`source_state_sufficiency_audit_20261016.md`. Scientific data decode and P1
training remain pending separate decoder review and capability checks.
