# S03-E015 — boundary-placement versus basis-capacity diagnostic

## Material Passport

Mode: prospective experiment plan. Domain: controlled experimental DIC.
Credibility: frozen design candidate, not run permission or validated inversion.
Owner: S03-E015; date2026-10-13; protocolv1. No human-subject study.

## Status and scope

NOT_READY until independent exact protocol/code review and actual spatial-asset
admission. Primary storylineS03, C2 conditional current-state diagnostic, not
phase-field evolution, material/fatigue recovery or future prediction. Preserve
E014's completed negative candidate-versus-secant result without retuning it.
Branch codex/s03-e015-boundary-basis-20261013, clean base
2d8398e2df9c9c514dab176b54870b0162981bd4. In scope: new driver/tests/analysis,
E015 records and finalS03 entry. Existing parser, projector and mechanics kernel
reused unchanged; no PIDL/source/training architecture edits.

## Evidence and freshness

Same locked Zenodo11945905 archive: size1248078255 bytes,
MD5e671b804e29401e70043bc1e17f66dd1, canonical original ZIP, no partial file.
Select FIRST next cycle group deterministically: stages10/11/12, cycle225211.5,
reference1. Previous scalar-header/DCPD use is disclosed; no known prior field
fit/score on this cycle in E014. Do not call it an unseen specimen or trajectory.
Read only10/11displacement fields for preparation. Stage12 scalar headers and
bytes may be read/hashed, but displacement/strain NEVER converted before all
predictions freeze. No search for a favorable later cycle if qualification fails.
Do not use recorded cracklength/controller displacement as geometry or BC.

## Frozen interventions and controls

| Arm | Artificial domain/boundary | Damage basis |
|---|---|---|
| B0K0 baseline |36x18mm,41x21nodes |right-tip amplitude only |
| B1K0 boundary-only |43.2x25.2mm,49x29nodes |same right-tip amplitude |
| B0K1 basis-only |36x18mm,41x21nodes |right and left tip amplitudes |
| B1K1 combined |43.2x25.2mm,49x29nodes |same two amplitudes |

Both centered at0, uniform0.9mm spacing and same CCW CST diagonal. B1 moves
closed Dirichlet boundary outward3.6mm on all sides without coarsening. This is
BOUNDARY-PLACEMENT/DOMAIN-EXTENT sensitivity, not pure BC-error identification:
domain and external material support change together. True grips unknown.
Both BCs from four nearest jointlyfinite10/11training facets, affineLSrank3,
fourthneighbor<=2mm. No fitted nuisance BCs, traction guessing or highload BC.

Common scoring observations: jointly finite trainingxyz/uvw, strict
abs(x)<16.2,abs(y)<7.2mm, positive source triangle-lumped areaweights. Same IDs,
xy and weights in all arms, regardless of B1 coverage. Source connections are
zero-based Type3, -1padding, absolute xy areas/3; degenerate/unsupported identity
stops preparation, not silently repaired. Artificial mesh has no NaN-derivedholes.

Same fixed prior d0=exp(-distance_to_segment[(-9,0),(6,0)]/1.5).
bR=exp(-((x-6)^2+y^2)/18), bL=exp(-((x+9)^2+y^2)/18).
d=d0+(1-d0)*(1-(1-qR*bR)*(1-qL*bL)); all bounded0..1.
K0:qL=0,qR21equal values0..0.95. K1:qR SAME21grid, qL SIX equal0..0.95.
K0 is an exact nested subset ofK1, not a differently discretized search.
Fixed scales/segment are transferable MODELING PRIORS, not measured crack truth.
No new-cycle geometry adaptation using high response. E1,nu.30 plane stress,
g(mean nodal d)=(1-mean d)^2+1e-6, no fracture energy/evolution law.

## Training selection and frozen predictions

