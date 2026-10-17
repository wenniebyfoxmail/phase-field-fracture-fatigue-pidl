# E038 — fixed five-frame image-geometry sensitivity

2026-10-17; Storyline S03; protocol `geometry-oat-stability-v1`; base51d199a.
User authorises existing5images only, original/mask/skeleton/mainpath/alongpath
thickness visualization and Obsidian update. No forecast-error parameter choice.

## Question, unit and scope

C2 controlled-experiment diagnostic: how sensitive is E037 visible image geometry
to small predeclared threshold/coarse-guide perturbations? Unit=one frame under
one setting;5frames ofone trajectory,not5specimens or45independent trials. No
prediction origin/horizon/target inthis experiment; no new forecast or scoring.
Existing E037 stages18/19/21/22/23 only, original JPGs375/379/385/388/391.
Reuse E037 ROI[3800,900,4800,3500], commonimageband[3900,1700,4600,1950],
source-only guides and exclusion polygons. No newimages,labels,thresholdfit,
correspondence/registration or oldfouranchorrepair. Guide/exclusion remain
AI/observer-defined,not truth. Hiddenareas notbridged; fullsupport visibleonly.

## Fixed comparator and interventions

Comparator=immutable E037v1saved mask/path/geometry perframe. Reconstruct default
once only to verify exact baseline before interpreting perturbations; stop on
baseline mismatch. E037v1code/oldhalfdepth andallprelockedoldresults protected.
Newrunner wraps unchanged v1measurement/skeleton/mainpath semantics,with separate
parameterised extraction. Eight one-at-a-time alternatives plus baseline:

| ID | gray upper | minimum local contrast | guide dx,dy nativepx |
|---|---:|---:|---|
| v1 |100|20|0,0|
| gray_minus5 |95|20|0,0|
| gray_plus5 |105|20|0,0|
| contrast_minus5 |100|15|0,0|
| contrast_plus5 |100|25|0,0|
| guide_x_minus5 |100|20|-5,0|
| guide_x_plus5 |100|20|5,0|
| guide_y_minus5 |100|20|0,-5|
| guide_y_plus5 |100|20|0,5|

5graylevels isabout2% of8bit range;5px is smallrelative60pxcorridor andbelow
12pxguidecontact radius. These are finite local stresses,not calibrated noise,
optimisation candidates,fullfactorial coverage orstatistical confidence bounds.
Keep101pxbackground/60corridor/12contact/30rowextent/exclusions/boundarywithholding
fixed. No selection/replacement ofv1 bymaskagreement or oldpredictionerror.
Threshold/guide settings fixed before any new source processing. Allarms shown.

## Outputs, primary descriptive estimand and limitations

Primary=perframe maximum absolute relative area change vs v1 across8alternatives,
reported separately forfullvisibleROI andfixedcommonband. No arbitraryPASS/FAIL
threshold: currentreference error/physicallabel uncertainty uncalibrated, and
these stresses do not have a samplingdistribution. Missingmetric remainsnull;
also reportavailablearms/9. Different unit metrics arediagnostics,notvote.

Diagnostics: signedarea/length relativechange,maskIoUwithv1(notgroundtruthIoU),
fragmentcount, own-mainpath thickness mean/P10/P50/P90 changes andmissingness;
symmetricnearest-path distances(mean/P90px) to distinguish pathbranch changes
from stablearea. These are image-geometry disagreements,notmaterialerror.

Alongline: freeze v1orderedmainpath coordinates in each frame. For eacharm,
sample2xEDT ofitsmask atthose coordinates only wherearmmaskcontains thepoint
and originalsafe maskallowsit. Missingretained, coverage printed. Plot baseline
andmin/max across available settings, not aCI; showpointwisesettingcount so
missingthinparts do not masquerade asstable. Ownpathdistributions savedseparately;
no attempt to match arc-length or physical materialpoints across stages/arms.
10px displaypadding betweenfragments isnot length orhiddenconnection.
New2xEDT thickness remainsmaskproxy,notoldhalfdepth,perpendicularaperture ormm.

Minimumdecisionvisuals: perframe 4imagepanels(rawsource/maskoverlay/all-skeleton/
selectedmainpaths), plusalongline thickness/settingcoverage beneath; all5frames,
sameROI/orientation/displayrules. Additionalallarms scalarheatmapsandmask-setting
support-count maps expose patternwithoutcherry-picking. No averagingawayframes,
significancetests,score-onlyplots or probabilistic maskconfidence interpretation.

