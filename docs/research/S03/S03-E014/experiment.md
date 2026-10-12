---
storyline_id: S03
experiment_id: S03-E014
protocol_revision: v1-design-freeze
status: draft_observation_operator_not_run_ready
claim_class: C2_state_measurement_diagnostic
evidence_domain: controlled_experiment
research_disposition: repair_observation_operator_then_review
---

# Single-cycle three-load observation-to-mechanics bridge

Owner: AA2024 bridge; branch `codex/aa2024-value-blind-audit`; base
`6a68ecec8ed3b5566acaf2b870b52f06ffdc4ca8`. In scope: this folder, the triplet
structural inspector and its tests, S03 claim-impact entry. Existing forecasting,
other Storylines, training/producer processes and shared checkout are excluded.
No new worktree is required: reuse the matching clean AA2024 worktree.

## Question and limited interpretation

Can one fixed, low-dimensional spatial degradation state explain a current
cycle's load-increment displacement field and reproduce its held-out higher-load
interior response, conditional on fixed geometry, reference/gauge and boundary
model? This is a current-state diagnostic, not fatigue-history recovery, next-
cycle prediction, unique phase-field identification or material calibration.

The user explicitly authorized this separate current-state bridge on 2026-10-12.
This does not retrospectively pass the earlier forecast/mechanics gate or lift
the no-parameter-inversion restriction inside that old experiment. No parameter
or state fit has occurred here. This document freezes the small design, NOT Run
Ready: the items in the admission section must be resolved and independently
reviewed first. Do not invent a numeric reference uncertainty or success margin.

## Evidence and deterministic selection

Use only the first admitted E012 cycle group: stages 7, 8, 9, cycles 126873.5.
No quality-ranked replacement group; if unusable, record why and preregister a
repair instead. All three are one sequence/one cycle, not independent specimens.
Archive: `local_archive/open_data/aa2024_dic_zenodo_11945905_20261008/raw/` +
`multiscale_digital_image_correlation.zip`, size 1,248,078,255 bytes, prior lock
MD5 e671b804e29401e70043bc1e17f66dd1. Preserve its identity; exclude `.partial`.
The selected member names, structural observations and exposure are recorded in
`inspection.md`. No full-trajectory spatial data or later cycle may be used.

## Frozen information sets and primary comparison

- Fit: stage7 low-load and stage8 intermediate-load fields only, their loads,
  headers, coordinate/validity information and connection records.
- Held-out target: stage9 **interior in-plane displacement increment** relative
  to stage7, measured in mm. Entire stage9 response is withheld from fitting,
  geometry selection, rigid-gauge alignment and hyperparameter selection.
- Stage9 load, coordinate/support metadata and headers are permitted for
  structural audit. Complete selected bytes were read/decompressed in the
  initial inspection; target displacement/strain values were not numerically
  analyzed or scored. This is not a cryptographically sealed-file claim.
- The mesh, ROI, crack basis and fit mask must be built from stages7/8 only.
  Do not choose a common three-load mask using target response quality. Report
  target missingness on frozen fit support (currently 116 coordinate-missing
  nodes before ROI selection), coverage and exclusions without zero filling.
- Freeze all candidate predictions before opening/scoring stage9 response.
  No high-load interior or boundary observations may tune the strict held-load
  candidate. A measured-high-load-boundary variant would be a separately
  declared conditional-interior task, NOT a rescue or full-load holdout.

Primary diagnostic estimand: area-weighted interior in-plane vector absolute
error (mm) at the high load, paired candidate minus direct field secant error,
on identical frozen spatial support. Report its sign and magnitude, comparator
and candidate errors, coverage and spatial error map. One cycle gives no
population confidence interval; nodes are not independent units. No numeric
scientific-pass margin is defensible yet. A lower diagnostic error is a bounded
descriptive observation, not verified damage truth.

Direct field comparator (same allowed observations):

`u9_hat = u7 + (u8-u7)*(F9-F7)/(F8-F7)`.

Also retain an intact elastic response using the exact same patch/BC/gauge as
the mechanics candidate. Neither comparator may use high-load measured BC.

## Frozen inversion variable, fixed quantities and output

The only adjustable state variable is one dimensionless local degradation
amplitude `q` in `[0, 0.95]`. Damage convention: 0 intact, 1 fully damaged.
Use `d(x;q)=d0(x)+(1-d0(x))*q*b(x)` and
`g(d)=(1-d)^2+1e-6`, with fixed `0<=d0,b<=1`.
`d0` is a geometry-compatible initialization; `b` a localized spatial basis.
They must come from a reviewed training-only crack/ROI construction, not NaN
rows interpreted as cracks and not a target-derived threshold. Their physical
support and regularization width must be frozen before fitting q. These assets
do not yet exist: the model is not presently executable or qualified.

