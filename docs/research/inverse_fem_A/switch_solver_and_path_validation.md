# A: switch solver, uniqueness evidence and complete-path validation proposal

2026-10-20. Continue the same Q4 material-inversion preparation (D2); no new
producer, FEM step, native-size algebra, real trajectory replay, fit, SSH,
training or protected observation is authorized or executed. A/B/C remain in
Obsidian; A is active. This is code preparation and a prospective validation
proposal, not an Experiment execution card. Previous c525/fa2e5042 reviews and
raw/source inventories carry forward except for the explicitly changed tape.

## What is implemented

`source/q4_inverse_switch.py` adds a sparse semismooth Newton solver for the
right-direction equations on an externally supplied accepted Q4 state. History
A/q is eliminated with the exact directional trial map, rather than frozen or
reset. Boundary and strong-lower motion are lifted; free displacement, interior
damage and weak-bound damage are unknowns. The existing full force/BC/damage/
history equation check remains independent of the Newton residual.

Let x be the reduced scaled direction and G(x) the scaled force/damage
directional residual. The product domain C is unrestricted on free-u/interior-d,
x_i >= dd_old_i/column_scale_i at weak lower bounds, x_i <= 0 at weak upper
bounds. Strong lower constraints use dd=dd_old; upper/fixed use dd=0. The natural
residual is x-P_C(x-G(x)): G on free coordinates, min(slack,G) at lower bounds,
max(x,G) at upper bounds. Its zero is equivalent to the directional VI and the
previous complementarity equations. Positive independent row/column scales
preserve these componentwise conditions. They are explicit and identity-bound.

The Newton matrix is assembled from analytic local12x12 Q4 blocks. Amor,
history positive-part and fatigue-threshold selections depend on the current
DIRECTION, and weak-bound rows choose the corresponding identity/residual row.
No finite-difference Jacobian, dense native matrix, global basis probing,
smoothing, implicit physical time stepping or optimizer is introduced. Each
Newton solve has an independent linear-residual audit. Budgeted residual-merit
backtracking accepts sufficient decrease; iteration/line search/factor/storage/
time failure returns a typed stop and never advances the sensitivity tape.
There is no claim of unconditional global Newton convergence.

`SensitivityTape.advance_switch_given` validates the parent, material, mesh,
load, exact supplied u/d and committed history BEFORE solving. It passes its
one immutable global material direction, repeats the full directional-equation
audit, and commits tangent/receipt only after successful uniqueness evidence
and solution. Failed or duplicate/mixed transitions do not commit. Stable
`advance_given` keeps its previous API and uses the same transition validator.
Neither method advances or writes a primal state.

## Why one selected Jacobian is insufficient

A directional complementarity problem may have multiple roots even when the
Jacobian on one chosen branch is nonsingular. Example: x>=0, G(x)=1-x>=0,
xG(x)=0 admits x=0 and1, while the natural residual's local Jacobian at0 is+1.
The solver does not interpret a small residual or selected LU as uniqueness.

Instead, local assembly also constructs an entrywise interval [Jlo,Jhi]
containing EVERY generalized derivative of G. At a history/fatigue switch their
selection product is over-enclosed in[0,1]; at an Amor kink both tensile and
compressive stiffness selections are included. Correlations are discarded,
which can make the bound inconclusive but cannot improve it artificially.
All selection correlations and the parameter/history affine RHS are preserved
in the actual Newton residual. Actual Q4 derivative blocks are compared against
the independent original directional map in the focused checks.

For every J in the enclosure, bound the symmetric part below by mu I. Two
explicit sufficient bound methods are available (no automatic retry):

- `sparse_ldlt_interval` (default): form the symmetric midpoint S and entrywise
  radius R. Symmetrically permuted sparse LU must give the same row/column
  permutation and positive diagonal D. Construct B=L D L^T, check its sparse
  product residual against S, and bound lambda_min(B) using positive triangular
  comparison bounds for ||L^-1||1 and ||L^-1||inf. Then
  mu = min(D)/(bound1*boundinf) - ||S-B||2_upper - ||R||2_upper.
  This does not assume SuperLU is Cholesky, or that U is exactly D L^T.
- `weighted_gershgorin`: a prospective positive comparison vector bounds every
  symmetric-part eigenvalue by weighted row discs of the full interval hull.
  This is cheaper but can reject an ordinary SPD mass matrix; sparse LDLT is
  the explicit default for that reason.

