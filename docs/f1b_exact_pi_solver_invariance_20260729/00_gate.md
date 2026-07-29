# F1b Fresh Dimensional Solver-Invariance Gate

1. **Mechanism question**: does a genuinely fresh GRIPHFiTH solve preserve the
   normalized eta0 SENS trajectory under the complete exact-Pi dimensional
   transform, including plane state, topology, thickness, BC, loading path,
   hard-recovery state, and event semantics?
2. **Claim changed**: pass would establish solver-level dimensional invariance
   for this one homogeneous plane-strain benchmark. Fail would identify an
   implementation/numerical invariance boundary. Neither outcome validates a
   road, layered pavement, traffic clock, temperature/rate law, forecast, or
   inverse method.
3. **Cheaper diagnostic**: F1a already passed the scaling and field-I/O replay.
   It cannot answer solver invariance, so a fresh FEM solve is now the minimum
   sufficient diagnostic. No PIDL training is permitted.
4. **Minimal output asset**: immutable input/provenance, new output root,
   c20/c40/c60 fields, first-hit and confirmed own-event fields, event trace,
   normalized FEM-centred metrics, active-support metrics, one residual figure,
   manifest, hashes, and decision.
5. **Registry path**: `docs/pidl_experiment_inventory.md` case
   `f1b_exact_pi_solver_invariance_20260729`, plus Windows-FEM Request 26 while
   producer execution remains outstanding.

## Locked Gate

The complete producer contract is
`producer_handoffs/f1b_exact_pi_20260729/INPUT_LOCK.json`, with the dimensional
residual audit frozen in `TOLERANCE_AUDIT.md`. Active Newton controls preserve
the normalized numerical problem: force residuals scale by `300`, phase
residuals/tangents by `3000`, and staggered convergence uses the separately
normalized residual sum. The acceptance gates are:

- damage linear MAE/RMSE/correlation: `<=0.002`, `<=0.005`, `>=0.995`;
- history/raw/active log10 MAE/RMSE/correlation: `<=0.05`, `<=0.10`, `>=0.99`;
- active FEM-p99 IoU `>=0.90`, area ratio `[0.90,1.10]`, and centroid shift no
  more than one local reference support-cell diameter;
- all gates at same-cycle c20/c40/c60 and first-hit/confirmed own-event states;
- first-hit and confirmed cycle errors each no more than one explicit cycle.

Floating-point identity is not required. These are predeclared solver/mesh
engineering gates, not mathematical residual-to-field error bounds.

A missing approved producer is `BLOCKED`. A completed fresh solve that violates
any locked criterion is `FAIL`; thresholds are not adjusted after inspection.
