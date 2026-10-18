# E044 — metadata-fixed next-stage extension of separated-input forecasts

2026-10-18; bounded exploratory sequential extension, controlled experiment.
Direct user approval: fix new stages/windows before validation; freeze
identification and prediction; retain old half-depth and scores; per-case figures
and Obsidian. Old80%usage stop rule was explicitly revoked by user.

## Selection before new candidate pixels

Use the first3complete metadata-linked stages after the largest E043 development
stage23, in chronological stage order. Within eachstage choose smallest literal
explicitlylinked fixed-camera filename (same recorded rule as previous work).
Cached MD01v1 metadata gives24/25/26 with IMG_0394/0397/0400.JPG. Readonly official
ID/bytes/SHA join; no load/response workbook values, new download or image search.
All3rawfiles already local under E034/raw_images and were previously viewed in
old half-depth investigations, but no E043candidate-area predictions. Therefore
new query/method extension, NOT untouched-image/dataset or new-specimen blind test.
Keep them if unusable; no replacement frame/window from outcome or appearance.

Windows fixed:22,23→24;23,24→25;24,25→26. Initial22/23 masks are byte-preserved
E038R001v1. Every new target is also the next origin only AFTER it is observed:
teacher-updated one-step extension, not autonomous three-step rollout.

## Frozen observations and identification

ROI[3800,900,4800,3500], scored imageband[3900,1700,4600,1950]. Candidatearea A,
occupied horizontalrows L, conditionalrowmass M=A/L exactly as E043. M isnot
normalwidth, EDT or oldhalfdepth; L isnotcracktruelength/recall. Pixelgeometry
only, no material-position/physicalwidth or time/kN claim. Shadows/pores remain.

Newstages use unchanged E037extract code, gray100,contrast20,box101,corridor60,
guidecontact12,componentheight30. Freeze ALL coarseguide and exclusion polygons
from stage23 for24/25/26, no target-assisted guide drawing/recentering, threshold
tuning, newporefilter or fixture repair. Earlier22/23 remain their saved observer-
guided masks, not reprocessed. This is a guide-transfer test with inherited older
observer supports, not a fully automatic or independently calibrated measurement.
Report exclusions/rowcoverage and original+mask overlay for every new target.
No skeleton, path or oldhalfdepth recomputation. No mandatorybackground matching.

## Fixed predictors and scoring

Reuse E043predict unchanged for all methods:
1 persistence A_b;2 area secant max(0,A_b+q*(A_b-A_a));
3 Lhat=L_b;Mhat=clip(M_b+q*(M_b-M_a),0,700);Ahat=Lhat*Mhat,
q=(target-b)/(b-a). Only first two observed preceding stages and requestedstage.
Save all3predictions and history hashes BEFORE decoding/extracting that target.
Scoring never changes predictor/guide. No sweep/newcoefficients/settingselection.

Primary diagnostic: all3per-window candidatearea AE and equal-window MAE,
baselinegains, calculablecoverage outof3 and missingness. No independentunit
confidence intervals from overlapping windows. Zero-historysupport makes M
undefined and separatedprediction null; rawcandidatearea0 is not trueabsence.
Exclude missing-separatedwindows only with denominators explicit and same paired
baseline subset; preserve their standalone baseline errors. If excludedpixels
entercommonband, markthatcase incomparable and retain output withoutscore.
No post-result acceptance threshold or oldscore rewrite.

At constantL and withoutMclipping, method3 mathematicallyequalsareasecant. Such
ties mean no incremental benefit inthatregime, not a failedimplementation nor
new independent evidence of earliercoverage-repairgain. If method3loses, preserve
negativecases and inspect measuredcoverage/conditionalmass, not change rule.

Cap: one3targetlocalCPUrun <=90sCPU/wall; no GPU/training/remote/newrawdata.
Abort on identity/cap failure, no numerical retry without new authorisation.
Relevant synthetic/unit checks plus local arithmetic/hash checks. This remains
exploratory; optional independentagentreview not requested for this small scope.

Figures from exact saved outputs: all3case rawband+candidate and history-to-target
prediction plots, plus aggregate per-caseerrors and L/M trajectories. Everycase,
same axes/units and methodcolours. PNG/PDF plus same-stemhow-to-read guides,
actually inspect renders and embed selectedcomparison in existing Obsidian note.
