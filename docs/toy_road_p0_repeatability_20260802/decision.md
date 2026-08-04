# Toy-Road P0 Repeatability Family Decision

Status: `BLOCKED_PENDING_EXECUTION_AUTHORIZATION`

This is the single primary asset for the synthetic FEM transfer family. It is
not real-road validation and carries no traffic-time, field-calibration, RUL,
or deployment claim.

## Current Decision

The independent review corrections reached a new LF-preserving clean sealed
preflight at source commit `eeda43d9faef01622731e877c5048a78f3c5003a`.
The launcher now locks the Python executable SHA-256, rechecks Git and source
identity immediately before MATLAB, and requires an external commit-fixed
one-shot wrapper plus dedicated-producer attestation for P0. Production
execution is not authorized. All five preflight receipts are non-authorizing
and cannot be used to launch P0, P0R, T1, T2, or T3.

The generated P0-only wrapper contains no execution authorization token. The
next decision is an independent review of the new evidence; only a later
explicit `P0_PARENT_EXECUTION_AUTHORIZED` record may authorize `P0_parent`.
P0R remains blocked behind P0 terminal validation and its c5 receipt.

P0/P0R are one producer qualification pair. They are not independent training
or LOTO trajectories. Only after a separately authorized, same-runtime P0/P0R
repeatability gate may T1/T2/T3 become the three synthetic transfer
trajectories, executed strictly in that order with terminal validation between
cases.

## Evidence Boundary

- Historical U0.12 remains an external reference; active-field backward
  equivalence is not claimed.
- Every case requires its own c5 same-process fixed-point/KKT receipt.
- All five cases must share the sealed rebuilt-MEX runtime identity.
- Windows host `CITPC12` must remain a dedicated producer from P0 one-shot
  authorization consumption through P0 terminal validation; no human or other
  agent may start MATLAB/FEM during that interval.
- The family has one registry row and one append-only attempt ledger.
- Future terminal receipts link here; they do not create new primary decisions.

## Assets

- Attempt ledger: `_pidl_attempt_ledger/attempts.jsonl`
- Rendered attempt: `attempt.md`
- Sealed preflight evidence: `preflight_evidence.json`
- Producer handoff: `producer_handoffs/toy_road_p0_repeatability_20260803/`
