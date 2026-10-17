# E037 figure QA, 2026-10-17

R003 six preview figures read against original content and tables. Issues:
F03 shared upper bound clipped larger later-stage thickness peaks; F04 annotation
intersected length line. Renderer-only bc0e96a explicitly sets global F03 maximum
and F04 headroom. R006 F03/F04 read again: no clipped peaks/overlap. No remeasurement.
R004 final render commit bc0e96a, layout_audit all six empty arrays.

Final twelve colour/gray PNGs: check_figure.py --strict returned0; all300dpi
(metadata299.9994). Six PDFs checked with pdffonts: embedded/subset/Unicode
CID TrueType DejaVuSans yes/yes/yes. Sidecar validator returned pass:
18figure files,12unique same-stem guides,0errors. Final F04 gray actually viewed;
circle/square/triangle and solid/dashed styles preserve mapping without colour.

All9frames data profile:5candidate/4unidentified,44% missing scalar outputs,
no fill or deletion. Scalar CSV6rows are heterogeneous metrics of1query;
generic profiler cross-unit correlations/log/boxplot recommendations rejected.
Exact points and units remain separate; noCI, pooledMAE or six-test voting.

Visual scientific limitations retained: observer guide not measured line;
cyan includes some texture/pore branches and misses fine upper cracks;
occluded regions shown and not bridged. Full visible supports differ across
frames; length drops cannot be called physical closure. F06 preserves all4
unidentified original crops, not automatic negative labels. Final source-mask
visual and numerical independent review is recorded separately inR005.

Independent reviewer actually read final F01/F03/F04/F05/F06 and F04gray:
no visual blockers; retained missingfinecracks/porebranches/occlusion limits.
F03 10px display-only fragment padding now explicit in analysisREADME;
not part of reported arc length. Obsidian existing note reopened and final
result text/two embedded images visibly verified through nativeUI.
