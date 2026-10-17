# E040 — bottom candidate recovered, left omission not repaired

2026-10-17. Source-only exploration, one existingStep19. Oldv1/halfdepth/scores
unchanged. Single extraction comparisonR001 clean4df7ac16, wall0.516s/CPU0.502s,
12protected files unchanged. Baseline mask/excluded/safe exactly reproduce E038.
No skeleton/path/thickness/forecast computed and no other source frame opened.

|Observable|Before|After|
|---|---:|---:|
|Excluded area px2|1084835|1016926|
|Candidate mask area px2|21803|22824|
|Released support px2|—|67909|
|Added candidate px2|—|1021|
|Old candidate lost px2|—|0|

All1021added pixels lie in previouslyexcluded support, native bbox
[4202,3300,4234,3361) (x0,y0,x1,y1). Fixed lowercrop contains1021 additions,
left/gluecrop contains0. Additions outside releasedsupport fromconnectivity=0.
Visible-source comparison places orange additions along a lower visible dark
crack-like segment, not hardware; this is qualitative AI review, not independent
pixel truth or measured physical width.67909released pixels are NOT new crack.

Local mechanism finding: the old bottom strip did suppress this candidate;
shrinking the left exclusion alone did NOT recover the left visible omission.
Thus purple support explains part, not all, of missingcrack. Fixed guide ends
3300,60pxcorridor; newmask ends3360, remaining lower source still unrecognised.
No width/length/physicalgrowth claim fromthe61row added support extent.
Pore/texture false positives unchanged; E039cleanup not combined here.

Initial source-only R000 preview exposed potentialgluefringe, so added10px
conservative leftkeep buffer BEFORE any crack extraction; effective R004
manifest583a101cb9794c900bf44f442009e4e0328519c26bf5a3a9950316bd56cee022.
One candidate segmentation only; no mask/error-tuned boundary retries. Right
excluded support unchanged. Real hidden regions remainunknown, not connected.

Figures read onlysavedR001. R002 firstpreview; R005compactpreview; R007final
preview fixes longnativecroplabels. R003earlier render retained; R006final at
renderer revision recordedinreceipt. No more than3preview rounds. FullROI plus
both preregisteredcrops, including0additionleft, shown. Pixel/identity subset
checks re-read savedarrays, not new extraction; no independent agent/review claim.

Next proposed: read-only explanation of the left missed visible segment against
fixed grayscale,localcontrast andcoarse-guide corridor decision layers. Identify
which existing condition excludes it before changing one lever. Do not continue
shrinking exclusions indiscriminately, fillnewlyvisible support ascrack, change
globalthresholds or waitforperfectmasks before simpleprediction planning.

[Full source/support/mask comparison](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E040-MD01/runs/S03-E040-MD01-R006/analysis/README_analysis.md).
