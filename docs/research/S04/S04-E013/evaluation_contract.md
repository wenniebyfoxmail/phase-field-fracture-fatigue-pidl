# S04-E013 proposed evaluation contract

Status: amended contract frozen. Stage 1 exact-commit Code Ready passed; the frozen producer matrix is authorized but not run.

## Two axes that must remain separate

The first axis is the **training signal**:

1. `SUPERVISED_CAPACITY`: the conditional UV-derived displacement is allowed in the loss. This is a representation ceiling, not a physics result.
2. `UNSUPERVISED_PHYSICS`: the reference displacement is hidden from the loss and used only after checkpoint freeze. The loss may use the locked geometry, load/BC, material parameters, fixed FEM damage, and the same native-Q4 UV energy/residual definition.

The second axis is the **evaluation reference**:

1. `STRICT_UV_DERIVED_REFERENCE`: fixed accepted FEM damage with the S04-E006/E008/E009/E012 UV-rebalanced displacement. This reference qualifies only the UV block.
2. `ORIGINAL_FEM_NATIVE_FIDELITY`: original Stage0b FEM fields on their own trajectory and native acceptance contract. This measures output fidelity, not strict teacher equilibrium.

Supervised and unsupervised branches use the same evaluation code and thresholds. A supervised pass cannot substitute for an unsupervised pass. A strict-UV pass cannot substitute for native trajectory fidelity, and native fidelity cannot upgrade the strict teacher claim.

### Training-information separation

- Stages 1 and 2 must use the same declared arrangement: either one network per state or one jointly conditioned network. Architecture, allowed inputs, initialization distribution and seeds, compute budget, stopping rule, and checkpoint-selection rule are frozen before either stage.
- Stage 2 starts from its own registered initialization. It may not inherit Stage 1 weights or optimizer state. Derived displacement, strain, and driver may neither select its checkpoint nor trigger further optimization.
- Stage 2 remains **conditional fixed-state UV recovery** because accepted FEM damage/history/fatigue are declared conditioning data.
- Stage 3's training-signal axis must be registered separately. Candidate and control start from the same registered physical initial state and evolve their own accepted states and histories. No FEM-state resets at evaluation cycles and no initialization from networks fitted to future evaluation states are allowed.
- A prevented later stage is `NOT_RUN`, not a failure on another axis.

## Route A — strict-physics UV block

### State set

The required peak set is `c20s4` (early), `c60s4` (middle), `c82s4` (late), and `c83s4` (transition). `c40s4` and `c76s4` are optional sentinels. `c82s5` remains a read-only evaluator control and is never a training target.

At contract freeze, coverage was incomplete because the c60 UV-derived reference had not been produced. S04-E013-R002 subsequently produced and qualified c60 under the conditional UV-only boundary; independent Evidence review admitted it. S04-E009 c20, S04-E008 c82, and S04-E006/E012 c83 retain their recorded exact-hash and parent semantics.

### Inputs and outputs

- Inputs permitted in both branches: coordinates/connectivity, exact load and essential BC, material parameters, fixed accepted FEM damage, locked free-UV set, nodal mass, and state identifiers.
- Supervised-only input to the loss: derived-reference displacement.
- Forbidden in the unsupervised loss: derived displacement, derived strain, derived active-driver values, or any metric computed from them.
- Model output: displacement only. Damage, fatigue, history, mesh, and state labels are immutable inputs and must be byte-identical before and after evaluation.

### Frozen proposed gates

Every required state must satisfy all of the following:

| Gate | Threshold | Meaning |
|---|---:|---|
| finite fields/scalars | exact PASS | execution validity |
| essential-BC max absolute error | `<= 1e-12` | actual prescribed displacement |
| mass-dual UV residual `rho_u` | `<= 1e-3` | strict UV physics screen |
| displacement mass RMS error / `Us` versus derived reference | `<= 1e-3` | field reproduction |
| strain relative L2 versus derived reference | `<= 1e-2` | gradient-field reproduction |
| damage/history/fatigue mutation | exactly zero / identical hashes | conditional-reference integrity |

The thresholds are conjunctive. Residual pass alone is insufficient, and field fit without residual pass is insufficient.

