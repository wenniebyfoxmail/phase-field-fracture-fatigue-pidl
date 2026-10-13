---
storyline_id: S04
experiment_id: S04-E018
protocol_revision: 20261012-r2-anchor-global-local-screen
status: completed-evidence-pass
---
# S04-E018 draft: smooth global + damage-local UV representation

Status: design draft only; no implementation or producer execution; separate from S04-E017 sampling allocation. Protocol and numerical launch require planning/code review. User authorizes parallel preparation. Proposed sampler α=0.7 is fixed before seeing E017; numerical execution can wait for E017 evidence closure and producer availability without choosing α retrospectively.

## Bounded question and evidence

Does giving a parameter-matched two-branch UV network local coordinates and compact damage-defined spatial support reduce final conditional FEM displacement error at early c20s4, middle c60s4, and transition c83s4, within the same 10,000-step procedure?

The target is same-state, in-sample representation/optimization capability, synthetic evidence. FEM damage is an admitted, frozen conditioning field. UV is the supervised output. FEM fatigue/history remain frozen and do not become training targets/features. Strain and native weak-form rho_u are secondary diagnostics only. No transition, full teacher, physical or cross-trajectory generalization claim is available.

References: reuse the exact S04-E013 admitted c20s4/c60s4/c83s4 UV packages and their existing identity locks, native Q4 evaluators, mass scale, BC definition and Us=0.11999988. Audit c60 identity/capability before use; no substitute cycle. c40 is admitted as the mandatory additional early-middle sentinel in E017. E018 keeps its predeclared primary three-state c20/c60/c83 screen; including c40 here requires an explicit reviewed extension, never a silent extra row.

## Smallest implementation with an honest capacity control

Use two independently initialized UV networks. Global branch G uses TrainableTanh, giving mathematically smooth raw global output; local branch L uses TrainableReLU, preserving the sharp local representation mechanism. Each is NeuralNet(2,2,8,283,activation,1.0), float64, Xavier. Both candidate and matched control have the same activations, layer widths, parameter counts and initialization order. Explicitly record that compared with old E013 MLP both activation mix and branch architecture change; the matched control isolates the spatial localization package (coordinates + compact window), not its two ingredients individually.

For physical x=(x,y), ξ=2x on the locked [-0.5,0.5]^2 domain, raw outputs are:

- matched two-branch control: r_C(x)=G(ξ)+L(ξ);
- damage-local candidate: r_M(x)=G(ξ)+w(x)L(z(x)).

Apply exactly the existing outer boundary ansatz to the combined raw output, never impose BC separately inside the window:

u=(y+0.5)(0.5-y) r_1;
v=(y+0.5)(0.5-y) r_2+(y+0.5)Us.

This preserves the exact top/bottom essential BC. No trainable damage output, learned gate, target-residual-based patch, hard output clipping, warm start, alternating optimizer, branch penalty, derivative penalty, or added training steps. Both branches jointly receive the unchanged full-field UV objective.

Parameter count of NeuralNet(2,2,8,w) with eight scalar trainable activation coefficients is 7w²+12w+10. Old 400-wide MLP: 1,124,810. Two 283-wide branches: 1,128,058 (+0.28876%). New arms are exactly matched; old MLP is matched within 1%, not exactly. Assert actual parameter counts from the constructed model; discrepancies block launch. Runtime/FLOPs are recorded, not assumed equal: same step/batch budget does not imply identical compute cost.

## Deterministic localization from allowed information

The r2 amendment in localization_amendment_r2.md supersedes all-damage rectangle
selection below: select the unique Q4-edge damage component touching the initial
notch anchor; retain ALL damage nodes in sampler/loss/metrics. The original r1
formula description remains the source of the unchanged window/coordinate
transform, evaluated on the anchor-component bounds. R2 PLAN PASS received before
implementation; changed geometry requires new exact-commit review.

