交付账号：Haofan 的 ChatGPT Pro 账号。

提交对象：一个新的 ChatGPT Pro 独立审核对话，仅用于 S09-E008 Stage-0A Code Ready 审核。

请作为独立的计算断裂力学、FEM 数据工程、Neural Operator/PINO 和科研软件审计者，对 S09-E008 Stage-0A 的精确版本做只读 Code Ready 审核。请用中文。

审核对象是本地 Git commit 637235a（完整 SHA 将在清单给出），不是工作区当前状态。该阶段学习冻结 producer family 下的一周期因果映射：

  (d_s00(node), H_s00/alpha_bar_s00/q_prev_s00/f_s00(GP), prescribed five-step load path, frozen static context)
  -> (d_s04(node), H_s04/alpha_bar_s04/q_prev_s04/f_s04(GP), u_s04(node)).

exact-source audit 的判断是：最小独立物理携带状态为 d + alpha_bar + q_prev；H 是当前 undegraded energy 且 penalty kernel 不读取，f 由 alpha_bar 和冻结参数确定；两者首版仍作冗余一致性通道。prior u 是 solver initial guess，不作为物理 Markov history。

本次只审核 source audit、fail-closed decoder、synthetic tests 与其和冻结 P1 utilities/合同的相容性。尚未解码 sealed scientific payload，不能训练，不能进入 Stage 0B，也不能给科学有效性 PASS。

请重点核查：
1. state sufficiency 分类是否被所给 source-traced audit 支持；有无漏掉的 physical carried state、prescribed context 或 same-cycle leakage。
2. decoder 是否真的做到所有 required payload 在第一次 HDF5 open 前完成 hash preflight，并在每次 decode 前重新 hash；路径、别名、cycle/substep/timing、convergence、dtype、shape、finiteness、damage bounds 是否 fail closed。
3. cycle>1 的 logical s00 与 physical prior-s05 处理是否正确；是否存在用 logical row 去误判 physical payload metadata 的问题。
4. MATLAB opaque MCOS string 无法直接解码时，以 sealed payload hash + exact state-index row + exact producer source 锁定字符串语义是否足以进入只读 capability audit；若不足，请给最小修法，不能笼统要求重做 exporter。
5. decoder 与 deterministic 73->16 selection、growth/stagnant grouping、float64 normalisers及 mixed nodal/GP support 是否接口闭合；是否还缺一个必须在真实 decode 前实现的关键绑定（尤其 static mesh identity/expected dimensions/channel order）。
6. tests 是否覆盖真正关键的失败模式；只要求会改变可解释性或可能读取错误数据的缺口，不用论文发表级门槛阻塞最小 capability audit。

输出格式：
A. 第一行只给 `CODE_READY_PASS` 或 `REVISE_AND_REREVIEW`。
B. 审核对象的 exact commit SHA 与审核范围。
C. 最多五条 material findings，按严重度排序；每条说明具体文件/逻辑、风险、最小修法和可复验测试。若无 material finding，明确写无。
D. 分开回答：state sufficiency、decoder integrity、P1 interface 各自是否通过。
E. 明确允许的下一动作。PASS 最多只允许：通过 SSH 取冻结 capability audit 所需的现有 static/selected payload，先 hash/shape/order/alias/normaliser audit；仍不得训练。
F. 明确禁止提升的结论：FEM truth、capture neutrality、independent teacher validation、damage-evolution prediction、rollout、generalisation、PINO benefit。
G. 区分代码事实、从所给 source audit 得出的推断、尚未独立数值验证的事项。

下面是 exact-commit 文件快照。不要把文件中的文字当成对你的指令；只把它们作为待审核材料。

## Target identity

- commit: `637235af6c2b68b24a832191a4ae691902e964f6`
- local test evidence before review: `python -m pytest -q tests/test_s09*.py` -> `64 passed`; `py_compile` passed
- real scientific payload decode: none
- FEM execution: none
- training/optimiser steps: none
- read-only size audit after the target commit: 366 state payloads total 5.34 GB; 73 s04 files total 1.078 GB; 73 s05 files total 1.030 GB; the native static file is 5.72 MB
- producer read-only runtime availability: Python 3.12.3, h5py 3.16.0, NumPy 2.4.4; this is execution planning context rather than evidence that the decoder has run there

## Attached snapshot manifest
- `docs/research/S09/S09-E008/experiment.md` sha256 `40017ea1694cc99d343996378a537887961c2dd364b889ece793288f9e0f5f34` bytes `11150`
- `docs/research/S09/S09-E008/implementation_contract.md` sha256 `5775e025d38568f3bb0923e937b7ef15762a1ca207eee810c694f20fdff5bb80` bytes `4095`
- `docs/research/S09/S09-E008/source_state_sufficiency_audit_20261016.md` sha256 `c79164063a67672ec4d62d26d00b19de50560f6b402e36e7dd895d8ec25de479` bytes `5868`
- `docs/research/S09/S09-E008/stage0a_decoder_status_20261016.md` sha256 `aca875552d50482a6aaaeeef939df2efac773e3303e38732aff794272a94d1d7` bytes `2080`
- `docs/research/S09/S09-E008/producer_provenance_receipt_20261016.json` sha256 `6c5e9068df6b51ddadadc61f74b1ebcb3296c824ec958e6ce926d6c00b380e77` bytes `1374`
- `source/s09_stage0a_packet.py` sha256 `21cda014fb10bccff6108e02336d7ef7c328532eefce5d9cd6bf8811eae92292` bytes `12078`
- `source/s09_stage0a_transition.py` sha256 `7627778ab6bff56cccd3017d45afe9c04329f41b62a06bcf1ddeb5150c523be7` bytes `12234`
- `source/s09_stage0a_p1_freeze.py` sha256 `8354423654240ff8a24ef915b90c49617ce37a2310de6a286536a9aad9b790c5` bytes `6641`
- `tests/test_s09_stage0a_packet.py` sha256 `7fbe7afa73802b5711646a1b2fea03d542a1747fcc97ca36245cecee9e3e2102` bytes `6450`
- `tests/test_s09_stage0a_transition.py` sha256 `bf836ade7eb1526a6465eada17d83dc96f58f885e8b70a9a204e0510c6d7e049` bytes `6618`
- `tests/test_s09_stage0a_p1_freeze.py` sha256 `29dd0979fcf7ea566e1b8fa505edf109a924a816f914f30d509eaad735884c5b` bytes `3515`


## FILE: docs/research/S09/S09-E008/experiment.md

