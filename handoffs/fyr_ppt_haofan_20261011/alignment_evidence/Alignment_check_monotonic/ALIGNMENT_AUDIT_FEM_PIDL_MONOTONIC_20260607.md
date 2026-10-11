# FEM/PIDL Monotonic Alignment Audit

Date: 2026-06-07

Folders audited:

- `Alignment check/FEM monotonic match/`
- `Alignment check/PIDL monotonic/`

## Verdict

The latest FEM monotonic match package is aligned with the PIDL `allFinePretrain` monotonic cases on the core comparison settings: soft-hist0 retained-material geometry, 24-step nonuniform monotonic loading to `U=0.2`, fatigue-on/off pair, and FEM soft-hist0 mesh used throughout PIDL training.

The PIDL `standard_pretrain` cases are not fully aligned for a strict mesh-history comparison because their coarse pretrain used `meshed_geom1.msh`; they only switch to `meshed_geom_fem_soft_hist0.msh` for the fine stage.

Important clarification: "FEM step" and "PIDL cycle" are only output labels, not different loading states. FEM names the first loaded state as step 1; PIDL names the first loaded state as cycle 0. The physical displacement sequence is the same.

## Aligned Settings

### Loading

- FEM displacement steps: `0.025`, `0.050`, `0.075`, `0.100`, then `0.105:0.005:0.200`.
- PIDL displacement steps: same sequence via `config.disp`.
- FEM uses one-based step names: `fields_000001_001.vtk` / figure `cycle01` is `U=0.025`.
- PIDL uses zero-based cycle names: figure `cycle0` is `U=0.025`.
- Mapping rule: `FEM step = PIDL cycle + 1`.
- Example: FEM step 13 / figure `cycle13` maps to PIDL cycle 12; both are `U=0.145`.

### Geometry / Precrack

- FEM match handoff states: retained material, soft diffuse precrack / hist0 initialization, no void slit, no duplicated crack-face nodes.
- PIDL all-fine cases use `meshed_geom_fem_soft_hist0.msh` as both coarse and fine mesh.
- The strict PIDL mesh and FEM VTK geometry have the same node count (`45591`) and no duplicate coordinates. FEM stores the cells as `45000` quads; PIDL stores the same grid split into `90000` triangles.
- Coordinate frames differ by a translation: FEM plate coordinates are `[0,1] x [0,1]`; PIDL coordinates are `[-0.5,0.5] x [-0.5,0.5]`.
- Therefore the same initial precrack maps as:
  - FEM: `x = 0..0.5`, `y = 0.5`.
  - PIDL: `x = -0.5..0`, `y = 0`.
- FEM source uses `notch_type='phase_field'`, `Lnotch_x=0.5`, `y_notch=0.5`, and an AT1-like squared-hat soft profile with support `2*ell`.
- PIDL uses `crack_dict = {"x_init": [-0.5], "y_init": [0], "L_crack": [0.5], "angle_crack": [0]}` and the same AT1 squared-hat `hist_alpha_init` form with support `2*l0`.
- The old PIDL/FEM void-notch diagnostic is not active in these monotonic PIDL runs: `void_notch_mask["enable"] = False`.

### Boundary Conditions

- FEM match case is explicitly reverseBC:
  - `fix_X` on top and bottom.
  - `fix_Y` on bottom.
  - `disp_Y` on top.
- PIDL monotonic runners explicitly disable the newer `exact_bc` / `fem_anchor` branch and use the original PIDL BC ansatz.
- In that original PIDL ansatz, for vertical loading (`theta=pi/2`):
  - `u = (y-y0)(yL-y) * NN_u * lambda`, so `u=0` on top and bottom.
  - `v = ((y-y0)(yL-y) * NN_v + (y-y0)/(yL-y0)) * lambda`, so `v=0` on bottom and `v=lambda` on top.
- This is essential-BC compatible with the FEM reverseBC constraints on top/bottom displacement. It is not the disabled `fem_anchor` branch, which would fix horizontal displacement only at one anchor.
- Caveat: the PIDL case folders do not currently write a clean `bc_mode` metadata field. The match above is confirmed from the source used by the monotonic runners, not from a self-contained line inside each archived case folder.

