---
storyline_id: S04
experiment_id: S04-E003
protocol_revision: 20261005-r1-frozen
status: design-pass; code-review-pending
---
# Same-field FEM weak-form / PIDL gradient and qualified history controls

Purpose: separate operator inconsistency from nonstationarity of the same c83 s4 FEM fields. Goal: compare archived original MATLAB/MEX free-displacement weak residual vectors with PIDL physical-node energy derivatives, then isolate damage-history/fatigue-history substitutions without updating any state. Steps: qualify source/fields/DOFs and precommit timing; freeze design; patch tests and exact-commit independent review; Windows CPU audit; evidence review and register outcome. No new FEM solve, neural training or history commit.

## Input qualification (new evidence, 2026-10-05)

S04-E002's earlier search missed the v1 `native_q4/` record. It is now found, not generated: `hard5_u012_exact_peak_native_q4_c76_c82_c83_20260821_v1/native_q4/cycle_0083_peak_native_q4.mat`. Its current u,v,d match v2.1 target exactly; v1 mesh coordinates/connectivity also match exactly. Same replay root C:/q4runs/request27_u012_exact_peak_c76_c82_c83_20260821_v1, solver cdf4e33710455606421806dfe6ff84ae09378d6b. Native file SHA256 e4270ebd45bf35703dffa8375c2d9b474bdceb303448ddfa6d5fc453956309d4, size34251696. Qualified input receipt: project-root local_archive/experiments/S04-E003/input_qualification.json.

`pre_phase_input/p_field_old` is the prior accepted damage, not `pre_phase_input/p_field` (last staggered iterate). `history_vars_old` is copied before the final accepted phase solve; both are unchanged until after the residual oracle is captured. Source solve_fatigue_fracture.m lines87–180 capture and save,183–194 commit. Oracle copies match those pre-phase fields exactly. Source capture_peak_state.m explicitly distinguishes timing. This qualifies prior history through state/call lineage, not merely a precommit filename. The v2.1 postcommit history remains unsuitable as a predecessor.

## Locked model and comparison

Archived INPUT_SENS + native capture driver: E1,nu.3,Gc.01,ell.01,plane strain,unit thickness,AMOR,eta0,AT1; only displacement loading, no Neumann load. Top/bottom UV DOFs are verified against archived free_u IDs. Original blocked [all u, all v] ordering is converted explicitly. Both oracle R_u and PIDL derivative use internal-minus-external convention (external zero). All original R_u arrays and partitions are preserved.

Primary: mass-dual norm of the **difference vector** on identical free UV IDs, divided by max(reference mass-dual norm,Es/Us), <=1e-9; Es=A*E*(Us/H)^2,Us=.11999988,H1. This nominal-floor convention is an implementation consistency gate, not a mechanics accuracy claim. Report raw max difference, L2 and full-vector comparison too. Independent NumPy Q4/AMOR assembly is a supplementary three-way comparator; it is not execution of the original MEX. Keep prior mass-normalized stationarity screen1e-3 separate.

History diagnostic: four fixed-field arms crossing {projected PIDL413 dprev,FEM accepted dprev} and {PIDL fprev,FEM f(alpha_prev)}; fifth arm FEM dprev with ftrial evaluated at the target and then frozen. Preserve PIDL coefficient16875 and original float32 PIDL fatigue-map then double. FEM fprev/ftrial use original double field/Fortran formula; preserve and compare stored f slot4. Do not differentiate through ftrial: it diagnoses the frozen-coefficient weak residual, not the full derivative of an energy containing f(d). No hard no-healing projection or retuning.

Report box-damage residual on all86756 PIDL damage nodes AND the86505 FEM free nodes. FEM's251 fixed crack nodes are excluded only in the common-free diagnostic, not silently removed from the original PIDL contract. FEM default penalty421875 is distinct from PIDL16875; damage-oracle comparison remains diagnostic until penalty activity/other terms are accounted for. No ratio of projected norms is a causal percentage.

## Gates and outcomes

Strict validity: exact input/mesh/field/cycle/substep/order/DOF identity, precommit qualification, finite values, unchanged histories. Invalid assets stop; do not substitute a cycle-end field. Four small distorted-Q4 tension/compression/shear/rigid tests and three existing energy/history tests must pass. Run on user-authorized D-26-09 via fresh Condor run; Mac development/light patch tests only.

Primary PASS supports same-field UV operator consistency, even if both residuals fail stationarity. FAIL needs implementation/model localization before mechanics attribution. History controls describe a fixed-field intervention only, not a new physically evolved trajectory. Minimal assets: comparison JSON, history table, source/input receipt, spatial diagnostic and decision. Registry: docs/pidl_experiment_inventory.md. Storyline:S04.

## Adopted design review (2026-10-05)

Pro final DESIGN PASS,9m48s, same review URL as E002. Five arms and direct archived-MEX UV primary accepted. Old fields checked through whole step: passed as intent(in) to Fortran, separate history_vars_new output, MATLAB value copies, committed only after oracle; source zip hash locked in qualification receipt. No Dirichlet row rewriting in oracle; raw assembled R_u minus load is partitioned only. Zero external load follows locked INPUT_SENS boundary construction and pre_iter_update zero-Neumann branch; no separately serialized RHS array is claimed. Primary vector comparison preserves sign from source. FEM penalty421875 is source default, runtime scalar not independently serialized/verified. Damage-oracle difference has no PASS/FAIL classification. Check raw damage-gradient four-arm interaction≈0 and identical UV gradients; retain same total-area masses on subsets. ftrial is one read-only evaluation, no state advance or commit; compare to postcommit stored f only as additional timing/formula corroboration, not a substitute for prior fields. No claim of full derivative through f(d).
