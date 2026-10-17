# E037 — per-frame visible image geometry, not material-point tracking

2026-10-17;StorylineS03;protocolper-frame-visible-geometry-v1;base66cf718.
User explicitly redirects priority: recognize crack/image geometry first; four
background template failure isnot a universal prerequisite. Do not repair those
anchors here. Old half-depth definition/operators/geometry/scores remain intact.
Current priority supersedes E036's proposed next background-repair action, not
E036 historical outcomes. New files/metrics/version, same task Obsidian note.

## Smallest question and domain

C2 controlled-experiment exploratory extraction: can visible crack fragments
be represented as per-image mask/path/length/area/local-thickness with explicit
occlusion? Then descriptive C3 scalar replay of already exposed21/22/23 only.
One same-source trajectory,no independent annotation accuracy/material-point,
physical aperture/mm/road/unseen-specimen or blind-target claim. Existing E036
9images only:12,13,15,16,18,19,21,22,23;do not download14/17/20or other sources.
source_lock.json fixes bytes/SHA/protected prior results; allimages were viewed,
no target-before-history novelty. Choose no windows or parameters by new errors.

## Separate the tasks

Per-frame extraction requires source identity,visible trace and exclusion of
fixture/wire/glue/uncertain regions,not temporal registration. Frame differences
can be interpreted as material change only with an additional correspondence
claim,which this experiment doesnot make. Different visibility mustnot masquerade
as shrinkage. Preserve full visible-fragment measures separately from metrics
in a fixed,unoccluded,common image-space evaluation band.

Fixed native ROI[3800,900,4800,3500]; allimage dimensions/orientation recorded.
Use source-only visual support lock per frame: coarse trace corridor and
fixture/glue/exclusion polygons drawn from that image,not by width/forecast
agreement. Early no-identifiable-trace means null/unidentified,not zero/no crack.
Method is observer-guided candidate extraction,NOT fully automatic segmentation
or manual groundtruth. Coarse polyline is spatial guidance,not measured path;
image threshold/connected components/skeleton supply measured readout.

## New geometry definitions and fixed cheap extractor

Native greyscale;101px box background estimate;candidate dark pixels require
grey≤100 and background-minus-grey≥20 (fixed8bit settings). No learned model,
threshold search,error tuning,or closing across occluded gaps. Restrict to≤60px
Euclidean distance from per-frame coarse polyline; retain connected dark
components touching≤12px guide neighbourhood and spanning≥30image rows.
Remove exclusion pixels BEFORE connectivity. Mask isvisible candidate,not truth;
missed/false branches must be shown,not hidden by scalar scoring.

Skeletonise binary candidates,8-neighbour graph with orthogonal edges1px and
diagonal sqrt2 only if no intervening orthogonal bridge. For each connected
fragment,two farthest-geodesic sweeps define an ordered dominant path; sum its
edge lengths for L_visible_px. This isdominant-path length of observed fragments,
not fullbranch-network length or extrapolated hidden crack. Area A_visible_px2
iscount of candidate-mask pixels. No hidden-portion interpolation or zero fill.

Along each dominant path,local mask thickness=2×Euclidean distance transform
to nonmask pixel centres. Save ordered(x,y,s,thickness), and pointwise10/50/90
percentiles plusmean. It is an inscribed-mask local-thickness proxy with grid/
threshold dependence,not orthogonal physical aperture and NOT old half-depth.
Thickness samples within60px of ROI/exclusion boundary are withheld to avoid
mask-edge truncation; their missing fraction reported. Alloutputs taggednew
geometry definition. No cross-unit pooled MAE or conversion to mm.

## Occlusion and minimum cross-frame consistency

Per-frame polygons label board/glue/wire/uncertain areas,including artificial
mask boundaries. Show excluded fraction and cut endpoints; do not connect
across polygons. Metrics cover only visible support; full-ROI values across
changed occlusion are descriptive,not growth/closure or prediction references.

For21/22/23,freeze common native band[3900,1700,4600,1950] above fixtures:
selected on historical source visibility,not error. Check same officialcamera/
orientation/dimensions,trace branch and no occlusion in this band. Sameimage
coordinates doNOT establish same material points. Broad upper-beam ORB+RANSAC
similarity fit is nuisance diagnostic for view/scale/rotation/translation only,
never used to move masks or repair old fouranchors. If unavailable,label
cross-frame comparability unknown; still return per-frame geometry.
No arbitrary similarity-error threshold or physical-position accuracy claim.