Positive mu makes G globally strongly monotone on C. If x,y are two VI
solutions, their inequalities imply (G(x)-G(y)) dot (x-y)<=0, while strong
monotonicity implies >=mu||x-y||². Hence x=y. The converged fully audited root
supplies existence to numerical tolerance; uniqueness is not inferred from
convergence. A global Lipschitz upper bound L from the same hull also supplies

```
||x-x_exact||2 <= [1+(L+1)/mu] ||x-P_C(x-G(x))||2.
```

Proof: y=P_C(x-G(x)) is feasible; its projection inequality and the exact VI
bound ||y-x_exact|| by (L+1)||x-y||/mu. Add ||x-y||. Both the natural residual
and this solution-error bound must meet their prospective tolerances, followed
by the independent physical/full-history directional-equation audit.

The positive mu and reciprocal mu/L thresholds, scaling, problem, resource
limits and bound method are identity-bound. Failure to prove the sufficient
bound is **inconclusive**, not proof that the real problem is nonunique. eta0
null modes, indefinite coupling, interval over-enclosure or poor conditioning
can all stop this route. No parameter compensation or arbitrary chosen tangent
is allowed to hide a stop.

### Numerical/domain limits that remain

- Float64 bounds include conservative rounding padding and checked factor
  residuals; as with the previous regularity provider, this is numerical
  evidence, not a formally verified interval-arithmetic proof.
- An exact constitutive kink defines a continuous piecewise-affine right-map.
  If trace/history/fatigue gap is nonzero but inside the nominal switch margin,
  the solver rejects certification and requests tighter state/branch evidence.
  It does not silently snap the primal state, lower a margin, or assert that
  a nearby smooth problem has the exact-kink derivative. Weak-bound activity
  remains the declared finite-tolerance KKT convention of the existing problem.
- Strong monotonicity is sufficient and conservative; this is not a complete
  decision algorithm for every degenerate/nonmonotone fracture problem. A
  genuine multiple branch or unproved bound stops the complete derivative
  horizon. A different sufficient theorem or model change would need review.
- Sparse LU is internally blocking. Python time/fill checks cannot prevent its
  temporary allocation. Native use requires an external process/RSS watchdog.
- Tests use <=11 reduced unknowns. Native bound usefulness, fill, performance,
  all600-state admissibility and full-path differentiability remain unknown.
  Sparse code structure alone does not close those numerical questions.

## Actual local checks and review request

New switch suite:20 small-array checks. Together with the18 affected offline
interface checks: **38 passed in0.32s locally**. The original19 residual/implicit
checks are unchanged and their prior independent result is reused.

Coverage: weak lower release/sticking for opposite Gc directions; moving lower
and old A/q transmission; exact unloaded Amor branch with free mechanics and
nonzero BC lifting in tension/compression; both fatigue-threshold directions;
selected sparse history-switch Jacobians versus central differences of the
independent directional map and their inclusion in the all-branch hull; positive
bounds versus dense tiny matrices and a branch-only nonunique counterexample;
upper natural-map equations (manufactured algebra, not a physical AT1 upper
state); nonunit scaling, identity mismatch, null/indefinite or inconclusive
bound, dimension/fill limits, empty system and atomic history transactions.
No new primal field is optimized. The original conditioned fixtures are unit
arrays, not newly qualified experimental data or a real recovery history.

Independent code review requested for the exact commit: analytic blocks,
all-selection enclosure, sufficient uniqueness proof/rounding interpretation,
VI/Newton/min/max signs, error bound, atomic integration and the prospective
plan/cost arithmetic below. Reviewer may inspect text and execute only these
small-array suites; no native solve/replay or parameter candidate evaluation.
The receipt will record exact version, checks, limitations and any fixes.

## Complete-path validation proposal (not authorized or executed)

**Question:** Does the implemented same-model parameter-to-observation map have
correct, attributable right-direction sensitivities through every accepted
loading/unloading/fatigue/constraint transition of one complete native path?
This validates derivatives, not material recovery or real-road physics.

### Fixed model, inputs and path

- Reuse the existing forward owner, not a second producer: native86756-node /
  86408-Q4/four-GP mesh; AT1/Amor/Carrara, E1,nu.3,Gc.01,ell.01,alphaT.5,p2,
  thickness1,eta0 and the existing supplied recovered crack profile. The initial
  profile is fixed across parameter candidates by definition; initial u/A/q
  tangents zero and f1. Numerical initial equivalence is a prerequisite, not
  inferred from the previously inspected header.