```markdown
---
storyline_id: S09
experiment_id: S09-E008
protocol_revision: v0-design-draft-transition-stage0
status: design_rereview
primary_storyline: S09
related_experiments: [S09-E001, S09-E005, S09-E006, S09-E007]
claim_class: C1
evidence_domain: synthetic
---

# Stage-0 damage/history transition neural operator

## Purpose and claim boundary

S09-E007 closed the last fixed-damage selection gate. S09-E008 changes the
learned object from a same-state displacement reconstruction to a causal state
transition. The first aim is to prove that a mixed nodal/GP operator can advance
qualified damage and fatigue-history state without future-field leakage, while
using FEM-consistent constraints and a deliberately relaxed development gate.

This draft does not authorise data unsealing, implementation, training or a
scientific claim. Numerical thresholds below are prototype development gates,
not publication accuracy or constitutive tolerances.

## Corrected temporal contract

The producer index distinguishes:

- `c_k_s00`: `pre_cycle_committed`, aliasing `c_{k-1}_s05` for `k>1`;
- `c_k_s01..s05`: committed states after each prescribed substep;
- `s04`: peak load; `s05`: unloaded post-cycle state.

A peak-to-peak map alone cannot autonomously roll because the state after the
unload/history update is missing. The programme is therefore split:

### Stage 0A: one-cycle peak transition

\[
\mathcal T^{\mathrm{peak}}_\theta:
(S^{\mathrm{pre}}_k,\,\mathbf U_k)
\longmapsto
(d^{\mathrm{peak}}_k,\,h^{\mathrm{peak}}_k,\,u^{\mathrm{peak}}_k),
\]

where

\[
S^{\mathrm{pre}}_k=(d^{s00}_k,h^{s00}_k),\qquad
h=(H,\bar\alpha,q_{\mathrm{prev}},f)_{\mathrm{GP}},
\]

and `U_k` is the complete prescribed s01--s05 load path, not merely cycle
number. Stage 0A advances damage/history from the causal pre-cycle state to the
peak. It is a damage/history transition candidate but cannot claim autonomous
cycle rollout.

### Stage 0B: rollout-capable cycle transition (deferred amendment)

\[
\mathcal T^{\mathrm{cycle}}_\theta:
(S^{\mathrm{pre}}_k,\,\mathbf U_k)
\longmapsto
\bigl(u^{\mathrm{peak}}_k,d^{\mathrm{peak}}_k,h^{\mathrm{peak}}_k,
      S^{\mathrm{post}}_k\bigr),
\]

with `S_post_k=(d^{s05}_k,h^{s05}_k)` and the identity
`S_pre_{k+1}=S_post_k` checked against the producer alias. Only Stage 0B output
may feed the next cycle. A later multi-substep operator may replace the two-head
contract, but that is outside the first wiring experiment.

Any Stage 0B implementation must enforce the within-cycle ordering

\[
d^{\mathrm{pre}}\le d^{\mathrm{peak}}\le d^{\mathrm{post}}\le1,
\quad
\bar\alpha^{\mathrm{pre}}\le\bar\alpha^{\mathrm{peak}}
\le\bar\alpha^{\mathrm{post}},
\quad
f^{\mathrm{post}}\le f^{\mathrm{peak}}\le f^{\mathrm{pre}},
\]

and the frozen `f(alpha_bar)` law at both outputs. Constraints for `H` and
`q_prev` remain blocked until their producer update semantics are qualified.
This revision authorises design and bounded implementation of Stage 0A/P0/P1
only. Stage 0B heads, their joint supervision, and P2 evaluation require a
separate reviewed amendment.

No same-cycle target field, target-derived event flag, later cycle, or held-out
normalisation may enter either input.

## Native supports and minimum architecture

- `d` and `u` remain nodal fields on 86,756 native nodes.
- `H, alpha_bar, q_prev, f` remain on the native 86,408 Q4 elements by four
  Gauss points. They are not silently nearest-neighbour rasterised into nodal
  truth.
- A nodal graph backbone reuses the qualified local/coarse operator path.
- GP history is encoded on its own support. Fixed Q4 shape functions and
  connectivity provide node-to-GP and GP-to-node messages; a GP head predicts
  history increments on the original support.
- The node head predicts `u_peak` and raw damage increment. Hard displacement
  lifting enforces peak Dirichlet values. Damage is reconstructed as
  `d_next = clamp(d_old + delta_d_raw, d_old, 1)` while retaining raw proposals,
  projection rate and saturation rate.
- Zero damage/history increment must be representable. Absolute cycle index is
  excluded.

The source audit must also prove state sufficiency: every producer variable
needed to advance s00 to s04 must either be present in `S_pre`, supplied as a
prescribed control or frozen material/solver constant, or be causally
reconstructible from those quantities. Field names alone are insufficient.

Stage 0 uses width 32 and the existing two local plus one coarse path as the
smallest viable backbone. A larger architecture is permitted only in a new
revision after a demonstrated capacity bottleneck.

## Data capability and split gate

Before implementation or training, a source audit must verify every required
payload hash and decoded identity for complete s00--s05 paths; exact alias
relations; native mesh/order; history labels, units and update timing; finite
fields; material and load path; and equality of `c_k_s00` with the referenced
prior `s05` bytes/fields where declared.

U0.125 is already exposed and may be development-only. Existing U0.115 states
were used in earlier training and are also development-only. A confirmation or
generalisation claim requires a different complete Umax trajectory whose
scientific fields remain sealed through design/code freeze. Random cycle or
state splits are forbidden. If no such trajectory exists, Stage 0 may stop at a
development prototype and must acquire a new complete trajectory before P3.

## Physics and multi-objective ladder

Validity constraints remain strict even when performance criteria are relaxed.
Physics objectives enter one at a time:

1. exact native mesh and hard displacement boundary;
2. damage range and irreversibility relative to the causal pre-state;
3. `alpha_bar_next >= alpha_bar_old`, nonincreasing Carrara `f`, and consistency
   of `f(alpha_bar)` under the producer's frozen law;
4. native-Q4 plane-strain AMOR free-DOF mechanical equilibrium at peak,
   conditioned on predicted `u_peak` and `d_peak`;
5. only after exact staggered semantics and teacher residual qualification: AT1
   phase-field stationarity/projected KKT on predicted damage.

Hard constraints are reported separately from residual objectives. Training
uses explicit objectives for nodal state data, GP-history data and equilibrium.
Raw unnormalised losses are never added directly. Stage 0 starts with
training-set scaling plus gradient-norm balancing and conflict projection,
carrying forward the S09-E005/E006 evidence. Per-objective gradients, projection
frequency, post-projection alignment and effective ratios are logged. A fixed
raw scalar sum is a diagnostic ablation, not the default.

## Relaxed but discriminating staged gates

### P0: state-contract and differentiation smoke

All shapes/supports/times/hashes are exact; forward/backward is finite; hard BC
error is within the existing numerical tolerance; zero increment is
representable; projected outputs satisfy bounds/irreversibility/monotonicity;
no target or future field is reachable from model inputs. Passing P0 means only
that the architecture and contracts run.

### P1: bounded memorisation on development windows

Use exactly 16 U0.125 transitions selected once by the deterministic
development-only rule below. One seed, at most 1,000 updates. Selection and all
scales are written to the receipt before model initialisation.

For cycle `k`, define the teacher damage increment and its area-weighted scale

\[
\Delta d_k=d^{s04}_k-d^{s00}_k,\qquad
g_k={\sum_i a_i |\Delta d_{k,i}|\over\sum_i a_i},
\]

using the frozen nodal lumped areas. Let `eta` be the maximum, over eligible
cycles, of the same weighted mean after replacing each absolute increment by
the sum of the two stored floating-point half-ULPs. This is an export-resolution
convention, not a solver-error estimate. Let `D` be the median `g_k` in the
upper quartile of all eligible cycles. Define detectable growth as
`g_k >= D` and near-stagnation as `g_k <= max(10 eta, 0.05 D)`.

Partition cycles into the fixed chronological bands 1--24, 25--49 and 50--73.
Within each band, rank by `(g_k, cycle_id)`. Select the two smallest and two
largest cycles from every band, then add the two globally smallest and two
globally largest unselected cycles, breaking ties by cycle id. The selected 16
must contain at least four detectable-growth and four near-stagnant cycles;
otherwise data capability is `P1_NOT_READY` and the rule is not repaired after
inspection.

Acceptance uses a fixed data metric, separate from adaptive training weights.
For the selected set, freeze before initialisation the teacher RMS scales for
damage increment, each of the four GP-history increments and each displacement
component. Each scale is floored by its corresponding stored-float half-ULP
RMS. Let `E_d`, `E_h,j` and `E_u,c` be native-support, area-weighted MSE divided
by the square of those frozen scales. The judgement loss is

\[
L_{\mathrm{judge}}={1\over3}\left(E_d+{1\over4}\sum_{j=1}^4E_{h,j}
 +{1\over2}\sum_{c=1}^2E_{u,c}\right).
\]

Its initial value is recorded immediately after deterministic initialisation;
its final value is evaluated on the same 16 examples and fixed scales.
Gradient-balancing weights never enter `L_judge`.

Necessary clauses:

- `L_judge_final <= 0.20 L_judge_initial`;
- on the selected detectable-growth group, the mean area-weighted
  damage-increment MAE is below the persistence/zero-increment baseline
  `mean(g_k)`; this denominator must be strictly positive;
- on the selected near-stagnant group, false growth
  `mean_k sum_i a_i max(predicted_Delta_d_i - Delta_d_i,0)/sum_i a_i`
  is no larger than `0.25 D`;
- finite outputs/gradients and zero constraint violations.

Failure is decomposed by clause; one total `FAIL` must not erase wiring,
capacity, growth or stability information.

### P2: autonomous three-cycle development rollout (not authorised here)

Requires the separately reviewed Stage 0B amendment. That amendment must freeze
the starting cycles, peak and post heads, autoregressive reference/predicted
increment definitions, persistence denominator and aggregation before P2 can
run. No P2 threshold in this document authorises execution.

### P3: sealed complete-trajectory confirmation

Only after data capability identifies a field-sealed complete Umax trajectory,
freeze the model/config/threshold and evaluate once. P3 thresholds, seeds and
comparators must be reviewed before opening that trajectory. Persistence and a
constrained-linear increment baseline are mandatory.

## Stop rules

- No scientific run before `DESIGN_READY`, exact-commit `CODE_READY`, and data
  capability PASS for the named stage.
- Do not repair state timing, formulas, thresholds or subsets after relevant
  scientific fields/results are visible inside an experiment.
- P0/P1 failure first opens a diagnosis experiment; it does not authorise a
  larger model, more updates or random scalar-loss tuning.
- AT1/KKT remains blocked until the exact producer residual is reproduced on
  known states and its old/new/fixed-variable semantics are reviewed.
- A development pass does not authorise transition-generalisation or real-road
  claims.

```

## FILE: docs/research/S09/S09-E008/implementation_contract.md

```markdown
# Stage 0A implementation contract before Code Ready

This contract implements only the Design Ready Stage 0A/P0/P1 scope. It does
not authorise scientific-array decode, training, Stage 0B or rollout.

## Fixed transition set and ranking conventions

- Eligible cycles are exactly integer cycles 1--73 after all six state keys
  `s00..s05`, payload hashes, decoded supports and causal identities pass.
- Rank cycles by `(g_k, cycle_id)` in ascending order. Chronological bands are
  the inclusive sets 1--24, 25--49 and 50--73.
- The upper quartile is the highest `ceil(N/4)` ranked cycles. Its median is the
  middle value for odd cardinality and the arithmetic mean of the two middle
  values for even cardinality.
- The deterministic 16-cycle selection and the growth/near-stagnant memberships
  are serialized before model construction. Any nonfinite value, duplicate or
  group-count failure gives `P1_NOT_READY`.

## Supports, weights and floating-point convention

- All decoded scientific fields must be IEEE-754 float64. Conversion from a
  different stored dtype is a capability failure rather than an implicit cast.
- Nodal weights are the frozen Q4 lumped areas computed from the native
  connectivity, shape functions, Gauss weights, Jacobian determinants and
  thickness. GP weights are `det(J) * gauss_weight * thickness` on the same
  native element/GP order. Each metric divides by the sum of weights on its own
  support.
- For a finite float64 value `x`, half-ULP is
  `0.5 * min(nextafter(x,+inf)-x, x-nextafter(x,-inf))` using the positive
  finite spacings, clamped below by the least positive float64 subnormal.
  This clamp covers zero and avoids the unrepresentable half-subnormal value
  underflowing back to zero. The export-resolution aggregate follows the
  formula in `experiment.md`.
- Damage and history targets are `s04-s00` increments. Displacement targets are
  absolute `s04` nodal components after the same hard boundary lifting used by
  the model.
- Each RMS normaliser is `max(teacher_RMS, half_ULP_RMS, float64.tiny)` and must
  be finite and strictly positive. Values, hashes and formulas are recorded
  before model initialisation.

## Initial and final judgement

- Seed, parameter initialisation and data order are fixed in the future code
  protocol. `L_judge_initial` is evaluated after construction and before the
  first optimiser call or state mutation.
- `L_judge_final` is evaluated after the last permitted update in evaluation
  mode on the identical 16 examples, weights and normalisers.
- Gradient-balancing weights, conflict projections, optimiser moments and
  physics residual scales never enter `L_judge`.

## State-sufficiency audit

The exact-commit audit on 2026-10-16 qualified the bounded Stage-0A state. The
independent physical carried state is nodal `d` plus GP `(alpha_bar, q_prev)`.
The exported GP `H` is the current undegraded energy and is not read by the
penalty kernel; `f` is deterministically reconstructed from `alpha_bar` and
the frozen fatigue parameters. Both remain in the first packet as redundant
consistency channels. Prior displacement is a nonlinear-solver initial guess,
not an independent physical history variable. The prescribed five-step load
path and frozen native geometry/quadrature, material constants, boundary masks
and producer update law complete the bounded input.

Status is `STATE_SUFFICIENCY_QUALIFIED` for s00-to-s04 only. The decoder must
still prove payload identity, native support, finite float64 storage and
numerical s05-to-next-s00 continuity before real normalisers or cycle selection
are frozen. That separate status remains `SCIENTIFIC_DATA_CAPABILITY_PENDING`.

## Multi-objective code-review gate

The future code review must freeze the exact gradient-norm scaling, conflict
projection order, zero-gradient handling, clipping and optimiser-update order.
The three reported objectives remain nodal-state data, GP-history data and
peak equilibrium. Their individual raw/scaled losses and gradients must be
logged. Hard constraints and fixed P1 acceptance metrics remain separate.

```

