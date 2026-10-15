# S03-E016 — training-opening geometry prior diagnostic

Protocol v2, prospective revision 2026-10-15 after the 2026-10-14 Pro review.
Owner S03-E016 / storyline S03. Original v1 retained at commit7383d43;
its REVISE_PLAN remains historical. No new-cycle fields or results viewed.
Plan review passed 2026-10-15 (review_round2.md); independent code and actual
training-asset reviews remain outstanding. No execution authority implied.
Controlled-experiment C2 conditional static-response diagnostic, with C1
coordinate admission. No independently measured crack-tip truth is available.
Question: does a training-opening-defined segment prior change held response
error versus the transferred (-9,0)..(6,0) prior under the SAME static model?
This tests a geometry-definition procedure, not physical crack-tip recovery.

Branch codex/s03-e016-geometry-alignment-20261013, clean base4d73af4 from
origin/codex/s03-e015-boundary-basis-20261013. Scope new runner/tests/plots/E016
records and dated S03 entry; existing parser/kernel/rigid quotient reused
unchanged. No PIDL training, material calibration, or E014/E015 retuning.

## Evidence and information boundary

Original Zenodo11945905 ZIP size1248078255, MD5e671b804e29401e70043bc1e17f66dd1.
FIRST next group stages13/14/15, cycle292018.5, reference1. Stage13/14 fields
only for geometry and BC; connections13 only for source area weights. Stage15
headers and whole bytes may be read/hash-bound before freezing, but NO response
body/coordinates/strain conversion until source-bound completed predictions.
Stage12 remains consumed by E015 and is NEVER a new input. Historical scalar
DCPD labels/headers already processed; do not claim unseen specimen/trajectory.
No later-cycle fallback, stage15-selected geometry, thresholds, or model change.

## What coordinate verification can establish

Require IDs exactly1..N with identical ordering, stage/reference/cycle identity,
increasing positive loads, jointly finite XYZ/UVW, reference XYZ agreement1e-6mm.
Use stage13 serialized reference XYZ (XY for planar operators) consistently for
all neighbours, ROI, areas, plane diagnostics and scoring. Stage14 coordinates
only check identity; never alternate or average coordinates between operators.
Use incremental displacement u14-u13 directly.
Do not reapply alignment headers: metadata describes degrees/translations, but
exact exporter transformation algebra is unresolved. Preserve header values.
Published consumer convention and previous fixed global quotient are retained,
not promoted to an authenticated exporter inverse. No side-specific alignment.
Record max coordinate mismatch on the whole jointlyfinite training set.
Plane diagnostic uses ONLY the fixed common scoring ROI defined below, equally
weighted: OLS z=c0+c1*x+c2*y, normal(-c1,-c2,1) normalized towardpositivez,
tilt atan(hypot(c1,c2)), orthogonal residual=(z-fit)*normal_z. Report normal,
tiltdegrees, RMS/max OLS-plane orthogonal residual and raw displacement-increment
RMS on thisROI, in fixed order DeltaU=U14-U13, DeltaV=V14-V13, DeltaW=W14-W13.
These are NOT differences of reference coordinates. This is not an orthogonal
best-fit plane: the residual is normal distance to the declared vertical OLS fit.
These are descriptive model-assumption checks, not a new threshold or permission
to automatically rotate coordinates or fit3D mechanics. Preserve3Dcoordinates.
Plane stress, small strain and 2D omission are assumptions, not validated facts.
E remains normalized1 and cannot be identified from all-Dirichlet displacements.
nu=.30, fixed damage/static kernel, no Gc/length-scale/history/evolution recovery.

## Deterministic training geometry operator (freeze before new fields)

Line y=0 and orientation x-axis RETAINED, not fitted or independently verified.
x_i=.9*i mm for integer i=-26..26. At (x_i,+b) and (x_i,-b) independently
interpolate the stage14-minus13 vector by affine LS over FOUR nearest jointly
finite source facets, using reference XYdistance. All profile bands use SAME-SIDE
support: upper from y>0, lower from y<0, excluding y=0. BC interpolation retains
all jointlyfinite facets, no side restriction. Resolve exact computed squared-
distance ties by ascending original facetID. Use centered[1,x-xq,y-yq] equal-
weight OLS, rcond1e-12, same neighbours/coefficients for the paired increment;
rank3 and fourth-neighbour distance<=2mm. Save neighbourIDs, distance, rank,
conditionnumber, four interpolation coefficients, L1 and L2 amplification for
ALL queries includingunsupported. No conditionnumber/noisecutoff added; rank or
radius failure yields missingprofile/support failure forBC; nonfinite numerics
stop, no alternative neighbourhood. Negativecoefficients reported, not called
convex averaging. This interpolates
same-x pairs; translation and infinitesimal in-plane rigid rotation contribute
zero normal difference. Local affine interpolators can still smear near cracks;
missing facets are NOT geometry labels. No strain columns used.

