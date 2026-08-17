# T3 Sibling Execution and T2-CONT Design

## Decision

Preserve the original T2 result as
`FAIL_COUPLED_FIXED_POINT_NONCONVERGENCE_AT_C5_S4`. Publish compact D-T2
evidence without modifying or copying over the immutable diagnostic run. Re-seal
T3 as a sibling experiment qualified directly by the P0/P0R repeatability gate,
then run exactly one T3 trajectory. Design T2-CONT concurrently, but limit it to
a c5/s4-only adaptive material-continuation diagnostic.

Neither the T3 sibling receipt nor a T2-CONT c5 PASS grants authority to start a
full T2 trajectory.

## Evidence graph

```text
P0/P0R repeatability PASS
        |-- T1 initial-defect trajectory
        |-- T2 material-state trajectory: FAILED at c5/s4
        |     `-- D-T2 observer: NONPERIODIC_NONCONTRACTION
        |           `-- T2-CONT c5/s4-only diagnostic (design/conditional run)
        `-- T3 loading-history trajectory (independent sibling)
```

T3 depends on the P0/P0R qualification and the unchanged sealed producer. It
does not depend on T1 or T2 success. The original serial `T1 -> T2 -> T3`
relationship is superseded by this graph for future execution, without changing
any historical artifact or receipt.

## Original T2 preservation

The existing T2 failure dossier remains authoritative and byte-preserved. Its
classification is a coupled fixed-point failure, not a Newton failure. The
terminal location is cycle 5, substep 4, after the 1000-stagger cap. No future
continuation or stabilization result may overwrite, rename, or reinterpret it as
a successful T2 production trajectory.

## Compact D-T2 evidence

The compact package contains only:

- a machine-readable diagnostic summary;
- iterate-geometry, active-set, process-zone, and fatigue-consistent objective
  tables;
- the read-only analyzer source and tests;
- SHA-256 bindings to `RUN_RESULT.json`, the 1000-row trace, mesh geometry, and
  the full iterate capture;
- a compact inventory and decision note.

The package does not copy the approximately 3.1 GiB iterate file. It binds that
file by SHA-256 and records its external immutable run path. The package records
that all 1000 iterate rows and four completed cycle shards exist. `tot_en` is
explicitly auxiliary and is excluded from the fatigue-consistent objective and
dynamics classification.

The accepted D-T2 classification is `NONPERIODIC_NONCONTRACTION`: the tail does
not close to a period-2 or period-3 orbit, and the adjacent damage increments do
not contract toward the existing `1e-3` fixed-point threshold.

## T3 sibling seal and execution

T3 changes only the locked loading blocks:

```text
c1-c30:   Umax = 0.108
c31-c60:  Umax = 0.126
c61-c150: Umax = 0.120
```

Mesh, material, recovery, event definition, MATLAB identity, four MEX binaries,
thread settings, solver, and all convergence thresholds remain unchanged from
the qualified P0 producer. T3 uses fresh output, work, temporary, preference,
and cache roots; it does not resume.

Before launch, a sibling seal must bind:

- the P0/P0R repeatability PASS adjudication;
- the sealed producer source and runtime identities;
- the existing T3 physics contract and physical-input projection;
- the superseding sibling graph;
- the exact T3 launcher input and fresh roots.

Authorization is scoped to exactly one T3 execution. It may use the smallest
wrapper required by the sealed launcher, but it must not add new layers of
external scientific validation. The launcher must first verify that no MATLAB or
FEM experiment is running. T3 terminal validation uses the existing package and
physics gates. It does not start any follow-on case.

## T2-CONT alternatives

Three continuation choices were considered:

1. **Adaptive material continuation in `Gc` (selected).** At the frozen T2
   c5/s4 subproblem, begin at `Gc=0.01` and move toward `0.008`. This directly
   probes the parameter that caused the fixed-point map to lose contraction,
   while leaving the target load unchanged.
2. **Adaptive load continuation.** Subdivide the 0.75-to-1.0 load transition.
   This introduces a different loading path inside an irreversible model and is
   less direct for diagnosing the observed `Gc` sensitivity, so it is rejected.
3. **Pseudo-arclength continuation.** This could traverse a noncontractive
   branch but requires a materially larger solver modification and an additional
   constraint equation. It is deferred unless material continuation fails with a
   clear fold signature.

Relaxation-factor and Aitken sweeps are excluded.

## T2-CONT algorithm

T2-CONT freshly reproduces T2 through c5/s3 with unchanged physics and numerics,
then stops normal trajectory advancement. It does not reuse the P0 c5 state. At
c5/s4 it freezes the original T2 traction, active DOFs, damage lower bound, and
history, then defines a numerical continuation coordinate `lambda`:

```text
Gc(lambda) = 0.010 - 0.002*lambda,  lambda in [0,1].
```

The `lambda=0` anchor is solved from the T2 c5/s4 entry state. The c5/s3 damage
state remains the fixed irreversibility lower bound for every stage, and the
c5/s3 fatigue/history state remains frozen. Accepted intermediate states provide
only warm starts for displacement and damage; they do not commit fatigue history
and do not count as physical substeps or cycles. Each raw stagger update remains
the unrelaxed `d_(k+1) = T_Gc(d_k)` map: no mixing, relaxation, Aitken, or line
search is introduced.

The controller is a single adaptive path, not a parameter sweep:

- initial `delta_lambda = 1/4`;
- after an accepted stage taking at most 250 staggers, double the next step;
- after an accepted stage taking 251-750 staggers, retain the current step;
- after an accepted stage taking more than 750 staggers, halve the next step;
- on a rejected stage, hash-verify rollback of both fields and halve the step;
- minimum `delta_lambda = 1/128`;
- no more than 24 attempted stages;
- terminate immediately if the minimum step is rejected or the attempt cap is
  reached.

Step-size bands influence only the next trial and never stage acceptance. Every
attempted stage retains the original Newton limits, 1000-stagger cap, and four
external gate thresholds: displacement residual `4e-4`, projected phase KKT
`4e-4`, consecutive damage infinity norm `1e-3`, and primal feasibility `1e-12`.
Raw phase residual is recorded but is not converted into a new gate. No tolerance
may be widened. A stage is accepted only after its Newton solves succeed and all
four coupled checks pass. The final stage must land exactly at `lambda=1`, hence
`Gc=0.008`, and pass the same four checks.

The sealed `ToyRoadC5Trace` remains unmodified and is not reused to represent
multiple continuation stages. T2-CONT has a separate diagnostic-only validator
whose formulas and constants are equality-tested against the sealed gate. Each
attempt owns one create-once trace subdirectory.

## T2-CONT outcomes and authority boundary

Allowed terminal classifications are:

- `PASS_TARGET_C5_S4_ONLY_NEEDS_SEPARATE_FULL_T2_AUTHORIZATION`;
- `FAIL_T2_CONT_ANCHOR_NONCONVERGENCE`;
- `FAIL_T2_CONT_MIN_STEP_AT_C5_S4`;
- `FAIL_T2_CONT_ATTEMPT_CAP_AT_C5_S4`;
- `FAIL_T2_CONT_NEWTON_AT_C5_S4`;
- `FAIL_T2_CONT_GATE_AT_TARGET_C5_S4`;
- `FAIL_T2_CONT_STARTUP_OR_RUNTIME`;
- `FAIL_T2_CONT_ROLLBACK_INTEGRITY`.

A PASS proves only that adaptive material continuation reaches the original c5/s4
endpoint under the original gates. It does not convert original T2 to PASS, does
not authorize cycle 6, and does not permit a full T2 trajectory. Any later full
trajectory requires a separate design that addresses whether identical
continuation numerics must be applied to P0, T1, and T3 before cross-case use.

## Evidence and tests

T3 tests must prove sibling predecessor selection, exact changed-axis closure,
fresh roots, no resume, unchanged runtime/solver/gates, one-case launch scope,
and no follow-on authorization.

T2-CONT tests must prove:

- exact endpoint interpolation and no overshoot of `lambda=1` or `Gc=0.008`;
- deterministic accept/grow and reject/rollback behavior;
- frozen c5/s3 history and damage lower bound across intermediate stages;
- no intermediate history commit or cycle/substep increment;
- unchanged Newton, stagger, residual, KKT, and fixed-point thresholds;
- absence of mixing, relaxation, Aitken, and line search;
- termination at minimum step and attempt cap;
- no code path beyond c5/s4, no c5 history commit, no s5, no cycle-5 shard,
  no event advancement, and no production authorization field;
- create-once evidence with an inventory of every attempt, accepted warm start,
  rejected rollback, final gate, source identity, and runtime identity. Every
  attempt ledger row records `lambda`, `Gc`, step size, start/end hashes, outcome,
  stagger count, raw phase residual, four final metrics, and rollback hash check.

## Execution order

1. Verify and retain the existing original T2 failure dossier.
2. Test, build, and push compact D-T2 evidence; leave the original run untouched.
3. Implement and verify the sibling graph and T3 seal.
4. Confirm no MATLAB/FEM experiment is running, then launch exactly one T3.
5. While T3 runs, implement and test T2-CONT tooling only; do not launch it in
   parallel with T3.
6. After T3 terminates, validate and seal T3. T2-CONT remains separately
   authorized and c5/s4-only.
