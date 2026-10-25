# S04-E041 — Reference-bound assessment of feasible damage representation

**Status:** parked at reference binding; no new FEM or PIDL computation was
started.

## Purpose and evidence stage

E040 established one narrow result: its state-referenced forward damage map can
keep `h <= d <= 1` over the completed synthetic PIDL trajectory without putting
an irreversibility penalty in the differentiated loss.  It did not establish
whether the q-local representation is closer to a FEM reference.  The next
decision is therefore not another feasibility run, but whether an exact,
qualified FEM state reference exists for the E040 physical trajectory.

This is a synthetic C1 reference-identity and numerical-comparison preparation,
not FEM validation, a physical claim, or a road-fracture prediction experiment.

## D1 reuse and current finding

Reuse the immutable E040 result archive
`/mnt/data2/drtao/pidl_archives/pf_s04e040_feasible_564ba10f_20261024T085200Z`
and its source commit `564ba10f787b6f62795808d133b07cbe6d90af64`; neither arm
is to be rerun for this assessment.  The prior state audit
`local_archive/research/pidl_fem_state_audit_20261020/audit_v1/summary.json`
records 143 state rows, zero fresh solver/model-forward calls, and verified
E011/Q4 paired products.  Its state map contains no `hard_d1_u0_recovery` /
E040 trajectory family.  Consequently those E011/Q4 products are not an E040
FEM reference merely because they share `Umax=0.12`.

**D1 decision: redirect.** The binding uncertainty is reference/state identity,
not q-local optimisation or available GPU time.  Do not launch a new E040-style
solve, select an old cycle-number match, or create a new FEM run just to fill
this gap.

## D2 result — 2026-10-25

Read-only inspection of the original Umax=0.12 hard-recovery package resolved
the remaining ambiguity.  Its
`Baseline/PIDL_hard_d1_u0_recovery_5step/Umax_0.12/original_case/README_FEM_AGENT.md`
states that the run is not the same initial-state object as the direct
soft-profile FEM baseline.  Its companion `notes/00_intent.md` describes it as
an initial-condition discriminator and explicitly says that it is not a full
FEM/PIDL alignment claim unless a matching FEM hard-damage zero-load recovery
reference is added.  The package retains PIDL diagnostics, not that matching
FEM field trajectory.

No qualified FEM reference is therefore available for E040's `c1/s4`, `c2/s4`
and `c3/s4` states.  The state-binding requirement fails; E041 is **parked**
before D3, with zero new GPU time, solver calls or model-forward calls.  This is
not evidence against q-local representation; it only prevents the proposed
FEM-error comparison from being interpretable.

## State-binding requirement

Before any field metric is calculated, an existing candidate reference must
provide a record for every intended comparison state with all of:

- the same physical family, material, geometry and initial/pre-crack treatment;
- the same mesh/support, or a declared fixed projection onto the E040 support;
- the same `Umax=0.12` loading schedule and branch;
- cycle, raw step, substep/phase, and pre/post solve and history-refresh timing;
- the native FEM damage channel and provenance/acceptance record; and
- an explicit map to the E040 `global` and `q_local` states.

If any field is unknown, the state is ineligible.  The historical E011/Q4
states may remain context for their own trajectory but may not substitute for
the required E040 reference.

## Conditional comparison contract

Only after the binding requirement is met, use the already archived E040
fields at the predeclared common peak states `c1/s4`, `c2/s4`, and `c3/s4`.
Compare the two E040 arms to the same frozen FEM damage field on the declared
common domain.  Report direct/projection mapping, element-area weights and the
comparison class in each row.

The primary exploratory observable is the trajectory-mean area-weighted damage
RMSE over those three states, reported separately for `global` and `q_local`.
The q-local mechanism predicts a smaller error near the crack-tip/process-zone
region; therefore a process-zone RMSE and full-domain RMSE are supporting
diagnostics, not a combined score.  No pass margin is frozen because reference
discretisation/variation for this exact state family is not yet available.  A
smaller q-local value would be a bounded representation observation only; it
would not validate FEM, material behaviour or roads.

## Decision ladder and resources

| Step | Decision-scale action | Advance / redirect condition |
| --- | --- | --- |
| D1 (complete) | Search existing state records and E040 provenance. | No exact E040 FEM reference found in the verified state audit; redirect to reference binding. |
| D2 (complete) | Bind an existing FEM source and complete the state-key table. | No matching hard-recovery FEM source exists; park E041. |
| D3 (not entered) | Calculate the declared field metrics from existing archived fields and record one comparator figure. | Requires a future matching reference and a separate amendment. |

The completed D2 task was read-only and had a **0 GPU-hour** ceiling.  It permits
no new FEM solve, no PIDL re-run, no seed/sweep/trajectory extension, and no
unannounced reference substitution.  D3 is offline analysis of existing assets
only; any new producer computation, changed reference family, or expansion
beyond the three named states needs a separate user-approved amendment.
