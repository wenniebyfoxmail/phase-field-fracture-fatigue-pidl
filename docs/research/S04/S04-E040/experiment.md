# S04-E040 — state-referenced feasible damage representation

**Status:** implementation prepared; no producer upload or execution yet.

## Question and scope

Can the standard Umax=0.12 PIDL path impose damage irreversibility by the
forward map, with no irreversibility penalty in the differentiated objective,
while retaining the global coupled displacement equilibrium and weights-only
L2 regularisation?  This is a synthetic numerical-admissibility experiment,
not FEM accuracy, physical validation, or a road-fracture claim.

The relevant negative predecessor is S04-E037-R003: its original-network PHR
arm reached a finite c1/s1 trial but did not satisfy its hard lower constraint,
so committed no state.  It does not rule out forward feasibility.

## Method contract

For accepted damage `h` and the detached raw q field of the accepted network
`q_ref`, each physical solve uses:

```text
r = q - stopgrad(q_ref)
sigma_plus(r) = 0.25 * relu(r) / (1 + 0.25 * relu(r))
d = h + (1 - h) * sigma_plus(r)
```

Thus finite inputs give `h <= d <= 1`, and `q=q_ref` gives `d=h` exactly.
Literal logistic sigmoid is intentionally not used because it cannot hold
`d=h` at finite raw q.  `h`, fatigue A, prior active driver, q reference,
tip center and mesh/node-order hash remain immutable while a step is solved.
At the one nonsmooth point `q=q_ref`, the implementation deliberately uses
the positive-side subgradient; PyTorch's default `relu'(0)=0` would otherwise
make every freshly initialized step damage-gradient-dead.  The forward map is
unchanged and remains strictly feasible.

The differentiated objective is `log10(E_el + E_d) + 1e-5 * sum(W^2)` over the
whole mesh.  `E_irr` is skipped by the energy routine, rather than multiplied
by zero, and is recomputed only under `no_grad` as a shadow diagnostic after
the final cached field is obtained.  A single cached field supplies all output,
fatigue update and accepted-state transaction.

The optional local representation is q-only:

```text
q = (1-beta) * q_global + beta * q_local
```

where beta is a smooth compact crack-tip window fixed from the preceding
accepted state.  u and v remain the global network outputs, while all three
fields remain coupled by one global energy integral.  This explicitly avoids
the existing alpha-only/full-partition path, which would attenuate global u/v.

## Fixed comparison

Reuse completed S04-E037-R001 without replay.  The approved computation uses
two new independent own-history arms: `global` and
`q_local`, each c1--c3 / 15 substeps from the legal recovery state.  Each step
uses fresh RPROP, a 240-second and 10,000-update cap; the runner envelope is
3,900 seconds so the 15-step trajectory plus committed diagnostics fits.  A
lower total budget is rejected before launch.  No seed, FEM case, sweep, retry
or full-life rollout is implied.

`global` completing all accepted substeps supports only the forward-feasibility
claim.  `q_local` is compared with it only at common accepted physical phases;
an early failure does not establish a timing or field-accuracy benefit.

## Implementation checks

The fixed code benchmark is:

```bash
/Users/wenxiaofang/miniconda3/bin/python3 -m unittest discover -s tests -p 'test_feasible_damage.py'
```

It checks exact accepted-state hold, bounds, inactive-branch derivative,
reference copying/non-finite rejection, and q-only partition preservation of
u/v.  It is an algebraic code check, not a PIDL training run.
