# Read-only cross-residual protocol — frozen 2026-10-05

Scope: approved user request, a pre-optimization subset of S04-E002. No network, optimizer, solve, trial or commit. External Pro final DESIGN PASS is now visible at https://chatgpt.com/c/6ac2e1ce-9940-83ed-a562-b17182126205 (earlier delivery records remain historical). Adopt the independent-leaf residual definition and 1e-3 practical stationarity screen, not a physical-accuracy theorem.

Inputs are the previously locked FEM c83s004 and PIDL checkpoint413. Existing input manifest verified. Accepted damage is clipped once at nodes; frozen fatigue map is evaluated with production float32 checkpoint and production function, then promoted for float64 derivative audit. Other checkpoint histories are read-only, not used to rebuild fatigue. All Q4 geometry and target fields stay native float64. Unit thickness, E1 nu0.3 w1=1 ell0.01 AT1 volumetric eta0 tol_ir0.005, gamma=16875. Existing compute_energy.py retained unchanged.

Mass fraction M_i = sum(detJ*N_i)/A. U_s=.11999988; E_s=A*E*(U_s/H)^2. Independent target nodal leaf gradients: g_u=U_s/E_s*dE/du; g_d=(dE/dd)/E_s. rho_u=sqrt(sum_free(g_u^2/M_i)), excluding only both UV components on top/bottom. Damage has no fixed DOFs; rho_d=sqrt(sum(M_i*(d-clip(d-g_d/M_i,0,1))^2)). Box is[0,1], not[d_prev,1]; healing scored separately atGP. Two total residuals<=1e-3 yields REFERENCE_STATIONARY, else REFERENCE_NONSTATIONARY. Components carry raw gradients, energies and dual norms; their projected norms are nonadditive diagnostics.

Test: float64 distorted-Q4 directional derivatives of each energy term against central differences, normalized error<1e-5, with smooth test fields; mass positivity/unit sum; box KKT signs; component gradient sum; frozen histories; elastic independence of fatigue and damage history. Stop on identity/BC/mass failure, nonfinite values, gradient mismatch or history mutation. No residual-based stop or re-optimization.

FEM previous-state control: searched exact-peak v2.1, canonical Hard5 formal run, local_archive and Downloads/_pidl_handoff_v2 for c83s003. No qualified preceding snapshot found. README explicitly marks all peak data and history_vars_old post-history-commit. Exclude them as a preceding-state control. No fabricated FEM history and no attribution to history alone.

Reviewer arithmetic U413=.08999991 is not adopted: actual production log says .08999988, from the explicit schedule. No optimizer settings are adopted in this audit.

Primary output: residual_components.csv, summary.json, residual_fields.npz. Frozen component gradients permit later spatial localization without another solve. Scientific scope: compatibility of one fixed FEM field with this exact projected-history PIDL objective; no capacity or trajectory claim.
