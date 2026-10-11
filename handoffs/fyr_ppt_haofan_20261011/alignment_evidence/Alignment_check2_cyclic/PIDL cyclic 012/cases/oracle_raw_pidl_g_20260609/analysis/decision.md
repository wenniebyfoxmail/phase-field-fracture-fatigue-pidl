# Decision

Verdict: mixed

Purpose:
Oracle raw-PIDL-g run: inject FEM raw `psi+` with five-substep load-squared scaling, then multiply by PIDL current `g(alpha)`, to test whether raw energy-driver shape/timing explains the FEM/PIDL gap.

Gate:
The gate requires state-labeled FEM/PIDL comparison of field shape, history/fatigue driver, active driver, incremental energy, mechanics fields, gradient balance, and timing. `N_f` alone is not sufficient.

What improved:
This run recovers the critical timing signal: boundary fracture is first detected at PIDL step `343`, which maps to `c69_peak`, and is confirmed by step `346`. The archive is complete locally, the corrected five-substep mapping is applied, and the regenerated package includes scalar histories, gradient balance, selected fields, FEM/PIDL residual maps, energy-driver residuals, and strain/stress residuals.

What worsened:
The timing match is bought through an over-strong history/driver response. At `c1_peak`, PIDL history max is `3.81955` versus projected FEM max `0.237152`; mean absolute history residual is `0.0165252`. Final gradient balance is still strongly history-dominated: `grad_E_hist=7.347308e+04`, much larger than `grad_E_el=8.719799e+02` and `grad_E_d=9.245477e+01`.

What is still missing:
A verified true unloaded PIDL prehistory state, process-zone overlap metrics, incremental damage-energy comparison, and a loss-weight interpretation of why the raw-driver oracle amplifies history so much.

Next action:
Treat `raw_pidl_g` as evidence that raw driver placement/timing can recover the FEM fracture cycle, but not as a physically clean fix. The next diagnosis should compare where the amplified history field sits relative to FEM process-zone growth.