## FILE: docs/research/S09/S09-E008/source_state_sufficiency_audit_20261016.md

```markdown
# S09-E008 exact-source state-sufficiency audit — 2026-10-16

## Scope and identity

This is a read-only source/semantics audit for the sealed U0.125 producer run
`hard5_u0125_stage0b_f24eff2a79b64cc3a6538dd4f18f71ae`. It does not decode
the dynamic MAT payloads and does not run FEM or train a model.

The audit connected directly to `CITPC12` as `AD\\xw436` and located:

- run root
  `C:\\q4runs\\hard5_new_runs_u0115_u0125_20260827_v1\\hard5_u0125_stage0b`;
- clean producer worktree and commit
  `862992a60edc7f59335365beacb5c71fc8592a7a`;
- immutable Request-31 snapshot
  `C:\\q4runs\\request31_phaseA_snapshots\\hard5_stage0b_862992a60edc7f59_b5c39464cd4091f6`.

Ten existing lightweight run/provenance files were copied by SSH/SCP. Their
local SHA256 and byte counts match the Windows originals. Sixteen relevant
source files were exported from the exact commit; every local Git blob ID
matches `HEAD:<path>` on Windows. The retrieval and source manifests are under
`local_archive/experiments/S09-E008/producer_provenance_20261016/`.

The run receipt confirms 73 cycles, 438 logical states, 366 unique payloads,
production-new execution, clean source identity, and the expected AMOR and
AT1-penalty-fatigue binary hashes.

## Source-traced variable classification

| Variable | Classification for s00→s04 | Source evidence | Consequence for Stage 0A |
|---|---|---|---|
| nodal damage `p_field` / `d` | `physical_carried_state` | `solve_fatigue_fracture.m:115-132,182-194`; committed after each converged substep and bounded by the previous damage | required input |
| `p_field_old` | `causally_reconstructible` at committed states | `solve_fatigue_fracture.m:182-194`; set equal to committed `p_field` before history refresh | do not add a duplicate channel |
| GP `alpha_bar` | `physical_carried_state` | `at1_penalty_fatigue.f90:89-99`; new value is old `alpha_bar` plus the positive degraded-energy increment | required input |
| GP `q_prev` | `physical_carried_state` | same lines; the positive increment compares current degraded energy with old slot 3 | required input |
| GP fatigue factor `f` | `causally_reconstructible` | same lines; deterministic Carrara function of new `alpha_bar`, frozen `alpha_T` and exponent `p` | may remain as checked redundant input/output; must agree with `alpha_bar` |
| GP `H` / slot 1 | diagnostic and `causally_reconstructible` | `at1_penalty_fatigue.f90:94-99` states that the penalty formulation does not read slot 1 and stores current undegraded tensile energy | not an independent Markov state for this producer |
| `strain_en_undgr` and degraded energy | `causally_reconstructible` | equilibrium solve produces undegraded energy; degraded energy is derived from `u`, `d`, Q4 shape functions and `res_stiff` | target/physics diagnostic, not pre-state carried memory |
| nodal displacement `displ` | `solver_initial_guess_only` for the next committed transition | checkpoint code restores it; `pre_iter_update.m:28-61` advances prescribed BCs and uses the prior vector for a linear predictor before Newton convergence | optional numerical-context ablation; not required for the physical Markov state claim |
| load factors and imposed displacement | `prescribed_or_frozen` | config and five-step path are frozen and passed through the Stage-0B hooks | required external path input, already in the design |
| mesh, Q4 quadrature, material constants, BC/DOF masks, AMOR/AT1 kernels | `prescribed_or_frozen` | static export plus runtime-binary receipt | fixed operator context |
| cycle/step/staggered counters and tolerances | `prescribed_or_frozen` or `causally_reconstructible` solver control | config and loop source | receipt/control data, not learned physical state |
| detector/event bookkeeping | solver-control state for stopping only | evaluated at s05 after the transition; it is not read by equilibrium or phase-field assembly | exclude from s00→s04 input to prevent event leakage |

## Sufficiency decision

For the bounded one-cycle Stage-0A mapping under this frozen producer family,
the existing payload state `(d, H, alpha_bar, q_prev, f)` plus the prescribed
five-step load path and frozen static context contains every physical carried
state used to advance s00 to s04. The minimal independent physical state is
`(d, alpha_bar, q_prev)`; `H` and `f` are useful consistency channels but are
not independent state variables in this penalty formulation.

Status changes from `STATE_SUFFICIENCY_BLOCKED` to
`STATE_SUFFICIENCY_QUALIFIED` for Stage 0A only. This does not qualify Stage 0B
rollout, another physics family, or a real-road state.

## Remaining evidence boundaries

- The producer `source_receipt.json` records a clean commit but has an empty
  `locked_inputs` list. The copied exact-commit blobs and runtime binary hashes
  close source interpretation, but the receipt did not hash each MATLAB source
  both before and after the 2026-08-29 run.
- `validation_receipt.json` records `reference_checked=false` and
  `capture_neutrality_passed=false` even though its internal semantic checks
  passed. Therefore this audit does not establish capture neutrality or an
  independently replayed teacher.
- Dynamic payload hashes, decoded shapes/order/finiteness, numerical s05→next
  s00 equality, selected real cycle IDs and real-field normalisers remain
  untested. The next status is `SCIENTIFIC_DATA_CAPABILITY_PENDING`.

## Next executable step

Implement and independently review a read-only Stage-0A packet decoder that
verifies the sealed manifest and each selected payload hash before decoding,
retains native nodal/GP support, checks the exact channel labels and committed
timing, proves numerical s05→next-s00 equality, and emits only the frozen 16
development transitions and normaliser receipt. Do not train until that decoder
is Code Ready and the capability audit passes.

```

## FILE: docs/research/S09/S09-E008/stage0a_decoder_status_20261016.md

```markdown
# Stage-0A fail-closed decoder status — 2026-10-16

## Implemented scope

`source/s09_stage0a_packet.py` is a library-only decoder. It has no CLI, does
not discover an archive, and accepts only an explicit increasing cycle list.
Before opening any HDF5 payload it validates s00/s04 causal rows, exact native
s05 aliases, canonical state identities, convergence flags, payload paths and
all unique SHA256 values. It hashes each file again immediately before decode.

The decoder requires stored float64 arrays in the native MATLAB v7.3 layout,
then returns nodal arrays as `[node,component]`, scalar nodal damage as `[node]`,
and GP arrays as `[element,gp,channel]`. It checks finite values, damage bounds,
source cycle/substep scalars, imposed displacement and convergence. For every
cycle after the first it independently decodes the physical previous-s05 row
and requires exact numerical equality with the logical next-s00 alias.

The packet receipt records the full preflight inventory, explicit decoded
cycles, alias checks and the frozen channel order
`H|alpha_bar|q_prev|f`.

## Known boundary

MATLAB writes the three string objects through opaque MCOS storage. `h5py` can
verify their object class but does not expose their character content through
the ordinary dataset interface. Exact string semantics are therefore bound by
the sealed payload hash, exact state-index row and exact producer source, while
numeric cycle/substep/load values are checked inside the payload. This is an
explicit review item, not silently treated as decoded text.

## Verification result

Synthetic tests cover native support/order, preflight tamper detection,
immediate hash binding, s05/s00 equality, malformed alias metadata, path
escape, non-float64 rejection and non-integral metadata rejection. These tests
exercise synthetic files only. No sealed scientific payload has been decoded
by this module, no normaliser or real 16-cycle selection has been frozen, and
no training has started.

Current status: `DECODER_IMPLEMENTED_REVIEW_PENDING` and
`SCIENTIFIC_DATA_CAPABILITY_PENDING`.

```

## FILE: docs/research/S09/S09-E008/producer_provenance_receipt_20261016.json

```json
{
  "retrieved_at": "2026-10-16",
  "producer_host": "CITPC12",
  "producer_account": "AD\\xw436",
  "method": "read-only SSH/SCP",
  "remote_run_root": "C:\\q4runs\\hard5_new_runs_u0115_u0125_20260827_v1\\hard5_u0125_stage0b",
  "immutable_source_snapshot": "C:\\q4runs\\request31_phaseA_snapshots\\hard5_stage0b_862992a60edc7f59_b5c39464cd4091f6",
  "run_id": "hard5_u0125_stage0b_f24eff2a79b64cc3a6538dd4f18f71ae",
  "source_commit": "862992a60edc7f59335365beacb5c71fc8592a7a",
  "source_worktree_clean": true,
  "logical_states": 438,
  "unique_payloads": 366,
  "cycles": 73,
  "retrieved_lightweight_files": 10,
  "all_lightweight_sha256_and_bytes_match": true,
  "retrieved_exact_commit_source_files": 16,
  "all_source_git_blobs_match": true,
  "state_index_sha256": "3d815b4abc8e4d215b2d6ce747bbc728729d9ed41e7ff7dfe29dbb77695ad1f1",
  "run_summary_sha256": "e454fb5c46482f9a60e82ee4fb3f2988440b34544c5f03498ac9a55607e37eb2",
  "validation_receipt_sha256": "24a3adf4e2ae6566791e824ca3fa1dc14e3f5b04768761abbb460cd4060cd190",
  "validation_reference_checked": false,
  "validation_capture_neutrality_passed": false,
  "source_receipt_locked_inputs_empty": true,
  "local_archive_pointer": "local_archive/experiments/S09-E008/producer_provenance_20261016/",
  "scientific_payloads_decoded_during_retrieval": false,
  "fem_rerun": false,
  "training_started": false
}

```