Primary prescribed gauge b=3.6mm. Normal-opening proxy is upper delta_v minus
lower delta_v. Fit an affine-in-x OUTER LINEAR TREND using exactly the14 locations
with abs(x)>=18mm, equal-weight ordinaryLS[1,x], rcond1e-12. Save their indices,
values/residuals and trend at all53locations; subtract it from the entire proxy.
No smoothing, robustreweighting, absolutevalues, negativeclipping or outlier
deletion. This trend fit is a TRAINING
observable definition, not a FEM BC correction or independently known remote
elastic strain. Require all53 primary pairs (106 queries) supported, all14outer positions,
rank2 tail fit, finite outputs. No favorable band/tail selection.

Let peak be the FIRST maximum of corrected primary opening. Require positive
peak (first in ascendingx, exactties). Define the piecewise-linear function
through all53 samples and the connected component of >=halfpeak containing it;
linear-interpolate its left/right halfheight crossings with adjacent below-half
bins. Require crossings exist, L<R and -16.2<=L<R<=16.2 (1.8mm margin inside
fixed B0). Multiple distinct lobes and the connected-bin rule are reported; no
claim these halfheight locations are true crack tips or optical crack length.
These two positions define the alternative segment (L,0)..(R,0). This is an
effective opening-localisation PRIOR. Save both bracketing intervals, primary
peak and number of halfheight lobes; plateaus at halfheight belong to the
connected component until the outermost edge with an adjacentbelowhalf sample.
No endpoint search by mechanical loss. Report old/new centers, lengths and both
endpoint differences separately; changing both endpoints changes position AND
length/damagecoverage. It is not a pure position intervention or proof of prior
error. A positivepeak is mathematical definability, not a noise/physical test.

Two prescribed secondary gauges b=1.8 and2.7mm use the same rule and report
support/curves/crossings when available; unavailable bins stay missing. Each
secondary trend uses only supportedouter positions, at least one on EACH side
and rank2. Selectfirstfinite maximum; require its contiguoushalfheight region
and both adjacentbelowhalf samples finite. Never bridge a missingbin; missing
outside that component need not invalidate it. Existinginteriorcrossingbounds
also apply to reportedsecondarycrossings. Conditions unmet -> bandundefined,
no substitution for primary. They do
NOT choose the primary band, veto/rescue held result, or qualify noise confidence.
Report endpoint spread and whether original endpoints lie in that descriptive
range. No bootstrap, node independence, pvalue or empirical noise threshold.
If primary support/crossing admission fails, STOP before FEM and high conversion;
retain diagnostic, no alternative gauge/cycle retry under this protocol.

## Minimal controlled mechanics comparison

One B0 domain36x18mm,41x21nodes,1600CCW triangles,0.9spacing,120boundary nodes.
BC from four-nearest affine training increment, rank3/fourthdistance<=2mm.
Common observations jointlyfinite13/14xyz/uvw, abs(x)<16.2,abs(y)<7.2, positive
source triangle-lumped absXYarea/3. Zero-based Type3connections; all-1padding;
unknown/mixednegative/repeated/duplicate triangles and retained degeneracies
fail; known nonfinite training facets only exclude weighting. No NaN mesh holes.

Only TWO damage priors: oldfixedsegment[-9,6] at y0 and primary proxy-defined
segment[L,R] at y0. Both d0=exp(-distance_to_segment/1.5), same diffuse width,
kernel E1/nu.30/plane stress/g(mean d)=(1-mean d)^2+1e-6. qR=qL=0 FIXED;
no amplitude inversion or grid search. One intact solve as component comparator.
Exactly3 solves, identical mesh/BC/scoring support. Save all three full nodal
fields and current prior damage, sampled fields and numerical residuals.
Report old/new artificialmesh discrete prior integral D_h=sum_e A_e*dbar_e
(mm2), multiplier integral sum_e A_e*g_e (mm2), area-mean local multiplier
sum_e A_e*g_e/sum_e A_e and area-mean local degradation fraction
R_g=1-sum_e A_e*g_e/((1+1e-6)*sum_e A_e), with positive CST area A_e,
dbar_e=mean of three nodal priors and g_e=(1-dbar_e)^2+1e-6. These quantify
coverage/local-multiplier change, NOT actual crack area, patch effective stiffness
or load-displacement compliance, and not extra parameter selection.
No amplitude inversion despite data-
adapted endpoints; geometry andBC are not independent measurements.
Predictions highincrement alpha=(F15-F13)/(F14-F13) times each static increment;
fourth prediction secant=alpha*(u14-u13). Save allfour predictions and successful
source-bound completion receipt BEFORE stage15body conversion. No high winner
adoption. All training-derived geometry gains are procedure-level, not a pure
intervention at independently fixed true geometry.

