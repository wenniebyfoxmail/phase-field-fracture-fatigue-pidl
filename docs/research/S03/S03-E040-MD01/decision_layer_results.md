# Read-only Step19 left-gap explanation — 2026-10-17

ExistingE040 result remains+1021bottom/0left, unchangedmask/halfdepth/scores.
This follow-up explains fixed gates, not another candidate extraction. Only
sameStep19 sourceROI andcached decisionarrays, no newframes/labels/predictions.

## What the source/layers show

Original coarseguide lies right ofpartof the visibleleft crack-like trajectory.
The60px corridor cuts some ofthat trajectory despite itsdark/localcontrast
eligibility. This is a source/algorithm alignment issue, not only purpleexclusion
or globallyhighgraythreshold. Plot shows exact source, independent gray/contrast
passes, guide+60pxboundary andactualsavedmask/unretainedpixelgateeligible areas.
Single-conditioncyan is NOT a crackmask; orange is NOT groundtruthmissedcrack.

In the same fixedleftcrop [4100,2600,4450,3160],16842previouslyexcludedpixels
were released. Sequential accounting, not crackrecall:

|Existing fixed condition|Released pixels rejected|
|---|---:|
|gray>100|749|
|contrast<20 aftergraypass|11069|
|outside60pxcorridor aftergray+contrastpass|3050|
|passesallpixelgates but absentfromsavedmask|1974|

Sum16842; none newly retained, matching E040left0. Counts includebackground/
pores/texture and depend on accountingorder; not causalpercentagesoftruecrack.
Independentfailurecounts retained inR008summary, no single-gate blame byranking.

## Why the1974 were still discarded

R008firstphase didnotcomponentlabel/reselect. Its1974releasedeligiblepixels
are27..59.908px fromguide, nonewithin12 locally. Separatelyrecorded post-hoc
R011labels cachedeligibleROI (no source decode, no newly selectedmask) and checks
existing savedretention component-by-component, including outsidecrop links:
all465component retentions agree with savedmask. Ofthose1974localpixels:

-1731belong tocomponents height>=30 but no contactwithin12pxofoldguide;
-243belong tocomponents failingboth contactand30pxheight;
-0are rejectedbyheightalone orretained.

Largest involvedcomponent has2597eligiblepixels, bbox[4193,2803,71,228],
1682releasedpixelsinthefixedcrop, height228px, no12pxcontact. This is a cached
component description, not an independentcrack label, physicalwidth or newmask.
SharedOpenCV/SciPy semantics disclosed; no independentagent/physicaltruth claim.

## Execution/protection and the one remaining action

R008clean9ce664f7 computes readonlylayers,18protectedfiles; R009preview,
R010finalrender at8e4af2b7, onepreviewround. R011clean8e4af2b7 cachedretention
explanation, additionalprotectedinputhashes. Nooldartifact/code/definitionchange.
Original E040controlledcandidate R001 notrerun; allfile identities checked.

One concrete repair is prepared, NOT evaluated:
[source-only localguide proposal](guide_repair_proposal.json). It changesonly
guide y>=2700 along source-visible trajectory, keepscorridor60/contact12,
gray100/contrast20/exclusions/componentheight30 unchanged. Onecandidate
comparison<=60s, no new source, width/path orforecast/scoring. This exceeds
the completed one-candidate E040support experiment, so newcandidate execution
needs explicitauthorisation; HQcoordination alone isnotproducerpermission.
No further userlabelling or ordinary-tool confirmation needed for this handoff.

[Decisionlayerfigure and full diagnostic report](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E040-MD01/runs/S03-E040-MD01-R010/analysis/README_analysis.md).