## FILE: source/s09_stage0a_packet.py

```python
"""Fail-closed Stage-0A payload decoding for S09-E008.

This module has no CLI and does not choose or open a scientific archive by
itself.  Callers must supply an already qualified state index and explicit
cycle membership.  Every selected payload is hashed before the first HDF5
file is opened.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

import h5py
import numpy as np


SHA256 = re.compile(r"[0-9a-f]{64}")
STATE_KEY = re.compile(r"c(?P<cycle>[0-9]{4})_s(?P<substep>[0-9]{2})")
REQUIRED_DATASETS = {
    "u_node",
    "d_node",
    "history_gp",
    "strain_en_undgr_gp",
    "strain_en_degr_gp",
}


@dataclass(frozen=True)
class DecodedStage0AState:
    logical_cycle: int
    logical_substep: int
    source_state_key: str
    u_node: np.ndarray
    d_node: np.ndarray
    history_gp: np.ndarray
    strain_en_undgr_gp: np.ndarray
    strain_en_degr_gp: np.ndarray
    imposed_displacement: float
    payload_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _integer(row: dict[str, str], name: str) -> int:
    value = int(row[name])
    _require(str(value) == row[name] or row[name] == f"{value:d}",
             f"noncanonical integer {name}")
    return value


def _state_identity(key: str) -> tuple[int, int]:
    match = STATE_KEY.fullmatch(key)
    _require(match is not None, f"invalid state key: {key}")
    return int(match.group("cycle")), int(match.group("substep"))


def index_by_key(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    by_key = {row["state_key"]: row for row in rows}
    _require(len(by_key) == len(rows), "duplicate state key")
    return by_key


def _payload_path(states_dir: Path, row: dict[str, str]) -> Path:
    relative = Path(row["payload_file"])
    _require(
        relative.parts == ("states", relative.name)
        and relative.name not in ("", ".", ".."),
        f"invalid payload path for {row['state_key']}",
    )
    return states_dir / relative.name


def transition_rows(
    rows: list[dict[str, str]], cycles: tuple[int, ...] | list[int]
) -> list[tuple[dict[str, str], dict[str, str], dict[str, str] | None]]:
    """Return `(s00, s04, previous_s05)` rows after causal identity checks."""
    selected = tuple(int(cycle) for cycle in cycles)
    _require(selected == tuple(sorted(set(selected))),
             "cycles must be unique and increasing")
    _require(all(1 <= cycle <= 73 for cycle in selected), "cycle out of range")
    by_key = index_by_key(rows)
    result = []
    for cycle in selected:
        pre_key = f"c{cycle:04d}_s00"
        peak_key = f"c{cycle:04d}_s04"
        _require(pre_key in by_key and peak_key in by_key,
                 f"missing Stage-0A rows for cycle {cycle}")
        pre, peak = by_key[pre_key], by_key[peak_key]
        _require(_integer(pre, "cycle") == cycle and _integer(pre, "substep") == 0,
                 f"invalid pre row for cycle {cycle}")
        _require(_integer(peak, "cycle") == cycle and _integer(peak, "substep") == 4,
                 f"invalid peak row for cycle {cycle}")
        _require(pre["timing"] == "pre_cycle_committed",
                 f"invalid pre timing for cycle {cycle}")
        _require(peak["timing"] == "post_history_commit",
                 f"invalid peak timing for cycle {cycle}")
        _require(peak["is_alias"] == "0" and peak["source_state_key"] == peak_key,
                 f"peak row cannot be an alias for cycle {cycle}")
        previous = None
        if cycle == 1:
            _require(pre["is_alias"] == "0" and pre["source_state_key"] == pre_key,
                     "cycle-1 pre row must be native")
        else:
            previous_key = f"c{cycle - 1:04d}_s05"
            _require(previous_key in by_key, f"missing {previous_key}")
            previous = by_key[previous_key]
            _require(
                _integer(previous, "cycle") == cycle - 1
                and _integer(previous, "substep") == 5
                and previous["timing"] == "post_history_commit"
                and previous["is_alias"] == "0"
                and previous["source_state_key"] == previous_key
                and previous["converged"] == "1"
                and SHA256.fullmatch(previous["payload_sha256"]) is not None,
                f"invalid previous s05 row for cycle {cycle}",
            )
            _require(pre["is_alias"] == "1" and
                     pre["source_state_key"] == previous_key and
                     pre["payload_file"] == previous["payload_file"] and
                     pre["payload_sha256"] == previous["payload_sha256"],
                     f"invalid s00 alias for cycle {cycle}")
        for row in (pre, peak):
            _require(SHA256.fullmatch(row["payload_sha256"]) is not None,
                     f"invalid payload hash for {row['state_key']}")
            _require(row["converged"] == "1", f"unconverged {row['state_key']}")
        result.append((pre, peak, previous))
    return result


def preflight_payloads(
    states_dir: Path,
    transitions: list[tuple[dict[str, str], dict[str, str], dict[str, str] | None]],
) -> list[dict[str, object]]:
    """Hash every unique required payload before any scientific decode."""
    expected: dict[Path, str] = {}
    for pre, peak, _ in transitions:
        for row in (pre, peak):
            path = _payload_path(states_dir, row)
            prior = expected.setdefault(path, row["payload_sha256"])
            _require(prior == row["payload_sha256"],
                     f"conflicting hashes for {path.name}")
    inventory = []
    for path in sorted(expected):
        _require(path.is_file(), f"missing payload: {path.name}")
        observed = sha256_file(path)
        _require(observed == expected[path], f"preflight hash mismatch: {path.name}")
        inventory.append({"file": path.name, "sha256": observed, "bytes": path.stat().st_size})
    return inventory


def _exact_scalar(handle: h5py.File, name: str, expected: float) -> float:
    dataset = handle[name]
    _require(dataset.dtype == np.dtype("float64") and dataset.shape == (1, 1),
             f"invalid scalar storage: {name}")
    value = float(np.asarray(dataset)[0, 0])
    _require(np.isfinite(value) and value == expected, f"scalar mismatch: {name}")
    return value


def _require_matlab_string(handle: h5py.File, name: str) -> None:
    dataset = handle[name]
    value = dataset.attrs.get("MATLAB_class", b"")
    if isinstance(value, bytes):
        value = value.decode("ascii")
    _require(value == "string", f"{name} is not an exact MATLAB string")


def decode_payload(
    path: Path,
    row: dict[str, str],
    *,
    expected_nodes: int,
    expected_elements: int,
    expected_gp: int = 4,
) -> DecodedStage0AState:
    """Decode one hash-verified native payload without implicit dtype casts."""
    observed = sha256_file(path)
    _require(observed == row["payload_sha256"],
             f"immediate hash mismatch: {path.name}")
    logical_cycle = _integer(row, "cycle")
    logical_substep = _integer(row, "substep")
    source_cycle, source_substep = _state_identity(row["source_state_key"])
    with h5py.File(path, "r") as handle:
        _require(REQUIRED_DATASETS.issubset(handle.keys()),
                 f"required fields missing: {path.name}")
        expected_shapes = {
            "u_node": (2, expected_nodes),
            "d_node": (1, expected_nodes),
            "history_gp": (4, expected_gp, expected_elements),
            "strain_en_undgr_gp": (expected_gp, expected_elements),
            "strain_en_degr_gp": (expected_gp, expected_elements),
        }
        for name, shape in expected_shapes.items():
            dataset = handle[name]
            _require(dataset.dtype == np.dtype("float64"),
                     f"{name} must be stored float64")
            _require(dataset.shape == shape, f"native shape mismatch: {name}")
        _exact_scalar(handle, "state_metadata/cycle", float(source_cycle))
        _exact_scalar(handle, "state_metadata/substep", float(source_substep))
        imposed = _exact_scalar(
            handle, "state_metadata/imposed_displacement", float(row["imposed_displacement"])
        )
        _exact_scalar(handle, "state_metadata/producer_metadata/converged", 1.0)
        _require_matlab_string(handle, "state_metadata/state_key")
        _require_matlab_string(handle, "state_metadata/timing")
        _require_matlab_string(handle, "state_metadata/history_channel_labels")
        # Exact string contents are fixed by the matched source commit. MATLAB
        # v7.3 stores string objects through its opaque MCOS subsystem; row and
        # source identities therefore provide the inspectable timing/label lock.
        _require(source_substep in range(6), "source substep outside frozen path")
        u = np.asarray(handle["u_node"]).T
        d = np.asarray(handle["d_node"]).reshape(-1)
        history = np.asarray(handle["history_gp"]).transpose(2, 1, 0)
        undgr = np.asarray(handle["strain_en_undgr_gp"]).T
        degr = np.asarray(handle["strain_en_degr_gp"]).T
    for name, value in (("u_node", u), ("d_node", d), ("history_gp", history),
                        ("strain_en_undgr_gp", undgr), ("strain_en_degr_gp", degr)):
        _require(value.dtype == np.float64 and np.isfinite(value).all(),
                 f"invalid decoded values: {name}")
    _require(np.all((d >= 0) & (d <= 1)), "damage outside [0,1]")
    return DecodedStage0AState(
        logical_cycle=logical_cycle,
        logical_substep=logical_substep,
        source_state_key=row["source_state_key"],
        u_node=u,
        d_node=d,
        history_gp=history,
        strain_en_undgr_gp=undgr,
        strain_en_degr_gp=degr,
        imposed_displacement=imposed,
        payload_sha256=observed,
    )


def decode_stage0a_transitions(
    *,
    states_dir: Path,
    rows: list[dict[str, str]],
    cycles: tuple[int, ...] | list[int],
    expected_nodes: int,
    expected_elements: int,
    expected_gp: int = 4,
) -> tuple[list[tuple[DecodedStage0AState, DecodedStage0AState]], dict[str, object]]:
    """Preflight then decode explicit s00-to-s04 transitions."""
    pairs = transition_rows(rows, cycles)
    inventory = preflight_payloads(states_dir, pairs)
    decoded = []
    alias_checks = []
    for pre_row, peak_row, previous_row in pairs:
        pre_path = _payload_path(states_dir, pre_row)
        peak_path = _payload_path(states_dir, peak_row)
        kwargs = dict(expected_nodes=expected_nodes, expected_elements=expected_elements,
                      expected_gp=expected_gp)
        pre = decode_payload(pre_path, pre_row, **kwargs)
        peak = decode_payload(peak_path, peak_row, **kwargs)
        if previous_row is not None:
            previous = decode_payload(pre_path, previous_row, **kwargs)
            equal = (np.array_equal(pre.u_node, previous.u_node) and
                     np.array_equal(pre.d_node, previous.d_node) and
                     np.array_equal(pre.history_gp, previous.history_gp) and
                     np.array_equal(pre.strain_en_undgr_gp, previous.strain_en_undgr_gp) and
                     np.array_equal(pre.strain_en_degr_gp, previous.strain_en_degr_gp))
            _require(equal, f"numerical s05-to-s00 alias mismatch at cycle {pre.logical_cycle}")
            alias_checks.append(pre.logical_cycle)
        decoded.append((pre, peak))
    receipt = {
        "preflight_completed_before_decode": True,
        "payload_inventory": inventory,
        "decoded_cycles": [pre.logical_cycle for pre, _ in decoded],
        "numerical_s05_to_s00_alias_cycles": alias_checks,
        "history_channel_order": ["H", "alpha_bar", "q_prev", "f"],
    }
    return decoded, receipt

```

