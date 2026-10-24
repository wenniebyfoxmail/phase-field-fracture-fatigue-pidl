# S04-E040 — state-referenced feasible damage representation

**Status:** reviewed design r1; local implementation and CPU contract tests are
complete. The requested internal ChatGPT Pro review returned *approve with
specific modifications* on 2026-10-24; its two required safeguards below are
adopted. An exact-source review and the single producer execution remain
pending. No producer upload or execution has been performed.

**Task owner:** S04-E040, controlled synthetic PIDL numerical experiment
(claim class C1: numerical admissibility and solver-state validity).

**Branch / base:** codex/pidl-u012-feasible-damage-20261024 from
99339eedabe685a3d22912b700776e7ab881137d.

**In scope:** an opt-in damage-map helper, one isolated runner, algebraic
tests, one continuous new-arm calculation, and comparison with the retrieved
standard arm. Shared defaults, completed S04-E037 source, FEM inputs, and the
baseline archive are excluded.

## Question and prior evidence

Can the standard Umax=0.12, seed-1, 8x400 PIDL path impose nodal damage
irreversibility through the forward representation rather than an
irreversibility penalty or PHR term in the optimized numerical loss, while
retaining weights-only L2 = 1e-5 and the state-timing contract?

This is a controlled numerical experiment, not an accuracy or FEM-validation
claim. A completed feasible trajectory would show only that this representation
can advance the declared synthetic path.

The comparator is complete S04-E037-R001: 15 continuous substeps, three cycles
with factors [.25,.5,.75,1,0], from the same recovery state. Its reported total
was 214.761 seconds. The repaired PHR arm S04-E037-R003 reached one finite but
unaccepted c1/s1 trial: after 1,320 updates, maximum lower-bound retreat was
3.526e-4 versus 5e-6, so it committed no history. That is a negative result
for that NN-plus-PHR solve, not for exact forward feasibility in general.

The simple map d=h+(1-h)*sigmoid(q) is rejected. It cannot represent d=h at
finite q; the archived algebra test gives the unchanged-raw ratchet
0.2 -> 0.6 -> 0.8 when its floor is refreshed. A local forward inspection of
the recovery checkpoint found direct sigmoid would raise all 45,340
non-fully-damaged nodes by more than 1e-3 before optimization. It is not a
valid continuation from the accepted state.

## Candidate representation

At the beginning of every physical substep, freeze accepted nodal damage h,
fatigue state A, prior driver psi_prev, and a detached raw third-head reference
q_ref from the current accepted network. For the current raw third output q,
define:

~~~text
t = 0.25 * clamp_min(q - q_ref, 0)
T = t / (1 + t)
d = h + (1 - h) * T
~~~

The implementation uses torch.clamp_min. It checks once on the actual producer
device that the selected derivative at zero is the right derivative, and stops
before optimisation if that device/Torch build differs; it propagates NaN rather
than hiding it.
The fixed 0.25 equals the central slope of the standard
NonsmoothSigmoid(support=2), so the active one-sided raw-head sensitivity
matches the standard map locally before the bound scaling.

For finite real inputs and 0 <= h <= 1, h <= d < 1 for h < 1, and d=1 for
h=1. The numerical acceptance test deliberately uses only h <= d <= 1, not a
strict upper inequality. At the beginning of a step q=q_ref, T=0/1 and d=h
bitwise for finite h. q_ref is detached and does not change during the solve.
Only after an accepted commit is q_ref replaced by the raw output of that same
accepted network. A capped or rejected step changes neither reference nor
history.

q_ref is a reproducibility-critical numerical reference history, not a
physical fatigue variable. It is stored atomically with the accepted network,
h, A, psi_prev, and a mesh/order hash, then verified after reload. The map is
nonsmooth: negative raw increments have zero damage Jacobian, shared parameters
can switch nodal branches, and the upper bound is approached rather than reached
at finite raw values. It guarantees feasibility on the declared mesh, not
field-space KKT optimality away from that support.

### Exact-start and commit invariant

Each atomic accepted record is
``(network, h, A, psi_prev, q_ref, mesh_order_hash)``. The runner must establish
all of the following before an inner solve begins:

~~~text
q(theta_accepted, inp) == q_ref
d(theta_accepted, h, q_ref) == h
~~~

Within the continuous runner, the first equality and the resulting damage use
`torch.equal` on the same fixed device, dtype, mesh order, and forward path.
The save/reload audit records maximum errors beside the declared
`32*eps*max(1,max(abs(q_ref)))` and `16*eps` diagnostics, but a record is
eligible for commitment only if both q and damage also satisfy bitwise equality.
The diagnostics do not silently rebase q_ref or weaken the exact-start gate
used by the continuous trajectory. At c1/s1, q_ref is captured from the already
loaded recovery network, never from a separately updated parameter state.

After each accepted solve, the final cached network is copied together with
the final `h=d`, `A`, `psi_prev`, and `q_ref_next`. Before writing that record,
the runner captures `q_ref_next` from that final network and proves
`d(theta_final, h_final, q_ref_next) == h_final`. A rejected, capped, or
invalid solve writes only a failure/trial record and cannot mutate any member
of the last accepted record.

## Solver and state contract

The new helper replaces only the particular FieldComputation instance's
alpha_constraint callable. That callable receives the raw third network output
before the legacy alpha map. The production default and its field forward stay
unchanged. Before capture, the runner asserts that this standard case has no
Williams transform, symmetry input remap, local patch, or other output transform;
otherwise it must capture the exact tensor supplied to the callable. The helper
checks frozen h/q_ref shape, dtype, device and finiteness at construction and,
on every forward, performs one composite device-side finite check of q, q-q_ref
and d. For finite q and q_ref with the fixed positive scale, the intermediate
t and T are finite by construction; the check therefore rejects overflow rather
than treating it as saturation without adding several GPU synchronizations per
forward.