Fixed constitutive diagnostic: small-strain, isotropic plane-stress elasticity,
Poisson ratio 0.33 as an explicit modeling assumption, not a measured AA2024
property. Use normalized homogeneous stiffness scale E=1 for a displacement-
driven patch; uniform stiffness scale cancels from this boundary-value problem.
Therefore it CANNOT recover E or match global force/reaction in physical units.
Force is used to define the increment ratio, NOT misapplied as traction on a
DIC view boundary. No joint optimization of E, nu, Gc, length scale, fatigue
parameters, load scale, rigid motion, plasticity or a free pixelwise damage map.
Gc/fatigue history are absent from this fixed-state elasticity diagnostic: this
is not a solved phase-field fracture evolution equation.

Use incremental response stage8-stage7 to avoid an unobserved reference-load
offset. Reference/gauge consistency still must be checked; subtraction alone
does not certify reference semantics or rigid-body compensation conventions.
Fit q using training interior increment only. Boundary increment is supplied
from a training-only artificial closed patch contour, spatially separated from
the scored interior. Extrapolate that boundary increment by the recorded force
ratio to stage9. This is an explicit proportional-boundary hypothesis; residual
failure may be boundary/model mismatch, not evidence that damage is absent.

Output: fitted q/profile over the fixed basis, reconstructed candidate d(x),
predicted in-plane displacement increments, held-out error and coverage, and
sensitivity/non-identifiability diagnostics. No recovered fatigue histories,
fracture energy or calibrated material properties. If multiple q are
observationally indistinguishable, report a feasible range/profile, not a
single uniquely recovered state.

## Admission and cheapest decisive tests

1. Qualified structural export: count/retain all missing/sentinel records;
   confirm IDs, reference coordinates, unit schema and exact fit-only support.
   Inspector currently has only local synthetic tests, NOT Code Ready review.
2. Verify DIC reference/gauge/compensation operator from export documentation or
   source; archived reference1 is absent. The release describes an unloaded
   global reference, but its actual reference load and compensation operation
   are not independently established by the selected files.
3. Freeze training-only ROI/crack initialization and artificial boundary. Check
   element support, nonzero area, orientation, connected components, holes,
   crack discontinuities and non-crossing triangles. Connection files are
   visualization topology, not an automatically qualified FEM mesh.
4. Verify whether out-of-plane motion, closure/plasticity or registration
   mismatch invalidates the plane-stress fixed-state interpretation, using
   training fields only. Do not infer crack geometry from missing facets.
5. Before any state fit, run a sensitivity/profile check on q against the
   fixed observation/gauge/BC. Same-direction loads add an amplitude check,
   not independent excitation directions and not automatic identifiability.
6. Independent read-only review bound to code, basis/mesh, protocol and archive
   lock. Renew review after a material change. Only then assign a fresh Run.

## Budget, stop and repair ladder

- Current stage: selected-triplet structural inspection and synthetic parser
  sanity only. No FEM solve, PIDL loop or optimizer on Mac.
- Eventual producer: task-authorized Taobo after availability/protocol checks;
  fresh `S03-E014-Rxxx` folder/receipt, no CSD3 fallback. Producer execution
  remains conditional on the admission and independent review above.
- Proposed first fit cap: one ROI with <=2,000 nodes, q grid of 21 values from
  0 to 0.95, one intact comparator, no architecture/parameter sweep or adaptive
  refinement after holdout access. This cap is not authorization to launch.
- Stop the claim-bearing Run on inadmissible mesh/gauge/BC, insensitive q,
  failed solve/residual/bounds, unavailable score, or cap. Do not add latent
  variables to rescue flat sensitivity.
- L0: reproducible schema/identity/missingness handling. L1: admissible local
  observation operator and static forward solve. L2: q sensitivity/profile
  established under the chosen assumptions. L3: held-load response compared
  descriptively with field secant/intact response. None establishes fatigue
  prediction or unique material truth.
- If boundary proportionality limits the result, next repair is a separate
  conditional-interior test with measured boundary, or verified specimen/grip
  geometry and traction. If localized q is insensitive, redirect to an
  observable compliance state rather than fitting more invisible variables.

Minimum future evidence: exact training-only mesh/basis/BC/masks, observation
operator, reviewed code, receipt, sensitivity profile, all candidate/comparator
predictions, missingness/coverage, area-weighted error table and target/prediction/
error visualization with README. No scored visualization exists yet.