Main replay requires same sourceview/dimensions and full commonband visibility
in all3images plusextractable candidate; allstate differences remain observed
image-space quantities. Report similarity diagnostics and potential support
drift alongside result,not pretend exact material registration.

## Scalar replay, criterion and limitations

First extract21/22 with fixed settings,save scalar predictions,then evaluate23
using same extractor and independent23source-only support. Since allimages
already exposed,this sequencing limits code leakage but isnot blind validation.
Compare clipped-at0 persistenceg2 and trendmax(0,2g2−g1) per metric; no arbitrary
120cap for newmetrics. Primary Δarea=AEtrend−AEpersistence on commonband
candidate area;negative directional benefit,positive loss,zero tie,missingnull.
Other L/mean/P10/P50/P90thickness deltas areseparate diagnostics with ownunits,
not rescue votes. One query,not6independent tests or5frames=5specimens. Full
support/missingness and all individual metrics shown. Small gains tentative
because candidate/reference error uncalibrated.

Cheapesttest local9sourceimages,onefixed extractor pass + split replay at most,
internal110s/external120s per numerical phase,no training/network/remotejobs.
Independent exact code/lock review + synthetic geometry tests before use,
independent mask-derived geometry/arithmetic/source/protection/figures review
after. New Run receipts code/cleanstate/host/PID/runtime/commands/identities.
Global source/protected-byte/algorithm mismatch stopsinterpretation; extraction
failure only limits that frame/metric,not whole recognition route.

Minimum evidence: source-only support/exclusion lock,all9raw overlays/candidates/
paths,visible masks/ordered thickness tables and perframe scalars,commonband
history prediction save/target reference,allmetrics comparator/coverage/visibility,
same-stem figure guides/preview+visualQA/independent report,Obsidian updates.

If candidate masks miss or confuse pores,record extraction bottleneck and a
separate mask/reference repair; do not return to fouranchor repair bydefault.
If full visible geometry changes only with occlusion,keepC2result but restrict
change claims to shared image-space band. Ifreplayloses,retain that result and
use increment/segmentation diagnostics to choose a separate next lever,no
target-conditioned position/threshold or newmodel. Initial state: no newmetrics.

## Executed outcome — 2026-10-17

R001history/R002target succeeded at clean0eba2af in3.767/1.342s. Existing9sources
only; no training/newsource/oldanchorrepair. Five visible-candidate frames
18/19/21/22/23; four early unidentified/null, not auto-detection accuracy or zero.
Step19geometry now returned despite original correspondence failure. Old
half-depth and prelocked result bytes unchanged.

Commonband21/22/23area4054→4565→5057px²; persistenceAE492,trendAE19,gain473px².
One query scored1/1, six heterogeneous scalar outputs6/6,not6independent tests.
Length gain−1.928932px and thicknessP10−.321452px retain losses; mean/P50/P90
gain1.062164/.770330/1.971573px. Area slightdeceleration511→492isdescriptive,
not calibrated slowing/turning validation or true-mask forecast accuracy.

Samecamera/dimensions,commonband fullyunoccluded. ORBfits22/23relative21scale
1.000456/1.001192,rotation−.013798/−.024862deg; translation persists,including
23nativeapproximately(−10.196,+36.470)px. No maskswarped/materialaccuracyclaim.
Fixedimageband drift may influence deltas; minimumviewdiagnostic isnot old
fouranchor requirement. Perframeoutputs remain separate from changeclaims.

Actualsourceoverlays show pore/texture branches,missed fine uppercracks and
fragmentedpaths. Fullsupportchanges/lengthdrops cannot be physical closure.
Pathendpoints notconfirmedtips; new2xEDTthickness notoldhalfdepth/mm. AIvisual
review not independent humansegmentation. Prioritise a separate source-only
candidate/path reliability version before extending simpleforecasts,not
mandatorybackgroundrepair or newarchitecture.

R003/R006previews ledonly todisplayheadroom/range fixes; R004six finalfigure
sets readfromsavedoutputs atbc0e96a. PNG300dpi/embeddedPDFfont/gray/sidecar
checks passed. IndependentR005 recomputes masks andsavedpathmetrics/6scores;
alternativeequalshortestpaths can perturb fullpaththickness slightly,not
commonband scores. Exactoutputreview andcompactreceipts in evidence/.

[Analysis, actual masks and all metrics](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E037-MD01/runs/S03-E037-MD01-R004/analysis/README_analysis.md).
Do not replace E0361/4coverage or anyoldscore with E037newdefinitions.