## Execution, protection and next lever

R000prepare hashesselectedsourceidentities andoldpayloads,doesnotdecodeimages.
Independent code/manifest review andsynthetictests before R001. R001onebounded
45setting-frame pass,internal180s/external200s; all5defaultreconstructions must
matchsavedv1 exactly. No training/network/remotejob. Failonidentity/protection/
baseline mismatch orbudget; retainpartialreceipt,nottuneandretrytoimproveoutcome.
Eachrunreceipt bindscommit/cleanstate/host/PID/runtime/start/end/command/paths.
Independentread-onlyoutput review afterrun; sharedv1functions areexplicitlynot
independentphysicaltruth. Separate preview/finalrender readssavedoutputs only.

Interpretation: ifarea consistentbutlength unstable,advanceboundedareaanalysis
while fixing path/fragment representation separately; not stopallrecognition.
Ifthreshold dominant,source-only segmentation/contrast lever next; ifguide
dominant,coarse-guidance dependence isthenextlever. Ifbothsmall,proposefixed
small-window baseline replication separately,notnewmodel. No automaticnewtarget
access orparameterselection. Preserve E037v1masks/oldscores andrecordthisasnew
sensitivityevidence. UpdateexistingObsidian tasknote/oneRoadmapentry withfew
keyfigures,traceablefullreportand identificationcodepath.

## Outcome — 2026-10-17

R001 executedonce clean8907da3; wall28.612s/CPU28.731s,45/45full/common outputs,
5/5default arrays/paths/metrics exactlyreproduceE037v1,all75protectedfiles
unchanged. No forecasts calculated oroldscoreparsed; code/manifest remained
unchanged whileonlyrendererdisplayalignment wascommitted separately.

PrimaryfullROI maxabsarea changes18/19/21/22/23=29.764/46.851/16.343/20.868/
12.448%; commonband70.203/156.454/19.635/11.172/8.602%. All5fullarea extremes
arecontrastperturbations. Across5fullROI area maxgray2.446%,guide6.958%,
contrast46.851%; commonguide remains43.653% (18) and38.726% (19),notirrelevant.
Fullpath lengthmaxchanges21.112/49.969/8.127/24.143/11.482%; originalsafev1
pathminretention71.644/88.889/89.218/92.457/96.206%. Ownpathmedianthickness
maxabsdelta2.083px; fixedpath commonvalidpointabsdifferenceP90max1.985px,
conditionalonremainingcoverage. No blanketstability/accuracy orphysicalclaim.

R004independently rebuiltall45masks/exclusions/safe/skeleton andsavedpath/EDT/
coverage/summary outputs; onlynearest-distancefloatingdifference1.78e-15.
Alternativeequalshortestpaths40ties havezero lengthdifference,ownmeanthickness
maxdifference.001267px; sharedskeleton/EDTlibraries andAIreference limits remain.
No independentmasktruth; defaultandoldhalfdepth/scores preserved.

R002firstpreview failedonly atfinalreceipt missingosimport,figuresretained;
renderer-only fix andtitle/withholdingclarification passedR005preview. R003
final8figuregroups at5bb5eb3: actualimage/layer/curve review,16PNGstrict300dpi,
8embeddedfontPDFs,24files/16sidecarnotes checked. No numericalretry.

Result=completedbounded C2sensitivitydiagnostic,notaccuracyqualification.
Researchdisposition=repairlocalcontrast/fragmentrepresentation whilekeeping
workablev1andseparatesimpleforecast route. NextPROPOSEDsource-only review of
contrast-added/removedpixels todefineanexplicitrepair,notselectthresholdby
predictiongain orreverttofouranchorrepair. No newwindow/target/training access.

[Fullresults, all5processpages andcodeentry](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E038-MD01/runs/S03-E038-MD01-R003/analysis/README_analysis.md).
Compactexactmetrics/receipts/independentreview in evidence/.

## Source-only classification material follow-up — 2026-10-17

[Two-frame four-region material protocol](source_review_materials_20261017.md)
uses only existingStep18/19savedcontrastdifferences for neutral source cards.
Preparation only; user first-round classification pending, not independent
validation completed. No extraction/path/thickness/forecast rerun, threshold
selection, v1change orsharedObsidian/Roadmapedit. No new agent ornetwork action.