Same global area-weighted planar-rigid quotient (two translations and one small
rotation), no per-side alignment. Minimize projected mean Euclidean vector error
of u11-u10. Evaluate126pairs per boundary once; nestedK0reuses qL0row. Select
first computed minimum, enumeration qLascending thenqRascending; no refinement.
Save EVERY sampled training field/profile and solver residual, both meshes/BCs,
selected amplitudes/currentd, numerical response spans and two-column weighted
secant sensitivity SVD atq0 (firstpositive qR/qL values, NOT tangent/noise rank).
All fields/parameters/predictions frozen before target access. No winner chosen
using high response. Numerical sensitivity<=1e-10mm does not cancel this forward
diagnostic: flag amplitude numerically unresolved and still evaluate fixed frozen
fields; do not claim inversion success. Rank/noise claims remain blocked.

Predict high increments by alpha=(F12-F10)/(F11-F10). Comparator secant=
alpha*(u11-u10), plus d0-only and intact under EACH boundary (9arms total).
Same-origin/direction within-cycle load extrapolation, not future-cycle forecast.

## Primary diagnostic estimand and decision map

Held common area-weighted quotient vector MAEs L00,L10,L01,L11 [mm].
One primary lever contrast D=L10-L01: positive favors basis-only over boundary-
only; negative favors boundary-only. Report sign, magnitude and gain overL00.
Boundary mean gain=((L00-L10)+(L01-L11))/2; basis mean gain=
((L00-L01)+(L10-L11))/2; interaction=L11-L10-L01+L00 are explanatory, not new
success gates. Show train AND held2x2tables/profiles, all9paired comparisons.

No defensible DIC noise margin/repeated independent units: descriptive diagnostic
only, no pvalue/spatialbootstrap/significance or physical threshold. Feasibility:
E014 candidateMAE0.00260239 vssecant0.00252766mm, only0.04055% benefit fromq;
near-flat objective motivates the nested-capacity and boundary intervention.
One cycle cannot conclusively separate boundary/model misspecification, unknown
crack prior, noise, plasticity, compensation or nonlinearity. Even both losses
improving does not identify the true cause. Exact tie or bothsinglechanges>=L00
means no preferred SINGLE repair; combined benefit means interaction; allpoor
means residual/model adequacy unresolved. Finite nonzero D alone is not proof.

Primary direction only chooses a plausible lever for a separately frozen future
experiment; no heldwinner adoption/retraining/re-scoring on this consumed cycle.
If all mechanics worse thansecant, preserve that result and component progress.

## Gates, budget and delivery

Prepare receipt binds exact input/package/source. Independent actual grid/BC/
basis/mask/weights admission BEFORE real solve. TaoboGPUServer8only,1CPUthread,
<=1421nodes/arm,252candidate+2intact=254solves, bounded600s wall time checked
between solves (no global kill). Stop any nonfinite/area/damage/residual>1e-8
failure, support/reference/receipt mismatch. No fallback producer or automatic
failed-fit retry. Real mechanics never onMac. FreshRunIDs and detached fit.
Validate onMac light scoring orTaobo, only successful source-bound frozen receipt,
exact targetbyte hash/stage/reference/cycle/force. Planar eligibility finiteXYuv,
coordinate agreement<=1e-6mm; >=10/rank3; identical subset all9arms, missing IDs
and area coverage. Missingz/walone irrelevant. Full crosscheck via closed-form
projection if numerical warnings; original outputs preserved.

Minimum evidence: source/prepare/fit/validate receipts, both actual asset sets,
all252sampled candidate fields/profiles, frozen9predictions, held target/residuals,
primary contrast/diagnostic table, sensitivity SVD, README and legible same-scale
field/profile/2x2figures from EXACT scored outputs, independent evidence review.
Validityfailure inadmissible; unavailable contrast inconclusive; completed valid
diagnostic records descriptive lever/no preferred lever, not physical recovery.
Disposition repair/redirect chosen only from stated findings. Sync task-level
decision/outcome to Obsidian, no duplicated chat transcript.