### Diagnostic interpretation

- Stage 1 passes: the registered architecture and fitting procedure constructively represent the registered targets within budget; this is not a general representation ceiling.
- Stage 1 fails: representation, optimization, and finite-budget effects remain unresolved.
- Stage 1 passes and Stage 2 fails the residual gate: physics-only training did not recover the required solution under the frozen configuration; the optimizer is not uniquely identified as the cause.
- Stage 2 passes `rho_u` but fails field/strain agreement: reference agreement failed; uniqueness has not been established, so do not label this an optimization failure.
- Both pass: grant `UV_BLOCK_REPRODUCED` for the admitted states only.

## Route B — original FEM native fidelity

### Required states and comparison classes

The minimum same-cycle matrix is four cycles by three substeps:

- c20 early, c60 middle, c82 late, c83 transition;
- s2 loading, s4 peak, s5 unloading.

Every row must include the physical cycle, substep, raw global step, load value, comparison class, checkpoint SHA, and export timing. Add `same-cycle-pre-event` and `own-event` rows using the connected confirmed penetration definition. Never substitute a late FEM state for a missing early model state.

### Fields and metrics

Map to the exact native-Q4 FEM element order and use element-area weighting. Record direct evaluation versus interpolation. Required fields are displacement, damage, Carrara history, fatigue degradation, raw driver, active driver, and strain.

All Route A strain/driver values and all Route B comparisons use the native-Q4 interpolation/evaluator from predicted nodal displacement, never network-coordinate derivatives. Inherit the E012 definitions for nodal mass, physical area, `Us`/`Es`, displacement error, and strain error.

Headline metrics:

- displacement mass RMS / `Us`;
- damage area-weighted relative L2 and correlation;
- Carrara-history relative/log error and correlation;
- fatigue-factor relative L2;
- active-driver log-MAE, correlation, FEM-p99 absolute-support IoU, own-top-1% IoU, and absolute support-area ratio;
- crack-tip position, damage IoU at 0.25/0.5/0.75, symmetry, and event timing.

### Proposed promotion gates

The exact native-Q4 eta0 configuration is the paired control, not ground truth. A candidate earns `NATIVE_FEM_FIDELITY_REPRODUCED` only if all required rows are present and all conditions below pass:

1. `abs(candidate_event_cycle - FEM_event_cycle) <= 3`;
2. peak-state displacement mass RMS / `Us <= 1e-2` at c20/c60/c82/c83;
3. peak-state damage relative L2 `<= 0.20` and correlation `>= 0.95` at c20/c60/c82/c83;
4. active-driver metrics follow the executable null/support definitions below;
5. candidate passes the field-wise paired-improvement and early/middle rules below;
6. every registered state passes the history/degradation non-regression guard below;
7. symmetry is diagnostic only and is not a promotion veto;
8. runtime, convergence, hashes, state mapping, and archive completeness pass.

These benchmark-specific gates require independent design review before launch. A candidate that passes timing or damage alone remains diagnostic.

### Executable active-driver definition

Let `a*` be the maximum FEM area-weighted RMS active driver over the eight registered loading/peak states; require `a*>0` and freeze `a0=1e-12*a*`. With physical area weights normalized to sum to one, log-MAE is `sum_i w_i * abs(ln((a_P+a0)/(a_F+a0))) <= 2.5`.

A state is reference-null when FEM area-weighted `RMS(a_F) <= a0`. For such a state, correlation, support IoU, and support-area ratio are `NOT_APPLICABLE_REFERENCE_NULL`; replace them by `RMS(a_P-a_F)/a* <= 1e-3`. The row remains in coverage and history comparisons. A constant candidate against a nonconstant eligible FEM reference fails correlation. Apply the same reference-driven constant-field policy to damage correlation.

For an eligible state, compute one area-weighted FEM threshold `t_j = Q^w_0.99(a_F | a_F>a0)`, including all ties. Both supports use this same threshold: `S_F={a_F>=t_j}` and `S_P={a_P>=t_j}`. Compute IoU and area ratio with physical areas. Do not threshold candidate and FEM separately. Eligible loading/peak states must pass log-MAE `<=2.5`, correlation `>=0.20`, IoU `>=0.10`, and area ratio in `[0.5,2.0]`.

