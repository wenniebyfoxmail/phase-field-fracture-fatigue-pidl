# G5 Contract A/B, roles and deployable-input audit

Date: 2026-10-12. Decision: `HOLD_PAIRED_MODEL_RUN__G5_NOT_FULLY_PASSED`.
Scope: C1 synthetic data admissibility. No numerical-result plot applies to
this schema/provenance audit; the decision table below is the visualization.
No confirmation scientific fields were used for model selection. No FEM or
training was launched. Independent cross-dialog review is pending.

## Evidence and decision

| Check | Evidence | Verdict |
|---|---|---|
| v10 seal identity | terminal audit: 1116/1116 hashes, 476 actual / 570 logical states; manifest `55b9f7e923fd7a00170761ec470fb63629e72d28cf82c168edbaa2644e7be561` | PASS integrity only |
| Contract A availability | Windows inventory: 95 `psi_fields/cycle_*.mat`, all 95 cycle files present | PASS availability |
| Contract A semantics | canonical solve accumulates GP maximum across s1..s5 then takes GP mean; d/alpha_bar/f reduced after s5 | PASS code/schema; full per-cycle independent numerical recomputation pending |
| Contract B availability/timing | 95 s4 rows, all `post_history_commit`; 94 prior aliases all s00 `pre_cycle_committed` | PASS inventory/index |
| Per-run numerical semantics | producer semantic validator passes 7 rows, including shapes/loads/bounds/H/q and event tail; it does not independently recompute Contract A reductions or trajectory irreversibility | qualified only to checks actually performed |
| Existing paired model dataset | D003 receipt explicitly `teacher_qualified=false`, `damage_fixed_point_gate=fail`; FEM cycle-summary versus PINN peak checkpoint in paired index | HOLD same-state/teacher claim |
| Additional development axis | U0.115 FEM reuse/reseal approved; a complete matching PINN U0.115 trajectory not found in inspected export/receipt inventory | missing paired asset, not proof that no remote archive exists |
| Nonlinear derived heads | D003 already measures mean(f(alpha_GP)) versus f(mean(alpha_GP)) differences | element-mean alpha cannot exactly regenerate mean f |
| Confirmation roles | U0.1175 seal maintained; U0.125 exposure unknown | PASS exclusion policy; predictive protocol/data lock still pending |
| Deployment inputs | PINN fields and load/mesh history permitted; FEM future event, oracle support/coefficients forbidden | policy frozen below; concrete feature pipeline review pending |

## Contract distinction

Contract A is a composite cycle summary:
`psi_elem=mean_GP(max_substep psi_raw_GP)` and s5 committed d/alpha_bar/f.
Contract B is the simultaneous s4 post-history-commit nodal u/d state; native
retained GP fields allow a separately declared s4 field target. A minus a PINN
s4 field is not a same-state residual. Such a cross-stage statistical mapping
could be defined as a new estimand, but cannot inherit same-state validity.

The three existing PINN trajectory exports contain peak post-step checkpoints
(c1 peak raw step 4 because their step0 is recovery); use each manifest's
explicit mapping, never a universal cycle-to-step shorthand. Their float32
payloads cannot be assessed with a blanket 1e-12 cross-producer equality gate.
Raw native validity tolerances and predictive error criteria are distinct.

For same-state Delta choose one declared support and phase on both producers.
For cycle-summary Delta obtain matching five-substep/cycle reductions on both.
Do not silently substitute cyclemax for s4, s5 for peak, or clipped processed
FEM for native states. Processed-reference imitation is a distinct bounded
claim, not a qualified native teacher claim.

## Roles and allowed information

| Umax | Role | Current allowed use |
|---:|---|---|
| .11/.12/.13 | exposed development | existing diagnostics; predictive use only under explicit representation/timing lock |
| .115 | additional development | FEM reuse; locate/qualify matching PINN asset before paired D0 |
| .1175 | final interpolation confirmation | metadata/validity booleans and sealed identity only; no fit/tuning |
| .125 | exposure unknown, excluded | closed |

Allowed deployable inputs: coordinates/connectivity, known Umax and applied
load, physical cycle/substep, current and past frozen PINN outputs available at
the declared prediction origin. This is post-hoc current-output correction,
not a future forecast. Future PINN states are unavailable at the current origin.

FEM values may be supervised targets and frozen evaluation references, never
inference features, train-fitted normalizers from confirmation, oracle support
or coefficients, FEM event-normalized progress, or confirmation-based model
selection. Event-aware evaluation masks are scoring information only. Any
train/validation selection or time stratum using future FEM first-hit needs an
explicit permitted development-only role; deployment strata should use fixed
physical-cycle bins or causal PINN progress. Include C0 only when a genuine
matching unloaded prehistory state exists.

`mean(f(alpha)) != f(mean(alpha))` generally, and mean(g(d)*psi) generally
differs from g(mean(d))*mean(psi). Exact derived f/active heads require native
GP/nodal parents followed by matching reductions; an element-mean approximation
must be declared and validated separately. Thus the current multiobjective
three-head plan is not run-ready on the existing reduced fields.

## Single next step and ownership

Reuse existing D003 diagnostic evidence; do not repeat its computations or
E015 unchanged. Before D0, assemble a metadata-only paired-asset manifest:
locate existing U0.115 PINN archives remotely, prove checkpoint coverage and
state/support semantics, and select either native same-state s4 or matched
cycle summaries. Independently re-review this data lock and derived-head
semantics. A missing export may be repaired from existing checkpoints; missing
training states are a new producer decision, not an automatic rerun.

G5/FEM asset owner: this dialogue. Multiobjective dialogue: minimal method/run
card and input review only until it receives an approved data lock. One D0
execution owner will be designated after G5, then one reviewed Taobo training
plan if D0 supports it. No parallel D0/NN or Windows solve.

Evidence pointers: Request31 v2 amendment; native canonical solver and
`validate_hard5_stage0b_case.m` retrieved into
`local_archive/experiments/S04-E016/g5_audit_20261012/source/`; terminal audit;
existing `local_archive/experiments/S04-direct-delta/runs/S04-direct-delta-D003/analysis/`.
