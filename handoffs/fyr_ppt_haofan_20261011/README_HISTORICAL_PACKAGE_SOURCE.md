# Code and Results Package for Brian

Prepared: 10 June 2026

This is the single intended entry point for the package. It is a clean review package for the First Year Report work, not the full GitHub history, and it intentionally excludes large raw PIDL archives, FEM `.mat` handoff datasets, and experimental run folders. The aim is to let you, or an AI agent working for you, understand the baseline, inspect the code, and check the current evidence without first navigating the whole project history.

The main research question for the First Year Report is:

> Can PIDL reproduce scalar FEM fatigue-life behaviour and achieve field agreement in controlled phase-field fatigue benchmarks?

The current answer is conservative: PIDL can give plausible scalar/event behaviour in selected controlled cases, but it does not yet reproduce the local FEM fatigue-fracture fields. The main unresolved gap is field-level fidelity, especially the local active-driver/history/degradation feedback near the crack tip and retained precrack band.

## Folder Map

```text
0 CODE/
  PIDL/                  PIDL source, runners, meshes and analysis scripts
  GRIPHFiTH_minimal/     FEM/GRIPHFiTH source closest to the current baseline

1 ALIGNMENT CHECK/
  Alignment_check_monotonic/
  Alignment_check2_cyclic/

2 WRITING/
  FYR.pdf
  Overleaf_tex/
```

Start with this README, then read:

```text
0 CODE/PIDL/README_PIDL_MINIMAL_FOR_BRIAN.md
0 CODE/GRIPHFiTH_minimal/README_GRIPHFiTH_MINIMAL_FOR_BRIAN.md
1 ALIGNMENT CHECK/Alignment_check2_cyclic/README.md
1 ALIGNMENT CHECK/Alignment_check2_cyclic/manifest/cases.csv
1 ALIGNMENT CHECK/Alignment_check2_cyclic/manifest/canonical_outputs.md
```

## Baseline

The baseline is a controlled SENT phase-field fatigue benchmark, not a full concrete pavement model.

| Item | Baseline choice |
|---|---|
| Geometry | SENT specimen with retained-material soft diffuse precrack |
| Model family | AT1 phase-field fracture with AMOR split and Carrara-type fatigue history |
| Main load case | `Umax = 0.12` cyclic loading |
| FEM reference | soft-hist0 reverseBC, standard retained cycle states `[0.25, 0.5, 0.75, 1, 0]` |
| PIDL reference | FEM-mesh softHist0 PIDL runs with one-peak and FEM-like substep variants |
| Validation target | scalar fatigue life/event timing plus local fields: damage, history, fatigue degradation, raw `psi+`, active `g(alpha) psi+`, and energy terms |

Main FEM baseline code:

```text
0 CODE/GRIPHFiTH_minimal/Scripts/fatigue_fracture/main_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m
0 CODE/GRIPHFiTH_minimal/Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m
```

Main PIDL baseline code:

```text
0 CODE/PIDL/SENS_tensile_minimal/config.py
0 CODE/PIDL/SENS_tensile_minimal/main.py
0 CODE/PIDL/SENS_tensile_minimal/run_fem_mesh_umax.py
0 CODE/PIDL/source/
```

## Two Stages Of The Work

The first-year work has two stages. This package mainly preserves the second stage, but the first stage explains why the current alignment diagnostics became necessary.

| Stage | Aim | Typical methods | What it taught us |
|---|---|---|---|
| Stage 1: broad PIDL representation search | Improve NN representation and recover FEM-like fatigue behaviour before the final alignment protocol was fixed. | Williams features, Fourier features, enriched ansatz, exact-BC/Fourier stacks, adaptive sampling, local/tip weighting, weak or oracle supervision, spatial `alpha_T`, fatigue-law variants. | PIDL could often move scalar/event behaviour and some local metrics, but stronger representation alone did not reliably produce FEM-like local fields. This is why `N_f` alone became an unsafe success criterion. |
| Stage 2: strict FEM/PIDL alignment and diagnosis | Remove avoidable FEM/PIDL mismatch first, then compare scalar history and local fields under a controlled baseline. | Monotonic alignment, soft-hist0 reverseBC FEM, FEM cyclic cadence controls, FEM-mesh PIDL, state-timing comparisons, active-driver/history/degradation audits, precrack fatigue-mask diagnostics. | The initial state and broad event window can be aligned, but the active-driver/history/degradation feedback remains different near the crack tip and retained precrack band. |

