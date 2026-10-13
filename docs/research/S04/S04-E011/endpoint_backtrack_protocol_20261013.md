# Joint fixed-point backtracking discriminator — 2026-10-13

Mechanism question: does continued damage/displacement coupling generate a direction which can reduce the native same-field feasible residual when the full step grows it? This is a numerical diagnostic, not a teacher or physical truth claim. Original E003/E011 and the completed tight arm remain frozen.

Cheaper check: offline outer20–30 native field localization and exact symmetric raw/degradation active decomposition, with separate residual maps. Cross replay is not a solved counterfactual; spatial co-location does not establish causality. Minimal asset: spatial map/CSV, trial receipt and accepted-endpoint table, decision and user report.

Admission: exact original s3 predecessor, native Q4 GP4 and archived same-cycle peak hashes; reproduce original settings and archived stopping iteration, fields maxabs1e-10/relative1e-8 and native ru/rd maxerr1e-10. At c83 the first complete tight candidate must also reproduce the previous tight outer21 fields/residuals within1e-10. Failures stop that state before attribution.

Controls fixed to the previous tight arm: inner u1e-8, damage4e-6, caps250/250, eta0, accepted s3 history/damage, peakU.11999988. Direction generated exactly once per outer attempt by native u→d block solves. Joint convex interpolation uses lambda=1,1/2,...1/64. Each trial recomputes native raw strain energy, trial-fatigue residual and tangent at its own u/d; no candidate raw field is reused for damped trials. Prescribed peak BC and d_s3≤d≤1 verified. Accepted tangent refreshed; all rejected trial state/history/cache mutations discarded. No history commit or later load step.

Merit M=||R_u,free||2+||R_d,nodal-monotone||2. Accept first trial with M_trial≤(1−1e-4 lambda)M_current, or screen M≤4e-6. This is sufficient-decrease fixed-point backtracking, not a proven Armijo gradient method. PIDL agreement and energy are never acceptance criteria. Nonsmooth bound projection and non-descent directions can cause stall.

Budget: at most10 outer attempts and7 trial evaluations/attempt, original innercaps. No accepted trial within7→NO_ADMISSIBLE_DESCENT_WITHIN_TRIAL_BUDGET. Preserve current accepted numerical iterate plus rejected trials; do not extend budget automatically. Nonfinite/identity/bounds/BC violation or inner failure stops. Screen PASS only numerical monitor; exhausted budget/stall not proof no equilibrium exists.

Sequence: c83 implementation/direction admission first. Then identical controls at predeclared earlier peaks c1,c20,c60,c76,c82, each from its own archived s3, unchanged baseline admission. This is a sparse mechanism-state grid, not independent trajectories or onset-cycle identification. Missing/failed baseline marks cycle inadmissible, no substitution selected by outcome. Compare same-cycle original FEM and original Q4 PIDL (step5*c−1), with exact state labels; accepted extra iterates are not post-history physical states.

Outcome: residual improves but active gap persists→coupled stationarity control alone does not close field discrepancy at this budget/state. Both improve→descriptive contribution at this state, not all-cycle attribution or truth. Stall→direction/merit route unclosed at declared trials. Registry and mesh对齐.md own result handoff. Independent design/source/result review required.

Review: independent local reviewer adopted joint direction once, per-trial raw refresh, accepted tangent restoration, no energy gate, stall preservation and sparse early-cycle grid. External ChatGPT request made to the previous review conversation, but response failed cloudflare_challenge and browser then became unavailable; no verified GPT Pro advice is claimed. No external model advice is included in the decision. Execution follows the user’s direct authorization with independent exact-source review and numerical admission gates.


Closed 2026-10-13: all six states completed, no added budget/history commits. [Terminal result](runs/endpoint_backtrack_grid_20261013.md), [compact metrics](runs/endpoint_backtrack_grid_metrics_20261013.csv). Baselines/direction/hash/state/trial gates and independent review PASS; no state reached4e-6.
