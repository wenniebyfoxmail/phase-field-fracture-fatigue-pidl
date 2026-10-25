# S04-E043 — conditional eta-KKT acceptance with zero-load theta preservation

**Status:** local implementation and focused CPU contracts are complete. No
producer package, upload, GPU execution, or numerical result has been created.

**Task owner:** S04-E043, controlled Umax 0.12 PIDL solver repair.

## Why this fork exists

The completed E042 archive established two separate facts.

1. The explicit eta carrier preserved the hard damage interval, but accepted
   all 15 steps from a loss plateau while its final eta projected residual
   remained nonzero. For example, the terminal residual infinity norm was
   0.08525 at step 15, and it was much larger at steps 2 through 4. The
   residual was a diagnostic only and did not control pointer publication.
2. At the exact zero-load step, held damage makes the theta physical gradient
   zero. The previous implementation nevertheless ran RPROP on the
   weights-only L2 term: the theta weight norm contracted from 34.1909 to
   0.00458. The next loaded step then lost its localized strain and raw
   psi-plus field before fatigue history diverged.

E043 repairs both faults but records them as distinct interventions. It does
not claim that either change establishes full-field stationarity, physical
validity, or FEM agreement.

## Frozen physics and objective

E043 retains the E042 recovery checkpoint, mesh, Umax 0.12 cyclic factors,
AT1 energy, current-active fatigue timing, accepted-only state transaction,
and weights-only L2 coefficient. At each physical step it freezes accepted
history h, fatigue state A, previous driver, frozen degradation f(A), and the
accepted base damage reference.

The carrier remains:

    d = h + detach(base(q) - base_reference) + eta

Eta is explicitly projected into the exact interval that gives h <= d <= 1.
The direct physical objective is unchanged:

    F = log10(E_el + E_d) + 1e-5 sum(theta_weight squared)

E_irr, multiplier terms, PHR terms, and differentiable clipping are absent
from F. A detached E_irr shadow remains a final-cache diagnostic only.

## Conditional eta-KKT acceptance

At a fixed theta, let g be the direct eta gradient. E043 evaluates the raw
bound KKT residual:

    r_i = 0             if eta_i is fixed
    r_i = min(g_i, 0)   at the lower bound
    r_i = max(g_i, 0)   at the upper bound
    r_i = g_i           in the interior

It also records the reference projected mapping:

    delta = eta - Pi_C(eta - 1e-4 M^-1 g)

where M is the normalized lumped nodal-area metric. The raw residual is used
for the gradient threshold; the mapping is used for a damage-scale threshold.
The fixed float32 thresholds are:

- raw eta-KKT infinity norm <= 1e-4
- projected mapping infinity norm <= 32 eps = 3.814697e-6
- active-set tolerance = 32 eps

After the inherited alternating iterations reach their loss plateau, E043
performs the existing ten held-damage theta re-equilibration updates and then
runs a final eta-only projected-gradient polish. Each proposal is checked by
projected-direction Armijo decrease with c1 = 1e-4, at most 12 backtracks,
and at most 128 accepted-or-rejected eta iterations. The final report is
recomputed after the final theta update. A pointer may be prepared only if
that report is finite, passes both fixed thresholds, and is explicitly marked
as a final-theta-fixed recheck.

An eta line-search failure, eta iteration cap, or wall cap produces an
unaccepted candidate and stops the arm. It never advances history or the
accepted pointer.

This is only a conditional eta-block KKT statement while theta is fixed. It
does not certify a global neural-network KKT point, displacement equilibrium,
or agreement with FEM.

## Exact zero-load policy

For the exact declared lambda = 0 substep, E043 does not run theta RPROP or
the L2 regularizer. It retains the theta state byte-for-byte, records its
state digest, and performs only the bounded eta-KKT check. This prevents a
physically zero theta gradient from being replaced by an optimizer-driven
regularizer update. A nonzero small load is not treated as zero.

The zero-load continuation policy and the eta-KKT acceptance repair have
different mechanisms. Any later E043 trajectory is therefore a combined
repair result. Attribution between them requires a separately authorized
ablation, not an interpretation of one combined run.

## Local fixed benchmark

The CPU contract uses a four-node constrained quadratic with h =
[0.2, 0.2, 0.2, 1.0], lumped metric [2, 3, 5, 7], and target damage
[0.0, 0.65, 1.2, 0.8]. One projected step reaches:

    d = [0.2, 0.65, 1.0, 1.0]

It verifies lower-bound blocking and release, upper-bound blocking, fixed
degrees of freedom, node and TRI3 feasibility, raw KKT residual zero, strict
objective decrease, Armijo rejection of a non-decreasing trial, and the
requirement that a final eta receipt pass its declared thresholds. Separate
contracts verify that only an exact zero load selects theta preservation.

## Execution boundary

The local change is deliberately isolated in the E043 worktree. A new
producer package, independent run card, fixed post-run analyzer, and explicit
GPU authorization are required before any remote execution. A later result
would first be a constrained-solver outcome; field, psi-plus, fatigue, timing,
and FEM comparisons remain separate descriptive evidence.
