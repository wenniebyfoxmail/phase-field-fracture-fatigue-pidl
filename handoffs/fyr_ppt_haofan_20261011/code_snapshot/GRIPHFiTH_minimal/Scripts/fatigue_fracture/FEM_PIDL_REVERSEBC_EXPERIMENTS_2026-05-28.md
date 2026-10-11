# FEM/PIDL reverseBC experiment audit log, 2026-05-28

This note records the FEM-side run and export scripts added for the PIDL
field-level mechanism comparison. Large solver outputs are intentionally not
committed; they were handed off through OneDrive and summarized in the PIDL
handover outbox.

## Common physics

- Geometry family: SENT, unit square.
- Material: `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01`.
- Phase-field/fatigue: `AT1 + AMOR + PENALTY`, `alpha_T=0.5`, `p=2`,
  `res_stiff=1e-6`.
- Loading: cyclic displacement control, `uy_final=0.12`, `R=0`, `n_step=8`.
- reverseBC: `fix_X` on top and bottom, `fix_Y` on bottom, `disp_Y` on top.
- Exported mechanism fields: `d_elem`, `alpha_bar_elem`, `f_fatigue_elem`,
  `psi_plus_elem`, plus mesh geometry, element areas, cyclewise metrics, and
  energy summaries from `monitorcycle.dat`/`CONV_*.log`.

## Runs and outputs

| Run | Mesh / notch convention | Nodes | Elements | N_f | Purpose |
|---|---|---:|---:|---:|---|
| `SENT_PIDL_12_reverseBC` | Existing `SENT_mesh.inp` / reference reverseBC geometry | 77900 | 77730 | 74 | Full reference field handoff for cyclewise FEM/PIDL mechanism comparison |
| `SENT_PIDL_12_fine_reverseBC` | `SENT_pidl_fine_lh5.inp`, PIDL fine mesh, void/slit notch | 10401 | 10261 | 69 | Check effect of coarsening FEM to PIDL-like mesh resolution |
| `SENT_PIDL_12_diffuse_precrack_reverseBC` | Continuous material `plate(... notch_type='phase_field' ...)`; no void slit; fixed diffuse `d=1` band | 45591 | 45000 | 69 | Reciprocal diagnostic: separate void-notch geometry from phase-field damaged-band initialization |
| `SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC` | Same continuous material mesh; soft AT1/PIDL-like initial `d`; zero initial fatigue history | 45591 | 45000 | 69 | Strict Request 18 diagnostic: remove hard Dirichlet band and artificial precrack fatigue degradation |

## Diffuse pre-crack convention

The diffuse pre-crack run keeps material in the pre-crack corridor. There are
no duplicated crack-face nodes and no traction-free internal crack boundary.
The PIDL-style centered mask `x <= 0`, `|y| <= 0.02` is implemented in plate
coordinates as `x <= 0.5`, `|y - 0.5| <= 0.02`.

The run fixes `5020` nodes as non-homogeneous phase-field Dirichlet nodes with
`d=1`. It also initializes `5000` centroid-selected elements with
`alpha_bar=1` and `f_alpha=(2*alpha_T/(1+alpha_T))^p = 0.444444444444`.

The strict soft/hist0 variant instead initializes `p_field` and `p_field_old`
with the PIDL `hist_alpha_init` AT1 squared-hat profile over the same crack
segment. It does not prescribe those nodes as phase-field Dirichlet nodes, and
it starts `alpha_bar=0`, `f_alpha=1` everywhere. The penetration detector uses
`initial_precrack_exclusion_nodes` to avoid counting the initial left-boundary
pre-crack as immediate boundary penetration.

## Source files added

- `INPUT_SENT_PIDL_12_reverseBC.m`
- `main_SENT_PIDL_12_reverseBC.m`
- `INPUT_SENT_PIDL_12_fine.m`
- `main_SENT_PIDL_12_fine.m`
- `INPUT_SENT_PIDL_12_fine_reverseBC.m`
- `main_SENT_PIDL_12_fine_reverseBC.m`
- `INPUT_SENT_PIDL_12_diffuse_precrack_reverseBC.m`
- `main_SENT_PIDL_12_diffuse_precrack_reverseBC.m`
- `INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m`
- `main_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m`
- `export_reverseBC_cyclewise_mechanism.m`
- `export_reverseBC_diffuse_precrack.m`
- `export_reverseBC_diffuse_precrack_soft_hist0.m`
- `solve_fatigue_fracture.m` (adds optional `initial_precrack_exclusion_nodes`)
- `Dependencies/SENT_mesh/gen_pidl_fine_lh5_mesh.py`
- `Dependencies/SENT_mesh/SENT_pidl_fine_lh5.inp`

## Handoff locations

- Full reverseBC cyclewise handoff:
  `C:\Users\xw436\OneDrive - University of Cambridge\PIDL result\_pidl_handoff_reverseBC_u12_cyclewise_mechanism_2026-05-28`
- PIDL-fine reverseBC handoff:
  `C:\Users\xw436\OneDrive - University of Cambridge\PIDL result\_pidl_handoff_fine_reverseBC_u12_cyclewise_mechanism_2026-05-28`
- Diffuse pre-crack reverseBC handoff:
  `C:\Users\xw436\OneDrive - University of Cambridge\PIDL result\_pidl_handoff_reverseBC_u12_diffuse_precrack_2026-05-28`
- Strict soft/hist0 diffuse pre-crack reverseBC handoff:
  `C:\Users\xw436\OneDrive - University of Cambridge\PIDL result\_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28`

The PIDL repository outbox commit `9c5c7b9` records the diffuse pre-crack
handoff and selected c1/c40/c69 metrics.