## Criterion and outcomes

One primary descriptive contrast Delta=L_old-L_proxy, area-weighted mean vector
norm after ONE global planar rigid quotient on identical eligible stage15support.
Delta>0 proxy procedure improves, Delta=0 equal, Delta<0 worsens. Report both
against secant/intact separately; no arbitrary physical-success threshold.
Held referencexy1e-6, finiteXYuv, >=10/rank3, SAME support allfour, IDs/missing/
area coverage reported. Missingz/walone does not change held eligibility.
Training interpolation (profiles AND BC) uses wholejointfiniteXYZ/UVW13/14;
plane and trainingscore use exactlystrictROI/positiveweights subset; held
projection is constructed once conceptually from that subset restricted to
stage15finiteXYuv, using frozen13referencecoordinates and weights. Equivalent
repeated deterministic projection calls do not imply per-arm alignment.
No held-weight recomputation, sidealignment or x/yMAE substitution.

Feasibility: E015 learningq added3.27% overd0 but geometry was transferred from
firstcycle and no tips were measured; boundary/basis repairs did not help. No
repeatability/noise model or independent specimen units. Geometric alignment
could help, hurt, or be too weak to distinguish descriptively; no expected win.
Independent components: reference admission, primary-gauge support, localization
profile, finite mechanics, prior-vs-intact gain, secant gap. Positive component
progress does not overturn Delta sign or establish recovery/future skill.

Validityfailure -> inadmissible, primary proxy not definable -> inconclusive
geometry repair/no solves, valid completed contrast -> descriptive improved/
equal/worsened prior procedure. No method-wide fail label. If bands disagree,
report localisation ambiguity and propose independently referenced geometry;
if proxy improves yet remains behindsecant, preserve gain and inspect model/
observation adequacy next; if non-improving do not add geometry parameters on15.
All adjustments require a new experiment and new held response.

## Review, budget and minimum evidence

Independent plan/code before actual13/14field processing; independent actual
mesh/BC/profile/derivedprior admission BEFORE3 real solves. Mac preparation,
analysis and light scoring only; real solve on TaoboGPUServer8 CPU1thread.
FreshRunIDs; no fallbackproducer. Soft600s completion rule before/after each
solve and after hashing/serialization; incomplete/overbudget artifacts forensic
only, no held access, no automatic retry. Numerical residual<=1e-8, allfinite,
damage0..1; same reviewed dependencies. Preserve all failure receipts.
Budget applies to WHOLE three-solvefit includingserialization/artifacthashing;
no prefix comparison or droppinglastarm. An inflight solve may finish, but any
observedelapsed>=600 marks wholefitnoncompleted, retainsforensics only and
blocksall stage15conversion. Finalelapsedcheckedafterhashingbeforesuccessreceipt.

Minimum evidence: training source identity+headers, coords/support diagnostics,
all53 primary and secondary gauge values/support/distances/background/crossings,
mesh/BC/sourceweights/priors and asset figure;3 full solved/sample fields and
four frozen predictions, prepare-fit-validation receipts and bindings;allfour
held residual fields/metrics/Delta, independent scalar crosscheck if warnings;
training geometry-overlay/profile decision figure and allfour heldresidual maps,
same units/scale/no cherry-picked case, README_analysis plus same-stem sidecars.
Independent Evidence review and dated storyline/Obsidian milestone beforeclose.
Review approvals concern scope/access/checks only, not scientific truth.

## 2026-10-15 post-review implementation clarification

Adopted round2 suggestions for discrete reports, stage13-only coordinates,
DeltaUVW names and OLS-plane residual terminology. No change to three solves,
stage15 holdout, information set, geometry rule, primary metric or stop rule.
Auxiliary peaks are only maxima on existing support, not over unobserved bins.
Current activity is local synthetic checks and independent read-only code review;
no actual13/14/15 fields, file transmission, remote sync or solver execution.
Implementation also rejects nonfinite alpha and frozen predictions BEFORE held
response conversion. Training-only renderer scripts/aa2024_geometry_prior_view.py
requires completed PREP/source bindings and creates profiles/spatial plots plus
README, sidecars and render receipt. Final stage15 four-arm result renderer is
still pending; no Evidence Ready claim is made or waived by this local code work.