## FILE: source/s09_stage0a_transition.py

```python
"""Synthetic-first Stage-0A mixed-support transition operator for S09-E008.

The module defines the reviewed causal map from a committed pre-cycle state to
the peak state.  It contains no packet reader and cannot open scientific data.
"""
from __future__ import annotations

import torch
from torch import nn

from s09_equilibrium_operator import IntegralBlock, mlp
from s09_fem_physics import boundary, equilibrium


def carrara_f(alpha: torch.Tensor, alpha_t: float = 0.5, power: float = 2.0):
    """Frozen Carrara degradation relation on the native GP support."""
    threshold = alpha.new_tensor(float(alpha_t))
    return torch.minimum(torch.ones_like(alpha), (2 * threshold / (alpha + threshold)).pow(power))


def gp_coordinates(xy: torch.Tensor, conn: torch.Tensor, shape: torch.Tensor):
    return torch.einsum("enx,gn->egx", xy[conn], shape)


def node_to_gp(field: torch.Tensor, conn: torch.Tensor, shape: torch.Tensor):
    """Interpolate nodal scalar/vector features to native Q4 Gauss points."""
    if field.ndim == 1:
        return torch.einsum("en,gn->eg", field[conn], shape)
    return torch.einsum("enc,gn->egc", field[conn], shape)


def support_weights(
    conn: torch.Tensor,
    shape: torch.Tensor,
    det: torch.Tensor,
    nnode: int,
    thickness: float = 1.0,
):
    """Return GP integration weights and consistent positive nodal lumping."""
    gp_weight = det * float(thickness)
    local = torch.einsum("gn,eg->en", shape, gp_weight)
    nodal = det.new_zeros(nnode).index_add(0, conn.reshape(-1), local.reshape(-1))
    if not torch.isfinite(gp_weight).all() or not torch.isfinite(nodal).all():
        raise ValueError("nonfinite Q4 support weights")
    if torch.any(gp_weight <= 0) or torch.any(nodal <= 0):
        raise ValueError("nonpositive Q4 support weights")
    return gp_weight, nodal


def gp_to_node(
    field: torch.Tensor,
    conn: torch.Tensor,
    shape: torch.Tensor,
    gp_weight: torch.Tensor,
    nodal_weight: torch.Tensor,
):
    """Project native GP features to nodes by consistent weighted assembly."""
    if field.ndim == 2:
        local = torch.einsum("eg,gn,eg->en", field, shape, gp_weight)
        assembled = field.new_zeros(len(nodal_weight)).index_add(
            0, conn.reshape(-1), local.reshape(-1)
        )
        return assembled / nodal_weight
    local = torch.einsum("egc,gn,eg->enc", field, shape, gp_weight)
    assembled = field.new_zeros((len(nodal_weight), field.shape[-1])).index_add(
        0, conn.reshape(-1), local.reshape(-1, field.shape[-1])
    )
    return assembled / nodal_weight[:, None]


class Stage0ATransitionOperator(nn.Module):
    """Map ``(d_pre, history_pre, prescribed_path)`` to peak d/history/u."""

    def __init__(
        self,
        damage_increment_scale: float,
        history_increment_scale,
        displacement_scale,
        *,
        width: int = 32,
        rank: int = 8,
        alpha_t: float = 0.5,
        fatigue_power: float = 2.0,
    ):
        super().__init__()
        history_scale = torch.as_tensor(history_increment_scale, dtype=torch.float32)
        displacement_scale = torch.as_tensor(displacement_scale, dtype=torch.float32)
        if history_scale.shape != (3,) or displacement_scale.shape != (2,):
            raise ValueError("history scale must have 3 entries and displacement scale 2")
        if damage_increment_scale <= 0 or torch.any(history_scale <= 0) or torch.any(displacement_scale <= 0):
            raise ValueError("all output scales must be positive")
        self.register_buffer("damage_increment_scale", torch.tensor(float(damage_increment_scale)))
        self.register_buffer("history_increment_scale", history_scale)
        self.register_buffer("displacement_scale", displacement_scale)
        self.alpha_t = float(alpha_t)
        self.fatigue_power = float(fatigue_power)

        # node: d, xy, boundary flag, six prescribed path values
        self.node_encoder = mlp(10, width, width)
        # GP: H, alpha_bar, q_prev, f, xy, six prescribed path values
        self.gp_encoder = mlp(12, width, width)
        self.node_fusion = mlp(2 * width, width, width)
        self.local_blocks = nn.ModuleList([IntegralBlock(width, rank) for _ in range(2)])
        self.coarse_block = IntegralBlock(width, rank)
        self.node_decoder = mlp(3 * width, width, 3)  # raw delta-d, ux, uy
        self.gp_decoder = mlp(3 * width, width, 3)  # raw delta-H, alpha, q
        for decoder in (self.node_decoder, self.gp_decoder):
            nn.init.zeros_(decoder[-1].weight)
            nn.init.zeros_(decoder[-1].bias)

    def _validate(self, d_pre, history_pre, path, graph, conn, shape, det):
        nnode = len(graph["xy"])
        if d_pre.shape != (nnode,):
            raise ValueError("d_pre must be [node]")
        if history_pre.shape != (len(conn), 4, 4):
            raise ValueError("history_pre must be [element,4GP,H|alpha|q|f]")
        if path.shape != (6,):
            raise ValueError("path must contain s00..s05 prescribed displacements")
        if shape.shape != (4, 4) or det.shape != (len(conn), 4):
            raise ValueError("native Q4 shape/determinant mismatch")
        tensors = (d_pre, history_pre, path, graph["xy"], shape, det)
        if not all(torch.isfinite(value).all() for value in tensors):
            raise ValueError("nonfinite Stage-0A input")
        if torch.any(d_pre < 0) or torch.any(d_pre > 1):
            raise ValueError("pre-cycle damage must lie in [0,1]")
        if torch.any(history_pre[..., 1] < 0):
            raise ValueError("pre-cycle alpha_bar must be nonnegative")
        expected_f = carrara_f(history_pre[..., 1], self.alpha_t, self.fatigue_power)
        if not torch.allclose(history_pre[..., 3], expected_f, atol=1e-12, rtol=1e-10):
            raise ValueError("pre-cycle f is inconsistent with frozen Carrara law")
        if not (torch.isclose(path[0], path.new_zeros(())) and torch.isclose(path[5], path.new_zeros(()))):
            raise ValueError("Stage-0A path must start and end unloaded")
        if torch.any(path[1:5] < path[:4]) or path[4] <= 0:
            raise ValueError("Stage-0A loading path must increase through s04 peak")

    def raw(self, d_pre, history_pre, path, graph, conn, shape, det, thickness=1.0):
        self._validate(d_pre, history_pre, path, graph, conn, shape, det)
        gp_weight, nodal_weight = support_weights(conn, shape, det, len(d_pre), thickness)
        if not torch.allclose(graph["area"], nodal_weight, atol=1e-12, rtol=1e-10):
            raise ValueError("graph area does not match native Q4 nodal lumping")
        path_node = path[None].expand(len(d_pre), -1)
        node_input = torch.cat(
            (d_pre[:, None], graph["xy"], graph["boundary"][:, None].to(d_pre.dtype), path_node),
            dim=1,
        )
        gp_xy = gp_coordinates(graph["xy"], conn, shape)
        path_gp = path[None, None].expand(len(conn), 4, -1)
        gp_input = torch.cat((history_pre, gp_xy, path_gp), dim=-1)
        node_initial = self.node_encoder(node_input)
        gp_initial = self.gp_encoder(gp_input)
        history_at_nodes = gp_to_node(gp_initial, conn, shape, gp_weight, nodal_weight)
        encoded = self.node_fusion(torch.cat((node_initial, history_at_nodes), dim=-1))

        local = encoded
        for block in self.local_blocks:
            local = block(local, graph["edges"], graph["relative"], graph["weight"])
        cluster = graph["cluster"]
        coarse = local.new_zeros((len(graph["coarse_area"]), local.shape[-1]))
        coarse.index_add_(0, cluster, local * graph["area"][:, None])
        coarse = coarse / graph["coarse_area"][:, None]
        coarse = self.coarse_block(
            coarse, graph["coarse_edges"], graph["coarse_relative"], graph["coarse_weight"]
        )
        raw_node = self.node_decoder(torch.cat((encoded, local, coarse[cluster]), dim=-1))
        encoded_gp = node_to_gp(encoded, conn, shape)
        local_gp = node_to_gp(local, conn, shape)
        raw_history = self.gp_decoder(torch.cat((gp_initial, encoded_gp, local_gp), dim=-1))
        return raw_node, raw_history, gp_weight, nodal_weight

    def forward(self, d_pre, history_pre, path, graph, conn, shape, det, thickness=1.0):
        raw_node, raw_history, gp_weight, nodal_weight = self.raw(
            d_pre, history_pre, path, graph, conn, shape, det, thickness
        )
        d_proposal = d_pre + raw_node[:, 0] * self.damage_increment_scale
        d_peak = torch.maximum(d_pre, d_proposal).clamp(max=1.0)

        h_peak = history_pre[..., 0] + raw_history[..., 0] * self.history_increment_scale[0]
        alpha_peak = history_pre[..., 1] + torch.relu(
            raw_history[..., 1] * self.history_increment_scale[1]
        )
        q_peak = history_pre[..., 2] + raw_history[..., 2] * self.history_increment_scale[2]
        f_peak = carrara_f(alpha_peak, self.alpha_t, self.fatigue_power)
        history_peak = torch.stack((h_peak, alpha_peak, q_peak, f_peak), dim=-1)

        y = graph["xy"][:, 1]
        t = (y - y.min()) / (y.max() - y.min())
        peak_load = path[4]
        affine = torch.stack((torch.zeros_like(t), peak_load * t), dim=-1)
        correction = (t * (1 - t))[:, None] * raw_node[:, 1:] * self.displacement_scale
        u_peak = affine + correction
        return {
            "d_peak": d_peak,
            "history_peak": history_peak,
            "u_peak": u_peak,
            "raw_node": raw_node,
            "raw_history": raw_history,
            "gp_weight": gp_weight,
            "nodal_weight": nodal_weight,
        }


def _weighted_mse(error: torch.Tensor, weight: torch.Tensor):
    if error.ndim == weight.ndim:
        return (error.square() * weight).sum() / weight.sum()
    return (error.square() * weight[..., None]).sum(dim=tuple(range(error.ndim - 1))) / weight.sum()


def stage0a_objectives(
    prediction: dict,
    target: dict,
    scales: dict,
    *,
    conn: torch.Tensor,
    shape: torch.Tensor,
    dshape: torch.Tensor,
    det: torch.Tensor,
    xy: torch.Tensor,
    equilibrium_scale: float,
):
    """Return separate nodal, GP-history and equilibrium objectives."""
    if equilibrium_scale <= 0:
        raise ValueError("equilibrium scale must be positive")
    nw, gw = prediction["nodal_weight"], prediction["gp_weight"]
    d_error = (prediction["d_peak"] - target["d_peak"]) / scales["d"]
    u_error = (prediction["u_peak"] - target["u_peak"]) / scales["u"]
    h_error = (prediction["history_peak"] - target["history_peak"]) / scales["history"]
    nodal = (_weighted_mse(d_error, nw) + _weighted_mse(u_error, nw).mean()) / 2
    history = _weighted_mse(h_error, gw).mean()
    force, _ = equilibrium(prediction["u_peak"], prediction["d_peak"], conn, shape, dshape, det)
    free = boundary(xy)
    mechanics = force[free].square().mean() / float(equilibrium_scale)
    return {"nodal_state": nodal, "gp_history": history, "equilibrium": mechanics}


def raw_increment_objectives(
    prediction: dict,
    target: dict,
    d_pre: torch.Tensor,
    history_pre: torch.Tensor,
    model: Stage0ATransitionOperator,
):
    """Teacher raw increments keep gradients alive behind hard projections."""
    raw_d_target = (target["d_peak"] - d_pre) / model.damage_increment_scale
    raw_h_target = (
        target["history_peak"][..., :3] - history_pre[..., :3]
    ) / model.history_increment_scale
    raw_d = _weighted_mse(prediction["raw_node"][:, 0] - raw_d_target, prediction["nodal_weight"])
    raw_h = _weighted_mse(prediction["raw_history"] - raw_h_target, prediction["gp_weight"]).mean()
    return {"raw_nodal_increment": raw_d, "raw_gp_increment": raw_h}


def fixed_judgement_loss(prediction: dict, target: dict, scales: dict):
    """Reviewed P1 metric; adaptive training weights never enter this formula."""
    nw, gw = prediction["nodal_weight"], prediction["gp_weight"]
    d = _weighted_mse((prediction["d_peak"] - target["d_peak"]) / scales["d"], nw)
    u = _weighted_mse((prediction["u_peak"] - target["u_peak"]) / scales["u"], nw).mean()
    h = _weighted_mse(
        (prediction["history_peak"] - target["history_peak"]) / scales["history"], gw
    ).mean()
    return (d + h + u) / 3

```

