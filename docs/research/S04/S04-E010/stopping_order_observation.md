# Limited read-only follow-up

Retrieved Stage0b solve_fatigue_fracture.m shows UV Newton atlines64–77, damage Newton115–128, nodal lower/upper bound enforcement132–135, stag.post_iter_update141–148, and export/historycommit afteracceptance149–196. Therefore metadata res_displ is returned from the UV Newton call before the final damage update; it is not automatically the final accepted-pair residual.

However stag.post_iter_update receives assembly_equilibrium_fh and finaldamage/currentUV. Its exact body is required before deciding whether final residual is recomputed and how it gates acceptance. A read-only SCP of that original helper was blocked by SSH jump-host maintenance. Do not claim the solver omitted an end-point check from the outer caller alone. This follow-up did not affect or modify the completed18-state audit.
