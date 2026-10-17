# AT1-fatigue mesh-PINO Stage 0 readiness decision

**Date:** 2026-08-24  
**Decision:** `STOP_FULL_PINO__REQUEST_PRODUCER_MATCHED_SUBSTEP_EXPORT`  
**Execution:** read-only Mac audit; no FEM solve and no neural-network training

## PIDL Experiment Gate

- **Mechanism question:** Can the locked four-trajectory archive evaluate the
  discrete equilibrium, AT1 projected-KKT and Carrara fatigue-history residuals
  required by a full fatigue PINO?
- **Claim changed if success:** A producer-matched PINO tooling gate could be
  designed for the same shared-geometry Hard5 factorial benchmark.
- **Claim changed if failure:** Existing cycle-peak states cannot support a full
  AT1-fatigue PINO; training remains blocked pending an exact state export.
- **Cheaper diagnostic first:** Inspect the existing NPZ dataset, bundle manifests,
  source MAT/VTK fields and checkpoints without running a producer.
- **Minimal output asset:** This decision note plus one machine-readable readiness
  audit.
- **Code/producer alignment:** Mac performed only file inspection and a lightweight
  audit script. No training command entered a loop.
- **Success criteria:** All required nodal/Gauss-point states and retained substeps
  exist coherently enough to evaluate all three residuals.
- **Failure criteria:** Missing per-cycle displacement/nodal damage, missing
  Gauss-point internal state, or missing unload/reload driver sequence.
- **Registry destination:** `docs/pidl_experiment_inventory.md`, one diagnostic row.
- **Decision:** `diagnose first`; Stage 0 fails readiness and training is not approved.

## Audited assets

The materialized dataset contains four trajectories and 348 cycle-peak states:

| trajectory | cycle MAT files | sampled cycle-end VTKs | c1 peak VTK | per-cycle MAT fields |
|---|---:|---:|---:|---|
| hard / 5-step | 86 | 39 | yes | `d_elem`, `alpha_bar_elem`, `f_alpha_elem`, `psi_elem` |
| hard / 8-step | 89 | 39 | yes | same four element means |
| soft / 5-step | 87 | 37 | yes | same four element means |
| soft / 8-step | 86 | 41 | yes | same four element means |

The cycle MAT sequence is complete for its declared peak-summary semantics. This
is useful data; the failure is that those semantics are insufficient for the
proposed residuals.

## Decisive findings

1. `psi_fields/cycle_XXXX.mat` has no displacement, nodal damage, committed
   Gauss-point history or retained substep sequence.
2. `peak_load_c1.vtk` supplies nodal `u,d` only for the first cycle peak; it is not
   a trajectory.
3. `fields_CYCLE_005/008.vtk` are sampled cycle-end/unloaded states, not coherent
   peak states at every cycle.
4. `checkpoint.mat` contains displacement, nodal phase field and Gauss-point
   history only at the terminal checkpoint; it cannot reconstruct prior substeps.
5. The peak `psi_elem` is a within-cycle maximum summary. It is not the ordered
   unload/reload driver sequence needed to check
   `sum_s <q_s-q_(s-1)>_+`.

Therefore:

| residual | Stage 0 status | blocker |
|---|---|---|
| mechanical equilibrium | not computable trajectory-wide | no coherent per-cycle peak `u,d` |
| AT1 projected KKT | not computable | no coherent nodal state plus Gauss-point committed history/lower bound |
| fatigue-history update | not computable | no retained substep driver/internal-state sequence |

## Interpretation

The archive remains valid for the historical four-channel cycle-peak temporal
operator. It cannot currently support the stronger claim that a network is
trained against the full producer-matched AT1-fatigue physics.

Using only equilibrium/phase regularization on reconstructed peak fields would
be a different, explicitly downgraded physics-guided operator. It must not be
reported as full fatigue PINO or compared as though the fatigue law had been
enforced.

## Next decisive test

Request the small Stage 0b residual-validation packet defined in
[`at1_fatigue_mesh_pino_track.md`](at1_fatigue_mesh_pino_track.md). First verify
real FEM residuals against perturbed states. Do not request or generate the full
training corpus until that evaluator passes.

## Claim boundary

This is a data-readiness failure, not evidence that PINO cannot outperform PIDL.
It also does not invalidate the four cycle-peak trajectories for their existing
within-Hard5 diagnostic use.