Within a physical step optimize:

~~~text
F(theta) = log10(E_el(u,v,d; f_fixed) + E_d(d; f_fixed))
           + 1e-5 * sum(weight parameters squared).
~~~

The runner-local RPROP loop builds F directly; it does not call the shared
``fit_with_early_stopping(..., hist_loss_weight=0)`` path because that path
still constructs ``0 * E_irr`` inside the graph. E_irr is computed only from
the final cached field under no_grad as a detached shadow diagnostic; it is
absent from F and its backward graph.
There are no multipliers, rho, PHR terms, clipping, or AT1 off-domain
extension. The original AT1 energy is evaluated on its feasible domain.
The runner retains standard fresh RPROP hyperparameters and invokes the shared
`EarlyStopping` class on CUDA tensors: it monitors the same scalar `F`, uses
`abs(F_t-F_prev)/(abs(F_prev)+np.finfo(float).eps)`, begins with `F_prev=0`,
and requires ten consecutive values at or below `min_delta=5e-7` before a
genuine pre-cap stop. The RPROP update happens before that test, and the
terminal iteration retains the previous-loss state exactly as the standard
loop does. Parameter-gradient RMS and an independently calculated
field projected residual are reports, not acceptance gates. Because
RPROP uses signs, the first backward pass also records the full and third-head
row physical/L2 gradients, cosine, and sign-change fraction; the first actual
update records raw-increment and active-branch fractions.

For every attempted step:

1. Load one atomic accepted network/state record, verify its mesh/order hash,
   calculate and detach q_ref from the actual raw third-head path, then install
   the map with frozen h and q_ref. At c1/s1, report the difference between
   legacy alpha(theta_0) and h before optimizing.
2. Hold h, A, psi_prev, q_ref, and f_fixed immutable through RPROP.
3. Evaluate the final field once. That cached field supplies energy, strain,
   raw psi+, trial fatigue update, saved output, and the only transaction.
4. Commit only if normal early stopping completes before the fixed cap, values
   are finite, and direct logical nodal and TRI3-GP bounds h <= d <= 1 hold.
   A cap or invalid state is unaccepted and terminates the new arm.
5. Stage h=d, A and psi_prev from the cached field, q_ref_next from the
   matching accepted network, all step artifacts, and an immutable hash index.
   Only after each is reopened and checked does the accepted-state pointer
   advance. Do not re-evaluate another damage field or perform another optimizer
   update after final-field evaluation and before that pointer publication.

## Fixed benchmark and reporting

Run one new arm only: c1--c3, 15 continuous substeps, on one Taobo GPU in a
fresh directory. Reuse R001; do not replay it. No new seed, FEM run, or retry.
The proposed bound is 240 seconds and 10,000 RPROP updates per attempted step,
3,300 seconds runner time, and 3,500 seconds detached wrapper time. Fifteen
seconds of each substep are reserved for final field checks and durable output;
if the protected reserve is reached first, the step is terminal and unaccepted.

The primary outcome is whether all 15 substeps are accepted with exact forward
feasibility. At every common accepted phase report against R001:

- relative L2 and area-mean ratio for strain and raw psi+;
- relative L2 and area-mean ratio for fatigue accumulation A;
- E_el, E_d, detached E_irr, L2, RPROP updates, and elapsed time;
- min(d-h), max(d), raw-increment/branch fractions, and local
  derivative/saturation summaries;
- initial physical/L2 gradient sign and cosine diagnostics, including the
  damage-output row, and the first actual update's raw-increment fractions.

At termination record the ten pre-update loss pairs that caused the ordinary
early-stop event, plus a separately evaluated post-last-update field. On free
nodes (`h<1`), report `q-q_ref<0` (zero damage Jacobian), `==0` (zero increment
but right derivative available), and `>0` branches as distinct lumped-mass
fractions, together with the normalized one-sided damage-Jacobian ratio.
Classify physical-energy stall only when the corresponding ten pre-update
physical-energy changes obey the same `5e-7` threshold. This is diagnostic
only: scalar RPROP plateau never establishes field-space stationarity, and the
post-update field can depart from the pre-update plateau without invalidating
the recorded stopping event.

Compare timing only over a common accepted horizon. A stopped arm has an
explicitly unaccepted terminal diagnostic; it supports no trajectory, speed,
FEM-agreement, or physical-improvement claim.

## Planned implementation checks

Tests must establish: bound algebra, exact hold at q=q_ref, no refresh ratchet,
right derivative at the boundary, h=1 fixed behavior, non-finite raw and
subtraction-overflow rejection, reference/history immutability on rejection,
a direct objective with no E_irr backward path, the exact-start/commit/reload
invariant (including the recorded reload diagnostics and required bitwise
identity), the copied
standard stopping arithmetic, an evidence-before-pointer transaction, and
unchanged default FieldComputation behavior without the helper. Preflight
checks the recovery checkpoint, mesh, R001 receipt, finite reference, accepted
input state, the c1/s1 legacy-alpha-versus-h difference, and the
no-update-after-final-field transaction boundary before a producer run.

## Requested review

ChatGPT Pro is asked only whether this state-referenced, one-sided feasible map
is a defensible next numerical experiment, whether its right-derivative and
state lifecycle are coherent, and whether this comparison record is adequate.
It is not asked to certify code, run a calculation, or validate physics.
