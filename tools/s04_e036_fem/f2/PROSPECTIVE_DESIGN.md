# F2 c1s4: fixed-f nodal-box alternating solve

Status: local source preparation only. No MATLAB/checkcode, toy solve, native
assembly, training, deployment or F2 execution has been performed. The running
`strict_c1s4_01` and its deployed `code_b34e97d` are unchanged. The isolated producer and local packet preparation source are now included; no
packet has been frozen from a committed source or dispatched. The generator
defaults to root_dispatch_approved=false. Root decides the source commit and
when to generate approved controls and launch the new method. The current
strict job must first terminate naturally, with either success or a complete
scientific rejection preserved, and with supervisor/job-object and owned-process
cleanup proved. Scientific success is not required; an unknown outcome or
missing terminal evidence cannot release the next job.

## One representative problem

Use the exact native-admitted F1 c1s3 checkpoint with SHA256
`36193d74aba9b0d894524a391271412068bd8ebd220ce5d8b074d795f7eb937b`.
The load is c1s4 = 0.11999988, using the same original load predictor as the
current strict run. Do not start from a chosen late iterate or change the
incoming old history, lower damage or version. Retain the original native Q4
mesh/order, AT1/Amor, E=1, nu=.3, Gc=.01, ell=.01, eta=0, alpha_T=.5, p=2,
GP irreversibility penalty 421875, recovery 13781.25, and the same 251 fixed
crack nodes. The problem is the E036 nodal box `old.d <= d <= 1` with the
original fixed displacement and crack DOFs.

This is a new F2 solver branch. Preserve the original main F1 failure and the
entire strict attempt; never substitute an F2 target into primary F1 improvement
rates, complete c1s5, or represent old E011/GP-QP results as current evidence.

## Small isolated reuse

`e036_f2_damage_solve` copies E011's generic constrained active-set core into a
new name, retaining its source path/hash in the header. It predicts active
bounds, solves the inactive system, and evaluates every projected line-search
trial. Its existing predeclared projected-diagonal direction is retained;
after both directions exhaust the line search it stops, with no new attempt.
Nonfinite values stop immediately. Only exact collapsed bounds have zero KKT
residual; a merely narrow box retains raw residual when both bounds look
active. Physical feasibility and fixed DOFs are exact. All callback calls and
factorization attempts, including rejected/failed ones, are counted.

`e036_f2_displacement_solve` copies E011's fresh-return Newton core: each field
update is followed by an actual new assembly before it can return success.
It does not use the original native Newton's pre-update convergence decision.
No diagonal shift, new recovery, alternative material, or automatic retry is
introduced. Original E011 runners/old outcomes and their f=1 assumptions are
not imported. Python `native_q4_damage_qp` is a structural reference only: its
GP-irreversibility domain and scaled certificate are not the E036 nodal domain
or acceptance norm.

## Frozen coefficients without pretending native f is fixed

The original PF MEX recomputes trial f from current d, raw and old slots 2/3;
there is no explicit frozen-f argument. Changing old slot 4 would not freeze f.
F2 leaves the old history and MEX untouched.

`e036_f2_quadratic` explicitly integrates the fixed-raw/f AT1 damage-dependent
energy using actual native Q4 geometry and order. It constructs H and b from
the physical terms, rather than blindly caching a native kink Hessian:

```text
H_gp = weight * [2*raw*N*N' + (3/4)*f*Gc*ell*B'*B]
b_gp = weight * [-2*raw + (3/8)*f*Gc/ell] * N
E_gp = weight * [((1-d_gp)^2+eta)*raw
                + (3/8)*f*Gc*(d_gp/ell + ell*|grad d|^2)]
```

The compressive elastic term is constant in d and is omitted from this
subproblem's energy differences. f is frozen only in the inner QP, then
refreshed from the **same immutable old history** in the coupled outer loop.
No derivative df/dd is added to the original physical phase equation.

Positive Q4 shape values and exact nodal `d>=old>=0` imply GP irreversibility
and recovery penalty values/first derivatives vanish throughout this feasible
domain. This fact alone does not license an arbitrary native kink Hessian.
The actual source uses strict `<0` tests for both penalty branches; the new
physical H excludes all inactive penalty curvature explicitly and validates
against the actual native H. A nonmatching native boundary branch is an
operator-validation failure, not a reason to silently insert that curvature
into the QP or change a tolerance.

## Validation occurs inside the same representative producer job

The first F2 outer block, before any active-set damage solve, runs the existing
native operator at two predeclared feasible points, keeping raw and old history
fixed. The anchor is the current d after the first U solve. The probe moves
each free node 0.001 toward the midpoint of its `[old,1]` interval; fixed crack
nodes stay unchanged. This moves nodes at old/zero into the feasible interior
and can expose a wrongly retained boundary penalty curvature. A collapsed
whole domain with no distinct probe fails the validation rather than inventing
another easier point.

At each point, compare actual native K and residual with explicit Q4 integration
using **that point's actual native recomputed f**. Independently verify the
native driver/A/f law from the unchanged old history. At the probe, separately
evaluate the anchor-f quadratic and verify its constant H/b, its gradient and
the exact energy increment identity
`E(x)-E(d) = r(d)'*(x-d) + .5*(x-d)'*H*(x-d)`.
Record the difference between native probe f and anchor f; never call the
native probe a frozen-f evaluation. Numeric checks use absolute 1e-10 and
relative 1e-8, matching the existing operator-equivalence scale. Every later
outer block checks its own native anchor against the constructed physical
quadratic; the two-point/energy check is not rerun as a separate experiment.

