# E045 — one frozen image-geometric guide-transfer candidate

2026-10-18; lightweight C2 controlled-experiment exploration, already-viewed
MD01 stages24/25/26. User approves first fixing guide-transfer rule, comparing
all3against E044 frozen version, focusing26omission/shadow risk, no prediction-
error position/parameter selection, oldhalfdepth/scores and Obsidian retained.

Question: can image-only continuous dark-region geometry restore the missed
upper26trace without also enlarging nearby background/shadow candidates?
Reference=computed E044frozenmask, NOT truth. No forecasts/scoring or newdata.

## Single candidate rule (no target-specific adjustments)

Same fullROI[3800,900,4800,3500] and scoringband[3900,1700,4600,1950]. Same E037
extractor(gray100,localcontrast20,box101,corridor60,guidecontact12,height30), same
stage23exclusionpolygons. Change onlyguide position using current image pixels.

1. Compute original grayscale/background gates across fullROI, excluding
   unchangedpolygons. No new threshold. Let D be EDT inside this eligible mask;
   it rewards centres of contiguous darkregions, not independent crack evidence.
2. Transfer onlyrows1640..2010 inclusive = originalband plus60pxmargin. At each
   row constrain x to±240px of interpolatedoriginal23guide (=4×old60corridor).
3. Findone path x_y maximising sum(min(D_yx,60))−sum|x_y−x_previous|. Both terms
   in imagepixels; no fittedweight. Maxrowstep=ceil(2×maxabs dx/dy of original23
   polyline)=3px. Fixed factors2/4 are geometric exploration choices, not tuned.
   Tieorder0,−1,+1,−2,+2,−3,+3; finalsmallestx. No targetendpoint or manual trace.
   No forced positive-support minimum; report eligible-path fraction and any
   gapbridging. If entire searchhaszero reward, return originalguidewithflag.
4. Replace original guidepoints inside1640..2010 by pathpoint at everyrow;
   retain outsidepoints and use normalpolylinejoins. Originalextract decides all
   candidatepixels. Guide bridging never fills noneligible imagepixels.
5. Applysame rule once per24/25/26. No sweep, adaptation after result or combining
   E039porefilter. Reconstruct E044baseline once percase for exactarray check.

This is current-image-assisted identification, not a future-prediction input.
It is not background/material registration. Shadows or pores may also form dark
ridges, so neither EDT nor continuouspath provescrackidentity.

## Fixed diagnostics before new candidate results

Allcases: old/new area, occupiedrows, conditionalrowmass; added/removedpixels,
guide shift, path eligibility. Candidate area outside old60corridor describes
recoveredsearchsupport, not truecrackrecall. Alloriginal anddelta overlays shown.

Native review rectangles, based on already-exposed source/E044diagnosis, not
newcandidate orprediction errors:
- Everycase right-backgroundcontrol:[4380,1700,4510,1950].
- Stage26upperomissionreview:[4020,1700,4210,1770].
- Stage26right-background/shadow-riskreview:[4250,1700,4335,1770].
They contain mixedpixels and have no humanpixeltruth. Counts are notTP/FP,
precision/recall or reviewedshadowaccuracy. Source panels remain authoritative
for qualitative interpretation; report any lostvisibletrace and uncertainarea.

No primary accuracy threshold without truth. Useful exploratory progress means
source-visible omittedtrajectory recovered and background-risk tradeoff made
explicit, not automaticwholemethodvalidation or automaticreplacement ofv1.
No newhalfdepth, skeleton, physicalwidth, forecast, oldscore rewriting, newimage,
GPU ortraining. AlloldE044artifacts andolderprotectedinputs hashed unchanged.

One numericcomparison <=90sCPU/wall, no retry/sweep of candidate; local synthetic
DPchecks, baselinearray reconstruction and post-runhash/arithmeticchecks.
No independentagentreview claimed. Savefreshnumeric/R002render receipts.

Figures: all3 source/old/new/delta panels plusfixed26omission andshadowrisk
crops withguides, sameextent. No bestcase-onlydisplay; eachfigure has source,
same-stemguide and short中文 See/Therefore/Doesnotshow interpretation inreport,
Obsidian andchat. Nativeimageunits only. Newcandidatekept separate fromoldv1.