Let A={node i: d_FEM,i>0.1}; B is its complement. Localization reads only xy, d_FEM, mesh identity and a frozen physical padding δ=0.02 (normalized domain units). δ is a frozen coordinate-design constant; no claim relating it to a verified FEM process-zone length is made. Freeze δ before UV error inspection, not from residual extent.

Compute per-axis core bounds a_j=min_{i∈A} x_ij, b_j=max_{i∈A} x_ij. A must be nonempty; a_j=b_j is permitted because padding keeps scale positive. Center c_j=(a_j+b_j)/2; scale h_j=(b_j-a_j)/2+δ. Local input z_j=(x_j-c_j)/h_j. Store bounds, centers, scales, damage mask counts and masses in a manifest. No future state is used to localize an earlier state. Each state's own admitted frozen damage determines its patch.

Define q_j=max(a_j-x_j, 0, x_j-b_j)/δ and s(t)=1-10t³+15t⁴-6t⁵ for 0≤t≤1. Let w_j=1 for q_j≤0, s(q_j) for 0<q_j<1, and 0 for q_j≥1. w(x)=w_x w_y. The window is C2 across core and outer support joins (zero first and second derivatives at joins). All damage nodes have w=1; background beyond the expanded rectangle has w=0. It covers the full damage strip without requiring crack-tip/event selection. It is not an oracle of displacement error. Report support mass and fraction of B inside the support, since a bounding rectangle may include substantial background.

This is one patch, two branches; do not start with six local networks. The local patch can carry both positive and negative corrections and the global branch stays active everywhere. A local branch is not guaranteed to specialize; branch magnitude and conditional errors measure whether useful separation actually occurs.

## Sampler and objective

Fixed α=0.7, batch 16,384: n_A=11,469, n_B=4,915. Draw with replacement mass-proportionally within strata. Use independent deterministic PCG64 streams seeded S+1,000,003; candidate/control consume exactly the same precomputed per-step node IDs. S=7. Do not use the viewed best α from E017 without a reviewed amendment explicitly labeling selection on these states as development.

With m_i native-Q4 lumped mass, M=Σm_i, P_A=Σ_A m_i/M, f_i=||UV_pred-UV_FEM||²/Us², unbiased loss is P_A mean_A(f)+P_B mean_B(f). Preserve exact implementation/normalization inherited from E013/E014: current domain M=1 makes this equal to their total-mass expression; assert M and do not silently renormalize the formal primary evaluator. No extra weighting after conditional mass-proportional draws.

Optimizer, cosine schedule, lr, final-only policy and 10,000 steps use the frozen E017/E014 constants. Fresh networks per arm/state; no reference target-derived initialization. Initialize G then L in fixed order with seed7 for both new arms. Pairing gives identical initial parameters and sampler draws; the changed forward mapping is the intervention.

## Screen and outcomes

Six new numerical units: matched control and localized candidate × c20s4/c60s4/c83s4, seed7. The existing E017 α=.7 8×400 MLP units are an additional comparator when available, not a replacement for the exact parameter/activation-matched control. Keep all states in all tables.

One primary capability criterion: candidate final E_UV≤1e-3 at every admitted state. This retains the existing desired fidelity and prevents a late-state-only success. A primary miss is recorded as negative for this procedure, without suppressing improvements. Full joint strain/rho qualification remains a later independently frozen criterion; secondary metrics cannot overturn this UV verdict.

Predeclare a separate matched-control diagnostic: candidate/control final error ratios for all three states; localization is helpful across the screen when all ratios<1. This is a component finding, not rescued primary success or proof of unique causality. Ratios near 1 in a single seed cannot establish statistical equivalence. If candidate passes primary and improves across states, freeze a full 4-state ×3-seed validation; do not begin Stage2 automatically. If primary misses but all state ratios improve, retain localization and use full-objective trajectories to select a separately reviewed optimization repair. If localization worsens any state, report the failure and inspect fixed support/branch contributions before any padding or activation sweep. Do not add viewed arms.

