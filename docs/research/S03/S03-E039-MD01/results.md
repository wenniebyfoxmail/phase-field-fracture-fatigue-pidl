# E039 — useful conservative cleanup, not solved pore recognition

The frozen short/broad terminal-side-branch filter was applied once to45 saved
E038 masks. Default-frame deletions18/19/21/22/23=3625/2336/2670/2887/2440px²,
12.183/10.714/7.733/7.349/6.025% ofv1 area. All213 input protections verified at
execution/review; v1, old half-depth and all old scores retained. No forecasts
parsed, no threshold tuning, no newly acquired images, no training.

All original full/common path pixels and their2xEDT thickness preserved exactly
in45cases BY CONSTRUCTION. This includes any original path false positives.
Reskeletonised new paths are distinct outputs, not guaranteed identical width
statistics. Mask2xEDT is not half-depth/perpendicular aperture/mm.

|Stage|Full area sensitivity before→after|Common area sensitivity before→after|
|---|---:|---:|
|18|29.764→28.199%|70.203→57.383%|
|19|46.851→44.866%|156.454→153.372%|
|21|16.343→14.505%|19.635→18.141%|
|22|20.868→18.795%|11.172→9.746%|
|23|12.448→11.880%|8.602→6.858%|

Sensitivity=max absolute relative area change across8existing OAT settings vs
the respective method's own default. Different denominator before/after; not
accuracy, physical uncertainty or aCI. All45 retained,5correlated frames ofone
trajectory. Small sensitivity gains are component progress, not blanket failure
or validated pore precision. Stage19 residual sensitivity remains substantial.

Source review shows pore-/texture-like lateral patches removed, but largest
deletion in22/23 lies near real crack edges and is ambiguous. One automatic
largest-component crop/frame is not exhaustive ground truth. AI saw overlays;
not a blind annotator. Loops, isolated blobs and trunk-associated pores remain;
deletion-only rule cannot recover omitted fine cracks. Do not promote as v1
replacement or equate removed area with false-positive reduction.

Numerics independently reconstruct exactly; heap equal-path ties change only
mean thickness by<=0.001378px, disclosed. R001 process exited nonzero at final
receipt exclusive-create collision; original running receipt retained, separate
completion_reconciliation.json verifies complete numeric retrieval without
re-execution. Start-to-summary file timestamp20.679s is NOT final wall/CPU time.
Future receipt naming fixed separately; original numeric code2fb6ba75 retained.

Next proposed: preserve v1 and this named candidate in parallel. Define a new,
explicit development replay of existing21/22/23 area persistence-versus-trend
for both without choosing a method by its error; leave old scores untouched.
Mark trunk pore/edge ambiguity separately rather than deleting harder or waiting
for perfect masks. If pore cleanup advances later, local elongation/directional
continuity plus source evidence are more informative than blob size alone.
No new window/target access or prediction calculation in E039.

Final source comparison pages and exact data:
[report](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E039-MD01/runs/S03-E039-MD01-R009/analysis/README_analysis.md).
