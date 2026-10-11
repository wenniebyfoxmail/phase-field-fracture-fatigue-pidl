# Per-Step FEM Damage Fields Needed

The current Umax0.2 FEM handoff does not contain enough field data to generate
true damage figures for every monotonic load step.

## What Is Present Locally

For each available Umax0.2 case:

- `fields_000001_024.vtk`: final load step only, `cycle=1`, `step=24`.
- `peak_load_c1.vtk`: peak-load snapshot only.
- `checkpoint.mat`: final state only.
- `psi_fields/cycle_0001.mat`: one final cycle summary only.
- `CONV_...steps00001.log` to `CONV_...steps00024.log`: convergence logs only,
  not damage fields.

Low-level VTK check: each `fields_000001_024.vtk` has one `POINT_DATA` block and
one `SCALARS d` block, so it cannot be split into 24 damage snapshots.

## Required Files

To render one damage figure per load step for the Umax0.2 cases, each case needs
the following 24 VTK files:

```text
fields_000001_001.vtk
fields_000001_002.vtk
...
fields_000001_024.vtk
```

The existing Python renderer will render the damage field for every `fields_*.vtk`
file once these VTKs are placed in each case's `_source/resources/` folder.

## FEM Export Issue

In `solve_fatigue_fracture.m`, `vtk_freq = 1` writes once per cycle because the
VTK output block is after the load-step loop. For the monotonic Umax0.2 setup,
there is one cycle with 24 load steps, so the current export writes only
`fields_000001_024.vtk`.

To obtain true per-step damage figures, the FEM run must either:

- write `paraview_step(...)` inside the `for i_step = 1:SOL_STEP_PAR.n_step`
  loop after each converged step, or
- save per-step `p_field`/state checkpoints that can later be converted to VTK.

Do not generate per-step figures by copying or interpolating the final damage
field; that would not be a valid FEM result.
