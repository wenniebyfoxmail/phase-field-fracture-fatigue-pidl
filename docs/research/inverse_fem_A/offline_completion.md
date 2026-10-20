# A inverse FEM: remaining interfaces prepared offline

Date: 2026-10-20. Same owner/branch/goal as implementation.md. Continue D2:
prepare consistent material derivatives and attributable observations. The
original human scope permits local implementation/read-only data inspection
and independent delta review only; no new FEM, inversion, trajectory replay,
native-size sparse solve, parameter evaluation, training, SSH or new holdout.

The baseline c525455c review and its 19 focused checks are reused. This update
does not change those files or repeat their broad review. It adds three
interfaces and 18 focused small-array checks (18 passed in0.18s after review fixes). No new producer
owner, physical state, scientific result or execution authority is created.

## 1. Native-shaped sparse interface (native performance unverified)

`source/q4_inverse_sparse.py`:

- `assemble_consistent_sparse(step, limits)` directly assembles reduced
  free-u/interior-d sparse J from12x12 local Q4 blocks, in declared chunks. It
  retains Kud, Kdu and trial-fatigue derivatives in Kdd. It never builds a
  dense native Jacobian or applies every global basis direction.
- `SparseSensitivityProvider(step, row_scale=..., column_scale=..., limits=...)`
  explicitly factorizes the supplied tangent problem with sparse LU. It is
  dormant unless called. No default native limits, producer or runner exist.
- Its evidence is bound to the exact stable-step operator, explicit physical
  row/column scales and a digest of the actual sparse matrix/scales. It is a
  callable tangent solver compatible with `ImplicitStep.propagate`; the
  original independent residual check remains.
- Sparse triangular comparison solves bound inverse1/inf norms without
  constructing a dense inverse. A checked LU-product residual is included via
  a perturbation bound; sigma_min lower and sigma_max upper feed the existing
  prospective magnitude/conditioning thresholds. Norm arithmetic is inflated
  conservatively in float64; this is numerical evidence, not interval proof.
- Dimension/matrix-nnz, factor-nnz, LU-product-work and between-stage elapsed
  checks fail closed with stage/reason. An inconclusive/overflowed bound is
  failure, not a favorable estimate. No automatic retries, dense fallback,
  residual-only approval or reuse of a different material factor occurs.
- LU's internal allocation/blocking call cannot be interrupted by those Python
  checks. A native invocation MUST have an external memory/time watchdog and
  measured factor-fill storage; these are requirements for future execution,
  not a launcher implemented or exercised here. Bounds may be too pessimistic
  on the native problem; their practical acceptance rate is unknown.

Mathematical interpretation: for scaled A and computed B=Pr^T L U Pc^T,
triangular comparison bounds give b1>=||B^-1||1 and bi>=||B^-1||inf. If
ei>=||A-B||inf, e1>=||A-B||1 and beta_i=bi*ei<1, beta_1=b1*e1<1, then
||A^-1||inf<=bi/(1-beta_i), ||A^-1||1<=b1/(1-beta_1). Their geometric mean
gives a conservative singular-value lower bound. Finite precision padding and
resource admissibility are part of the provider record, not physical evidence.

New checks compare sparse local blocks against independent matrix-free JVPs
in both tension/compression and fatigue accumulation branches. An analytic
4-cell patch checks nonunit scaling, conservative bounds against dense SVD,
the tangent RHS and boundary behavior. Manufactured null modes and dimension/
fill/product caps reject or stop. Maximum tested reduced dimension is11;
**no native factorization or native condition number has been measured**.

## 2. Full-history transmission and constraint-switch strategy

`source/q4_inverse_trajectory.py`:

- `SensitivityTape.advance_given` consumes an already supplied accepted state
  and an already prepared stable `ImplicitStep`; it never calls a primal
  stepper. It checks parent fingerprint, material/mesh/load identity,
  version+1/load-index+1, exact u/d correspondence and fresh-trial versus
  committed A/q/f before one atomic sensitivity commit. Any exception leaves
  the old state/tangent/receipts unchanged; duplicates and mixed histories fail.