Parallel progression rule: prepare protocol, window/network module, deterministic tests and code review while E017 runs. Numerical launch can follow E017 closure at the same fixed α=.7. The user explicitly approves concurrent direction advancement, so E017 primary failure is not a prerequisite for preparing E018. If E017 passes UV across early/middle/transition, keep E018 as secondary representation diagnostic and prioritize broader validation of the simpler passing MLP. If E017 does not pass, E018 becomes the next bounded capability test. Preserve all original E014 verdicts and report sampling progress separately.

## Full-field traces and evidence

At steps 0,1000,...,10000 evaluate without optimizer updates:

E_all² = Σ_i m_i||e_i||²/Us²;
E_A_cond² = [Σ_A m_i||e_i||² / Σ_A m_i]/Us²;
E_B_cond² analogously;
C_A = Σ_A m_i||e_i||²/Us²; C_B analogously.

Exact identity E_all²=C_A+C_B=M(P_A E_A_cond²+P_B E_B_cond²) must hold. Record both conditional RMS and contributions; a small region can have large conditional error but a small full-field contribution. Record branch raw/physical RMS on A/B/support and global/local cancellation; these are explanatory only. Evaluate Q4 strain and rho_u finally on the combined nodal UV, not coordinate gradients, preserving native comparisons.

Final-only scoring. Trajectories cannot select a checkpoint, alter lr, stop early or add steps. Stop only for nonfinite outputs, invalid identity/BC/reference, execution failure or the frozen resource cap. No adaptive suppression of a bad state.

Minimum package: exact code/data/protocol locks, six fresh Run receipts, final prediction arrays, checkpoint state, full-field trace CSV, final metrics with baseline/control/candidate columns, summary/verdict, and decision plot (all states; 1e-3 line; A/B trajectories and contribution decomposition). Separate execution/retrieval/scientific status. No scientific conclusion from import/window tests alone.

## Reuse and deterministic verification

Reusable paths under existing E014 worktree or shared child repo:

- source/network.py: NeuralNet, TrainableTanh, TrainableReLU, init_xavier.
- SENS_tensile/run_s04_e013_stage1_supervised.py: reference validation, exact BC, normalization, final_metrics, q4_strain, residual_metrics, provenance constants.
- SENS_tensile/run_s04_e014_stratified_screen.py: unbiased sampler and full-field monitoring from E014.
- SENS_tensile/field_computation.py:_local_patch_output: precedent for normalized patch coordinates/windows; legacy 3-channel/coupled field wrapper must not be imported wholesale.
- SENS_tensile/run_fem_mesh_fbpinn_umax.py: historical FBPINN approach only. It enters fatigue/energy coupled training and uses six predeclared path patches; not a runner for the present frozen-damage supervised UV claim.
- SENS_tensile/analyze_fbpinn_chain_vs_fem_nstep2.py: historical result warns that local authority changed propagation failure modes without closing FEM energetic mechanism; it neither predicts success nor rejects this separate UV screen.

Implement a small dedicated UV module in a new E018 worktree, not edits in the shared integration tree. Prefer importing pure E013 helpers rather than modifying legacy coupled FieldComputation.

Nontraining checks: model parameter counts, candidate/control initialization equality, exact BC with arbitrary raw outputs, C2 window boundary values/derivatives and damage-node coverage, positive localization scales including zero-width A, target-independent localization via synthetic target perturbation, unbiased loss expectation by exact weighted sums on a toy mesh, identical sampler IDs, trace decomposition identity, and checkpoint/provenance serialization. Then exact-commit independent Code Ready review; formal training only on authorized producer with fresh attributable paths/GPU/PID receipts.

## Arithmetic erratum 2026-10-12

Nontraining construction exposed a one-width-term error in the stated parameter
count. Correct counts/formula above replace the arithmetic only. Both declared
architectures remain8x283, with identical counts between candidate/control; no
model, activation, budget or scientific criterion changes. Actual constructed
counts must pass unit checks before Code Ready review.