Failed validation stops before the damage solve. The adapter retains the last
attempted/evaluated native arrays and operator vector for diagnosis. There are
no additional toy science runs, alternative test states, refits or third
attempts. These pending producer checks are not claimed as already passed.

## Outer sequence and unchanged acceptance

`e036_f2_solve(sys,eq,pf,u0,d0,pre,bc,traction,policy,budget,limits,checkpoint)`
is a candidate-only adapter. It requires the actual admitted c1s3 preimage.
The caller must source-bind the original load predictor and provide the same
native eq/pf handles, material, DOFs, timing checks and existing final adapter.

1. Fresh-return U solve at current feasible d.
2. Validate the frozen operator, then solve the nodal-box QP at fixed raw/f.
   The explicit required `limits.d_inner_tol=4e-8` governs both the damage
   subsolve and its successful-return check. Each U subsolve still uses 1e-8.
3. Fresh-return U solve at the resulting d, keeping d fixed.
4. Existing `e036_native_candidate` independently reassembles final Ru, raw,
   native phase residual/KKT and f from the original old history. Preserve
   strict `Ru<=1e-8`, `Ru+KKT<=4e-6`, active_tol 1e-10 and existing physical
   bounds/history rules. Also require the declared fixed-point condition
   `max(abs(f_frozen-f_final))<=1e-10`; this is an additional F2 condition.
5. If either condition fails, continue only the declared coupled iteration
   with updated candidate u/d. Never advance old history/lower/version. If it
   passes, return a proposal, still with zero history commits.

Each U subsolve has at most 250 callback evaluations, each damage subsolve at
most 250 including rejected line-search trials, and at most 1500 outer blocks.
The caller passes the existing finite 86400 s job / 43200 s step anti-hang
budget and 4-CPU cap; no cumulative resource ceiling is inferred. Two U solves
per outer means the costs are not matched by counting outer iterations. Record
all actual native assemblies, QP evaluations, factorization attempts and wall
time. Failure, line-search stall, cap or nonfinite output ends this attempt
without another solve under a new setting.

Every completed outer block prints fresh Ru, phase KKT, f delta and cumulative
native U/PF assemblies, QP evaluations and U/damage factorizations with `%.17g`.
The checkpoint callback receives only a compact progress struct: the current
`trace_row`, cumulative `counts`, `limits`, `policy`, method, stage, outer,
accepted flag, `terminal_status` (`running`, `outer_cap` or
`fresh_joint_and_f`), elapsed time and explicit zero-history-commit fields.
It does not receive full fields, matrices, native arrays or accumulated trace
each round. Final `out` retains the terminal arrays, complete trace and other
diagnostics for the caller's single failure or proposal save; the callback
cannot commit history. The isolated producer freezes source and inputs, performs native admission,
binds source/authority, preserves terminal failures, and uses the existing
proposal/checkpoint/readback machinery only when `out.accepted` is true.
Root still chooses the committed source and dispatch timing; preparation is not
execution approval.

## Evidence to report

Report the native two-point checks, energy identity, full fresh outer residual
and frozen/final-f trace, fixed predecessor proof, active-set work and complete
terminal outcome. Compare against the preserved current strict c1s4 result;
evaluate standard tolerances secondarily without changing the strict decision.
An accepted F2 endpoint establishes a same-predecessor nodal solution under the
declared discrete problem and new solver; it does not establish uniqueness,
restore the original full trajectory, or prove physical correctness.

## Isolated producer and packet preparation

`e036_f2_driver` retains the existing complete Stage A evidence/runtime checks
from the recorded B driver source, with a separate explicit F2 request and
committed source lock. `e036_f2_predecessor` retains the actual published-step
proof and native admission/readback, restricted to this exact F1 c1s3 SHA; no
later main-window completion is inferred. `e036_f2_run_step` uses the original
load predictor once, counts its native assembly and factorization separately,
and records its fields/source/hash before the new solve.

Each completed outer writes one small JSONL row and prints Ru/KKT/f_delta with
17 significant digits. It does not rewrite input arrays or matrices per outer.
A failure saves the final candidate diagnostic arrays/trace once and stops.
Success saves the ordinary accepted proposal and native field checkpoint,
performs the existing exact readback plus the extra frozen-f proof readback,
then publishes an explicitly F2 completion and performs one accepted-state
assignment. Result file is `f2_result.mat`; no primary `window_result.mat` is
created. F2 is never silently consumed as a missing primary F1 step.

`prepare_f2_config.py` reads only a full actual Git commit and exact existing
strict config/manifest/authority/evidence plus locally present immutable inputs.
It writes a fresh packet directory, source lock, F2 config/authority/entry,
hash-bound launch script and ZIP. Default `root_dispatch_approved=false` causes
the launcher to reject before consuming a label. Generating a new approved
packet requires root's explicit launch decision; it does not require another
user budget. The existing process-local policy, 4-CPU job controls and finite
anti-hang guards are retained. No current source tree or running process is
changed and no Stage A work is repeated.

Example local preparation after root commits these files (replace COMMIT with
that actual full commit, and use a fresh output directory):

```text
python tools/s04_e036_fem/f2/prepare_f2_config.py \
  --checkout <this worktree> --source-commit COMMIT \
  --strict-config <strict package>/payload/strict_c1s4_01_config.json \
  --output <case>/run_workspace/fem_f2_c1s4_preparation_v1
```

This source preparation has only static text/identity checks. No MATLAB
checkcode, native assembly, solver, training or new regression suite has run.
The first actual native two-point check remains inside the prospective job.