- `freeze_variation` preserves prior u/d/A/q tangents. Each tape requires a
  finite immutable global (dE,dGc,dAlphaT) direction at construction; omitted
  per-step parameters reuse it, and a changed direction rejects before any
  solve/commit. Prescribed-displacement directions can follow the load controls. The opaque
  native channel is preserved, not promoted to a newly identified physical H.
- `DirectionalTransitionProblem` supplies right-direction force, BC, damage
  and history equations at constitutive/weak-constraint switches. For weak
  lower activity it requires dd-dd_old>=0, dRd>=0 and complementarity; for weak
  upper activity -dd>=0, -dRd>=0. Fischer-Burmeister equations encode these
  nonlinear directional conditions. Strong constraints retain dd=dd_old or0.
  Wrong-sign bound multipliers beyond the declared weak band reject even if
  a broader primal residual tolerance would otherwise admit them.
- `check` audits a SUPPLIED direction, including A/q consistency and fixed
  scaling, and always returns derivative_unique=False. A small directional
  residual is not a uniqueness proof. This problem is never passed to the
  classical linear Jacobian/provider or silently allowed to advance the tape.

**Complete-trajectory policy:** at every ordinary stable state, use the
consistent sparse provider and carry the old history tangent once. At an
exactly unloaded/nominal-switch/weakly active state, form the directional
complementarity problem and stop the tape without accepting a new tangent.
A future independently reviewed semismooth/directional solver plus directional
uniqueness/regularity checks is needed to resume that branch. Do not set its
history tangent to zero, freeze all constrained nodes, smooth the model,
delete unloading states or reuse a selected linear branch without evidence.

This is an implemented transmission/failure interface and formulated switch
problem, **not a completed semismooth solver or proof of differentiability of
all600 states**. The actual zero-mode/switch landscape needs authorized
numerical validation. Small analytic weak-lower examples check release versus
sticking for opposite Gc directions; no new primal state is optimized.

## 3. Source/header binding of initialization and reaction timing

`source/q4_inverse_contracts.py` implements explicit MATLAB-block/interleaved
DOF/displacement and HDF-history axis conversions, backend material identity,
`InitialBinding` and `ReactionBinding`. Legacy cached force cannot masquerade
as a fresh exact-given-state derivative; model/boundary/state-phase mismatch
rejects. Units and signed force weights must be supplied explicitly.

`tools/bind_inverse_source_contract.py` produces
`source_observation_binding.json` using local source text and headers only:

- Four archived producer-source files match the prior existing source_lock:
  runner b08b0187..., solve d3603548..., init cd3ba4bd..., staggered post
  6313b4ad.... These are the same source family already used by the owner
  replay preparation; no new source or binary was fetched.
- Source init zeros u/history; the zero-load phase recovery then sets the
  accepted d/lower, resets A=qprev=0, f=1, before c1s1. Recovery is not a physical
  cycle. Exact source anchors and corresponding metadata scalars are saved.
- Raw state0_analysis stores only coordinates/damage. The existing MCS input
  `common_common_initial.mat` additionally has u/d/lower/raw/full history,
  version0 and source metadata. Its header and already-stored state0 comparison
  scalar are recorded; no new whole-array equivalence or recovery solve occurs.
- The inverse first version explicitly fixes this supplied recovered geometric
  profile across candidates, so initial tangents are zero BY DEFINITION of the
  inverse problem. This is not differentiation of a new recovery computation.
  Requesting differentiate_recovery is rejected rather than silently zeroed.
- Runner source fixes bottom/top X, bottomY, imposed topY. The old scalar Fy
  is minus bottom internal-force sum; MATLAB index is fix_Y+N in1-based block
  layout, Python is2*(node_id-1)+1. Index/unit/sign conversion is tested on
  supplied small arrays, not on the native geometry.
