# Intent: oracle active FEM driver

- Date: 2026-06-09.
- Purpose: test whether giving PIDL the exact FEM active fatigue driver closes the history/process-zone gap.
- One-factor change: replace the PIDL fatigue-history driver input with FEM-projected `g(alpha_FEM) * psi_plus_raw_FEM`, scaled by the explicit substep load factor squared. PIDL displacement/damage training remains unchanged.
- Runner: `SENS_tensile/run_fem_mesh_oracle_field_umax.py`.
- Oracle kind: `active_fem`.
- FEM reference: `FEM cyclic 012/cases/standard/raw_data/reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat`.
- PIDL mesh: `SENS_tensile/meshed_geom_fem_soft_hist0.msh`.
- Loading: `Umax=0.12`, physical cycles `80`, substeps `[0.25, 0.5, 0.75, 1, 0]`.
- State mapping: `cN_peak -> PIDL step 5*(N-1)+3`; `cN_unloaded -> PIDL step 5*(N-1)+4`.
- Diagnostic exports required: alpha, alpha_bar, f, g, psi_raw, psi_active, history driver, delta_alpha_bar input, strain/stress, energies, gradient terms at c1/c2/c3/c20/c40/c60/c69 peak/unload.
- Gate: if active-FEM closes the gap but raw-PIDL-g does not, the missing mechanism is the nonlinear `g(alpha)`/damage localization interaction. If it still fails, the damage/irreversibility response is suspect.

Producer command template:

```bash
CUDA_VISIBLE_DEVICES=<gpu> PIDL_ARCHIVE_DIR=<archive_root> \
  python -u run_fem_mesh_oracle_field_umax.py 0.12 \
  --oracle-kind active_fem \
  --n-cycles-physical 80 \
  --fem-data-dir <soft_hist0_standard_fem_raw_data>
```