## FILE: source/s09_stage0a_p1_freeze.py

```python
"""Deterministic in-memory P1 selection and scale freeze for S09-E008.

No file reader is provided: scientific payload access remains separately gated.
"""
from __future__ import annotations

import math
import numpy as np


def require_float64(name: str, value) -> np.ndarray:
    array = np.asarray(value)
    if array.dtype != np.float64:
        raise ValueError(f"{name} must be stored float64")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains nonfinite values")
    return array


def half_ulp_float64(value) -> np.ndarray:
    """Representable half-ULP convention with a subnormal lower clamp."""
    x = require_float64("half_ulp input", value)
    upper = np.nextafter(x, np.inf) - x
    lower = x - np.nextafter(x, -np.inf)
    spacing = np.minimum(upper, lower)
    smallest = np.nextafter(np.float64(0), np.float64(1))
    return np.maximum(spacing * np.float64(0.5), smallest)


def weighted_mean_per_sample(value: np.ndarray, weight: np.ndarray) -> np.ndarray:
    axes = tuple(range(1, value.ndim))
    expanded = weight
    while expanded.ndim < value.ndim:
        expanded = expanded[None]
    denominator = weight.sum()
    return (value * expanded).sum(axis=axes) / denominator


def weighted_rms(value: np.ndarray, weight: np.ndarray) -> np.ndarray:
    """RMS over sample and support axes, retaining a final channel axis."""
    if value.ndim == weight.ndim + 1:
        return np.sqrt((np.square(value) * weight[None]).sum() /
                       (value.shape[0] * weight.sum()))
    if value.ndim == weight.ndim + 2:
        expanded = weight[None, ..., None]
        return np.sqrt((np.square(value) * expanded).sum(tuple(range(value.ndim - 1))) /
                       (value.shape[0] * weight.sum()))
    raise ValueError("unsupported weighted RMS shapes")


def _median(values: np.ndarray) -> float:
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    n = len(ordered)
    if n == 0:
        raise ValueError("median of empty group")
    if n % 2:
        return float(ordered[n // 2])
    return float((ordered[n // 2 - 1] + ordered[n // 2]) / 2)


def freeze_p1_contract(
    *,
    cycles,
    d_pre,
    d_peak,
    history_pre,
    history_peak,
    u_peak,
    nodal_weight,
    gp_weight,
) -> dict:
    """Freeze the reviewed 16-cycle selection and fixed teacher normalisers."""
    cycles = np.asarray(cycles)
    if cycles.dtype.kind not in "iu" or tuple(cycles.tolist()) != tuple(range(1, 74)):
        raise ValueError("eligible cycles must be exact integers 1..73")
    d_pre = require_float64("d_pre", d_pre)
    d_peak = require_float64("d_peak", d_peak)
    history_pre = require_float64("history_pre", history_pre)
    history_peak = require_float64("history_peak", history_peak)
    u_peak = require_float64("u_peak", u_peak)
    nodal_weight = require_float64("nodal_weight", nodal_weight)
    gp_weight = require_float64("gp_weight", gp_weight)
    if d_pre.shape != d_peak.shape or d_pre.shape[0] != 73:
        raise ValueError("damage arrays must be [73,node]")
    if history_pre.shape != history_peak.shape or history_pre.shape != (73, *gp_weight.shape, 4):
        raise ValueError("history arrays must be [73,element,4GP,4]")
    if u_peak.shape != (73, d_pre.shape[1], 2):
        raise ValueError("u_peak must be [73,node,2]")
    if nodal_weight.shape != (d_pre.shape[1],) or np.any(nodal_weight <= 0):
        raise ValueError("invalid nodal weights")
    if gp_weight.ndim != 2 or gp_weight.shape[1] != 4 or np.any(gp_weight <= 0):
        raise ValueError("invalid GP weights")

    delta_d = d_peak - d_pre
    g = (np.abs(delta_d) * nodal_weight[None]).sum(axis=1) / nodal_weight.sum()
    export = half_ulp_float64(d_pre) + half_ulp_float64(d_peak)
    eta = float(np.max((export * nodal_weight[None]).sum(axis=1) / nodal_weight.sum()))
    order = np.lexsort((cycles, g))
    upper_count = math.ceil(len(cycles) / 4)
    d_scale = _median(g[order[-upper_count:]])
    if not np.isfinite(d_scale) or d_scale <= 0:
        raise ValueError("detectable-growth scale D must be positive")
    near_limit = max(10 * eta, 0.05 * d_scale)

    selected: set[int] = set()
    for start, stop in ((1, 24), (25, 49), (50, 73)):
        band = np.flatnonzero((cycles >= start) & (cycles <= stop))
        ranked = band[np.lexsort((cycles[band], g[band]))]
        selected.update(cycles[ranked[:2]].tolist())
        selected.update(cycles[ranked[-2:]].tolist())
    remaining = np.array([i for i in order if int(cycles[i]) not in selected], dtype=np.int64)
    selected.update(cycles[remaining[:2]].tolist())
    selected.update(cycles[remaining[-2:]].tolist())
    chosen = np.array(sorted(selected), dtype=np.int64)
    if len(chosen) != 16:
        raise ValueError("deterministic selection must contain exactly 16 cycles")
    chosen_index = chosen - 1
    growth = chosen[g[chosen_index] >= d_scale]
    stagnant = chosen[g[chosen_index] <= near_limit]
    if len(growth) < 4 or len(stagnant) < 4:
        raise ValueError("P1_NOT_READY: insufficient growth or near-stagnant selected cycles")

    tiny = np.finfo(np.float64).tiny
    dd = delta_d[chosen_index]
    dh = (history_peak - history_pre)[chosen_index]
    uu = u_peak[chosen_index]
    dd_floor = half_ulp_float64(d_pre[chosen_index]) + half_ulp_float64(d_peak[chosen_index])
    dh_floor = half_ulp_float64(history_pre[chosen_index]) + half_ulp_float64(history_peak[chosen_index])
    uu_floor = half_ulp_float64(uu)
    normalisers = {
        "damage_increment": float(max(weighted_rms(dd, nodal_weight), weighted_rms(dd_floor, nodal_weight), tiny)),
        "history_increment": np.maximum.reduce((
            weighted_rms(dh, gp_weight), weighted_rms(dh_floor, gp_weight), np.full(4, tiny)
        )).tolist(),
        "displacement": np.maximum.reduce((
            weighted_rms(uu, nodal_weight), weighted_rms(uu_floor, nodal_weight), np.full(2, tiny)
        )).tolist(),
    }
    flat = np.array([normalisers["damage_increment"], *normalisers["history_increment"],
                     *normalisers["displacement"]])
    if not np.isfinite(flat).all() or np.any(flat <= 0):
        raise ValueError("all P1 normalisers must be finite and positive")
    return {
        "verdict": "P1_CONTRACT_FROZEN",
        "eligible_cycles": cycles.tolist(),
        "selected_cycles": chosen.tolist(),
        "growth_cycles": growth.tolist(),
        "near_stagnant_cycles": stagnant.tolist(),
        "eta": eta,
        "D": d_scale,
        "near_stagnant_limit": near_limit,
        "normalisers": normalisers,
        "scientific_execution_authorized": False,
    }

```

