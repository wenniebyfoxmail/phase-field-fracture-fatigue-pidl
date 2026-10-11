# reverseBC u=0.12 cyclewise FEM mechanism export

Request: `docs/handovers/fem_cyclewise_mechanism_request_2026-05-28.md commit 0272625`.

Files:
- `C:\Users\xw436\Downloads\_pidl_handoff_v2\reverseBC_u12_cyclewise_mechanism_2026-05-28\reverseBC_u12_cyclewise_mechanism_metrics.csv`: one row per available cycle, c1-c74.
- `C:\Users\xw436\Downloads\_pidl_handoff_v2\reverseBC_u12_cyclewise_mechanism_2026-05-28\reverseBC_u12_cyclewise_element_fields_c1_c74.mat`: compact all-cycle element fields.
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
- Nodes: 77900; elements: 77730; element type: Q4.
- Mesh is identical to previous reverseBC u=0.12 handoffs using `mesh_geometry.mat`.
- Material/fatigue: AT1 + AMOR + PENALTY; E=1, nu=0.3, Gc=0.01, ell=0.01, alpha_T=0.5, p=2.
- Loading/BC: reverseBC u=0.12, R=0, fix_X top+bottom, fix_Y bottom, disp_Y top.

Metric definitions:
- Nominal Kt denominator: `abs(y) > 0.3 and x > -0.3`.
- Crack tip: `x_tip_dXXX is the maximum centroid x among elements with d_elem >= threshold; y is the y of the highest-x threshold element`.
- Process-zone width: `near-tip width uses elements with d >= threshold and |x - x_tip| <= 2*sqrt(mean(element_area)); yspan is max(y)-min(y)`.
- Right-boundary diagnostic: `right boundary means x >= max(element_centroids(:,1)) - 2*sqrt(mean(element_area)); d >= 0.95`.
