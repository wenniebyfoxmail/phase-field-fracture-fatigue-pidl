# ChatGPT Pro review packet — S04-E040

**Surface:** the user's logged-in ordinary ChatGPT Chat, with the Pro model
option visibly selected.

**Material:** the complete text below pasted into the chat. There is no file
attachment.

**Scope:** internal, non-binding design review only.

---

You are reviewing a narrowly scoped numerical-method design for a controlled
phase-field/PIDL fatigue benchmark. Assess the design on its technical merits.
Do not infer execution, code correctness, FEM agreement, or physical validation
from this packet. Do not propose a broader experiment matrix; identify only
changes needed before one fixed benchmark is run.

## Context

The standard benchmark is a Umax=0.12, seed-1, 8x400 neural variational
phase-field model with AT1 damage, cyclic factors [.25,.5,.75,1,0], and three
continuous cycles (15 substeps) from a saved recovery state. Its usual loss is:

~~~text
log10(E_el + E_d + E_irr) + 1e-5 * sum(weight squared).
~~~

E_irr penalizes healing. RPROP uses ordinary fresh-per-step hyperparameters.

In a prior hard-constraint attempt, a primal--dual
Powell--Hestenes--Rockafellar solver removed E_irr from the scalar physical
energy but added numerical constraint terms outside the log. Its repaired run
made one finite c1/s1 trial but accepted no substep: maximum lower-bound retreat
was 3.526e-4 against a declared 5e-6 tolerance after 1,320 primal updates and
eight outer loops. No history was committed. This is a negative result for that
NN-plus-PHR solve, not for exact-feasibility approaches generally.

A direct map d=h+(1-h)*sigmoid(q) is rejected for this follow-up. It cannot
represent d=h at finite q, and an archived algebra test shows an unchanged-raw
floor refresh can ratchet 0.2 -> 0.6 -> 0.8. A local forward inspection of the
standard recovery network also found that direct sigmoid would raise all 45,340
non-fully-damaged mesh nodes by more than 1e-3 before optimization. The new
design must begin exactly at the accepted state.

## Proposed state-referenced feasible representation

At the start of every physical substep, freeze and detach accepted nodal damage
h (0 <= h <= 1), fatigue history A, prior driver psi_prev, and raw third-head
output q_ref from the current accepted network. Freeze f_fixed derived from A.
For the current raw third output q:

~~~text
t = 0.25 * clamp_min(q - q_ref, 0)
T = t / (1 + t)
d = h + (1 - h) * T.
~~~

The clamp_min convention is intentional. In the installed PyTorch version it
selects the right derivative at zero and propagates NaN rather than masking it.
Thus, at the beginning of a step d=h exactly and the positive-side derivative
with respect to q is 0.25*(1-h). The factor 0.25 is the central slope of the
legacy NonsmoothSigmoid(support=2). For finite real raw values, h <= d < 1
where h<1; if h=1, d=1. Runtime acceptance tests logical h <= d <= 1 bounds.
The map rejects non-finite q, q-q_ref, t, T, or d on every forward so an
overflow cannot be accepted as apparent saturation.

q_ref does not change during the inner solve. It is updated only after a
successful commit, from the same network state that made the accepted field. A
rejected or capped step changes neither q_ref nor physical history. It is saved
as a numerical reference history in an atomic accepted record beside the network,
h, A, psi_prev, and mesh/order hash. The map is nonsmooth: negative raw
increments have zero damage Jacobian and shared network parameters can change
branches across nodes.

The implementation replaces only one FieldComputation instance's
alpha_constraint callable, which receives the raw third head before the legacy
alpha map. Default production behavior is not modified.

## Objective, lifecycle, and fixed benchmark

Within each substep, optimize exactly:

~~~text
log10(E_el(u,v,d; f_fixed) + E_d(d; f_fixed))
+ 1e-5 * sum(weight parameters squared).
~~~

The runner builds this objective directly. It does not use a ``0 * E_irr``
shortcut inside the shared fit routine, because that would still construct
E_irr in the backward graph. E_irr is recomputed only from the final cached
field under no_grad as a detached shadow diagnostic. There are no PHR terms,
dual variables, penalty coefficients, clipping, or AT1 off-domain extension.
Standard fresh RPROP hyperparameters and relative early stopping remain in a
runner-local loop. Parameter-gradient RMS and an independently calculated
field-space projected residual are diagnostics, not NN-solution acceptance
tests.

During a solve h, A, psi_prev, q_ref, and f_fixed are immutable. The final
field is evaluated once; that same cached field provides energy, strain, raw
psi+, trial fatigue update, saved output, and the one history transaction. An
accepted substep requires ordinary early stopping before the cap, finite values,
and direct logical nodal plus TRI3-GP bounds h <= d <= 1. A capped or invalid
substep is not committed and stops the new arm. The first backward pass records
physical and L2 gradient signs/cosines, including the damage-output row, and
the first actual update's raw-increment/active-branch fractions.

The planned calculation is one fresh Taobo-GPU arm: the same 15 continuous
substeps, maximum 240 seconds and 10,000 RPROP updates per substep, and 3,300
seconds runner time. The completed original arm is reused. At every common
accepted phase, analysis compares strain, raw psi+, fatigue A, energy
components, update counts, exact-bound diagnostics, raw-reference branch and
saturation statistics, and elapsed time. There is no new seed, FEM run, retry,
or enlarged study.

## Questions

1. Is this state-referenced one-sided map a coherent way to remove the
   irreversibility penalty from the optimized energy while imposing the
   discrete nodal constraint by construction? Does refreshing q_ref only after
   acceptance resolve the floor-ratchet problem sufficiently?
2. Is the right-derivative convention at q=q_ref technically defensible for
   RPROP, or is there a fatal directional or active-set problem that requires
   an explicit projected damage subsolve instead?
3. Does retaining standard RPROP while dropping PHR and dual terms isolate the
   intended intervention, or is another solver condition indispensable for a
   meaningful one-run test? In particular, is the runner-local reproduction of
   the existing relative early-stop rule an adequate way to avoid constructing
   E_irr in the graph?
4. Are the stop rule, state-commit rule, and comparison outputs adequate to
   distinguish numerical feasibility from field or physical improvement?
5. Give one clear verdict: **approve as written**, **approve with specific
   modifications**, or **do not run**, with the smallest technical rationale.

---

End of packet.