Older Stage 1 material is not fully copied into this clean package. If needed, it is in the working repository:

```text
upload code/docs/advisor_method_evolution_en.md
upload code/SENS_tensile/
upload code/SENS_tensile/validation_table_all_methods.csv
upload code/SENS_tensile/validation_v4_v7_all_methods.csv
upload code/_analysis_fem_mechanism_20260528/figures/pidl_method_promise_summary_20260529.png
upload code/_analysis_fem_mechanism_20260528/variant_rescore_j0map/
```

The clean package focuses on Stage 2 because it is the closest evidence for the First Year Report conclusion.

## What Was Tried

| Step | Why it was tried | Where to look | Main result |
|---|---|---|---|
| Monotonic FEM/PIDL alignment | Check geometry, loading, mesh convention and boundary conditions before cyclic fatigue. | `1 ALIGNMENT CHECK/Alignment_check_monotonic/ALIGNMENT_AUDIT_FEM_PIDL_MONOTONIC_20260607.md` | Monotonic comparison is substantially aligned. FEM step and PIDL cycle labels differ by one index, but physical displacement states match. |
| FEM cyclic cadence controls | Test whether FEM results are driven by retained loading substeps or unload-state storage. | `1 ALIGNMENT CHECK/Alignment_check2_cyclic/FEM cyclic 012/` | FEM unload-retaining variants fracture at `c69-c70`; `peak_only` is the outlier and does not fracture by `c120`. |
| PIDL one-peak and substep controls | Test whether FEM-like PIDL loading substeps fix the scalar/event or field mismatch. | `1 ALIGNMENT CHECK/Alignment_check2_cyclic/PIDL cyclic 012/` | PIDL one-peak and FEM-like substep runs fracture around `c82`. Substep protocol alone does not close the field-energy mismatch. |
| FEM/PIDL field comparison | Compare the most comparable FEM and PIDL states on a common grid. | `1 ALIGNMENT CHECK/Alignment_check2_cyclic/comparisons/latest_align_state_field_comparison_20260608/` | Initial state is aligned, but crack-surface energy, fatigue history and fatigue degradation diverge. |
| History-driver audits | Check whether the mismatch is only a raw/active driver definition issue. | `1 ALIGNMENT CHECK/Alignment_check2_cyclic/comparisons/latest_align_state_field_comparison_20260608/README_history_driver_definition_audit.md` | Raw `psi+` can be close or even too high in PIDL, while active/degraded driver is too weak in key regions. |
| Precrack fatigue mask | Test whether the old soft precrack band should accumulate fatigue history. | `1 ALIGNMENT CHECK/Alignment_check2_cyclic/comparisons/precrack_fatigue_mask_vs_fem_state_fields_20260609/` | Scalar history increment integrals become closer, but residual fields still show different spatial mechanisms. |
| Representation and training diagnostics | Test whether architecture, local refinement, staging, optimiser polish or scalar `alpha_T` tuning closes the gap. | `0 CODE/PIDL/SENS_tensile_minimal/` runners listed below | These can move scalar/event behaviour, but none has yet produced a convincing FEM-like field mechanism. |
| M2S feasibility | Test whether measurement-to-state/RUL inference is feasible as a framework while keeping the forward-field caveat visible. | `0 CODE/PIDL/SENS_tensile_minimal/run_m2s_next_stage_feasibility.py` | State-driver proxies improve RUL prediction compared with visible-damage-only features, but this is feasibility evidence, not proof of a reliable state estimator. |

## Key Numbers

FEM cyclic cadence:

- Standard FEM `[0.25, 0.5, 0.75, 1, 0]`: fracture/event at `c69`.
- FEM `n_step_2`: event at `c70`.
- FEM `n_step_3`: event at `c70`.
- FEM `n_step_10`: event at `c69`.
- FEM `peak_only`: no fracture by `c120`.

PIDL cyclic controls:

- PIDL one-peak and FEM-like substep runs fracture around `c82`.
- This is the same broad event window, but it is not scalar-identical to FEM.

Latest aligned field comparison:

- Initial state is aligned:
  - damage max: FEM `0.905`, PIDL `0.905`;
  - damage mean: FEM `0.0378045`, PIDL `0.0378045`;
  - `alpha_bar = 0` and `f_fatigue = 1` everywhere in both.
