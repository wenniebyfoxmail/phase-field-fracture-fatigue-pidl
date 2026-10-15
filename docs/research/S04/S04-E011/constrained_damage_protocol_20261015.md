# Fixed captured-u nodal damage repair — protocol r1, 2026-10-15

Storyline S04 / parent experiment S04-E011; synthetic C1 numerical diagnostic.
Run proposed: `pf_s04e011_damage_repair_20261015_v1`, not launched. This
supplement changes solver controls and adds nodal constraints, not the frozen
E003/E011 production results or their original verdicts.

Question: can fresh stopping alone, or a genuinely nodal-bound-constrained
phase solve, remove the measured phase imbalance at fixed captured displacement
and raw driving energy? The unit is one independent saved peak state. There is
no prediction horizon, propagated trajectory, new seed or new event estimate.

## Evidence, comparator and causal contrast

Use exactly the four v2 native capture states c1 outer3/13 and c83 outer20/28,
with their original peak `initial.p_field`, captured `u_return/raw_return`,
original accepted s3 history and nodal lower bound. Both arms start from the
same original peak damage; no state or arm initializes another. Mesh 86,756
nodes / 86,408 native Q4, 2x2 GP; E1, nu.3, Gc.01, ell.01, alphaT.5,p2,
eta0, GP penalties421875/13781.25. Exact source/binary/state hashes are reused;
new manifest locks the v2 capture SHA256. Native oracle and clipped-phase
replay must reproduce old residuals within1e-10 before a field solve.

Reference: [completed native v2 capture](runs/phase_capture_v2_result_20261015.md),
local archive `pf_s04e011_phase_capture_20261014_v2`. It is a numerical
comparator, not a qualified teacher. Old clipped feasible phase norms were
1.06868e-5/1.06292e-5 at c1, 2.56122e-5/2.56170e-5 at c83.

- **fresh_only**: preserve native Picard/Newton, no line search, evaluate current
  raw phase residual before deciding to update. Return the field whose residual
  was tested. Retain the unbounded endpoint and an independently assembled
  post-clipped endpoint. Infeasible raw-residual convergence is not phase
  constraint convergence.
- **constrained**: every trial obeys nodal `d_previous <= d <= 1`; prescribed
  crack values remain fixed. Use predicted active sets from `d-R/D` with D the
  frozen positive native initial diagonal. Active displacements enter the
  inactive RHS via `K_FA delta_A`. Recompute active sets each iteration, so nodes
  can release. Use native symmetric Picard Kdd without adding the trial-f chain.
  No shift changes, factorization retries or automatic outer solve.

This isolates fresh stopping through fresh_only versus old native/clipped;
constrained versus fresh_only additionally changes nodal admissibility and its
required constrained globalization. Do not attribute that contrast to bounds
alone while ignoring globalization. This is a VI/root diagnostic for the
native phase residual. At c83 it is not labelled an energy-minimizing convex
QP: trial-f depends on d and native Kdd omits its chain derivative. At c1,
f=1 is checked; the fixed-coefficient residual has a positive elastic term
and gradient stiffness on free phase variables, making an accurate constrained
endpoint plausible. No global Hessian qualification is claimed from this fact.

Nodal monotonicity is a stronger constraint than GP monotonicity on this Q4
rule: positive shape weights imply nodal d>=old gives GP d>=old. Retain the
native GP penalties; do not replace them, add GP inequalities or claim the
constraint set equals the earlier E004 DirectQC proposal.

## Frozen stopping, budget and order

Primary criterion, separately per state: returned field is finite and feasible
(bounds within1e-12), fresh nodal feasible phase residual L2<=4e-6. Use exactly
the previous bound filter tolerance1e-10. This is a phase-subproblem criterion,
not the former combined u+d target. Report all four states individually. The
predeclared c1 prerequisite is both c1 constrained endpoints passing; otherwise
finish c1 evidence and skip c83, without retuning the plan. Both c1 states are
attempted, independently. If they pass, execute both c83 states identically.

The 4e-6 screen is inherited, not selected from new results. It requires about
2.7x/6.4x reduction from the prior clipped endpoints. c1 f=1 allows an analytic
constrained-stationarity target near numerical precision; c83 has no empirical
convergence ceiling, so a miss is diagnostic of the remaining nonlinear/Picard
limitation, not evidence of an irreducible residual floor.

Budget is **250 native phase assemblies per state/arm**: at most248 optimization
callbacks (initial evaluation and every rejected line-search trial count), plus
two reserved terminal audits at returned and post-clipped damage. Two shared
admission phase calls per state (original oracle and captured clipped replay)
are reported separately, outside either arm. Four states/two arms therefore
have a maximum2008 phase calls including shared admissions, not 2000. Mechanical
postchecks do not enter the phase count. Compare actual cost and accepted-step
curves; caps do not mean equal realized work. No full120-cycle or new coupled
outer iteration is authorized by this diagnostic.

Constrained line merit is continuous natural residual
`||D (d - P[d - D^-1 R(d)])||_2`, with D frozen from initial native diagonal,
not the discontinuous bound-filtered primary norm. Try lambda=2^-j,j0..20;
accept primary phase tolerance, or merit reduction at least1e-4*lambda relative.
If the predicted-active-set direction fails, one predeclared projected-diagonal
direction uses the same finite grid and budget. This is explicit globalization,
not a post-result algorithm change. If both fail, stop with line_search_stall.
No extra calls, new shift, wider grid or alternative tangent after results.

