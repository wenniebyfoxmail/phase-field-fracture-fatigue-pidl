# S04-E036: one target-free release of the C0 clamp plateau

Prepared 2026-10-24 by `/root/constraint_release_design`. **Source/design only;
not executed, validated numerically, deployed, or added to the resident queue.**
The owner decides execution after the existing C0 continuation finishes. This
directory is an isolated prospective method addition; source `68291a0a`, all
previous results, Stage A ownership, and the six queued jobs remain unchanged.

This applies `research-decision-core` and the existing PIDL state contract. It
continues the selected node-step/retraction branch of
`CASE/analysis/first_principles_design.md`; it is not another method search.
`CASE` is `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E036/gap_attribution_20261022`.

## Question and measured mechanism

At the c1s2 2000-update endpoints, C+ and C0 have all 86,756 actual damage values
equal to immutable old damage. The saved native diagnostics identify 4,646 free
nodes where raw damage is below the lower bound while the phase force requires
an increase. These nodes carry all measured phase-KKT squared residual. Sources:

- `CASE/analysis/c1s2_matrix_clamp_activity_20261023.json`;
- `CASE/analysis/c1s2_matrix_saved_diagnostic_summaries_20261023.json`;
- `tools/s04_e036/run_mechanism_matrix.py`, `MechanismField.values`,
  `EndpointEngine.nodal_diagnostic`, and `lbfgs_phase`;
- `source/cyclic_acceptance.py`, `nodal_box_residual` and the fresh checker.

The saved diagnostic force uses freshly rebuilt trial-f. Therefore the release
must recompute its force at the **saved, explicitly frozen f_solve**. It must
not quietly reuse the saved force if these coefficients differ. If the measured
blocked directions disappear at this coefficient, this method stops without a
release attempt; coefficient coupling is a different unresolved mechanism.

The original-network FEM-target fit is a separate seen-target witness. Neither
its weights nor its targets enter this method. A smaller fit error motivates
examining optimization but does not establish that the particular local step
below can be realized by the network.

## One chosen algorithm

Use one **fixed-f nodal damage descent followed by full-network raw-preimage
retraction**. The node step holds displacement fixed so that its accepted
decrease specifically comes from a feasible phase-field correction. Retraction
trains every existing network parameter; it does not append node coefficients,
change widths, alter activation functions, or change the C0 output map.

Let `a=d_old`, `r(theta)=d_legacy(theta)` (after the existing hard crack boundary),
and

\[
 d(theta)=P_{[a,1]}r(theta),\qquad y(theta)=(u(theta),v(theta),d(theta)).
\]

The collapsed interval `a=1` stays exactly 1 with zero derivative. All 251 hard
damage nodes retain their original value. The existing top/bottom displacement
ansatz is unchanged. Raw `r` and actual `d` are always stored separately.

At the saved C0 terminal weights `theta_0`, freeze `f_* = saved f_solve` and all
old state. Use the actual Q4/GP4 energy

\[
 E_*(u,v,d)=E(u,v,d;d_{old},f_*),\qquad
 R_d=\partial_d E_*(u_0,v_0,d_0).
\]

`compute_energy` supplies this scalar and its derivative. The fatigue coefficient
is detached; no derivative through `f(y)` is used. Penalty terms and all physical
coefficients stay in the energy even though their value/gradient vanish on the
feasible nodal domain. This is not a new Hessian construction.

### 1. Obtain one real feasible damage descent

Let `m_i` be the positive native Q4 lumped nodal area normalized by total area.
Set `v_i=-R_di/m_i` on free noncollapsed nodes, zero elsewhere, and remove
outward directions at exact active bounds. Such directions project to zero for
every t; large normal reactions must not shrink the step scale of feasible
directions. The first trial step has `max_i |t v_i|=.02`; the value `.02` is a step proposal scale, not a
physical acceptance tolerance. For each of at most 25 backtracks,

\[
 \tilde d(t)=P_{[a,1]}(d_0+t v),\quad
 p=\tilde d-d_0,\quad \tilde y=(u_0,v_0,\tilde d).
\]

Check the projection identity `R_d.p <= -sum(m*p^2)/t`, then require the actual
native energy to satisfy

\[
 E_*(\tilde y)\le E_*(y_0)+10^{-4}R_d^T p<E_*(y_0).
\]

Halve `t` on a finite nondecreasing trial. Nonfinite values, invalid supports,
changed boundaries, and failed projection identities stop immediately. An
unresolved/sub-roundoff step or failure after 25 backtracks is terminal for this
attempt, not a reason to change tolerances or restart another seed.