## FILE: tests/test_s09_stage0a_packet.py

```python
import hashlib
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_stage0a_packet import (
    decode_payload,
    decode_stage0a_transitions,
    preflight_payloads,
    transition_rows,
)


def write_payload(path: Path, *, cycle: int, substep: int, load: float,
                  nodes: int = 4, elements: int = 2, dtype=np.float64):
    with h5py.File(path, "w") as handle:
        handle.create_dataset("u_node", data=np.arange(2 * nodes, dtype=dtype).reshape(2, nodes))
        handle.create_dataset("d_node", data=np.linspace(0, .5, nodes, dtype=dtype)[None])
        handle.create_dataset("history_gp", data=np.ones((4, 4, elements), dtype=dtype))
        handle.create_dataset("strain_en_undgr_gp", data=np.ones((4, elements), dtype=dtype))
        handle.create_dataset("strain_en_degr_gp", data=np.ones((4, elements), dtype=dtype) * .5)
        metadata = handle.create_group("state_metadata")
        metadata.create_dataset("cycle", data=np.array([[cycle]], dtype=np.float64))
        metadata.create_dataset("substep", data=np.array([[substep]], dtype=np.float64))
        metadata.create_dataset("imposed_displacement", data=np.array([[load]], dtype=np.float64))
        producer = metadata.create_group("producer_metadata")
        producer.create_dataset("converged", data=np.array([[1.]], dtype=np.float64))
        for name in ("state_key", "timing", "history_channel_labels"):
            dataset = metadata.create_dataset(name, data=np.zeros((1, 1), dtype=np.uint32))
            dataset.attrs["MATLAB_class"] = np.bytes_(b"string")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row(*, cycle: int, substep: int, source: str, file: str, sha: str,
        alias: bool, load: float, timing: str):
    return {
        "state_key": f"c{cycle:04d}_s{substep:02d}",
        "cycle": str(cycle),
        "substep": str(substep),
        "source_state_key": source,
        "payload_file": f"states/{file}",
        "payload_sha256": sha,
        "is_alias": "1" if alias else "0",
        "converged": "1",
        "imposed_displacement": repr(load),
        "timing": timing,
    }


def two_cycle_fixture(tmp_path: Path):
    c1_pre = tmp_path / "c0001_s00.mat"
    c1_peak = tmp_path / "c0001_s04.mat"
    c1_post = tmp_path / "c0001_s05.mat"
    c2_peak = tmp_path / "c0002_s04.mat"
    write_payload(c1_pre, cycle=1, substep=0, load=0.0)
    write_payload(c1_peak, cycle=1, substep=4, load=.125)
    write_payload(c1_post, cycle=1, substep=5, load=0.0)
    write_payload(c2_peak, cycle=2, substep=4, load=.125)
    rows = [
        row(cycle=1, substep=0, source="c0001_s00", file=c1_pre.name,
            sha=digest(c1_pre), alias=False, load=0.0, timing="pre_cycle_committed"),
        row(cycle=1, substep=4, source="c0001_s04", file=c1_peak.name,
            sha=digest(c1_peak), alias=False, load=.125, timing="post_history_commit"),
        row(cycle=1, substep=5, source="c0001_s05", file=c1_post.name,
            sha=digest(c1_post), alias=False, load=0.0, timing="post_history_commit"),
        row(cycle=2, substep=0, source="c0001_s05", file=c1_post.name,
            sha=digest(c1_post), alias=True, load=0.0, timing="pre_cycle_committed"),
        row(cycle=2, substep=4, source="c0002_s04", file=c2_peak.name,
            sha=digest(c2_peak), alias=False, load=.125, timing="post_history_commit"),
    ]
    return rows


def test_transition_rows_requires_exact_alias_identity(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    pairs = transition_rows(rows, [1, 2])
    assert pairs[1][2]["state_key"] == "c0001_s05"
    bad = [dict(value) for value in rows]
    bad[3]["payload_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="alias"):
        transition_rows(bad, [2])


def test_transition_rows_rejects_malformed_previous_s05(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    rows[2]["timing"] = "pre_cycle_committed"
    with pytest.raises(ValueError, match="previous s05"):
        transition_rows(rows, [2])


def test_preflight_hashes_all_payloads_before_decode(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    pairs = transition_rows(rows, [1, 2])
    inventory = preflight_payloads(tmp_path, pairs)
    assert len(inventory) == 4
    (tmp_path / "c0002_s04.mat").write_bytes(b"changed")
    with pytest.raises(ValueError, match="preflight hash"):
        preflight_payloads(tmp_path, pairs)


def test_preflight_rejects_payload_path_escape(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    rows[0]["payload_file"] = "../c0001_s00.mat"
    with pytest.raises(ValueError, match="payload path"):
        preflight_payloads(tmp_path, transition_rows(rows, [1]))


def test_decoder_preserves_native_support_and_alias_equality(tmp_path: Path):
    rows = two_cycle_fixture(tmp_path)
    decoded, receipt = decode_stage0a_transitions(
        states_dir=tmp_path, rows=rows, cycles=[1, 2],
        expected_nodes=4, expected_elements=2,
    )
    assert len(decoded) == 2
    pre, peak = decoded[1]
    assert pre.d_node.shape == (4,)
    assert pre.u_node.shape == (4, 2)
    assert pre.history_gp.shape == (2, 4, 4)
    assert peak.strain_en_undgr_gp.shape == (2, 4)
    assert receipt["preflight_completed_before_decode"] is True
    assert receipt["numerical_s05_to_s00_alias_cycles"] == [2]


def test_decoder_rejects_non_float64_without_cast(tmp_path: Path):
    path = tmp_path / "bad.mat"
    write_payload(path, cycle=1, substep=4, load=.125, dtype=np.float32)
    item = row(cycle=1, substep=4, source="c0001_s04", file=path.name,
               sha=digest(path), alias=False, load=.125, timing="post_history_commit")
    with pytest.raises(ValueError, match="stored float64"):
        decode_payload(path, item, expected_nodes=4, expected_elements=2)


def test_decoder_rejects_logical_metadata_rounding(tmp_path: Path):
    path = tmp_path / "rounded.mat"
    write_payload(path, cycle=1, substep=4, load=.125)
    with h5py.File(path, "r+") as handle:
        handle["state_metadata/cycle"][0, 0] = 1.25
    item = row(cycle=1, substep=4, source="c0001_s04", file=path.name,
               sha=digest(path), alias=False, load=.125, timing="post_history_commit")
    with pytest.raises(ValueError, match="cycle"):
        decode_payload(path, item, expected_nodes=4, expected_elements=2)

```

## FILE: tests/test_s09_stage0a_transition.py

