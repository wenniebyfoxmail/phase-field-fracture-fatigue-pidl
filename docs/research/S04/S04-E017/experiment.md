---
storyline_id: S04
experiment_id: S04-E017
protocol_revision: 20261012-r1-alpha-screen
status: completed-evidence-pass
---
# Unbiased damage-stratified sampling ratio comparison

## Purpose and evidence scope

Test whether reducing damage-zone batch allocation from 90% improves the
conditional two-component displacement fit across early, middle and transition
states while preserving the supervised full-field mass-weighted objective.
Synthetic, within-reference supervised optimization diagnostic; no transfer or
architecture-capacity claim. S04-E014 remains SAMPLING_ONLY_REPAIR_REJECTED for
its frozen 90% two-state screen; its 34.30/35.44% improvement is retained.

Targets are equilibrated_uv under state-specific fixed FEM damage, frozen
history/fatigue and prescribed load Us=0.11999988. The primary physical field
is (u,v), never history energy. Strain and native-Q4 displacement weak residual
rho_u are secondary only. No damage/history/fatigue update is allowed.

## Matrix and identities

Fresh independent networks for seed7, alpha in {0.5,0.7,0.9}, and:

| state | role | exact NPZ SHA256 |
|---|---|---|
| c20s4 | primary early | 23d00fbe07a77b406008886c07b698cebe463b88ece4cbd9fa08ac3238ea953b |
| c60s4 | primary middle | 46b53c0f546b62606c232aea8188bcc43bc6dc39f7078d2265b917e45ddb7ec2 |
| c83s4 | primary transition | 24557eaad9ea09f925fdceb8079116427e2bf7602e9626841db46742d6371eae |
| c40s4 | mandatory early-middle sentinel | 64c5fd2ff16cc2588d723854edff25c288bc0bfa708f7dc3f17f4e5374460e7c |

12 fresh runs, no seed substitution/retry/checkpoint continuation. c40 is the
E009 admitted conditional UV reference from a separate early FEM replay; do not
infer same-execution trajectory continuity. Existing E014 alpha=.9 c20/c83 are
historical reproducibility controls, not substituted for new rows. Existing
E013 mass-sampling seed7 c20/c60/c83 are contextual baselines; c40 has no such
baseline and must not receive a fabricated baseline.

## Exact training and sampling procedure

Reuse E013 8x400 TrainableReLU, float64, CPU seed7 Xavier initialization, exact
SENS BC/global coordinate bounds, AdamW lr1e-3 and original options, cosine
Tmax10000 eta_min1e-5, 10000 optimizer steps, final-step-only decision. Use
CUDA deterministic algorithms with explicit GPU and CUBLAS_WORKSPACE_CONFIG.
Same input and model initialization in every arm; changed sampling trajectories
are part of the intervention. No model weights shared between arms.

A={damage>0.1}, B=complement. Both must have positive finite mass and be nonempty.
Each step draws conditionally mass-proportional with replacement, A then B,
PCG64(seed+1000003), no shuffle. Batch=16384; exact allocations:

| nominal alpha | n_A | n_B | realized alpha |
|---|---:|---:|---:|
| .5 | 8192 | 8192 | 0.5 |
| .7 | 11469 | 4915 | 11469/16384 |
| .9 | 14746 | 1638 | 14746/16384 |

Estimator = P(A)*mean_A(||uv-uv_ref||²)/Us² +
P(B)*mean_B(||uv-uv_ref||²)/Us², with no second nodal-mass weighting.
All arms optimize the same objective; identical seed does not imply common
sample indices when batch allocations differ.

## Monitoring, metric definitions and decisions

At step0 and each1000 through10000 record:
L_A=sum_A p_i||error_i||²/Us²; L_B analogously;
R_all=sqrt(L_A+L_B), R_A=sqrt(L_A/P(A)), R_B=sqrt(L_B/P(B)).
Distinguish conditional regional RMS from global weighted contributions.
Monitoring is passive, chunked no_grad, no RNG consumption/model/optimizer
mutation. Final monitored R_all must equal voting metric within atol1e-14.
Report secondary BC<=1e-12, native-Q4 strain and rho_u, plus finite/identity
validity; strain/rho do not vote on sampling-ratio primary success.

Primary criterion for each fixed alpha: max R_all across c20/c60/c83 <=1e-3.
This retains the absolute FEM displacement tolerance used in E013/E014. No new
50% rejection line. Report c40 sentinel separately; sentinel failure blocks
claims extending success to c40 but does not rewrite the primary three-state
criterion. Require all12 evidence rows before any comparison or selection.

For design selection rank alpha by max R_all over all four states; ties within
1e-12 select smaller alpha. This is development-only selection, not independent
validation. Report all states/arms and the primary criterion separately.
No alpha-by-state cherry-picking or unrecorded alpha tuning.

If a fixed alpha passes primary, register THREE_STATE_SUPERVISED_FIT_SCREEN_PASS
for that arm only; separately design cross-seed validation. Otherwise register
NO_ALPHA_RECOVERS_THREE_STATE_DISPLACEMENT_GATE and retain all measured progress.
A failed ratio still may be useful; rank and preserve its region-level findings.
Inadmissible identities/artifacts take precedence; missing/interrupted runs are
INCONCLUSIVE, no automatic scientific retry or budget extension.

## Feasibility and next repair

E014 .9 gives .003212/.003435 after10000; no evidence currently assures that
.5/.7 can meet .001. Reference rho is ~1e-11 and BC/strain reconstruction passed;
reference numerical equilibrium is not a true-solution uncertainty estimate.
This experiment is a bounded optimization discriminator with a fixed aspirational
fit gate, not a powered proof of alpha superiority or coverage causality.

If every alpha has final R_all>=.0025 in each primary state, record
COMMON_ERROR_FLOOR_SCREEN, a descriptive threshold 2.5x the fit gate motivated
by the user's ~.003 concern; it is not proof of convergence/representation cause.
Advance the independently prepared global/local representation screen. Other
failed patterns select repairs from measured regional errors without inventing
new runs or redefining this gate. Parallel representation design and non-training
implementation are authorized now; producer execution needs its own exact review.

## Evidence, resources and stop rule

Fresh Taobo runs/receipts per state-alpha; explicit live GPU choice; preserve
existing processes. Fixed cap12x10000 steps. Halt only on systemic validity
failure; complete all scientific failures, no outcome-dependent early stop.
Minimum: all12 final models/predictions/metrics/monitoring/receipts/archive copies,
fail-closed aggregate, state-by-alpha region table, trajectories and field maps,
paired .9 historical checks, decision figure/README, independent Evidence review.
Planning and exact-commit Code Ready reviews precede producer execution.
Full FEM reproduction, teacher qualification, Stage2 and trajectory transfer
remain outside scope.
