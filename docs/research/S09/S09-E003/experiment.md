---
storyline_id: S09
experiment_id: S09-E003
protocol_revision: v1-equilibrium-pinn-c0
status: prepared
---
# FEM-aligned physics loss: native audit and fixed-damage PINN probe

User 2026-10-09 requests trying PINN physics by checking FEM constraints.
Owner S09-E003; branch codex/s09-e003-fem-physics-20261009, base 95ec8fd13d9b4402edcbed693398a6dd79599d54.
Scope new s09_fem_physics, copied/renamed s09_q4_quadrature from ad749c8, new runner/tests and this experiment. Existing S09 models/runs unchanged. No shared dirty checkout edits.

## Frozen question and scope

C0 synthetic diagnostic: can a neural displacement field reduce the correctly assembled FEM AMOR free-force residual with fixed native damage and exact imposed displacement BCs? This is a one-state weak-form PINN, not an operator training experiment, not damage forecasting. The eventual GNO physics arm needs nodal u,d outputs and native GP state; current element-mean S09 tensors cannot be substituted.

Reference: first chronologically available preselected native anchor, U012 c76 s4 from S04-E001 archived native Q4 package. 86756 nodes,86408 Q4 elements. No target u labels enter training. Reference u/psi/g/strain are used for preflight identity and diagnostic comparisons only. Frozen d and effective applied displacement define the conditional mechanics problem. No prediction origin/horizon or heldout claim. Source snapshot is unqualified as a full teacher; native equilibrium residual is reported, never presumed zero.

## Physics identity

GRIPHFiTH local source b680bb0, clean: INPUT_SENS_tensile.m selects AMOR, AT1, PENALTY, plane strain E=1 nu=.3 Gc=.01 ell=.01. Actual Hard5 pre-run lock eta=0, alpha_T=.5, nominal five substeps .25,.5,.75,1,0; effective load differs by 1e-6 in load factor. Use actual native displacement BC value, not nominal .12.

AMOR: g=(1-d)^2+eta; psi+=K/2<tr eps>_+^2+mu eps_dev:eps_dev; negative volumetric energy undegraded. Assemble Ru=int B^T sigma dOmega; sum assembled nodal forces once, select free DOFs, no repeated area weighting. Bottom u=v=0; top u=0,v=U; sides natural zero traction. d is frozen exactly, no clipping; natural notch is diffuse damage, no void edges.

AT1 penalty residual implemented/tested separately: int N[2 psi(d-1)+3Gc f/(8ell)+gamma_i min(d-dold,0)+gamma_r min(d,0)]+3Gc ell/4 f gradN.grad d. GP psi,f held fixed in phase partial derivative. This is penalty residual, not hard-KKT; history-field variant is a separate method. Native phase is NOT trained/audited here because correct old nodal damage and trial/accepted substep timing must be bound separately. No forced zero unconstrained residual on legal hard-constrained stagnation.

Fatigue trial: q=g(d)psi; alpha_new=alpha_old+max(q-q_old,0); f=min(1,(2alpha_T/(alpha+alpha_T))^p). Re-evaluate from immutable accepted old state. Peak differences cannot replace all loading substeps. Nonlinear GP averaging cannot be reversed.

## Validity and execution

Native audit rel L2 psi/g/strain and max abs d_GP/Dirichlet <=1e-8 in float64. This checks implementation/export consistency, not equilibrium/teacher qualification. Unit checks: force=energy derivative in tension/compression, phase=energy derivative with frozen coefficients/penalties, immutable fatigue, nonzero network gradient and exact BCs. Independent code review bound to exact execution commit required.

Taobo GPUServer8 only, one GPU fresh preflight, .33 memory fraction, float64, seed1. Tanh 2->64->64->64->2 displacement PINN with zero last layer. Hard ansatz u=(0,U t)+U t(1-t)NN(x,y). Full native mesh each update; Adam lr.001, clip10, 500 updates fixed, assessments every25. No retries/tuning after scientific FAIL. Native u is NEVER a target in loss. Pure affine BC field is initial baseline.

One primary operational criterion: FINAL free-force RMS / initial affine free-force RMS <=.8 (20% diagnostic reduction, not numerical tolerance). No first-pass stop or best-checkpoint rescue. Best fields saved for labelled diagnostics, final metric authoritative. NaN/invalid identity/resource failure stops. No automatic extra seeds/arms.

Minimum evidence: native audit, receipt/config/code identity, all21 evaluated scores, final metrics, best checkpoint/fields, residual history vs affine and .8 plus full-domain u/native/difference plot, README_analysis; independent evidence review. Training and physics behavior remain distinct; neither this nor a residual decrease licenses generalization, crack growth, exact equilibrium, PINO superiority, or full FEM teacher claims.
