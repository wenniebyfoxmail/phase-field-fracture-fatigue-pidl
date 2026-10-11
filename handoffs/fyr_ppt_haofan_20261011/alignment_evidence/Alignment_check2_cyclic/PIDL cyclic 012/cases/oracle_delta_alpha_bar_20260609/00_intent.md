# Intent: oracle FEM Delta alpha_bar

- Date: 2026-06-09.
- Purpose: test whether correct FEM fatigue-history placement alone is sufficient to close the PIDL/FEM gap.
- One-factor change: bypass the normal PIDL history update and add FEM-projected cycle-wise `Delta alpha_bar` at the peak substep only. PIDL displacement/damage training remains unchanged.
- Runner: `SENS_tensile/run_fem_mesh_oracle_field_umax.py`.
- Oracle kind: `delta_alpha_bar`.
- FEM reference: `FEM cyclic 012/cases/standard/raw_data/reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat`.
- PIDL mesh: `SENS_tensile/meshed_geom_fem_soft_hist0.msh`.
- Loading: `Umax=0.12`, physical cycles `80`, substeps `[0.25, 0.5, 0.75, 1, 0]`.
- State mapping: `cN_peak -> PIDL step 5*(N-1)+3`; `cN_unloaded -> PIDL step 5*(N-1)+4`.
- Diagnostic exports required: alpha, alpha_bar, f, g, psi_raw, psi_active, history driver, delta_alpha_bar input, strain/stress, energies, gradient terms at c1/c2/c3/c20/c40/c60/c69 peak/unload.
- Gate: if this closes timing and field placement, the main culprit is history-increment placement. If this still fails, PIDL's damage-energy/irreversibility response to the correct history is not FEM-like.

Producer command template:

```bash
CUDA_VISIBLE_DEVICES=<gpu> PIDL_ARCHIVE_DIR=<archive_root> \
  python -u run_fem_mesh_oracle_field_umax.py 0.12 \
  --oracle-kind delta_alpha_bar \
  --n-cycles-physical 80 \
  --fem-data-dir <soft_hist0_standard_fem_raw_data>
```