- One120-cycle path, all5 physical substeps per cycle, no selected-peak shortcut.
  Prospective reuse of the forward owner's current nominal load specification:
  `[.02999988,.05999988,.08999988,.11999988,0] * .108` in its normalized units.
  This is explicitly the owner's scaled nominal history, not an unscaled
  Umax=.12 run. Freeze exact source convention when preparing the execution
  card. No automatic amplitude change if this history supplies no f<1 support.
- At least one genuine f<1 segment is necessary to claim fatigue-path derivative
  validation. If absent, report limited elastic/fracture coverage; do not claim
  alphaT validation. Failed/stopped histories stay failed/stopped.
- Existing original600 snapshots are primitive/source diagnostics only. They
  are not accepted targets for the changed nodal-K model. The nominal and
  perturbed paths must each satisfy the original current-model acceptance
  tolerances and carry their own full history from the fixed initial profile.
  Preserve the owner's120s physical-step deadline and all force/KKT/history
  criteria; do not inherit its execution permission or136-host-hour budget.

### One integrated comparison, exact work count

Use log parameters xi=(logE,logGc,logAlphaT), with nu/ell/p/geometry fixed.
Four relative directions: eE,eGc,eAlphaT and (1,-1,1)/sqrt3. For each direction
v and -v, compute a complete right-direction sensitivity tape from the nominal
path, including all600 transitions. Stable states may share the exact same
factor for several RHSs; switched states use the direction-dependent solver
and fresh audits. No factor from a different material/state may be reused.

For h=.01,.001,.0001, generate theta(h)=theta0*exp(h*v) and theta(-h) likewise,
with complete independent primal histories and exactly the same initialization,
loading calendar and acceptance rules. This is24 perturbed full paths plus1
nominal path = **25 paths /15000 maximum primal substeps**, plus **8 directional
passes /4800 sensitivity transitions**. No inverse optimization, training,
new truth families,9 reference-recovery design or protected holdout is included.
These are development numerical differences, not blind scientific confirmation.

Compare u,d,A,q,f and the declared fresh reaction/sparse displacement operators
at every state. Include material-explicit force terms. The sparse displacement
sensors/BC/sign/units and solve-versus-commit phase are frozen beforehand.
Only stable neighborhoods are combined into central differences; at switches
compare the corresponding right direction to its own one-sided path, including
one-sided branch changes. Never average opposite-direction tangents there.
The mixed direction is an independent combination check; it need not equal a
linear combination of coordinate directions at nonsmooth transitions.

### Criterion, uncertainty and minimum evidence

Primary numerical criterion: every state of all8 directional tapes must have
valid bound evidence and full equations, and its one-sided observation change
must agree with finite differences within the independently measured combined
forward/numerical difference uncertainty. Report the maximum standardized
mismatch and the first unavailable state; no best-prefix result is called a
complete-path pass. This is one whole-path consistency claim, not a vote by
many correlated states.

Do not import a universal1% gradient threshold. At each h, propagate the
independently audited forward error bounds through the paired difference
(dividing by h), include the tangent solution-error bound and local difference
truncation uncertainty estimated across the three declared h values. Require
a resolved convergence window before the error platform, not merely overlapping
wide intervals. If forward residuals cannot be turned into trustworthy field/
observation error bounds, or3h values show no resolved window, classify as
inconclusive and preserve the reason. Stable-window Taylor remainder should
show second-order decay before the platform; a switch uses right-map consistency
and may need a narrower branch-valid h window. Additional h, tolerance changes,
new loads or repeated trajectories require an explicit amendment, not an
unlimited automatic sweep.

Evidence: all transition/branch/regularity/uniqueness receipts; failed states and
resource limits; nominal/perturbed accepted tapes; both-sided derivative/error
curves over the whole calendar; branch/event map; reaction and selected field
comparison at the first load/first unload, first f<1 state, first weak release,
maximum predeclared mismatch and final state (duplicates removed, no cherry
picking). Runtime table counts primitives, audits, rejected Newton trials,
failed work, IO, factor storage and total wall/CPU/RSS. Show native agreement
and gradient cost separately; do not infer that differentiability is faster.

If the first nominal path fails forward acceptance, return to its existing
owner. If a uniqueness bound fails, stop and diagnose nullspace versus bound
conservatism without choosing a favorable branch. If full derivatives pass but
observations have little alphaT information, the next decision is loading/
observation design. Parameter recovery/profile and excluded-loading validation
are a later separately budgeted experiment.