Finite/bounds failure, assembly/factorization failure or budget exhaustion is
saved and stops that numerical attempt. Save last accepted state separately
from last attempted/evaluated fields and failure stage; no failed trial becomes
an accepted endpoint. The six tiny algebraic selftests precede native cases.
MATLAB checkcode and those tests have **not** run on Mac (no MATLAB/Octave).
They run only on the producer after exact-version upload approval; failure
prevents field execution. Python syntax/import/bundle checks do not substitute
for MATLAB execution.

## Exports, comparison and outcomes

Every arm saves returned/pre-clip and post-clipped d, fresh residuals, trial
history234, fixed u/raw and s3 history, all accepted-step residuals and rejected
trial merits/call counts, stop reason and failure record. Also save mechanical
free-R at the new damage, refreshed raw diagnostic, native active/fatigue fields
through saved inputs/history, and full nodal differences from v2 clipped output.
Do not compare undefined kernel history slot1.

Offline analysis admits fresh native phase residuals against the existing
source-equivalent formula within1e-10, checks exact frozen inputs and bounds,
then compares phase norms/ratios, mechanical imbalance, damage changes, active
integrals and area-weighted active relL2 versus v2. A decision plot shows all
available predeclared states on common residual scale with old native/clipped
markers and4e-6 threshold; companion CSV is authoritative. Spatial fields are
saved for localization. No cherry-picked state selection.

Evidence identity or reconstruction failure -> inadmissible. Valid criterion
pass -> supports this fixed-u phase-subproblem repair at that state only.
Valid miss -> negative for this solver/budget, with cache-only, constraint,
globalization and trial-f component records selecting the next repair. Missing
endpoint -> inconclusive. Mechanical or active worsening remains visible and
cannot be rescued by a phase pass. No teacher, physical truth, altered Nf,
full-trajectory convergence or disappearance of FEM/PIDL differences.

## Review and transfer

Local independent read-only design/code review is required and bound to exact
source commit/package hashes. Existing ChatGPT advice is recorded as earlier
ChatGPT advice, not verified Pro-model review:
`docs/research/S04/S04-E004/pro_design_advice_20261005.md` and local
`fem_final_residual_audit_20261011/design_review.md`. They support constrained
stationarity/fresh checks, but the old E004 GP constraint set differs.

The legacy project skill asks GPT Pro before a new branch; no external message
has been sent in this preparation. Current shared gate requires independent
read-only review. A local-only review substitution needs the user's explicit
agreement if the legacy Pro requirement is retained. Prepare that exact choice
with the upload approval, not an unauthorized new external consultation.

Proposed account CITPC12 `AD\\xw436`, fresh directory
`C:\Users\xw436\jobs\E011_DR_20261015_v1`. Six exact files: native runner,
generic solver, algebraic selftest, input manifest, entry and WMI launcher.
Prepare complete contents, hashes and exact action before asking approval.
No Git push, other recipient, external Pro send or source-tree overwrite is
included. Producer checkcode must be inspected before launch. Single CPU
thread; refuse an existing run receipt/output or competing MATLAB process;
never kill a process. Finish by retrieving/hash-checking results, updating this
protocol/track/registry and then `mesh对齐.md` and frontier.

## Execution and descriptive-analysis note — 2026-10-15

User explicitly approved six-file v1 transfer/execution and local independent
review substitution. Exact approved source commit8070c028dde7c1a5ef56fb4ab21e64f9883a4c4c,
all remote file sizes/hashes matched. Producer checkcode found NASGU/MSNU only;
six selftests passed. Native run started UTC12:20:25, finished12:22:39,
wrapper46180/worker46172. Both c1 constrained prerequisites passed, so both c83
states ran. Four states/eight arms completed, no history commits. Full retrieval
and field-admission status are recorded separately from this execution result.

After viewing remote primary residual outcomes, the local analysis additionally
plans a **post-hoc descriptive** comparison with the already-used paired Q4
PIDL nodal NPZ `pf_s04e011_pidl_pair_ad749c8_20261008T0912Z/analysis/multicycle_cross_replay/pidl_nodal/pidl_q4_nodal_trajectory.npz`.
Use only existing c1s4/c83s4 peaks, checkpoints4/414. This paired run retains
recovery at global step0 and uses global_step(c,s)=5(c-1)+s; do not subtract1
using a different600-step archive convention.
No new holdout, run or network evaluation. Compare active fields with original
GP weights, using both the legacy FEM-variant denominator and a fixed PIDL norm,
plus integral differences/correlations. This cannot change the phase primary
verdict or qualify coupled mechanics. Visualization also localizes changes at
the two predeclared last saved states, with common signed scales and explicit
crack-band crop. All original thresholds, inputs, solve budgets and stopping
rules remain as approved. No new code was uploaded after launch.


## Terminal result

[Completed comparison](runs/damage_repair_v1_result_20261015.md): all4constrained fixed-u phase endpoints pass, fresh-only postclip nonepass.187phasecalls,40files verified, independent numerical review passed. c83-last mechanicalRu increases14.75% and descriptive sum5.91%; active gap modestly improves but integral gap worsens. No coupled/trajectory/teacher repair. Next unexecuted lever: displacement re-equilibration with constrained damage and fresh joint checks.
