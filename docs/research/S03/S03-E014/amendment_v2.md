# E014 v2 prospective execution amendment — 2026-10-12

Status: implementation and synthetic sanity complete; independent Code Ready /
spatial asset admission pending. NOT launch permission. Supersedes v1 execution
choices only after exact review. No q fit or high-load response score exists.
Reason: round1 review permits a fixed rigid-quotient observable; primary-source
indexing and nu corrections; deterministic training-only local geometry/BC.
Old v1/round1 verdicts are preserved, not rescued.

## Bounded estimand and assumptions

One current-cycle triplet, stages7/8 fit and9 high response held out. All source
identity/grouping rules from v1 remain. Primary descriptive estimand is
area-weighted vector absolute error of the HIGH-LOAD DISPLACEMENT INCREMENT
MODULO ONE GLOBAL PLANAR RIGID FIELD, candidate minus direct field secant on
identical support. Units mm. No physical success threshold/noise model,
independent specimens, unique damage truth, material recovery or forecast claim.
Same-direction held load tests proportional-boundary extrapolation and a
mechanics-constrained spatial reconstruction, not a new load direction.

Exact projector implemented in `aa2024_rigid_observable.py`: one weighted rigid
span (two translations and infinitesimal in-plane rotation) on the scoring
coordinates; geometry and weights come solely from fit data. Centering preserves
the span. Use weighted least squares with rcond1e-12; fail if rank!=3 or
condition>1e12. Missing high observations restrict all candidates to the SAME
eligible subset and recompute that same geometrical operator on this subset;
no response-dependent weights/coordinate transform or separate crack-side
alignment. Rank/eligibility failure stops validation. Finite3D rotation,
non-rigid compensation, plasticity and frame changes are not corrected.

## Exact training-only spatial assets to be produced

- Rectangle x[-18,18],y[-9,9]mm;41x21 regular nodes,861 nodes,1600 CCW CST
  triangles,120 outer-contour nodes. Artificial displacement-driven local patch,
  NOT real specimen grips. No holes inferred from missing DIC facets.
- Initial prior segment from(-9,0) to(6,0)mm; d0=exp(-distance_to_segment/1.5).
  b=exp(-((x-6)^2+y^2)/(2*3^2)). Width1.5mm and scale3mm are fixed training-
  informed modeling priors, NOT measured true crack or material length scale.
- d=d0+(1-d0)*q*b; q21 equally spaced values0..0.95. g=(1-d)^2+1e-6.
  Fixed damage during each static solve. CST element stiffness uses g of mean
  nodal d; plane stress E1,nu0.30. No evolution/energy-balance/Gc/fatigue solve.
- Boundary increment: affine least squares through FOUR nearest jointly finite
  training facets. Require fourth-neighbor distance<=2mm and rank3. This exactly
  reproduces affine/rigid fields; no high boundary values are used. The observed
  scalar force-gap ratio extrapolates the fitted increment to high load.
- Interior observations: jointly finite fit positions/u inside abs(x)<16.2,
  abs(y)<7.2mm, with positive training mesh-lumped facet area. Areas from stage7
  correctly zero-indexed triangles on common fit support, area/3 to each node;
  not from stage9 or from a target-selected ROI. No zero filling of missing data.
- Model values at original DIC positions: fixed diagonal CST barycentric
  interpolation on the regular rectangle, exact for affine fields.

Explicit comparator: d IDENTICALLY0 is intact on this same continuous domain.
q0 means d0-only and is a separate fixed-prior comparator, not intact. Secant
increment is alpha*(u8-u7). All four use identical geometry/scoring operator.

## Selection, sensitivity and numerical limits

Training loss uses the same area-weighted global-rigid-quotient vector error.
Evaluate all21 q candidates; choose the first computed minimum (lowest q for
exact ties). No refinement, tuning, additional arms or basis selection after
any high response access. Profile, solver residuals and response span retained.

Before selection/validation, report maximum projected weighted response
difference from q0 over the grid. If<=1e-10mm, stop without opening high response.
This is a NUMERICAL visibility floor, not DIC noise or practical identifiability.
A larger response span or a unique minimum does not establish physical q
recovery; reference repeatability/noise remain unavailable. Frozen fixed-basis
q/profile is only conditional state diagnostic evidence.

Zero-body-force linear Dirichlet solves: fail on nonpositive element area,
invalid d bounds/support, nonfinite solution or free residual normalized by RHS
norm>1e-8. Required producer budget: <=2000 nodes,21 candidates plus one intact
solve;1 CPU thread; fresh Taobo Run root. No PIDL loop/GPU training.
CLI prevents real fit off hostnameGPUServer8. Tiny synthetic unit patches are
the only local mechanics tests; no real-data solve is permitted on Mac.

## Three isolated modes and access freeze

1. `prepare`: on Mac, read only locked archive; reviewed structural inspector
   admits specified identity/scalars. Reads stages7/8 training fields; stage9
   response bytes may be hashed but NEVER converted to observations. Generate
   prepared.npz, provenance/preparation JSON and fresh receipt. Includes single
   prepared package hash and exact external held-member hash for later binding.
2. `fit`: on Taobo, input ONLY prepared assets, not the raw archive/high member.
   Check package lock. Compute q profile, fixed predictions and fit receipt.
   Save predictions BEFORE any high-field parse. Stops if q numerically invisible.
3. `validate`: separate invocation ONLY after fit completion/output freeze,
   using the exact held member matched to the external byte hash. Confirm
   stage9/reference1/cycle126873.5/force and reference-coordinate agreement
   <=1e-6mm; finite in-plane target support only. If fewer than10 eligible points
   or projector rank fails, no score. Report count AND area coverage; all
   comparators use the same subset. No fit call/geometry update in this mode.

Outputs: profile, q, conditional d prior, predicted increments, matched
candidate/secant/intact/d0-only held error/coverage. Model state has no qualified
fatigue history. Each mode gets a fresh execution folder/receipt with run ID,
declared source commit and actual runner/dependency hashes. Exact snapshot
membership and prepared assets must be independently checked before producer
fit. Failed outputs are forensic only, not completed scientific evidence.

## Review and evidence requirements

`aa2024_patch_driver.py`, kernel, projector, exact structural dependency and
three new test modules require independent review before real preparation/fit.
Synthetic checks cover affine patch, uniform-E invariance, load homogeneity,
rigid superposition, localized damage sensitivity, interpolation/domain failure,
global-rigid quotient profile invariance/non-rigid preservation, missingness,
frozen prediction/held-member tamper and metric definition. They do not qualify
the actual observation-to-state inverse. Real asset review must check grid,
basis/BC/masks/areas and source lineage, not only file hashes.

Numerical result needs all-scored spatial field/residual figure and profile,
same scales/units/comparators, README and visual QA, then evidence review before
claim closure. Any negative/inconclusive outcome preserves component findings
and selects the next controllable BC/basis/model repair in a fresh protocol.