## Concrete proposed resource envelope (not an ETA or permission)

No native invocation occurred in this task. Actual existing owner evidence:
first native accepted step38.733s, next step stopped at120s in repeated mechanical
LU, sampled RSS4.084GiB. This is one short prefix on the previous owner version,
not a600-step rate, current-switch factor memory, or proof that any full path
will finish. Source: current owner's `linux_validation_result_v1.md/json`.
Its newer coupling repair has no complete-path cost outcome available here.

For a future exact packet, propose CPU-only on the SAME approved forward
producer (currently the owner's Linux GPUServer8; any host/allocation change
needs explicit task authority), one worker, at most16 CPU threads, RSS64GiB,
no GPU. These are ceilings subject to a real capacity check, not reservations.
Mac continues to perform development checks only; no SSH or reservation now.

| Budget component | Hard cap, host wall hours | Basis |
|---|---:|---|
| Initial/source/observable numerical audit |4|Existing arrays; charged separately; no independent recovery solve |
| Nominal complete path |20|600*120s, aggregate IO/cleanup must also fit; first failure stops |
|24 perturbed complete paths |480|24*20h; all from initial state, no borrowed history |
|8 whole-path directional passes |24|8*3h; average allowance18s/transition, NOT measured; first budget failure stops |
| Analysis/evidence |4|Whole-calendar errors, field panels, resource ledger |
| Supervision/termination reserve |4|Inside global cap; no extra retry budget |
| **Total** |**536**|**8576 allocated core-hours max at16 threads;0GPU-hours** |

Per physical step deadline120s remains unchanged. Proposed per directional
state deadline60s, up to20 Newton iterations and12 backtracks per iteration;
aggregate3h/pass prevails even when individual states meet60s. Factor/matrix
nnz/product-work caps must be fixed using the approved64GiB envelope BEFORE
launch; external RSS/time watchdog covers blocking SuperLU. No numeric nnz
limit is invented here as a guarantee of native fit; the execution card stays
disabled until arrays/index widths/library versions and peak storage have been
bound and independently checked. No restart after timeout or fill failure.

This is a conservative **complete study ceiling**, about22.3 days if one host
were occupied continuously, not the expected runtime. A useful planning formula
is `T_total = 25*T_path + T_8tangents + T_audit/analysis/overhead`, capped above.
For illustration only, if a full path later measures1/5/10h and the remaining
allowances are used in full, totals are61/161/286hosth. Those scenarios are not
measurements or estimates from the first38.7s step. Do not approve/reuse another
owner's budget merely because it is smaller. The nominal path and its tangent
passes are the first portion of this SAME integrated study; a stopped prefix
terminates before spending on the remaining24 trajectories, without a duplicate
profiling/restart ladder.

Storage: retain minimal complete accepted u/d/lower/four-channel history for
all25 paths, plus du/dd/dA/dq for8 passes and receipts/figures. One primal state
is about13.84MB uncompressed, so15000 states about208GB decimal;4800 tangents
about36.5GB, before headers/raw/failure evidence. Propose512GiB primary plus
512GiB independent archive, >=1TiB free combined; no compression saving is
assumed. Symbolic/numeric factors are transient and may not accumulate per state.
Stop before reserve exhaustion; no partial transfer claimed as complete archive.
No paid-compute cash amount is known; this envelope is compute/storage, not a
cloud quote. Producer availability and tariff would be checked only if chosen.

**Status:** exact code156f9924d2aa5ee4352dbd32cc6ebf839746fb1d passed independent
review (review_v5.md),38 small-array checks independently passed in0.31s.
No code/tests/tools changed after review. Proposal not executable: no fresh Run ID/command/runtime pin/resource
card or human execution approval. No FEM, inverse fit or native replay started.

## Supporting methodological sources (targeted, not a literature review)

The VI uniqueness proof and bound above are spelled out for this exact adapter.
Semismooth residual formulations alone do not establish uniqueness; see the
primary research examples of multiple VI roots in
[Farrell et al., Deflation for semismooth equations](https://arxiv.org/abs/1904.13299).
For the broader VI/semismooth algorithm setting see
[Gfrerer et al., application of semismooth* Newton to VIs](https://arxiv.org/abs/2007.11420).
This implementation does not claim to reproduce those methods or their global
convergence results; its specific sufficient certificate and bounded Newton
failure policy are the contract actually inspected here.
