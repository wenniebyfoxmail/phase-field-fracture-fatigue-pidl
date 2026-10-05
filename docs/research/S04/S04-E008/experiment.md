---
storyline_id: S04
experiment_id: S04-E008
protocol_revision: 20261005-r0
status: design-pass; exact-code-review-pending
---
# Fixed-FEM-damage UV precision at c76 and c82

Purpose: following hard-bound KKT alignment, quantify corrections needed for the original c76/c82 FEM fields to pass the common UV screen. S04-E007 found native rho_u1.01373/1.35335, while nodal hard-KKT migration screens pass. These residuals alone do not quantify field error.

Five-question gate: mechanism=UV residual sensitivity versus field correction; success qualifies only fixed-damage UV; failure preserves numerical failure; cheapest diagnostic E007 completed; minimal assets before/after scalars and field corrections; registry S04 storyline plus experiment inventory. User approved this staged sequence. No new damage solve, history commit, fatigue refresh, long trajectory or neural training.

Reuse E006 reviewed algorithm, tolerances, initialization, BC and diagnostic norms exactly. Two states only, each from identity-locked native c76/c82 captures on common geometry from E003 qualified_fields. Reconstruct each own original-target trial fatigue from pre_phase_input/history_vars_old plus original current active driver as in E003; freeze it across UV correction. Correct accepted nodal prior from p_field_old, never last stagger trial p_field or postcommit history. Compare original native full/free UV and damage residuals against recomputed energy gradients before solving; vector gate1e-9. Preserve failed before/after values in JSON before gate failure.

E1 nu.3 ell.01 Gc.01 eta0 t1 Us.11999988 H1. Native GP(++,-+,+-,--) and solver permutation[2,3,1,0], assert N/det. Sparse AMOR at most50 iterations, update1e-9, internal force1e-8, pivot1e-14, original FEM UV initialization, first successful return. Final independently reconstructed NumPy/Torch force agreement1e-9 and scientific rho_u<=1e-3. No stabilization, removed nodes, hidden retry or threshold change.

Continuous corrections: whole-domain mass RMS(delta UV)/Us; tensor strain and active-driver GP weighted relativeL2; original positive weighted-p99 support and area. E006 diagnostic nominal floor1e-12 unchanged. Report box and hard-bound KKT at original/corrected UV using the SAME frozen coefficient; hard-KKT uses E007 classifier and4e-4 migration screen only. Original fatigue consistency checks apply to original field; corrected field is explicitly not refreshed. Complete teacher always NOT_QUALIFIED.

Mac development and small sanity only. Actual two solves on user-authorized D-26-09 via HTCondor, private existing runtime, CPUfloat64 one thread. Outputs retain state identity and run receipt. Early/mid/cycle-internal missing evidence remains NOT_EVALUABLE, not extrapolated from these two peaks.