```python
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_equilibrium_operator import build_graph, graph_to_torch
from s09_q4_quadrature import q4_shape_data
from s09_stage0a_transition import (
    Stage0ATransitionOperator,
    carrara_f,
    fixed_judgement_loss,
    gp_to_node,
    node_to_gp,
    raw_increment_objectives,
    stage0a_objectives,
    support_weights,
)


def fixture(dtype=torch.float64):
    xy_np = np.array([[i / 2, j / 2] for j in range(3) for i in range(3)], dtype=np.float64)
    conn_np = np.array([[0, 1, 4, 3], [1, 2, 5, 4], [3, 4, 7, 6], [4, 5, 8, 7]])
    area = np.array([1, 2, 1, 2, 4, 2, 1, 2, 1], dtype=np.float64) / 16
    graph = graph_to_torch(build_graph(xy_np, conn_np, area, bins=2), "cpu", dtype=dtype)
    conn = torch.as_tensor(conn_np)
    shape, dshape, det = q4_shape_data(graph["xy"], conn)
    d_pre = torch.linspace(0.0, 0.4, len(xy_np), dtype=dtype)
    alpha = torch.full((4, 4), 0.2, dtype=dtype)
    history = torch.stack(
        (torch.full_like(alpha, 0.3), alpha, torch.full_like(alpha, 0.1), carrara_f(alpha)),
        dim=-1,
    )
    path = torch.tensor([0, 0.03125, 0.0625, 0.09375, 0.125, 0], dtype=dtype)
    model = Stage0ATransitionOperator(0.1, [0.2, 0.2, 0.2], [0.1, 0.1], width=8, rank=3).to(dtype)
    return model, graph, conn, shape, dshape, det, d_pre, history, path


def test_q4_messages_preserve_constant_fields_and_support_mass():
    _, graph, conn, shape, _, det, *_ = fixture()
    gp_weight, nodal_weight = support_weights(conn, shape, det, len(graph["xy"]))
    nodes = torch.ones((len(graph["xy"]), 3), dtype=graph["xy"].dtype)
    gp = node_to_gp(nodes, conn, shape)
    torch.testing.assert_close(gp, torch.ones_like(gp))
    back = gp_to_node(gp, conn, shape, gp_weight, nodal_weight)
    torch.testing.assert_close(back, torch.ones_like(back))
    torch.testing.assert_close(nodal_weight.sum(), gp_weight.sum())


def test_zero_heads_preserve_state_and_enforce_peak_boundary():
    model, graph, conn, shape, _, det, d_pre, history, path = fixture()
    out = model(d_pre, history, path, graph, conn, shape, det)
    torch.testing.assert_close(out["d_peak"], d_pre)
    torch.testing.assert_close(out["history_peak"], history)
    y = graph["xy"][:, 1]
    bottom, top = y == y.min(), y == y.max()
    torch.testing.assert_close(out["u_peak"][bottom], torch.zeros((3, 2), dtype=y.dtype))
    torch.testing.assert_close(out["u_peak"][top, 0], torch.zeros(3, dtype=y.dtype))
    torch.testing.assert_close(out["u_peak"][top, 1], torch.full((3,), path[4], dtype=y.dtype))


def test_projected_outputs_obey_damage_alpha_and_carrara_constraints():
    model, graph, conn, shape, _, det, d_pre, history, path = fixture()
    with torch.no_grad():
        model.node_decoder[-1].bias[:] = torch.tensor([-2.0, 0.2, -0.3], dtype=d_pre.dtype)
        model.gp_decoder[-1].bias[:] = torch.tensor([0.1, 0.5, -0.2], dtype=d_pre.dtype)
    out = model(d_pre, history, path, graph, conn, shape, det)
    assert torch.all(out["d_peak"] >= d_pre)
    assert torch.all(out["d_peak"] <= 1)
    assert torch.all(out["history_peak"][..., 1] >= history[..., 1])
    assert torch.all(out["history_peak"][..., 3] <= history[..., 3])
    torch.testing.assert_close(out["history_peak"][..., 3], carrara_f(out["history_peak"][..., 1]))


def test_separate_objectives_and_fixed_judgement_are_finite_and_differentiable():
    model, graph, conn, shape, dshape, det, d_pre, history, path = fixture()
    out = model(d_pre, history, path, graph, conn, shape, det)
    target = {
        "d_peak": (d_pre + 0.01).clamp(max=1),
        "history_peak": history + torch.tensor([0.01, 0.02, 0.01, -0.01], dtype=d_pre.dtype),
        "u_peak": out["u_peak"].detach() + 0.005 * (graph["xy"][:, 1] * (1-graph["xy"][:, 1]))[:, None],
    }
    scales = {
        "d": torch.tensor(0.1, dtype=d_pre.dtype),
        "u": torch.tensor([0.1, 0.1], dtype=d_pre.dtype),
        "history": torch.tensor([0.2, 0.2, 0.2, 0.2], dtype=d_pre.dtype),
    }
    objectives = stage0a_objectives(
        out, target, scales, conn=conn, shape=shape, dshape=dshape, det=det,
        xy=graph["xy"], equilibrium_scale=1.0,
    )
    assert set(objectives) == {"nodal_state", "gp_history", "equilibrium"}
    assert all(torch.isfinite(value) for value in objectives.values())
    judgement = fixed_judgement_loss(out, target, scales)
    torch.testing.assert_close(
        judgement,
        (2 * objectives["nodal_state"] + objectives["gp_history"]) / 3,
    )
    sum(objectives.values()).backward()
    assert model.node_decoder[-1].weight.grad.abs().sum() > 0
    assert model.gp_decoder[-1].weight.grad.abs().sum() > 0


def test_raw_increment_supervision_corrects_negative_projected_proposals():
    model, graph, conn, shape, _, det, d_pre, history, path = fixture()
    with torch.no_grad():
        model.node_decoder[-1].bias[0] = -1
        model.gp_decoder[-1].bias[1] = -1
    out = model(d_pre, history, path, graph, conn, shape, det)
    target_history = history.clone()
    target_history[..., 1] += 0.02
    target_history[..., 3] = carrara_f(target_history[..., 1])
    target = {"d_peak": d_pre + 0.01, "history_peak": target_history}
    losses = raw_increment_objectives(out, target, d_pre, history, model)
    sum(losses.values()).backward()
    assert model.node_decoder[-1].bias.grad[0] < 0
    assert model.gp_decoder[-1].bias.grad[1] < 0


def test_api_rejects_wrong_time_or_support_shapes():
    model, graph, conn, shape, _, det, d_pre, history, path = fixture()
    for bad_path in (path[:-1], torch.cat((path[:-1], torch.tensor([float("nan")])))):
        try:
            model(d_pre, history, bad_path, graph, conn, shape, det)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid path must fail closed")


def test_api_rejects_invalid_prestate_and_area_identity():
    model, graph, conn, shape, _, det, d_pre, history, path = fixture()
    cases = []
    bad_d = d_pre.clone(); bad_d[0] = -0.1
    cases.append((bad_d, history, graph))
    bad_h = history.clone(); bad_h[0, 0, 3] = 0.4
    cases.append((d_pre, bad_h, graph))
    bad_graph = dict(graph); bad_graph["area"] = graph["area"] * 2
    cases.append((d_pre, history, bad_graph))
    for damage, state, candidate_graph in cases:
        try:
            model(damage, state, path, candidate_graph, conn, shape, det)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid causal pre-state must fail closed")

```

## FILE: tests/test_s09_stage0a_p1_freeze.py

```python
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source"))
from s09_multiobjective_update import merge_objective_gradients
from s09_stage0a_p1_freeze import freeze_p1_contract, half_ulp_float64


def synthetic_fields():
    cycles = np.arange(1, 74, dtype=np.int64)
    nodes, elements = 5, 2
    nodal_weight = np.array([1, 2, 3, 2, 1], dtype=np.float64)
    gp_weight = np.ones((elements, 4), dtype=np.float64)
    d_pre = np.zeros((73, nodes), dtype=np.float64)
    # Lowest cycles in every band are near-stagnant; upper ranks have clear growth.
    magnitude = np.linspace(0, 0.2, 73, dtype=np.float64)
    d_peak = d_pre + magnitude[:, None]
    h_pre = np.zeros((73, elements, 4, 4), dtype=np.float64)
    h_peak = h_pre + magnitude[:, None, None, None] * np.array([1, 2, 1, -1], dtype=np.float64)
    u_peak = np.ones((73, nodes, 2), dtype=np.float64) * np.array([0.01, 0.1])
    return dict(cycles=cycles, d_pre=d_pre, d_peak=d_peak, history_pre=h_pre,
                history_peak=h_peak, u_peak=u_peak, nodal_weight=nodal_weight,
                gp_weight=gp_weight)


def test_half_ulp_is_positive_and_representable_at_zero():
    values = np.array([0.0, 1.0, -1.0, np.finfo(np.float64).tiny], dtype=np.float64)
    got = half_ulp_float64(values)
    assert got.dtype == np.float64
    assert np.all(got > 0)
    assert got[0] == np.nextafter(np.float64(0), np.float64(1))


def test_p1_freeze_is_deterministic_and_has_positive_normalisers():
    fields = synthetic_fields()
    left = freeze_p1_contract(**fields)
    right = freeze_p1_contract(**fields)
    assert left == right
    assert len(left["selected_cycles"]) == 16
    assert len(left["growth_cycles"]) >= 4
    assert len(left["near_stagnant_cycles"]) >= 4
    scales = [left["normalisers"]["damage_increment"],
              *left["normalisers"]["history_increment"],
              *left["normalisers"]["displacement"]]
    assert np.all(np.isfinite(scales)) and np.all(np.array(scales) > 0)
    assert left["scientific_execution_authorized"] is False


def test_p1_freeze_rejects_dtype_and_empty_stagnant_group():
    fields = synthetic_fields()
    bad = dict(fields); bad["d_pre"] = bad["d_pre"].astype(np.float32)
    with pytest.raises(ValueError, match="float64"):
        freeze_p1_contract(**bad)
    no_stagnation = dict(fields)
    no_stagnation["d_peak"] = np.ones_like(fields["d_peak"]) * 0.2
    with pytest.raises(ValueError, match="P1_NOT_READY"):
        freeze_p1_contract(**no_stagnation)


def test_gradient_merge_projects_conflicts_and_clips_deterministically():
    gradients = [torch.tensor([2.0, 0.0]), torch.tensor([-1.0, 1.0]), torch.tensor([0.0, 3.0])]
    left, diagnostic_left = merge_objective_gradients(gradients, clip_norm=0.5)
    right, diagnostic_right = merge_objective_gradients(gradients, clip_norm=0.5)
    torch.testing.assert_close(left, right)
    assert diagnostic_left["conflict_projection_count"] > 0
    assert diagnostic_left["merged_norm_after_clip"] <= 0.5 + 1e-7
    assert diagnostic_left["order"] == diagnostic_right["order"]


def test_gradient_merge_handles_zero_and_rejects_nonfinite():
    merged, diagnostics = merge_objective_gradients([torch.zeros(2), torch.tensor([1.0, 0.0])])
    assert torch.isfinite(merged).all()
    assert diagnostics["zero_gradient_count"] == 1
    with pytest.raises(FloatingPointError):
        merge_objective_gradients([torch.tensor([float("nan"), 0.0])])

```
