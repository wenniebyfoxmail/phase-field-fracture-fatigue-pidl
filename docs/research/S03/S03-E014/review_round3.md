# E014 independent review round3 — 2026-10-12

Exact submitted implementation commitd86d8ec792157d7ce026464e6b21090e245b02e3.
External reviewer: https://chatgpt.com/c/6ac7974d-c838-8325-9322-fbc639d581cb .
Verdicts: A structural inspector `PASS_CODE_READY`; B v2 workflow `REVISE_CODE`.
Old physicalv1 NOT_READY remains unchanged. This is a faithful review summary.

## Source and structural closure

Original CrackPy1.1.1 source SHA2561a5c2f5a4604899f886e56995448280f0d3b1f03dec374d422048474ad50ffc7
and Git blobfc72daaff2d96210b9b837229c6de2eb57a4d880 independently verified.
to_vtk supports c+1 mapping; read_data_file consumes displacement columns
without reapplying alignment metadata there. This is consumer behavior, not
original exporter compensation algebra. Unchanged inspectorcf5e4b9d... and its
13-case tests92b9ca56... retain previous verification. One fresh bounded C1
inspection was explicitly permitted; source/invariant hardening notes remain.

Actual allowed RunS03-E014-R001 subsequently succeeded locally, fresh directory
`local_archive/experiments/S03-E014/runs/S03-E014-R001/`, report+receipt available.
Locked size/MD5 verified. Fit common position/displacement support39891 nodes;
target coordinate missing116. Correctly indexed non-padding/finite supported
triangles:78276/78054/78117 for stages7/8/9; allType3; no unknown nonnegative
indices. Stage9 responses remain unconverted/unscored. No FEM/q fit occurred.
This producer result is not independently evidence-reviewed mesh admission.

## Reproduced workflow blockers and focused repairs

B1: absent or FAILED fit receipt could still enter validate and read/score high
response. Reviewer reproduced on wholly synthetic prepare-fit-validate outputs.
Fix: require succeeded fit-mode receipt bound to fit metadata/predictions/profile
before held access; also enforce prepare completion before fit. Actual hashes
recorded by each mode; missing/failed/mode/runner/artifact mismatch refused.

B2: target finite_xyz mask excluded a finite x,y,u,v point solely because z was
NaN, reversing a synthetic comparison. Fix: target eligibility purely x,y,u,v,
as already intended in amendment. z-only missingness regression now preserves
the complete metrics. No change based on actual held response occurred.

## Independently verified capabilities, not real-data validity

All14 supplied new tests passed independently. A full synthetic three-mode
workflow used861nodes/1600triangles,21q + intact solve, freeze and validation.
CST/plane stress/mean-nodal degradation, basis formulas, interpolation,
Dirichlet solve, E invariance, linear load/rigid superposition and global
projector matched the protocol. Closed-form projector agreement approximately
4.4e-16 on synthetic nonuniform weights. Common scoring support, error
definition, high-response access restriction, prediction/held-hash mutations,
numerical response floor and intact-vs-d0 comparators were consistent.

Nonblocking: require/verifyType3 in weight construction (now enforced); actual
mesh/order/interpolation assets still need review; oneCPU thread set/verify at
producer launch. Numerical gates do not identify noise or actual q. No real
archive, spatial preparation, fit, held score or producer was accessed in review.