- Crack-surface energy diverges:
  - `E_d` PIDL/FEM ratio is `0.955` at cycle 1,
  - `0.781` at cycle 20,
  - `0.621` at cycle 40,
  - `0.502` at cycle 60,
  - `0.448` at cycle 69.
- Fatigue history/degradation mismatch at `c69`:
  - `alpha_bar_max`: FEM `19.53`, PIDL `2.00`;
  - `f_fatigue_min`: FEM `0.0146`, PIDL `0.170`.
- Raw driver can be misleading:
  - at `c69`, `psi_raw_max` is similar: FEM `2433.7`, PIDL `2638.7`;
  - but `psi_raw_p99` differs strongly: FEM `500.1`, PIDL `0.555`.
- Active/degraded driver is the important gap:
  - `c1` `g psi+ p99`: FEM `0.0358`, PIDL `0.0341`;
  - `c69` `g psi+ p99`: FEM `0.1059`, PIDL `0.0336`.

M2S feasibility:

- Combined trajectories: state-driver RUL MAE `29.03` cycles vs visible-damage tiers around `69-71` cycles.
- Legacy five-Umax stress test: state-driver RUL MAE `34.77` cycles vs damage-only around `82-86` cycles.
- The strict cadence subset is too easy because trajectories are nearly identical, so it should not be over-interpreted.

## Code Guide

PIDL:

```text
0 CODE/PIDL/README_PIDL_MINIMAL_FOR_BRIAN.md
0 CODE/PIDL/source/
0 CODE/PIDL/SENS_tensile_minimal/
```

Useful PIDL runners:

```text
run_fem_mesh_umax.py
run_fem_anchor_bc_umax.py
run_fem_mesh_precrack_fatigue_mask_umax.py
run_fem_mesh_probe_driver_umax.py
run_fem_mesh_history_driver_umax.py
run_fem_mesh_oracle_field_umax.py
run_fem_mesh_staged_alpha_umax.py
run_fem_mesh_inverse_alphaT_umax.py
run_fem_mesh_fbpinn_umax.py
run_fem_mesh_local_patch_umax.py
run_m2s_next_stage_feasibility.py
```

FEM / GRIPHFiTH:

```text
0 CODE/GRIPHFiTH_minimal/README_GRIPHFiTH_MINIMAL_FOR_BRIAN.md
0 CODE/GRIPHFiTH_minimal/Sources/
0 CODE/GRIPHFiTH_minimal/Scripts/fatigue_fracture/
```

Main FEM scripts:

```text
main_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m
INPUT_SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC.m
solve_fatigue_fracture.m
```

## Result Guide

For cyclic alignment, start here:

```text
1 ALIGNMENT CHECK/Alignment_check2_cyclic/README.md
1 ALIGNMENT CHECK/Alignment_check2_cyclic/manifest/cases.csv
1 ALIGNMENT CHECK/Alignment_check2_cyclic/manifest/canonical_outputs.md
```

Most important comparison package:

```text
1 ALIGNMENT CHECK/Alignment_check2_cyclic/comparisons/latest_align_state_field_comparison_20260608/
```

Useful figures:

```text
1 ALIGNMENT CHECK/Alignment_check2_cyclic/FEM cyclic 012/figures/protocol_comparison/fem_loading_step_protocol_metrics_20260608.png
1 ALIGNMENT CHECK/Alignment_check2_cyclic/PIDL cyclic 012/figures/protocol_comparison/standard_fem_vs_aligned_pidl_protocol_metrics_20260608.png
1 ALIGNMENT CHECK/Alignment_check2_cyclic/comparisons/latest_align_state_field_comparison_20260608/figures/energy_histories_latest_aligned.png
1 ALIGNMENT CHECK/Alignment_check2_cyclic/comparisons/latest_align_state_field_comparison_20260608/figures/residual_fields_damage_history_degradation_peak_states.png
1 ALIGNMENT CHECK/Alignment_check2_cyclic/comparisons/latest_align_state_field_comparison_20260608/figures/residual_fields_energy_drivers_peak_states.png
```

For monotonic alignment:

```text
1 ALIGNMENT CHECK/Alignment_check_monotonic/ALIGNMENT_AUDIT_FEM_PIDL_MONOTONIC_20260607.md
```

For writing:

```text
2 WRITING/FYR.pdf
2 WRITING/Overleaf_tex/
```
