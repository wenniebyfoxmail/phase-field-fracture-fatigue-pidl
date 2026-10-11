# Decision

Verdict: negative

Purpose:
Oracle delta-alpha-bar run: inject FEM-projected cycle-wise `Delta alpha_bar` only at peak substeps to test whether history/fatigue accumulation increments explain the FEM/PIDL gap without scaling irreversible fields.

Gate:
The gate requires state-labeled FEM/PIDL comparison of field shape, history/fatigue driver, active driver, incremental energy, mechanics fields, gradient balance, and timing. `N_f` alone is not sufficient.

What improved:
The intended injected quantity is almost exactly aligned at `c1_peak`: PIDL history max is `0.237152` versus projected FEM max `0.237152`, with mean absolute history residual `1.74102e-10`. This confirms the projection/injection machinery is working for `Delta alpha_bar`. The archive is complete locally, the corrected five-substep mapping is applied, and the regenerated package includes strain/stress residuals.

What worsened:
Perfect early history increment alignment does not recover the FEM failure event. The run completes PIDL step `399` without boundary fracture in the final log tail; final `alpha_max@bdy=0.2599` and `N_bdy>0.95=0`. The final gradient balance remains history-dominated, with `grad_E_hist=7.158979e+04`.

What is still missing:
A true unloaded PIDL prehistory state, process-zone overlap metrics, incremental damage-energy comparison, and later-cycle checks of whether injected history increments produce the correct stiffness redistribution and crack-tip stress localization.

Next action:
Treat `delta_alpha_bar` as a clean negative control: FEM history increments alone are not enough. The next oracle should target the coupled loop after history update, especially stress/strain localization and degradation feedback into the next peak state.
