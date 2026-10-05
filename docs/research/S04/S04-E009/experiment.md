---
storyline_id: S04
experiment_id: S04-E009
protocol_revision: 20261005-r0
status: design-pass; code-review-pending
---
# Restored c20/c40 native FEM peak audit

Purpose: distinguish early/middle teacher residuals from late peaks using restored original accepted priors and MATLAB endpoint vectors. User approved continuing missing-asset recovery.

Five questions: mechanism=whether residual discrepancy exists at c20/c40; success adds qualified original-state comparison; failure preserves admission/solve failure; cheapest archive recovery completed, no trajectory replay needed; minimal asset metrics/decision; endpoint inventory plus S04 storyline.

Inputs locked in input_lock.json and asset_admission.json. Original producer citpc12 read-only recovery. c20/c40 current fields match sealed Request29 v3 postcommit current fields exactly; that file mesh matches E003 exactly. Postcommit is never used as predecessor. Own native pre_phase_input accepted old and hist agree with own oracle. Early c0→c40 replay is distinct from late c0→c83 replay, same source/config but not same execution. Prior anchor equality supports compared states only.

Reuse E008 numerical definitions, full pre-solve three vector checks1e-9, strict damage/prior feasibility, BC and quadrature, raw hardKKT4e-4 migration, normalized UV/box1e-3. Coefficient reconstructed once at original target then frozen. Full baseline is saved before any gate. If original rho_u<=1e-3: UV_SCREEN_PASS_NO_SOLVE, corrections null (not zero). Otherwise one unchanged E008 solve at most50iterations; independently check endpointforce, pivot/residual/BC/damage/prior/coefficient invariants. No damage solve, no fatigue refresh/historycommit, no training, no changed threshold or rescue.

D-26-09 authorized producer, CPUfloat64 one thread, Condor allocation8CPU32GB1GPU (GPUunused as required by scheduler). Two states maximum, fresh RunID. Mac smalltests and archived-array checks only. Five original peak residuals may be compared with replay labels; correction trends include only actually solved points. Fullteacher always NOT_QUALIFIED. Newly found Stage0b all-substep files are separate candidate assets, not automatically native-oracle qualified or included in E009 numerical run.
