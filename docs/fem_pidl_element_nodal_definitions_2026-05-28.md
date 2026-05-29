# FEM/PIDL Element and Nodal Field Definitions Audit

Date: 2026-05-28

FEM source audited: local GRIPHFiTH mirror at `b680bb0df0cd3bb5702c63e49d48952d49fc8bbc`, equal to `origin/devel` after fetch.

## FEM Exports

Primary file: `GRIPHFiTH/Scripts/fatigue_fracture/solve_fatigue_fracture.m`.

At cycle export, FEM writes:

- `psi_elem = mean(peak_psi_plus, 2)`;
- `alpha_elem = mean(history_vars_old(:,:,2), 2)`;
- `f_alpha_elem = mean(history_vars_old(:,:,4), 2)`;
- `d_elem = mean(p_field(sys.MESH.elem(:, 1:sys.MESH.nel)), 2)`.

Meaning:

| Field | FEM definition | Linear/nonlinear note |
|---|---|---|
| `d_elem` | nodal phase-field `p_field` averaged over element connectivity | nodal mean; for affine low-order elements this is close to an element mean, but it is not a Gauss-point history variable |
| `psi_elem` | Gauss-point mean of cycle-peak raw `psi+` | raw/undegraded positive energy; FEM validation later forms active driver as `((1-d)^2 + 1e-6) * psi_elem` |
| `alpha_elem` / `alpha_bar_elem` | Gauss-point mean of fatigue history `history_vars_old(:,:,2)` | element mean of a GP history variable |
| `f_alpha_elem` | Gauss-point mean of `f(alpha_bar_GP)` | nonlinear mean; not equal to `f(mean(alpha_bar_GP))` in transition elements |

The Jensen/nonlinear point is explicitly documented in `validate_fatigue_5_6.m`: stored `f_alpha_elem = <f(alpha_bar_GP)>_GP`, while `alpha_elem = <alpha_bar_GP>_GP`.

## PIDL Exports

Primary files: `source/compute_energy.py`, `source/model_train.py`, `SENS_tensile/posthoc_mesh_probe_alignment.py`.

PIDL evaluates the NN on mesh nodes, then uses linear triangular element formulas:

| Field | PIDL definition | Linear/nonlinear note |
|---|---|---|
| `alpha_elem` | mean of the three triangular nodal alpha values | for linear triangles this equals centroid value and area mean |
| displacement gradient / strain | constant per triangle from linear triangular shape functions | one-point/constant-strain element evaluation |
| `psi_plus_raw` | raw positive energy density from `strain_energy_with_split(...)[1]` | now exported explicitly by posthoc mesh-probe script |
| `psi_plus_active` | `g(alpha_elem) * psi_plus_raw` | this is what older PIDL `psi_plus_elem` meant |
| `hist_fat_elem` / `alpha_bar` | per-element scalar fatigue history from `update_fatigue_history` | no within-element GP distribution |
| `f_fatigue_elem` | Carrara `f(hist_fat_elem)` | nonlinear function after reducing history to one element scalar |

## Alignment Consequence

For same-probe scoring:

- `damage_alpha`, `alpha_bar`, and `fatigue_f` are useful field comparisons, but `alpha_bar`/`fatigue_f` remain GP-mean vs one-scalar approximations.
- `psi_plus_raw` is the correct raw driver comparison: FEM `psi_elem` vs PIDL raw `psi+_0`.
- `psi_plus_active` is the correct active driver comparison: FEM `((1-d)^2 + 1e-6) * psi_elem` vs PIDL `g(alpha) * psi+_0`.
- The old single label `psi_plus` was ambiguous and should not be used as a final metric label.

The 2026-05-28 rerun showed that reverseBC raw tip driver is close on common probes, while active driver remains far apart. This shifts the leading hypothesis from "PIDL cannot match raw elastic `psi+` amplitude" toward "PIDL damage localization/degradation coupling differs from FEM after the raw driver is available."
