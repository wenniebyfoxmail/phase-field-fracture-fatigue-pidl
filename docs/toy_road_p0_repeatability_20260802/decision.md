# Toy-Road P0 Repeatability Family Decision

Status: `BLOCKED_PENDING_SEALED_PREFLIGHT`

This is the single primary asset for the synthetic FEM transfer family. It is
not real-road validation and carries no traffic-time, field-calibration, RUL,
or deployment claim.

## Current Decision

Implementation of the approved v2.1 producer and v1.1 execution plan is in
progress. Production execution is not authorized. Preflight receipts are
non-authorizing and cannot be used to launch P0, P0R, T1, T2, or T3.

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
- The family has one registry row and one append-only attempt ledger.
- Future terminal receipts link here; they do not create new primary decisions.

## Assets

- Attempt ledger: `_pidl_attempt_ledger/attempts.jsonl`
- Rendered attempt: `attempt.md`
- Producer handoff: `producer_handoffs/toy_road_p0_repeatability_20260803/`

