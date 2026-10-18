# S04-E011-UVH-C1-PC16-v1 — implementation contract

2026-10-18. Local preparation only; no producer access or numerical test.
Owner: 验证位移–damage 耦合机制, 01a14e3b-f1ff-7360-a084-c1f13b261cc6.
S04/E011, synthetic seen-state C1 numerical diagnostic, origin c1s4, horizon0.
Approved design: ../uv_head_c1_20261018_r2/conditioning_proposal_v1_20261018.md
at 52d240880e91124bcdf30ee502922e3ad93c4c2c. r2 remains a frozen negative.

Question: does one fixed initial-energy-Hessian PC16 solver metric improve the
same retained-head energy solve enough to beat saved PBD inside a paid shared
budget? No claim that conditioning caused r2's finite-budget nonstationarity.
Existing r2 records cannot answer this intervention; no new pilot/smoke arm.

## Invariants and new input capability

Same c1s4/U=.11999988/MCS outer9 conditional accepted FEM d, canonical86756
nodes/86408Q4/2x2GP, AT1 volumetric split, original model4 float64 UV bubble/lift.
Hidden parameters, activation coefficients, original damage head and original
discarded head coefficients stay unchanged. Keep original initial UV field.
Frozen r2 transform(401x388) only: no new SVD, rcond/rank/width changes, final-r2
head/z initialization, PBD endpoint fitting, regularizer, damage/history or rollout.
New permission requested: decode ONLY transform from frozen r2 head.npz.
Exact five-file paths, sizes, hashes and keys are in inputs.json. Whole-file
identity hashing belongs to future approved execution, not preparation.
Two original input identities are inherited from r2's tracked inputs.json;
three r2 output identities are copied from its already-stored transfer manifest,
without reading/hash/decode of scientific payloads during this implementation.

u,v=(u0,v0)+Bz; z has776 coordinates interleaved as(388,2), z0=0.
F=original fixed-d elastic energy / frozen original E0=.010889692759145935.
PBD E=.005672469584399648 and r2 E=.006360077631691784 are saved JSON scalars;
neither endpoint is reevaluated. FEM displacement arrays only define H1/L2 and
display reference; FEM energy/residual are not recomputed as a comparator.

## Frozen PC16 and admissibility checks (future execution only)

At z0, each AD HVP rebuilds the SAME original energy graph; no Hessian refresh
elsewhere, smoothing or constitutive replacement. NumPy default_rng(1) defines
Omega(776,16), sampled CPU float64 then moved to CUDA.16 HVP produce Y; reduced
QR produces Q;16 more HVP produce HQ and S_raw=Q.T@HQ. Check unsymmetrized S
before averaging. All16 eigs must be finite/positive. No floor, ridge, jitter,
direction truncation, seed/k fallback or full776x776 Hessian/C materialization.

C(v)=v+Q(S^-1/2-I)Q.T v; inverse substitutes S^1/2. All776 y coordinates
remain available; y0=0. C is fixed through optimization and identity outside Q.
Numerical QR independence: abs(diag R)>eps64*776*||Y||F; this is a stop-only
roundoff/rank check, never a new physical-basis cutoff. Q orthogonality scaled
Frobenius error<=1e-10. S symmetry, whitening, inverse-factor errors<=1e-10.
Two fixed unit probes from default_rng(2) supply exactly two more HVP. AD symmetry
tolerance1e-8+1e-4*max(|p.Hq|,|q.Hp|); each quadratic form must be at least
-(1e-8+1e-4*||Hv||2). Two-sided C/inverse action on both unit probes, full-Q
subspace action and identity-complement action must have scaled error<=1e-10.
The latter probe vectors have norm<=1, so their absolute bound is also the
declared scale-normalized bound. Any failure stops; there is no repair-in-run.

At z=0 and a single default_rng(1) nonzero z probe normalized to1e-6, compare
old z and new y=C^-1 z: UV maxabs<=1e-9, energy absolute<=1e-10, gradients in
original z and chain gy=C.T gz within1e-8+1e-4*maximum gradient component.
Original actual energy is checked once. At nonzero probe reconstruct the raw
UV head, check actual UV/energy/gradient against basis, verify frozen parameters
and damage output, then restore ORIGINAL raw head. Never use a fitted start.
Retain r2's one fixed FD direction and steps1e-5/1e-6/1e-7, existence-of-one
derivative check using the same tolerance. No probe/amplitude replacement.

