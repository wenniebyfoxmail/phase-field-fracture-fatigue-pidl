---
storyline_id: S04
experiment_id: S04-E006
protocol_revision: 20261005-r0
status: completed-diagnostic; conditional-UV-pass; full-teacher-unqualified
---
# FEM teacher fixed-damage displacement precision

Purpose: measure the correction required to reach displacement equilibrium for the frozen c83 s4 FEM damage. Goal: distinguish operator-consistent residual from field sensitivity, without certifying a coupled teacher or changing prior gates. Steps: source/input qualification; reviewed protocol and exact code; small tests; Windows fixed-damage sparse solve; independent residual and field-change audit; evidence review and register.

## Five-question gate

Mechanism: how much does the archived FEM displacement/strain/active driver change when re-equilibrated at the same FEM damage? Success supports only conditional UV accuracy characterization; failure leaves that block unqualified. Cheaper E003 already establishes weak-form/energy-gradient consistency. E001 solved PIDL damage, not this FEM damage, so its numerical results cannot answer this question. Minimal assets: before/after table, field correction figure, decision, provenance. Registry: pidl_experiment_inventory, S04 storyline.

S04-E004 exists on a separate worktree and stopped at its original admission gate; this experiment neither modifies nor bypasses that coupled-solver protocol. S04-E005 is the separately requested cross-cycle audit.

## Frozen contract

Reuse E003 native c83s4 current field, mesh, qualified prior damage and target-point ftrial. Source of prior and fatigue is the immutable E003 fields.npz (SHA256 ecee498054293f66c881a7bcf08a51b1b0315b4e2d11fa20a50c7bbe204f16c5). Original E002 manifest/audit locks normalized target. Histories and damage remain unchanged. No fatigue refresh, no damage solve, no history commit, no neural training. The resulting state is a conditional displacement equilibrium, not a new accepted coupled state.

E1 nu.3 plane strain t1 eta0 U=.11999988. Reuse existing sparse AMOR solver, at most50 iterations, update1e-9, solver relative-force tolerance1e-8, minimum pivot ratio1e-14. No eta rescue, row removal or hidden retry. Solver starts at archived FEM displacement through an optional initial_displacement argument; the default existing affine path is unchanged. Its internal force normalization is not the scientific screen.

Preserve E003 scientific rho_u = sqrt(sum((g_u Us/Es)^2/mass)) on common free UV DOFs, Us=.11999988 and Es=area*E*(Us/H)^2, H1. Primary block gate rho_u<=1e-3, unchanged. At both states require independent NumPy/Torch difference-vector consistency<=1e-9 under the original nominal-force denominator. GP order solver(--,+-,++,-+) is mapped to native(++,-+,+-,--) by [2,3,1,0], with explicit shape/det assertions. Retain same BC and all mesh nodes. Failure produces a failure receipt, not a qualified result.

Report nodal-mass RMS(delta u)/Us, quadrature-weighted tensor-strain relative L2 (engineering shear squared weighted by1/2), quadrature active-driver relative L2, and active error restricted to the ORIGINAL field's weighted p99 mask. Quantile is weighted left inverse CDF, mask includes ties but requires positive original active; report actual mask area. Save error/reference norms; if reference norm<=1e-12 times nominal norm, divide by nominal and label nominal_scale. Nominal strain norm=(Us/H)*sqrt(area); active norm=E*(Us/H)^2*sqrt(area), with subset area on p99. This pre-run diagnostic floor is new, not a change to scientific residual gates. Empty support is unavailable. No new field-accuracy acceptance thresholds: these are continuous corrections, not error against physical truth. Report elastic energy before/after.

Damage box residual uses unchanged original-target ftrial at both displacements, all86756 nodes and common86505 FEM free nodes with original total-domain masses. This does not differentiate fatigue evolution or certify its fixed point. Full FEM teacher remains NOT_QUALIFIED by this UV-only experiment, independent of UV outcome. No mesh/time-step convergence, trajectory or uniqueness claim.

## Original stopping semantics

Archived cdf4e337 post_iter_update.m: norm_res_displ=norm(res_displ(active_dof)); lines92–97 store raw displacement/phase residuals and stop on their sum<=SOL_STAG_PAR.tol. This differs from the present mass-normalized screen. Current archived weak residual is not a newly serialized exact solver-stop receipt for every block; do not claim a tolerance-only causal explanation.

Additional source observation: solve_fatigue_fracture.m obtains res_pf from the phase Newton call, then applies max(p,p_old) and optional upper clipping before post_iter_update. That function reassembles UV but carries res_pf into the stop sum. Therefore the stored acceptance scalar is not automatically the post-clipping, target-point-fatigue, box-projected damage residual audited here. This source fact motivates future endpoint certification; its quantitative contribution is not identified by this UV-only test.

## Completed

R001/Condor63, c543b1d, exit0,21 tests PASS,6 retrieval hashes match. Conditional UV screenPASS, damage screenFAIL; full teacherNOT_QUALIFIED. See decision.md/summary.json/metrics.csv/run_receipt.md. Visualization-only scaling update after execution does not alter numerical results.
