# UVH-C1-PC16-v1 — same retained field space, conditioned solver coordinates

2026-10-18 Europe/London. **DESIGN ONLY, NOT IMPLEMENTED OR RUN.** User
authorized one minimum conditioning proposal through the S04 coordinating chat.
No source/model/array reads, numerical tests, fits, SSH or producer work were
authorized by this design task. This file uses only existing code and tracked
r2 result text. No independent code-review PASS is claimed for an unimplemented
method. No new Run directory, claim or producer identity has been created.

Owner: 验证位移–damage 耦合机制 /01a14e3b-f1ff-7360-a084-c1f13b261cc6.
Frozen r2 remains fd8f3588/result_20261018.md, source9a0bf3c7; no resume/retry or
revision to its verdict. This task does not touch the shared checkout, E025/E026
or residual Obsidian/Roadmap; those records retain their other owner. The user
explicitly removed the former80% quota floor; no reset/purchase is proposed.

## Question and exact intervention

Can **one frozen low-rank initial-Hessian coordinate preconditioner**, with the
same retained UV space and original starting field, lower actual same elastic
energy below saved PBD within the shared work/resource cap? This is a synthetic,
seen c1s4 conditional numerical exploration, not a physical/teacher/forecast or
coupled-evolution test. The question does not assume conditioning is the cause.

Evidence motivating the test: r2 actual energy.006360077631691784 was12.1218%
above saved PBD.005672469584399648; retained z-gradientL2=16.13189014219088,
stationarity=false. It stopped at its evaluation reserve with395total reads,
not the600s optimizer deadline. A lower original-initial energy was achieved,
but the procedure did not deliver a stationary retained solution. The reported
6.329e9 condition belongs to the retained mass-weighted design, not a measured
energy-Hessian condition; no Hessian-spectrum diagnosis was performed.

Keep: c1s4/U=.11999988/MCS outer9 FEM d; canonical Q4/2x2GP/Amor energy;
original model4 UV bubble/lift and float64 convention; all hidden parameters and
activation coefficients; original UV head initial coefficients; original damage
head; r2 retained transform and its388basis columns; energy normalization;
physical data/information set and saved comparators. No damage/history update.

Write the existing field as

    (u,v) = (u0,v0) + B z,       z in R^776, z_start=0
    F(z) = E_el(u,v; fixed d) / saved original E0

B here denotes the two-component block form of the SAME388-column r2 physical
basis. Original discarded directions remain at their original head coefficients.
Use the frozen r2 transform as an implementation control artifact, not a new
SVD/rethresholding. Do not initialize from r2's final z, its fitted head or PBD's
hidden parameters. No rank, width, new feature, regularizer, target or data change.

## One chosen construction: PC16

1. At original z=0 form the operator H0*v = Hessian_z F(0)*v by exact AD HVP.
   It is the SAME fixed-d energy, not an alternate elastic objective. Freeze
   this initial operator for construction; no iteration-wise Hessian refresh.
   ReLU split knots use the existing AD convention, not a new constitutive rule.
2. Use one predetermined Gaussian sketch Omega(776x16), seed1. Compute16 HVPs
   Y=H0*Omega and reduced QR Y=Q R. No alternative seed/sketch-size search.
3. Compute16 more HVPs H0*Q. Let S=Q^T H0 Q, a16x16 matrix. Check symmetry
   before symmetrization and require positive finite eigenvalues. Do NOT floor
   eigenvalues, add jitter/ridge, discard directions or fall back to a smaller k.
4. Define the invertible full776-coordinate map

       C = I + Q(S^(-1/2) - I16)Q^T,       z = C y

   and optimize F(C y), starting y=0. Apply C through its small factors; do not
   materialize an element-by776-by776 tensor. C is identity outside Q's16D
   subspace and invertible inside it. ALL776 solver coordinates remain available;
   PC16 is not a16-parameter model or a change to the rank388 retained basis.
5. Keep the r2 L-BFGS-B method, memory10, line-search maxls20, objective scale
   and relative-energy ftol1e-14. Gradient stationarity and any gradient stop
   must use the SAME original z-coordinate infinity threshold1e-8. A small
   transformed y-gradient cannot establish z-stationarity. If implementing this
   requires disabling the library's coordinate-dependent internal y-gradient
   stop and routing the original z check explicitly, that is the stated
   equivalence routing, not a new or relaxed physical stopping threshold.
   An energy-tolerance/line-search/budget stop with unresolved z-gradient stays
   unresolved; do not restart or continue until a stationarity result appears.

This can normalize initial curvature within the chosen response subspace. It
does NOT guarantee the full condition number falls, that the sketch captures
the decisive modes, or that curvature stays similar as strain signs change.
Whether it materially improves the finite-budget solve is the test hypothesis.
The r2 mass-coordinate gradient alone does not identify this mechanism.

## Same-problem validity before interpretation

