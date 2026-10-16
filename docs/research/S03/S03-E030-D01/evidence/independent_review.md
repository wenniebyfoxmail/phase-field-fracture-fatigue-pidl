# E030 independent review

2026-10-16; read-only `/root/conditional_interface_review`, required by experiment
workflow. No edits, external communication, new target or position search.

## Pre-execution admission

Numerics reviewed fb04eb80d6211ec44cdfd9b1caffb26348002757, protocol
T1-fixed-background-sampling-v1 and fixed_positions.json from preceding
8218e32bf59504529d7e968fb29ebe43d14361c3. Eight synthetic tests independently
pass. Numerics/lock/protocol and E028 reused core unchanged through
a6c8f2945d1f412616ceae7f2f823574dd84f758; admission inherited explicitly before
R001 execution. Three fixed-background shifts add directly to original-H,
not oldFIT. Exactly3images×3arms=9profiles; no new position fitting/search.
Snapshot closed before geometry/width/image access; original half-depth/QC,
finite baseline reproduction, nulls, coverage and clip decomposition correct.
E025 six files protected before/after hashes. Reviewer did not open real
JPEGs/widths/target outputs or run producer before admission.

Renderer independently pre-reviewed a6c8f29: saved-output-only, no JPEGs or
new numerical computation. Each arm uses its own reference; original n/t strip
boundaries±35.125/±8.125, edge+shift_n and t=shift_t mapping, ±2 band correct.
Explicit arm legend and NA query coverage confirmed. Nonblocking future note:
F03 could show unavailable comparison text if a new profile fails; current
9/9valid output does not encounter this condition.

## Independent numerical evidence

After R001 reviewer read ONLY three authorised CRC-verified existing JPEGs,
E018 geometry/H, saved E030 positions and baseline/source/output records.
Hand-implemented inverse-H, nearest-even1/32float32 bilinear, five-line median,
shoulder medians and half-depth calculation without E030/E028 new computation
functions or original measure as the reference core. All9profile/deficit/
background arrays, widths/left/right/peak/depth/noise, all3arm query values
and complete stage/clip/prediction/reference-change decomposition reproduce
with maximum numerical difference0.

Fixed widths16.32419349214178/16.19684096456086/16.762657830124773px;
signedsecant error-.693169393144835. Versus oldFIT-.886626089269008,
deltaerror+.193456696124173, including prediction+.168456336766994 and
reference-.025000359357179; clip0. Down/up trend persists. Fixed secant
absolute error remains greater than its local persistence .565816865563914.
Not a new forecast validation, physical reference or global-method comparison.

Position snapshot chronology agrees with reviewed save-before-width code;
not OS-level blinded access certification. Source/input hashes and old E025
six protected files before=after=current verified. Definition/oldscore unchanged.

## Figures

Owner opened all3colour andF03gray. Mechanical audit all3empty,6PNG strict
300dpi and9formats/6same-stem notes pass. Documentation-only heading patch
adds literal 'data provenance' to template/6notes, no numerical/figure rerun.
Independent reviewer actually opened F01–F03colour andF03gray: no critical
overlap/cropping/scale problem. All3arm own-reference semantics, original n/t
strip mapping and contribution values agree with numeric evidence. SixPNG
300dpi,3PDF,6same-stem notes and receipt/README/source bindings confirmed.
Heading-only postrender patch does not change pixels/numerics and does not
require rerender; actual R001/R002 remain bounda6c8f29. No closure blocker.

## Bounded conclusion

Fixed position slightly reduces the local mismatch without removing it;
secant still trails persistence here. Prediction and reference both move.
Retain the partial component gain, not a physical/localisation-accuracy,
independent-forecast or revised-oldscore claim. Independent review complete.
