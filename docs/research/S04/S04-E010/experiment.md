---
storyline_id: S04
experiment_id: S04-E010
protocol_revision: 20261005-r0
status: complete; evidence-pass; teacher-not-qualified
---
# Reconstructed native-Q4 residuals across six cycles and three substeps

Purpose: extend the SAME mathematical residual definitions to c20/c40/c60/c76/c82/c83 at s2 loading, s4 peak, s5 unloaded, using each own immediately previous ACCEPTED state s1/s3/s4. This is FEM-own-history diagnosis, not a cross-PIDL-history audit.

Five-question gate: mechanism=cycle/phase dependence of original teacher residuals; success=18-state reconstructed screen, not complete teacher; failure=preserved bridge/input mismatch, no trend conclusion; cheaper=read-only archive recovery and existing original-native overlaps; minimal=CSV, decision, evidence-kind labels, vectors; registry=S04 and inventory. No production trajectory, no training or any nonlinear solve.

Sources: sealed Stage0b53ce560 replay,30 selected state payloads hash-matched state_index; static original native mesh/GP/material/free sets exact versus E003. input_manifest.json is identity locked in runner. Five peaks20/40/76/82/83 have original MATLAB endpoint vectors from two cdf4e337 replay exports. Currentu/d and acceptedprevd/history channels2:4 exactly coincide at these five overlaps. New slot1 is current raw tensile energy, documented source output-only addition; never used in this penalty objective and never renamed maximum-history H. Source patch and differences retained. Equality claims apply to checked fields/states, not all unobserved trajectory data.

Admission: verify all files, state_index hashes and convergence/timing plus numeric cycle/substep/load. Use own previous payload; never target postcommit as previous. Strict0<=previous<=damage<=1 is necessary for omitted healing penalty; any violation refuses evaluation. Crack fixed values are checked by hardKKT. Actual imposed BC per substep, but Us=.11999988 and Es=area*Us² at every state including unload; no division by zero load. E1nu.3Gc.01ell.01eta0,cw8/3,t1. HDF Nxi is already GP×node; native order(++,-+,+-,--) verified without transpose.

New independent NumPy AT1 damage weak assembly: frozen fatigue, elastic -2(1-dGP)psi*N, fracture Gc/cw*f*(N/ell+2ell gradN dot gradd), no penalty only after strictfeasibility. Small tension/compression/shear AD and directional finite-difference tests plus infeasible-state rejection precede execution. Existing independent NumPyUV weak form and Torch energy unchanged.

ALL five known peaks must pass nativeMATLAB vs NumPy and Torch freeUV/freeDamage vector gates1e-9 plus samefield/prior identity before any new point. Every new point independently checks NumPy vs Torch UV/damage1e-9. Save each row and vectors before numerical gate verdict; any failed agreement terminates run and blocks full18-state trend, retains completed rows. Failure file cannot erase evidence. All files/outputs disjoint and fresh.

Screens unchanged: rho_u and box massRMS1e-3, hardKKT rawL2 migration4e-4, original boundtol1e-12 with exactfeasibility mandatory; hard normalized map has no threshold. Fatigue reconstructed from originaltarget+acceptedalpha/qprev once, frozen. No UVsolve, no damage solve, no historycommit, no training. Record original phase/raw stopping scalars separately from reconstructed values; these are not interchangeable.

Evidence labels: five bridges archived_MATLAB_bridge;13newpoints reconstructed_not_archived_MATLAB and archived_oracle_gate=NOT_AVAILABLE. Passing bridge/numerical reconstruction never promotes originaloracle qualification. All fullteacher NOT_QUALIFIED. Tables use same definitions but preserve this evidence distinction. Trends descriptive over sampled cycle×substeps only; no causal onset/monotonic/fulltrajectory claim. D-26-09 CPUfloat64,one thread,8CPU32GB1GPUallocation (GPUunused),fresh run only after Design/CodeReady.

Design clarification: raw psi is independently computed from original UV, not active energy or slot1. Fatigue is the original target-point trial coefficient, not prior/target committedf; its array is retained and detached from AD. Physical screen FAIL does not stop or discard a valid observation; only identity/feasibility/implementation gate failure blocks trend. box_01_original is an explicit output alias retaining original [0,1] values, not hardbound KKT.
