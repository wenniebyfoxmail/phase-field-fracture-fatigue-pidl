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
