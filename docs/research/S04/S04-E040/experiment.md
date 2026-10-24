# S04-E040 — state-referenced feasible damage representation

**Status:** implementation audited; fixed producer calculation completed.

**Execution amendment, 2026-10-24:** the first Taobo launch reached the raw-q
initialization but made no optimizer update: the global network remained on
CPU while the mesh was on CUDA.  It yielded no scientific observation.  The
runner now moves the whole field network after optional q-only patch creation;
the fixed code check covers both field modes, and a new fresh producer run is
required rather than reusing that incomplete directory.

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

## Producer result — 2026-10-24

The fresh Taobo calculation used source commit `564ba10f787b6f62795808d133b07cbe6d90af64`
and the fixed recovery-state baseline.  The immutable run archive is
`/mnt/data2/drtao/pidl_archives/pf_s04e040_feasible_564ba10f_20261024T085200Z`;
the two committed output directories are its `output/global` and
`output/q_local` children.  Their manifests record the same mesh hash
`49565321fa939a95feb55bcd26dac377e909460d12ab98daa2d6080bb0dff9e4` and
`irreversibility_in_loss: false`.

Both arms completed all 15 fixed substeps and every receipt was accepted.
At every accepted state, the node and Gauss-point lower-bound margins were
zero or positive (`min(d-h)=0`), the sampled damage range was `[0, 1]`, and
the no-grad shadow irreversibility diagnostic was zero.  The global arm used
4,252 updates / 159.046 seconds and finished with `E_d=0.00472642528`; the
q-local arm used 5,695 updates / 241.613 seconds and finished with
`E_d=0.00541965012`.  The q-local and global damage fields were identical at
step 1, then differed from step 3 onward (step-15 RMS difference `0.021815747`,
maximum absolute difference `0.163426399`, 2,518 changed nodes).  This confirms
that the q-only patch was active while the globally coupled displacement path
remained unchanged by construction.

The outcome is forward numerical-admissibility evidence for this one synthetic
PIDL trajectory: strict damage feasibility was retained without differentiating
an irreversibility penalty, and both fixed arms committed their full paths.  It
does not compare against a physical/FEM reference, establish an energy or
accuracy advantage for q-local, identify a causal mechanism, or support a
road-fracture prediction claim.  The higher final `E_d` and compute cost of the
q-local arm are observations, not a performance ranking.
