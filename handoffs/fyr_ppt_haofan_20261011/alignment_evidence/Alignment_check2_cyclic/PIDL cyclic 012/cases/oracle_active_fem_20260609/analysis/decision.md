# Decision

Verdict: negative

Purpose:
Oracle active-FEM run: inject FEM active driver `g(alpha_FEM) * psi_raw_FEM` with five-substep load-squared scaling to test whether fully FEM-shaped active energy-driver forcing explains the FEM/PIDL gap.

Gate:
The gate requires state-labeled FEM/PIDL comparison of field shape, history/fatigue driver, active driver, incremental energy, mechanics fields, gradient balance, and timing. `N_f` alone is not sufficient.

What improved:
The early history/driver field is much closer than the raw-PIDL-g oracle. At `c1_peak`, PIDL history max is `0.248798` versus projected FEM max `0.237152`, with mean absolute history residual `0.00102867`. The archive is complete locally, the corrected five-substep mapping is applied, and the regenerated package includes strain/stress residuals as required.

What worsened:
The run does not recover the FEM failure event. It completes PIDL step `399` without boundary fracture in the final log tail; final `alpha_max@bdy=-0.0012` and `N_bdy>0.95=0`. The final gradient balance remains history-dominated, with `grad_E_hist=7.315385e+04`.

What is still missing:
A true unloaded PIDL prehistory state, process-zone overlap metrics, incremental damage-energy comparison, and a check of whether the active-driver oracle under-feeds the boundary/tip region after early cycles.

Next action:
Treat `active_fem` as a useful negative test: matching the active driver more cleanly at c1 is not sufficient to reproduce FEM c69 fracture. The remaining gap likely involves later localization, degradation feedback, or damage/history update coupling rather than only the scalar active-driver field.