### Executable paired promotion

Freeze candidate and exact-native-Q4 eta0 control on a common physical initial state, native-Q4 configuration, loading/state semantics, seeds, and declared budget. For each registered state `j`, define separate dimensionless lower-is-better errors `E_k` for damage `d`, committed fatigue history `alpha_bar`, previous driver `q_prev`, current active driver `a`, and degradation `f`; all reference scales are FEM-derived and frozen before candidate results. Let `D_kj=E_control-E_candidate` and `tau=1e-12`.

- Require `median_j(D_kj)>tau` separately for `k in {d, alpha_bar, q_prev, a}` across all 12 states; never pool fields.
- For each of those fields and each cycle `c in {20,60}`, require `max_{s in {s2,s4}} D_k,(c,s)>tau`.
- Require `E_candidate <= 1.10*E_control + tau` at every state for `k in {alpha_bar,q_prev,f}`.
- Equal already-negligible errors do not count as improvement.
- `symmetry_status=DIAGNOSTIC_ONLY` and `symmetry_is_promotion_veto=false`.

### Event and export semantics

Before producer launch, bind one deterministic event detector: physical field, threshold, spatial region, accepted-state timing, and first-occurrence rule. The horizon must extend through FEM event `+3` cycles. No detected event within a completed horizon fails; an interrupted run is incomplete.

- Same-cycle matrix: candidate and FEM at identical cycle/substep keys.
- Same-cycle pre-event: last prescribed peak strictly before the FEM event, evaluated at that same key in both trajectories.
- Own-event: each trajectory's first detected event, explicitly time-shifted. Own-event similarity cannot replace failed same-cycle comparison.

The exporter must provide nodal displacement and damage, required history/degradation/driver channels, own-prior references, and exact accepted-state export timing. Candidate and control evolve their own accepted histories.

## Current Stage 0 verdict

`STAGE0_C60_AND_PAIRED_ASSETS_ADMITTED__CANDIDATE_TRAINING_NOT_AUTHORIZED`.

- FEM native-fidelity references exist for all 12 required states in the S04-E010 archive.
- The c60 conditional UV-derived reference is admitted; its damage/history/full-teacher status is unchanged.
- The native-Q4 eta-zero control now has the 12-state matrix, nodal displacement and the separately labelled own-event row, registered as `PAIRED_CONTROL_ASSETS_READY`.

Track four distinct states: `REFERENCE_ASSETS_READY`, `EXPORT_SCHEMA_READY`, `PAIRED_CONTROL_ASSETS_READY`, and `CANDIDATE_TRAINING_AUTHORIZED`. Exporter and c60-reference code may be developed now. A frozen schema authorizes only its asset/control producer, not candidate training or asset-complete status. The declared c60 and paired-control asset prerequisites are now admitted. Candidate training still requires its separate explicit authorization gate; asset admission is not that authorization.

The Stage 1 training plan is frozen in [stage1_training_authorization.md](stage1_training_authorization.md) and [stage1_contract.json](stage1_contract.json). External planning review returned `PLAN PASS` after four corrections. Exact-commit Code Ready re-review then returned `PASS` for `769396f93ae5258eb984e1585d4274f7990afb11`. `CANDIDATE_TRAINING_AUTHORIZED` is true only for this frozen Stage 1 matrix and reviewed commit; no scientific result exists before execution and Evidence review.

## Claim map

| Status | Evidence required | Claim allowed |
|---|---|---|
| `SUPERVISED_CAPACITY_PASS` | Stage 1 gates | the fixed finite-budget procedure reproducibly fits all admitted UV targets across the registered seeds |
| `UV_BLOCK_REPRODUCED` | Stage 2 gates on all Route A states | unsupervised physics recovered the admitted conditional UV fields |
| `NATIVE_FEM_FIDELITY_REPRODUCED` | Route B gates | free trajectory matches original FEM under the frozen native-fidelity metrics |
| `FULL_FEM_REPRODUCTION` | unavailable | no claim under the present contract |
| `QUALIFIED_FEM_TEACHER` | unavailable | no claim under the present contract |

No overall rule may be written as “either route passes.”