Define `B` at this same coefficient as the free nodes satisfying either
`r_0<a and R_d<0`, or `r_0>1 and R_d>0`. Require a resolved positive
`W_B^node = -sum_B R_d*p`. This prevents a pure displacement or unrelated phase
decrease from being mistaken for a clamp release.

### 2. Construct a raw preimage and retract with the full network

Create a fixed detached raw target

\[
 \tilde r_i=\begin{cases}
 \tilde d_i,&p_i\ne0\text{ on a free node},\\
 r_{0i},&\text{otherwise}.
 \end{cases}
 \qquad P_{[a,1]}\tilde r=\tilde d.
\]

The last identity is checked exactly. Unmoving clipped nodes keep their original
raw values rather than being unnecessarily dragged to the bound. At a lower
blocked node that should grow, `tilde r>a`; the raw target explicitly crosses the
flat region. The raw network has its original small tail slope; this method
does not replace it or invent a derivative through the clamp.

Starting from `theta_0`, minimize the one fixed proxy

\[
 S(theta)=\tfrac12\sum_i m_i\left[
  ((u_theta-u_0)/.12)^2+((v_theta-v_0)/.12)^2
  +(d_theta-\tilde d)^2+(r_theta-\tilde r)^2\right].
\]

Use full-network float64 L-BFGS, persistent memory 100, ordinary derivatives,
one optimizer step per call and at most 25 closure calls per step. The proxy
gradient through the raw term is nonzero before the actual damage leaves its
clamp plateau. **It is the true gradient of S, not the gradient of physical
energy, and not a straight-through estimator.** Intermediate proxy iterates
remain provisional; they can cross a raw distance without prematurely being
discarded because actual damage has not yet moved.

The network architecture, 1,125,211 trainable parameters, C0 map, lambda=0,
physical domain, mesh, load, old history and old damage remain unchanged.
Retraction is a new optimization method within the existing C0 function family.
C0 itself is already a different composite map from the original legacy arm;
this distinction must remain in comparisons.

### 3. Accept only actual physical progress and verified saved weights

After every accepted proxy step, perform a fresh network forward and evaluate
the **actual clamped field**. Require exact `a<=d<=1`, exact hard damage values,
the existing BC tolerance, finite float64 fields, unchanged old state and f.
Do not project an already computed candidate again for acceptance.

Let `DeltaE_node=E_*(y_0)-E_*(tilde y)>0`. Accept the release transaction only if

\[
 E_*(y_0)-E_*(y(theta))\ge .1\,\Delta E_{node},
 \qquad
 -\sum_{i\in B}R_{di}(d_i(theta)-d_{0i})\ge .1\,W_B^{node}>0.
\]

At least one actual blocked damage value must change. Energy decrease must also
exceed the explicit 64-epsilon energy-scale roundoff guard. The two factors `.1`
are fixed algorithmic sufficient-progress fractions; they are not claimed gap
explanation percentages, and do not replace any original scientific tolerance.
Report all observed fractions rather than reporting only a boolean.

An actual energy decrease alone could arise from unintended displacement drift.
The blocked-work requirement separately confirms realization of a feasible phase
direction. Save both displacement drifts. At finite steps, blocked linear work
is not itself an energy partition or proof that KKT decreases; the full native
energy remains the acceptance scalar.

Then invoke the existing fresh checker: rebuild trial history/active/f from the
immutable old state, differentiate with fresh f detached, and report Ru, phase
KKT, bounds, BC and coefficient fixed point. This check **does not refresh f_***.
Physical acceptance remains exactly the existing protocol:
`max((Ru+Rd_KKT)/4e-4, Ru/1e-6)<=1`, existing feasibility and BC rules, and
the `2e-6 + 2e-6*max(abs(f_solve),abs(f_commit))` coefficient condition.

Persist the complete network, raw and actual fields, old state, f_solve,
fresh-history/f_commit, proposal and trace using the existing exact snapshot
readback. Only after successful publication may the new weights remain installed.
History commit count stays zero even if the independent endpoint is qualified.

## Failure, rollback and the next decision

The transaction stops at the first physical release accepted above, or at one
of these verifiable points:

| Stop | Preserved conclusion | Next decision for the owner |
|---|---|---|
| No B at saved f | This coefficient has no measured blocked direction | Resolve coefficient timing; do not run an irrelevant release |
| Node Armijo fails or step unresolved | This selected projected step did not produce resolved descent | Preserve finite numerical failure; do not blame NN |
| Proxy has 20 consecutive relative changes <=1e-10 without physical acceptance | This finite retraction did not realize the requested physical release | Inspect actual/raw mismatch and conditioning; no expression lower bound |
| Line search exceeds 25 closures, nonfinite value, watchdog or technical error | Attempt terminated with its own reason | Roll back; no automatic scientific retry |
| Physical release accepted, fresh endpoint still fails | The measured clamp barrier is traversable with this same C0 network | Owner may continue the existing target-free physical solver from these weights in this new method attempt |
| Release and fresh endpoint both pass | This conditional endpoint meets the existing physical tolerances | Score against F1 separately; it does not establish trajectory reproduction |

For **every** unsuccessful or exceptional return, restore all network parameters
and buffers exactly to the anchor. Restore saved f, clear proxy gradients,
discard proxy L-BFGS memory; no history or lower bound is updated. Preserve actual
attempted work counts and traces. Proxy steps/closures are counted in the new
`proxy_work`, separately from the engine's physical optimizer counters.
Publication failure is an exception and also
rolls back. There is no automatic retraction retry, seed change, trust-radius
menu, architecture growth, or repeated transaction in this module.

If the owner continues physical optimization after a successful release, use
the already declared C0 continuation method with a **fresh physical L-BFGS
memory**, because S curvature is not physical-energy curvature. Keep the same
old state. A later fatigue refresh creates a new fixed-f segment and invalidates
comparisons of raw energy between segments. Attribute this as the new release
method plus its subsequent solve; never merge it into the frozen 2x2 results.
No FEM target participates in proposal, stopping, parameter choice or acceptance.

## Counterexamples and interpretation limits

- A feasible decreasing nodal target need not be reachable by this finite neural
  retraction. Full-network L-BFGS failure supplies no lower bound on global
  expressiveness, even though every parameter was trainable.
- A different raw preimage of the same clamped physical target may be easier to
  represent. The selected lifted preimage can contain sharp changes at B and can
  make this proxy difficult while the physical target remains representable.
- The legacy raw damage tail has slope .001. Removing the clamp's zero derivative
  does not remove poor scaling, shared-weight coupling, or inactive ReLU units.
- The node direction is mass-preconditioned gradient descent, not an exact damage
  QP. AT1 local stiffness can make the accepted step small. There is no claim of
  mesh-independent convergence or optimal node-space progress.
- A good raw fit may still produce bad u/v or gradients through shared weights.
  The actual energy/readback rejects an adverse combined result; a small S alone
  is never a physical success criterion.
- Frozen-f energy can decrease while the fresh-f residual worsens. This is why a
  release and a self-consistent physical solution have separate statuses.
- Two qualified nonlinear or degenerate node states can differ from F1. A solver
  success need not remove the field gap. Report J/G and field differences only
  after the physical run, without using them to select the candidate.

## Minimal source interface and remaining integration

`release.py` contains one callable, not a runnable producer entry:

```python
attempt_release(engine, emit=record_event_or_arrays,
                publish=publish_verified_candidate)
```

The loaded engine must be the actual **terminal** c1s2 C0 continuation endpoint,
float64/CUDA, 1,125,211 trainable parameters, zero history commits. It must be
loaded and verified through the existing bound endpoint mechanism. Do not choose
an earlier prettier checkpoint or substitute any witness weights. If the current
C0 continuation succeeds or ceases to show this barrier, do not launch this
proposed repair simply because its source exists.

`emit(event, payload)` writes a new attributable event/array record. `publish`
calls existing `publish_snapshot(..., endpoint=True, extra=extra)` in a fresh
path and returns its verified completion receipt. The caller binds the terminal
source completion/bundle hashes, source overlay, inputs, single GPU 5 authority,
finite per-job watchdog and exclusive attempt ownership. It also records
`method=nodal_damage_raw_preimage_release_v1` and the release work separately from
old physical L-BFGS counts. No launcher/authority manifest has been created here.

The producer adapter is now prepared in `run_release.py`; `README.md` documents
the actual terminal late-binding step and deliberately unapproved authority
template. Before execution, the owner still needs the real source binding and
prospective amendment. This is part of the already authorized research objective;
the execution decision depends on the pending continuation result, not another
request for cumulative resources. The resident queue is never edited/interrupted
to insert this method. No Mac forward, optimizer step, native assembly, SSH or
scientific test was run to prepare these files. Only syntax/direct source
consistency is checked locally; a representative physical execution remains
unperformed.