Check fixed dimensions/r2 transform identity/unchanged model and d. Q must have
16 independent columns with Q^TQ identity within1e-10 scaled error. Use two
additional predetermined probes for H0 symmetry/positive-semidefinite behavior;
do not replace a failing probe or sign convention. Require scaled S symmetry,
Q-subspace whitening and C/C-inverse checks within1e-10; the AD symmetry probe
may use the r2 derivative scale1e-8+1e-4*derivative magnitude. Material negative
curvature, rank failure, nonfinite values or numerical noninvertibility stops.

Use z=0 and one fixed small nonzero probe (seed1, norm1e-6, no amplitude search)
to compare fields/actual energy/chain-rule gradients in old and new coordinates.
Require physical displacement equality<=1e-9 and energy discrepancy<=1e-10;
gradient chain-rule error uses1e-8+1e-4*gradient scale. Preserve r2's final actual
raw-head reconstruction and unchanged hidden/damage-row checks. Failure makes
the implementation comparison inadmissible, not a physical negative.

The original initial energy may be checked once against its frozen value as a
new-code identity control. Do not evaluate PBD or r2 endpoints again. Their
stored energies/field metrics remain comparators; report actual candidate field
metrics with the same definitions and use the saved baseline values.

## Transparent single shared budget

Keep900s total guard/600s no-new-optimization/840s work,8GiB sampled hostRSS,
8GiB CUDA process/allocator limits,100MiB all generated output, one GPU and
4GiB free margin. The extra construction must fit INSIDE these caps.

Introduce one conservative work ledger, shared with the400 cap:

    W = N_energy_or_energy+gradient + N_standalone_gradient + 2*N_HVP <=400

An energy-plus-first-gradient call costs1 as in r2. An HVP costs2 even if a
graph is cached; any separately issued energy/gradient is charged additionally.
Batching/multiple RHS never turns several HVPs into one. Invalid/rejected trials,
callbacks, FD probes, equivalence checks and final restoration/readout all count.

|Work|Prospective allocation|
|---|---:|
|16 sketch HVP +16 projected HVP +2 independent operator probes|34HVP =68units|
|Initial/equivalence/chain-rule/retained FD controls|at most16units|
|Optimization, including line-search and callbacks|at most308units|
|Final actual/basis/original-z-gradient checks/report readouts|at most8units|
|TOTAL|at most400units|

QR/eigendecomposition/factor applications and serialization are not energy/HVP
evaluations; they consume the SAME900s/memory/output budgets and must have
timing/size records. There is no separate free setup job or numerical probe run.
No additional producer smoke or baseline run is included. The candidate has
fewer optimizer calls than r2 because construction is paid from the shared cap;
do not present it as400optimizer evaluations or equal wall-clock work per call.
8GiB construction/runtime feasibility is unmeasured; no advance claim of fit.

## Reference, future inputs and decision

The primary remains actual reconstructed candidate energy versus frozen PBD:
G=(saved_PBD_Eel-actual_candidate_Eel)/saved_PBD_Eel, same1e-4 directional screen
and10times numerical readout-resolution rule. Use frozen r2 baseline uncertainty
and current actual/basis/initial-identity uncertainty; no baseline rescoring.
Keep smaller resolved gains, energy regression and numerical ambiguity distinct.

Relative to r2, report energy change and the SAME z-gradient, free-u residual,
H1/L2 and field costs as components. No all-metric-win criterion. Beating r2
while remaining above PBD is component progress, not passing the PBD claim.
Beating PBD with unresolved stationarity can be a practical optimization witness,
not an optimum. Missing PBD without stationarity does not reject all conditioning
or establish retained/full-network capacity. Even a verified retained stationary
point cannot establish whole-network impossibility or a physical teacher.

Future exact inputs need their own card approval. Scientific state/model inputs
stay within the same c1s4/model4 information boundary. To preserve exactly the
same basis, future preparation must separately list the frozen r2 transform
field in head.npz plus its basis/summary/control metadata. This artifact is not
new scientific training data, but it IS an additional array-read capability and
must be explicitly named; it is not covered by the consumed r2 grant. Only its
transform is used, never its final head/z as a start. PBD/r2 comparison energies
come from saved JSON; no endpoint re-evaluation or new baseline fit. Exact paths,
allowed fields and file count will be bound during approved implementation.
No such array/model/control payload was opened in this design task.

## New identity and stops

Proposal ID: S04-E011-UVH-C1-PC16-v1. A future run will have a fresh unique ID
(proposed stem pf_s04e011_uvh_c1_pc16_r1), exact code/protocol/input/resource card,
static equivalence review and separate human execution approval. It is not r2
resume and inherits none of r2's already-used reading/execution permission.

Use r2's explicit GPU3 UUID/shared-service/4GiB margin policy only after fresh
authorized identity/resources/duplicate checks. Service restart or extra process
does not permit re-whitelisting or switching GPUs. Identity/resource/nonfinite/
Hessian-construction/equivalence/realization/IO/budget failure stops the sole
attempt, without retry, new seed/k/rank, jitter, cap change or another producer.
Only our own fresh child may be stopped; existing services are never changed.

Next approval requested is only adoption of this design for minimal
implementation and static review. No implementation, fixture, science input
access or run is currently authorized. The exact final new run card will be
presented after that work, before any scientific reading/computation.
