# reverseBC u=0.12 cyclewise FEM mechanism export

Request: `docs/handovers/windows_fem_inbox.md Request 19 Variant B`.

Files:
- `C:\Users\xw436\Downloads\_pidl_handoff_v2\reverseBC_u12_diffuse_precrack_soft_hist0_peakonly_2026-05-29\reverseBC_u12_diffuse_precrack_soft_hist0_peakonly_cyclewise_mechanism_metrics.csv`: one row per available cycle, c1-c120.
- `C:\Users\xw436\Downloads\_pidl_handoff_v2\reverseBC_u12_diffuse_precrack_soft_hist0_peakonly_2026-05-29\reverseBC_u12_diffuse_precrack_soft_hist0_peakonly_element_fields_c1_c120.mat`: compact all-cycle element fields.
- `mesh_geometry.mat`: copied mesh geometry.

Field definitions:
- `d_elem`, `alpha_bar_elem`, `f_fatigue_elem`, `psi_plus_elem` are element means over Gauss/history data from `psi_fields/cycle_XXXX.mat`.
- Source files store fatigue history as `alpha_elem`; this export aliases it to `alpha_bar_elem`.
- `psi_plus_elem` is the saved per-cycle peak/summary field, not a raw nodal projection.
- The fields are post-cycle history exports. The available VTK nodal fields are unloaded step-5 snapshots and are not used in this scalar CSV.

Monitor note:
- `alpha_bar_monitor_max` comes from `monitorcycle.dat` column `||fat||_inf`.
- It differs from `alpha_bar_elem_max` because monitor output is a solver/internal-state maximum or norm, while `alpha_bar_elem` is an element-averaged field exported from Gauss/history data.

Mesh and parameters:
- Nodes: 45591; elements: 45000; element type: Q4.
- Mesh: Continuous material plate mesh from specimen.internal.plate notch_type=phase_field; no void slit or duplicated crack faces; soft AT1-like initial d profile, alpha_bar=0 everywhere.
- Material/fatigue: AT1 + AMOR + PENALTY; E=1, nu=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2.
- Loading/BC: u=0.12, R=0, reverseBC fix_X top+bottom, fix_Y bottom, disp_Y top.

Variant parameters:
- GRIPHFiTH `res_stiff`: 1e-06.
- `SOL_STEP_PAR.n_step`: 1.
- Cycle update semantics: one prescribed u=0.12 peak solve per cycle; displacement reset before each cycle, damage/fatigue history retained.
- Side-boundary traction note: No explicit side-boundary stress/traction residual is exported for displacement-only reverseBC; side boundaries are natural/free in this setup..

Diffuse pre-crack diagnostic:
- Centered request mask: `x in [-0.5,0], y = 0, AT1 support radius 2*ell`; implemented plate mask: `x in [0,0.5], y = 0.5, AT1 squared-hat support |distance| <= 2*ell`.
- Material treatment: material retained; no duplicated crack-face nodes.
- Initial/fixed profile: soft AT1-like squared-hat phase-field initial condition; not a hard Dirichlet band.
- Pre-crack support nodes: 5170; support elements: 5432.
- Pre-crack core nodes with `d>=0.95`: 251; core elements: 0.
- Initial `alpha_bar`: 0.
- Initial `f_alpha` in those elements: 1.
- GRIPHFiTH `tol_irrev`: 0.001; AT1 penalty coefficient: 421875.
- `E_d` includes the fracture/damage energy of the prescribed diffuse pre-crack band; there is no PIDL-style separate irreversibility penalty term in this FEM export.

Initial-state audit:
- Pre-crack `d` mean/max at initialization: 0.32970086077 / 1.
- Pre-crack element-mean `d` mean/max at initialization: 0.313181783907 / 0.905.
- Pre-crack `alpha_bar` mean/max at initialization: 0 / 0.
- Pre-crack `f_alpha` mean/min at initialization: 1 / 1.
- Outside-precrack `alpha_bar` mean/max at initialization: 0 / 0.
- Energy values are absolute FEM energies unless a CSV column explicitly forms an increment; `E_d` is not shifted by the initial pre-crack energy.

Event audit:
- Native final/fracture cycle in this export: 120.
- Final right-boundary `d>=0.95` count/yspan: 0 / 0.
- First right-boundary `d>=0.95` cycle: NaN.
- First `x_tip_d095>=0.995` cycle: NaN.
- First `d_max>=0.95` / `d_max>=1.0` cycles: 1 / NaN.
- First `f_fatigue_min<=0.05` / `<=0.01` cycles: NaN / NaN.
- First `alpha_bar_elem_max>=10` cycle: NaN.

Metric definitions:
- Nominal Kt denominator: `abs(y) > 0.3 and x > -0.3`.
- Crack tip: `x_tip_dXXX is the maximum centroid x among elements with d_elem >= threshold; y is the y of the highest-x threshold element`.
- Process-zone width: `near-tip width uses elements with d >= threshold and |x - x_tip| <= 2*sqrt(mean(element_area)); yspan is max(y)-min(y)`.
- Right-boundary diagnostic: `right boundary means x >= max(element_centroids(:,1)) - 2*sqrt(mean(element_area)); d >= 0.95`.
- Near-tip integrals: `near_tip_int_* columns are area integrals sum(field * element_area) within r <= ell, 2ell, 4ell around the selected d-threshold crack tip.`.
