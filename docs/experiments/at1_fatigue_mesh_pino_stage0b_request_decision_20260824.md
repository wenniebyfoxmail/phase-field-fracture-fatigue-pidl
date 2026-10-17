# AT1-fatigue mesh-PINO Stage 0b request decision

> **Superseded as the active gate on 2026-08-26.** Request preparation remains
> valid, but execution and residual validation are deferred by
> [`at1_fatigue_mesh_pino_data_first_amendment_20260826.md`](at1_fatigue_mesh_pino_data_first_amendment_20260826.md).

**Date:** 2026-08-24  
**Decision:** `REQUEST_READY__DO_NOT_EXECUTE`  
**Attempt class:** tooling / producer-state contract  
**Canonical track:**
[`at1_fatigue_mesh_pino_track.md`](at1_fatigue_mesh_pino_track.md)

## Five-question gate

1. **What mechanism question does this test?**  
   Whether exact GRIPHFiTH retained-substep states make the free-DOF
   equilibrium residual, producer-matched AT1 phase residual and Carrara
   history update computable and discriminative.

2. **What claim changes if it succeeds?**  
   Only that a selected 39-transition Umax=0.12 hard-crack packet is suitable
   for a Stage 1 numerical PINO micro-test. It does not approve a teacher
   corpus, full training, or physical/generalization claims.

3. **What claim changes if it fails?**  
   Full fatigue-PINO training remains blocked. Missing or inconsistent producer
   state may not be repaired by tuning physics weights, interpolation, or an
   architecture sweep.

4. **What cheaper diagnostic comes first?**  
   The read-only Stage 0 audit already established that existing cycle-level
   element means and sampled unload VTKs cannot compute the residuals. The
   smallest next diagnostic is six selected cycles, not a full trajectory.

5. **What is the minimum output asset?**  
   One common native-Q4 mesh/physics file; 45 indexed committed states covering
   39 transitions; producer residual/iteration metadata; provenance and hashes.

## Source-code finding that changed the design

`solve_fatigue_fracture.m` commits `history_vars_old` after every converged
substep. The AT1 fatigue kernel updates raw Gauss-point channels as
`H, alpha_bar, q_prev, f`. Peak-to-peak data cannot reconstruct the positive
increments accumulated during unload/reload.

The same kernel does not use `p_field_old`, although the generic solver passes
it. Therefore this gate requests the active-DOF AT1 phase residual and a
separate damage non-recovery audit. It does not call GRIPHFiTH's state a
projected-KKT/VI solution.

## Prepared assets

- Windows-FEM request:
  [`../handovers/windows_griphfith_request_30_at1_fatigue_pino_stage0b_substep_export_20260824.md`](../handovers/windows_griphfith_request_30_at1_fatigue_pino_stage0b_substep_export_20260824.md)
- Locked schema:
  [`at1_fatigue_mesh_pino_stage0b_export_spec_v1.json`](at1_fatigue_mesh_pino_stage0b_export_spec_v1.json)
- Fail-closed validator:
  `SENS_tensile/validate_at1_fatigue_pino_stage0b_packet.py`
- Validator tests:
  `tests/test_at1_fatigue_pino_stage0b_packet.py`

## Local validation

```text
/Users/wenxiaofang/miniconda3/bin/python3 -m pytest -q \
  tests/test_at1_fatigue_pino_stage0b_packet.py
```

Result: `2 passed`. The positive fixture reproduces the exact four-channel
history law; a deliberately corrupted alpha channel fails closed. Python
compilation and `git diff --check` also pass.

## Decision boundary

The request is implementation-ready, but no producer job or export/replay has
been launched. User approval is required before Windows-FEM execution. When a
real packet arrives, a schema/history pass is still insufficient: Mac must
independently recompute the equilibrium and phase residuals and verify that
controlled field perturbations/shuffles score worse.
