# FN776 protocol v1 — preparation only

Protocol: `S04-E011-UVH-C1-FN776-v1`. Proposal: `S04-E011-UVH-C1-FN776-PROPOSAL-v1`.
The user approved implementation, code packaging and static review on 2026-10-19.
Execution awaits approval of the final exact `S04-E011-UVH-C1-FN776-CARD-r1`.

## Decision and frozen science

Determine whether the existing 388-column UV space can reach original-z
stationarity by a full 776-coordinate square-root branch Newton solve. This
addresses the unresolved solver question after the bounded PC16 result; it
does not revise that negative result or claim capacity, mechanics closure,
physical-teacher truth or generalisation.

Only synthetic seen c1s4, U=0.11999988, fixed MCS outer9 FEM damage, horizon0.
Keep the original model, hidden parameters, activation, UV lift, energy and
E0=0.010889692759145935. Use the existing rank388 transform, interleaved
z=(u1,v1,...,u388,v388), starting at the original network z=0. No fitted r2 or
PC16 warm start, new SVD/cutoff, hidden/damage/history update, residual
stiffness, objective penalty, baseline solve or baseline reevaluation.

`inputs_fn776.json` is the sole input/limit contract. Its five files total
20,911,589 bytes. Hash each whole exact file once only during future execution;
decode listed keys only. In particular r2 head.npz provides transform only,
never its fitted z, UV weights or bias. No additional data or directory scan.

## Full square-root direction

At each Gauss point set rho=(1-d_GP)^2, K=lambda+2mu/3,
tau=e11+e22, gamma=2e12, c=rho for tau>0 and c=1 otherwise, including exact zero.
The three residual rows for E/E0 are:

```
e1 = sqrt(w*rho*mu/E0) * (e11-e22)
e2 = sqrt(w*(rho*mu/3+K*c)/E0) * (e11+e22)
e3 = sqrt(w*rho*mu/E0) * gamma
F = 0.5 * ||e||^2; A = de/dz; H = A^T A
```

Build augmented [A,e] in at most4096-GP chunks. Balanced TSQR transforms every
column together, retaining all776 coordinate columns and the last e column;
no pivot of that last column, local rank rejection, truncation or normal-matrix
factorisation. From the global777-by777 root, T=root[:776,:776], b=root[:776,776].
Solve T*p=-b with consistent column equilibration. Global zero diagonals,
nonfinite values or failed controls terminate; no ridge, jitter, SVD or fallback.

Check reconstructed raw energy (absolute1e-10) and gradient against the paid
same-point original-function AD. One independently paid current-z AD HVP is
checked against the root operator. At exactly tau=0 the original ReLU-square
AD volumetric second derivative is zero; add ONLY the exact selected generalized
tangent correction sum(w*K/E0 * trace_row^T trace_row * probe). No epsilon,
smoothing, omitted GP or empirical tangent adjustment. Derivative equivalence
uses absolute1e-8 + relative1e-8; this is separate from the primary1e-8 threshold.

Use at most3 original Newton-residual refinements with the same square root;
require ||H*p+g||inf <=1e-3 ||g||inf, backward error<=1e-12 and g.p<0.
Gram spectra/symmetry are small diagnostics only, not a solve, cutoff or gate
that drops modes. Negative rounded smallest eigenvalues yield unknown condition
estimates. Persist initial/latest unvalidated roots before rank/control assertions.

At most16 directions. Each line search uses the original F and g, Armijo
c1=1e-4, alpha=2^-j for j=0..31. Promote a point only after explicit acceptance;
cache its paid F/g. Exhaustion is terminal. No duplicate callback evaluation or
promotion of an unconfirmed trial. Every checkpoint is the original zero or the
last explicitly accepted point.

## Budget and stopping

| Category | Cap | Definition |
|---|---:|---|
| Curvature | 24,832 | 16 complete construction/TSQR/diagnostic/solve/refinement slots at1,552 each |
| Controls | 64 | E or E+g=1, HVP=2; planned upper bound4+16*(1+2)=52 |
| Trials | 512 | At most16*32 true F/g trials,1 each |
| Final | 16 | Planned3 actual/basis/original-z F/g readouts |
| Total | **25,424** | No category transfer or free setup/factor/refinement |

The curvature charge is a conservative prospective776*2 work proxy, not a
measurement of runtime equivalence. Precharge each whole slot before work,
including a slot that fails. All IO, construction, QR, serialization and figures
belong to the900-second guard clock. No new optimizer work from600s; no fresh
science from840s; guard terminates its owned process group at890s, reserving10s
cleanup. A600s optimization stop may perform the budgeted final readout of the
last accepted point before840s; failure at840s performs no fresh science.

Worker-tree RSS<=8GiB; Torch reserved<=8GiB; own CUDA process NVML<=8GiB.
The100MiB envelope counts root bundle/log/receipts plus outputs, task caches and
temporary files, reserving1MiB for terminal receipts. Immutable code checkout
is excluded. Runtime GPU free margin>=4096MiB. Admission requires>=12288MiB
free, GPU utilisation<=10%,>=16GiB host available, mounted data2 and>=5GiB free.
RSS/output nominal100ms; NVML nominal1s, each command timeout2s. These are
sampled safeguards, not OS hard-peak guarantees. No numerical feasibility claim
can be made from static review.

One fresh attempt only. An approved guard invocation consumes the card even
when later preflight fails. Deployment/admission/failure/limit stop requires a
new reviewed package and human authority before another attempt. No automatic
retry, restart, resume, alternate optimizer, GPU fallback or budget purchase.
Only the guard's verified child process group may be stopped; no other process
is modified. Shared-service disappearance/appearance/identity drift is terminal.

## Numerical verdict and evidence

Primary: BOTH basis original-z AD and actual-network force pulled back to the
same original-z coordinates have infinity norm<=1e-8. Actual/basis UV difference
<=1e-9 and raw energy difference<=1e-10; frozen hidden and damage output remain
bitwise unchanged. A factor/control/identity failure yields no scientific pass.

Separately report energy relative to saved PBD and r2. A PBD improvement witness
requires relative gain>=1e-4 AND raw gap>10 times the frozen/reconstruction
uncertainty. It cannot substitute for stationarity, and stationarity alone does
not establish that energy witness. No old verdict is overwritten.

Record stiffness_branch_changes using the actual tau>0 mask; exact zero and
negative trace share the compression branch. Record negative/zero GP counts
independently, so zero-to-positive changes are included and zero-to-negative
changes are not falsely counted as stiffness-branch changes.

Preserve paid work ledger, accepted/trial/gradient traces, control errors,
initial/latest factors, terminal states, guard resource samples and source/input
identities. On completion retain actual network/basis gradient readouts, fields,
head and a same-run decision figure with sidecar. Main visual readout is the
original-z gradient curve and actual-network marker against1e-8; scalar energy
and displacement maps are secondary. Failure preserves partial evidence without
calling it a completed scientific result.

Static preparation is standard-library AST/text/Git inspection only. No numpy,
torch, scipy or matplotlib import; no fixture, matrix assembly, QR, gradient,
payload stat/hash/read, SSH, deployment or compute. Final review admits only the
identified code/contract/package and never certifies runtime or convergence.