L-BFGS-B: maxcor10,maxls20,ftol1e-14,maxfun/maxiter308. Internal y gtol=0
disables a positive coordinate-dependent y threshold. Explicit stationarity
uses ORIGINAL z infinity norm<=1e-8, at original zero or a callback-confirmed
accepted point only. Callback evaluations count separately. At every callback,
check monotonic energy and store the accepted y/z before any stationary stop.
Only last verified accepted callback point (or original zero) is reconstructed;
never promote the final library result.x or an unaccepted lower-energy trial.
Energy tolerance, line search, optimizer budget or deadline return is not a
stationarity verdict. No restart to chase a stationary solution.

Final actual raw-head energy/field, basis readout and original-z gradient must
agree at the original r2 tolerances1e-10 energy/1e-9 UV; hidden/damage row and
actual damage output remain bitwise unchanged. Invalid/undefined result is
inadmissible/inconclusive, not a physical negative.

## One paid ledger and resource envelope

W=N(E or E+first-gradient)+N(standalone-gradient)+2*N(HVP)<=400.
Each HVP owns its forward/first/second derivative for one direction and costs2;
separate calls always cost separately, even with cached graphs. No batching
discount. One reverse call yielding both gz and gy is one first-gradient
evaluation of the one objective, not two separately issued evaluations.
Charge before work, including rejected/failed calls; append work_ledger.jsonl.

|Category|Hard allocation|Planned uses|
|---|---:|---|
|HVP|68|16+16+2 directions, each2|
|Controls|16|12: actual initial1, coordinate checks4, actual nonzero probe1, FD6|
|Optimization|308|all trials and accepted-callback rereads|
|Final|8|3 planned: actual+gradient1, basis+gradient1, original-z objective+gradient1|
|Total|400|No reallocation of unused category reserve|

All tensor construction, QR/eigh/inverse actions, IO and figures consume the
SAME wall900s, sampled worker-tree RSS8GiB, Torch reserved8GiB, own total NVML
CUDA-process8GiB, generated100MiB. No new optimizer evaluation after600s and
no new scientific work after840s. Factorization/serialization timing and bytes
are recorded. Guard cuts off at890s with10s cleanup reserve, output1MiB reserve.
Full GPU3 UUID/service checks and>=4GiB runtime free margin are in inputs.json
and guard.py. These are sampled caps, not hard-peak/zero-interference guarantees.
No numerical/resource feasibility was tested during preparation.

## Primary, components, evidence and next decision

G=(saved_PBD_E-actual_head_E)/saved_PBD_E. Preserve G>=1e-4 AND absolute gain
>10*uncertainty as r2's directional witness. Uncertainty is the maximum of frozen
r2 numeric uncertainty, current initial identity error, actual/basis discrepancy,
64eps64*E0. No baseline reevaluation. Smaller resolved positive gains, resolved
regressions and numerical ambiguity are separate outcomes. Threshold is the
pre-existing diagnostic directional screen, not a physical acceptance margin;
attainable gain remains unproven. No new all-metric-win conjunction.

Report original-z/y/full-head gradients, same free-u residual/H1/massL2, and
energy change versus frozen r2. Beating r2 alone is component progress. Beating
PBD without stationarity is a finite-budget optimization witness, not an optimum.
A primary miss with nonstationary z cannot reject all conditioning or establish
retained/full-network capacity. No coupled evolution, raw-Delta feedback,
E025/E026 attribution, teacher qualification or physical/real-road transfer.

Minimum asset: summary+ledger+trace+accepted+conditioning checks+factors+candidate
head/fields+guard/worker/source/input receipts, decision.png+same-stem.md+
README_analysis.md. Show all-node actual u/v/FEM-reference/difference maps and
frozen-scalar PBD/r2/current energy and residual bars; no extra baseline field
array access or posthoc numerical recomputation. A single seen state supplies
no independent-unit uncertainty. Future execution/retrieval/evidence status stay
separate from the bounded result. Main S04 owner records Obsidian/Roadmap.

Resource/identity/IO/nonfinite/QR/eigen/curvature/equivalence/realization failure
stops the sole attempt, with no retry/resume/new seed/k/rank/GPU/budget/service
change. Optimization cap/deadline permits only reserved final reporting, never
continued optimization. No science work after840s; first fatal stop is terminal.
Execution requires new exact-source/card human approval; old r2 grant is consumed.
