# Decision

Verdict: mixed, corrected counter mapping applied and residual diagnostics regenerated

Purpose:
Strict aligned-coarse FEM-mesh probe-driver rerun with stress/strain mapped states and pre-history-refresh E_el/E_d/E_hist gradient diagnostics.

Gate:
The gate requires state-labeled FEM/PIDL comparison of field shape, history/fatigue
driver, active driver, incremental energy, mechanics fields, gradient balance, and
timing. `N_f` alone is not sufficient.

What improved:
The previous analysis outputs were deleted and regenerated from source data using
the explicit mapping `cN_peak -> PIDL step 5*(N-1)+3` and
`cN_unloaded -> PIDL step 5*(N-1)+4`. The c1/c69 counter ambiguity is resolved.
The package now includes a c1 fatigue-driver mask audit in addition to peak-state
FEM/PIDL residual maps.

What worsened:
The corrected mapping does not make the mechanism fully agree. At c1 peak,
fatigue factor matches because both fields are still 1, but the history/fatigue
driver has PIDL max `0.286676` versus projected FEM
max `0.237152` and mean absolute residual
`0.000422505`. The final gradient balance remains
history-dominated with `grad_E_hist = 7.749828e+04`.

What is still missing:
A verified true PIDL unloaded prehistory state, overlap/process-zone metrics,
polished peak and unloaded residual figures for all mechanics quantities,
incremental damage-energy comparison, and loss-weight interpretation.

Next action:
Use the regenerated state-mapped diagnostics as the clean case record. For the
cycle-one mask question, treat the fatigue factor as matching at c1, but do not
claim the history/active driver itself is absent near the precrack.
