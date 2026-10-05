# S04-E002-R003 — frozen FEM/PIDL413 cross-residual audit

Purpose: test whether the FEM c83 s004 peak u,d is stationary under the PIDL physical objective with projected accepted step413 history frozen. Goal and steps: lock input/state identity; independently differentiate physical nodal fields; evaluate UV and box-damage residuals plus energy decomposition; verify execution, review interpretation, register decision. No neural fitting, optimizer, trial update or history commit.

## Decision

**REFERENCE_NONSTATIONARY** under the predeclared practical residual screen 1e-3. This is a projected legacy-history counterfactual, not FEM's own equilibrium test or a PINN impossibility result.

| Component | Energy | rho_u | box rho_d | Unprojected damage dual norm |
|---|---:|---:|---:|---:|
| Elastic | 1.8033163293e-5 | .04133147972 | .00321493374 | 13.30684957 |
| Fracture | .007972126858 | 0 | .09779164950 | 27.36114671 |
| Irreversibility | 5.81373319814 | 0 | .17025413366 | 30545.85543381 |
| Total | 5.82172335817 | .04133147972 | .17479701282 | 30545.25969882 |

Both total residuals exceed 1e-3 (41.33 and 174.80 times). GP positive previous-minus-current damage: max .30220191499; area RMS .02624947706. The irreversibility penalty is 99.86275% of total energy and dominates unprojected damage-gradient magnitude. Gradient vectors add, but neither type of gradient norm is an additive contribution or causal percentage.

At fixed current fields, both fracture and penalty energies are independent of displacement. Merely replacing fatigue/damage history in this implementation cannot remove the UV residual .04133148. Check original FEM convergence records and discrete weak-form/energy-gradient, boundary and constitutive consistency before assigning a cause. A stored staggered iteration count of 24 alone does not establish convergence or failure.

No qualified FEM c83 s003/precommit control was found in the exact-peak v2.1, canonical formal Hard5, local archive or handoff search. v2.1 source_postcommit history_vars_old is explicitly after history commit and must not be used as a predecessor. The measured gap is relative to projected PIDL413, not evidence that FEM violated its own irreversibility. Missing control prevents unique history attribution, but does not block this counterfactual's stationarity verdict.

Supervised expression remains a separate single-state diagnostic. Physics polish departing from FEM would not, by itself, show optimizer failure: the target is already nonstationary for this frozen objective. No training has been launched or qualified by this result.

## Execution and verification

- Numerical source: afb3b80, branch codex/censor-numerical-diagnostics-20261004; original Q4/energy kernels unchanged. Protocol: cross_residual_protocol.md.
- D-26-09 Windows Condor58, remote C:/Users/xw436/jobs/censor_cross_20261005_r003, PID29176. Normal scheduler termination, exit0. Audit finished 2026-10-05T00:11:12Z.
- CPU float64 nodal derivatives; original float32 fatigue-map values promoted to float64. Torch2.8.0+cu128. Scheduler allocated GPU3d74ea12 but this audit used no CUDA compute.
- Three derivative/mass/box/history tests passed remotely; identity/BC/finite/mass/history immutability/component-gradient sum checks passed. Three tests also passed locally before exact-commit review.
- Mathematical evaluation .4108s excludes runtime extraction/import; scheduler execution128s, slot busy136s. No inference about training speed.
- Code Ready PASS and evidence/interpretation PASS from Pro, scoped to supplied implementation and evidence, not independent archive recomputation; see adjacent review records.
- Attempt-specific ledger validation passed. A broader legacy-ledger check reports unrelated missing historical assets; this audit does not repair or qualify those older attempts.
- Raw arrays, tests, execution identity and scheduler receipts retained under project-root local_archive/experiments/S04-E002/runs/S04-E002-R003. Exact CSV and JSON are also tracked adjacent to this note. Figure uses native Q4 polygons and diagnostic cell reductions, not gate norms.

## Next gate

Read-only mechanics consistency audit: evaluate/compare FEM's assembled free-UV weak residual and the PIDL energy derivative on the same c83 field, with exact constitutive split, boundary exclusions, quadrature and scaling documented. Separately obtain a lineage-qualified pre-c83-peak FEM state for the damage-history control. Do not tune residual thresholds or launch long training to bypass these unresolved distinctions.


## 2026-10-05 correction: qualified predecessor found

The earlier unavailable-predecessor statement was a search omission. S04-E003 located the v1/native_q4 precommit capture, qualified exact target/mesh identity and source timing, and completed five history controls plus original MATLAB weak-residual comparison. E002 numerical counterfactual results remain unchanged. See [S04-E003 decision](../S04-E003/decision.md).