### Model Pair

- FEM: `AT1 + AMOR + PENALTY`, `E=1`, `nu=0.3`, `Gc=0.01`, `ell=0.01`, `res_stiff=1e-6`.
- PIDL monotonic case names/logs indicate the matching AT1/fatigue-on/off softHist0 monotonic setup on the FEM soft-hist0 mesh.
- FEM fatigue-on: `alpha_T=0.5`.
- FEM fatigue-off: `alpha_T=1e10`.
- PIDL fatigue-on logs: `fatigue_on=True`, Carrara accumulator, asymptotic degradation, `alpha_T=0.5`.
- PIDL fatigue-off logs: `fatigue_on=False`.

## Not Aligned / Caveats

1. `standard_pretrain` PIDL cases are only fine-stage aligned.
   - `softHist0_standard_pretrain_fatigue_on/off` use `meshed_geom1.msh` for coarse pretrain.
   - They use `meshed_geom_fem_soft_hist0.msh` for fine training.
   - Use these as a pretrain-history ablation, not as the strict FEM-mesh baseline.

2. `allFinePretrain` PIDL cases are the strict mesh-aligned PIDL cases.
   - `softHist0_allFinePretrain_fatigue_on/off` use `meshed_geom_fem_soft_hist0.msh` for both coarse and fine stages.

3. PIDL fatigue-on outputs stop one frame earlier than FEM.
   - PIDL fatigue-on figure manifests have 23 rows, `cycle0..cycle22`, ending at `U=0.195`.
   - FEM fatigue-on has 24 frames, `step1..step24`, ending at `U=0.200`.
   - PIDL fatigue-off cases have all 24 rows through `U=0.200`.
   - This is not a loading-index contradiction. For every common loaded state, the mapping remains `FEM step = PIDL cycle + 1`; PIDL fatigue-on is simply missing the last `U=0.200` saved output.

4. Fatigue-on versus fatigue-off is effectively inactive in monotonic PIDL fields.
   - Existing PIDL comparison note reports monotonic fatigue-on/off alpha snapshots are identical over common saved steps because `loading_type='monotonic'` leaves fatigue history unchanged: `alpha_bar=0`, `f=1`.
   - FEM fatigue-on/off are also nearly identical in load response, but they are still labelled separately through `alpha_T=0.5` and `alpha_T=1e10`.

5. Output step naming can cause off-by-one comparison mistakes.
   - Compare FEM `cycle13` / VTK step 13 with PIDL `cycle12` for `U=0.145`.
   - Compare FEM `cycle12` / VTK step 12 with PIDL `cycle11` for `U=0.140`.

6. BC metadata should be exported in future PIDL archives.
   - The source-level BC check is positive for these runs.
   - Future experiment records should write `bc_mode: original_pidl_top_bottom_u_fixed_vertical_ramp` or equivalent into `model_settings.txt`, so this does not have to be re-audited from source.

## Recommended Comparison Set

For strict FEM/PIDL monotonic alignment, use:

- FEM: `Alignment check/FEM monotonic match/cases/umax020_fatigue_off`
- FEM: `Alignment check/FEM monotonic match/cases/umax020_fatigue_on`
- PIDL: `Alignment check/PIDL monotonic/cases/softHist0_allFinePretrain_fatigue_off`
- PIDL: `Alignment check/PIDL monotonic/cases/softHist0_allFinePretrain_fatigue_on`

Use the `standard_pretrain` PIDL cases only to discuss sensitivity to coarse-pretrain mesh history.

For the main updated experiment, use only the `allFinePretrain` PIDL pair against the `FEM monotonic match` pair. Treat the `standard_pretrain` PIDL pair as an ablation because the coarse-stage mesh history differs.

## Key Matched Instability Point

The aligned load-drop transition is:

- FEM step 12 / PIDL cycle 11: `U=0.140`, pre-collapse.
- FEM step 13 / PIDL cycle 12: `U=0.145`, post-collapse / fracture detected.

FEM force collapses from about `0.0928` at `U=0.140` to about `4.6e-4` at `U=0.145`. PIDL logs detect fracture at zero-based cycle 12, which is the same `U=0.145` state.
