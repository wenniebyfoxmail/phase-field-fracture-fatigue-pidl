# S04-E042 — projected explicit-damage active-set solver

**Status:** implementation and the fixed CPU carrier-contract benchmark are
complete.  No producer package, upload, GPU launch, or new numerical result
exists yet.

**Task owner:** S04-E042, controlled synthetic PIDL numerical-method
experiment (claim class C1: constrained-solver admissibility).

**Goal anchor:** E040 showed that a state-referenced ReLU map can enforce
`d >= h` without putting irreversibility energy in the objective, but its first
RPROP proposal put essentially all free nodes on the negative, zero-Jacobian
branch.  The new question is whether a direct, projected damage update can
retain the hard bound while preserving a usable outward damage direction.

**D1 reuse decision:** fork from the completed E040 result at `00ea5de2`.
Reuse its Umax=0.12 recovery state, mesh, AT1 energy, fatigue timing, accepted
state transaction, standard weights-only L2 coefficient, and R001 comparison.
Do not modify E037, E040, defaults, FEM inputs, or the baseline archive.

## Method boundary

At one physical step, freeze the accepted lower field `h`, fatigue state `A`,
previous driver, and fatigue degradation `f(A)`.  Let `b_theta` denote the
legacy smooth/nonsmooth neural damage base evaluated on the current raw third
head, and freeze its accepted value `b_ref`.  The E042-only carrier is

```text
d(theta, eta) = h + (b_theta - b_ref) + eta.
```

`eta` is a temporary nodal leaf variable.  Its feasible interval is evaluated
from the current base at every projection:

```text
b_ref - b_theta <= eta <= 1 - h + b_ref - b_theta.
```

Thus `d` is exactly `h` at the start of a step (`b_theta == b_ref`, `eta == 0`)
and is always projected into `[h, 1]`.  At an accepted endpoint, store
`h_next = d_final` and `b_ref_next = b_theta_final`, then discard `eta`; the
next state again starts bitwise at `d=h`.

The physical objective remains exactly

```text
F(theta, eta) = log10(E_el(u_theta, v_theta, d; f_fixed) + E_d(d; f_fixed))
                + 1e-5 * sum(network weight parameters squared).
```

`eta` receives no L2 term.  `E_irr`, multipliers, PHR terms, clipping inside
the differentiated energy, and off-domain AT1 extensions are absent from
`F`.  A detached shadow `E_irr` may be reported only after the final cache.

The solver alternates at fixed `(h, A, previous driver, f, b_ref)`:

1. With the current feasible `d` held exactly fixed, update the network by
   fresh RPROP on `F`; after each proposal, reconstruct `eta` from the current
   base so the field is still that fixed `d`.  This block detaches both carrier
   paths into `d`, so it is genuinely a fixed-d network solve rather than a
   network update whose damage derivative is merely corrected afterwards.
2. With the network fixed, form the direct damage gradient and take a
   lumped-mass projected step `d <- Pi_[h,1](d - tau M^-1 grad_d F)`.  Backtrack
   on the same physical `F`; rejection restores the complete damage iterate.
3. If damage changed, repeat the displacement/network equilibration before a
   final cache and possible commit.

For the damage block, report the projected residual
`R_tau = (d - Pi_[h,1](d - tau M^-1 grad_d F)) / tau`, active/releasable mass,
accepted damage step, and backtracks.  The receipt records the normalized
lumped-nodal-area metric and its SHA-256; after the final held-damage
re-equilibration it recomputes this diagnostic without changing `eta`, so the
reported residual corresponds to the accepted cache rather than an earlier
alternating iterate.  This is a damage-block active-set/KKT diagnostic.  It
is not a certificate that the shared neural parameterisation solves the full
field-space KKT system or matches FEM.

## Fixed comparison and interpretation

The planned new arm retains Umax=0.12, seed 1, 8x400 TrainableReLU,
AT1/volumetric split, mesh, recovery checkpoint, load factors
`[.25, .5, .75, 1, 0]`, `current_active` fatigue semantics, one accepted-only
history transaction per physical step, and direct field/fatigue comparisons
with R001.  E040 is also retained as the dead-branch comparator.

The fixed CPU benchmark established exact start, exact nodal/Tri3 feasibility
after projection, a usable direct-damage release direction, held-theta versus
direct-eta gradient separation, `h=1` fixed-DOF behaviour, and no
irreversibility energy path.  It does not authorize a producer run or
establish a physics/FEM result.

For any later one-arm producer card, successful completion requires all 15
accepted states, finite fields, zero direct node/Tri3 bound violations, and a
recorded nontrivial direct-damage response.  It would support numerical
feasibility of this solver only.  Field agreement, fatigue evolution, and time
would remain separate descriptive comparisons; no scalar loss is comparable
across objectives or solver families without that boundary.

## Authority

The user requested advancement of this next method route.  That covers local
design, implementation, and the declared fixed CPU benchmark.  E040's
completed single-arm envelope does not automatically cover a new producer
experiment because this solver changes the numerical state variables and
update rule.  A later launch card will state its single-arm GPU/time cap and
stop rule before any upload or execution.