- Crucially: staggered K is rebuilt from final u/d, THEN optional damage clipping
  and history commit occur, THEN scalar response is written using cached K,
  THEN post-commit snapshot is written. The peak oracle is a different freshly
  assembled pre-commit point with frozen pre-phase lower/history. Stored Fy
  cannot be called fresh post-clip reaction without actual numerical comparison.
- The scalar step-post formula is verified in a local GRIPHFiTH library mirror.
  That file is not among the four locked producer blobs; its exact legacy
  producer identity remains explicitly unverified. The locked solve source
  binds call order/cache semantics, not an invented fifth source match.

New A's observation contract is a fresh force at the exact supplied u/d,
declared model family/boundary/units and phase. Legacy responses remain useful
development observations with their precision/timing uncertainty. Do not
silently merge their solve-state reaction with a different committed d/history.

## 4. One complete next validation proposal (NOT executed/authorized)

Purpose: decide whether consistent material sensitivities and attributable
observations can identify E then Gc/alpha_T, rather than merely reduce a loss.
Use the same model/acceptance policy, independent parameter axes and complete
loading/unloading/history as the earlier A design. No extra tiny-test ladder.

1. Freeze one future execution packet: exact reviewed code, parameter/initial
   convention, provider scales/thresholds, source/observation phase contract,
   native resource limits and an external watchdog. Sparse native cost/fill,
   usable bound conservatism and actual branch coverage are UNKNOWN now.
2. In that one authorized packet, audit initial/common identity and original
   cached-versus-fresh reaction timing using the existing arrays. Preserve
   source-family mismatch as a result. Do not use original snapshots as KKT
   targets for the new nodal-K model. Raw original tape can check primitives;
   a jointly accepted current-model path must come from the existing forward
   owner, not a second producer or stitched conditional endpoints.
3. Cover stable loading, f<1 fatigue, unloading, bound release/sticking and
   the first event neighborhood with whole-history tangents. Compare central
   parameter differences on stable branches and right-direction differences
   at switches. A switch without uniqueness evidence remains unavailable;
   report the stopped horizon, not a fabricated full-path gradient.
4. Once a complete derivative path is demonstrably valid, use the previously
   proposed3 parameter truths (baseline/Gc-only/alpha_T-only), two calibration
   load histories and one excluded-from-fit history, with reaction-only versus
   reaction+sparse displacement observations. Compare implicit sensitivities
   against the same-forward finite-difference inverse baseline, including all
   failed evaluations, factors, histories, IO and wall/memory costs. Do not
   predeclare that AD is faster for two parameters.
5. Decide by identifiable parameter recovery at the designed noise/parameter
   scale and consistent excluded observations. If only parameter combinations
   are identified, report those sets and redirect observations/loads; if native
   bounds/cost or switched derivatives fail, repair that stated mechanism.
   No test-set selection by future cracks, lowered old tolerances or parameter
   compensation to conceal forward mismatch.

Budget must be determined from the authorized native cost/branch evidence
BEFORE generating the9 future reference paths or running any fit. No credible
native hours or memory figure is available now; the previous owner's budget
is not inherited. A later packet may explicitly authorize the integrated
validation, but this offline update does not.

## 5. Review scope

Request only delta review of these new sparse, transmission/directional and
source/observable interfaces. Reuse c525455c and its19 checked behaviors.
Allow only the new18 small-array tests and text/header inspection. Keep
native matrices/solves, trajectory replays, primal FEM, inversion and all
remote/holdout access outside review execution. Record exact commit and
limitations. Source/array availability or a review PASS is not scientific
parameter recovery or run authority.

The first delta review of 4c0c78b5 requested two repairs: immutable global
material direction per tape, and rejection of wrong-sign bound multipliers
outside the weak band. Both are implemented and covered by the focused suite;
the corrected exact commit fa2e50427c2e48b54d547dd6e4597f5b63628c70 passed
independent focused rereview, 18 tests in0.17s (review_v4.md). Original review
findings remain in review_v3.md. No source/tests/tools changed after that review.
