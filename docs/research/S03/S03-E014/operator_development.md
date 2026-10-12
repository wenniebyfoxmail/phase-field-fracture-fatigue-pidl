# Observation-operator development and correction — 2026-10-12

Status: development findings/proposed assets, not a qualified FEM input or q
fit. High-load displacement/strain remain unscored. v1-design-freeze is retained;
this is a pre-fit correction and candidate operator specification requiring
renewed independent review. No real-data FEM solve has occurred on Mac.

## Source checks and correction to the earlier inspection

Primary detailed-method supplement downloaded successfully through direct
publisher URL after Jina Reader returned404 (the PDF itself was available):
https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41598-024-63915-x/MediaObjects/41598_2024_63915_MOESM1_ESM.pdf
Local diagnostic copy: `/tmp/e014-source-d6qAKK/detailed.pdf`, verified by
`file` as a3-page PDF and read with `pdftotext -layout`. Section1.4.1 reports
E72GPa and nu0.3; section1.4.3 describes an unloaded global reference image.
Neither establishes the actual exported reference force or exact rigid-motion
compensation algebra. Adopt nu0.3 in the next reviewed execution revision rather
than the earlier assumed0.33. E remains normalized1 for the displacement-driven
diagnostic; this is not an E estimate or calibrated reaction-force model.

CrackPy source inspection found an IMPORTANT correction: connection node values
are zero-based indices corresponding to `facet_id - 1`, not the nodemap's
one-based facet IDs. Node0 is valid; -1 is padding/missing. The earlier
`inspection.md` raw0/out-of-set findings are preserved as historical exploratory
findings but MUST NOT be used for mesh exclusion or readiness. The inspector
and synthetic cases have been corrected to map connection index c to facet c+1
without renumbering after missing facets are removed. Its new snapshot needs
review: an earlier PASS cannot cover changed bytes.

Pinned published version: CrackPy tag1.1.1, commit
`7556651812bc1c0d38159d718a47847524fd1dd0`, source path
`crackpy/fracture_analysis/data_processing.py`. Current main source was also
consulted at `crackpy/input/input_data.py` (main commit
`f5178fd4248adca457238ab55551444c1c7ae5ee`); it must not substitute silently for
the published version. Direct source entrypoints are listed for reviewer checks.

Direct training-only geometry check after c+1 mapping:

| Fit stage | Non-padding supported triangles | Zero xy areas (<1e-12mm2) | Orientation | abs area min/median/max, mm2 |
|---|---:|---:|---|---|
|7|78276|0|all negative|0.200837459 /0.334485463 /0.460348708|
|8|78054|0|all negative|0.200837459 /0.334586789 /0.460348708|

All non-padding triangles now have finite coordinate support. Consistent
negative orientation can be reoriented deterministically; it is not evidence
of inverted physical elements. These counts are exploratory direct checks,
not independent qualified mesh admission. Crack crossing, non-overlap,
components/holes and actual specimen BC still need explicit checks.

## Training-only spatial candidate

All39,891 jointly finite training coordinates/displacement increments were
displayed in the full-view `training_increment.png`. It was visually inspected:
nonblank correctly oriented fields, readable axes/colorbars, no stage9 data.
Display colors saturate at the training99th absolute percentile only; values
were not clipped or smoothed. These are displacements, not damage labels.
Raw output/README/sidecar:
`local_archive/experiments/S03-E014/analysis/development_view_20261012/`.

A training-only opening proxy uses x bins centered at -24,-21,...,24mm, half-
width1.5mm, and paired y bands[1.5,3.5] and[-3.5,-1.5]mm. For each supported
bin compute median(delta_v_upper)-median(delta_v_lower); medians are not
independent specimens or a calibrated noise model. At x=-9,-6,-3,0,3,6,9mm
the proxy is approximately0.004003,0.006964,0.008699,0.007272,0.007384,
0.004990,0.000914mm. Outer bins have nonzero asymmetric background. This
supports a localized opening hypothesis, NOT unique crack tips or true length.
Missing center facets are not used as crack labels.

Candidate basis for the next review (prior specification, NOT truth): patch
x[-18,18],y[-9,9]mm; artificial rectangular outer contour; geometry-compatible
initial segment x[-9,6],y0; diffuse width1.5mm as a resolution-linked modeling
choice, not recovered length scale; localized right-tip amplitude basis centered
at x6,y0 with3mm radius scale. These numbers came from training inspection only.
Do not call the segment an independently verified crack. Mesh/BC construction
and interpolation support must be frozen and reviewed before q evaluation.
Boundary increments come only from stage8-stage7; predicted high boundary is
their load-gap-scaled extrapolation. No high-load boundary may repair the fit.

Training-only boundary support diagnostic for a regular0.9mm grid on that
rectangle:861 nodes,120 outer-contour nodes,117 distinct nearest source facets;
maximum/median distance to jointly finite training facets0.765349/0.315014mm.
There are646 original jointly finite observations in the proposed interior
`abs(x)<16.2,abs(y)<7.2`mm. This establishes available boundary samples, not a
qualified interpolation or true grip condition. A boundary-only2D rigid-mode
matrix has rank3; its least-squares rigid-only residual RMS is0.00223039mm.
This confirms boundary increments are not solely a rigid motion; the residual
contains deformation AND measurement/model error and is not a noise estimate.
No FEM matrix or q response was evaluated in this diagnostic.

## Gauge and q sensitivity: what is established versus pending

Reading supplied columns directly without reapplying header compensation is
the conservative consumer convention; exact exporter compensation remains
unverified. The published1.1.1 `InputData.read_data_file` explicitly assigns
disp_x/y/z from their nodemap columns; it does not reapply alignment metadata
there. Thus direct consumption is source-supported, whereas claiming an exact
inverse of the ARAMIS exporter is not. A fixed 2D rigid-mode quotient is a possible repair, not a verified
exporter inverse. Translation and infinitesimal in-plane rotation produce zero
small-strain elastic energy. A fixed projection onto the orthogonal complement
of those modes, defined from training geometry and used identically for both
observations and candidates, can remove their nuisance contribution without
learning target-dependent alignment. It cannot remove unknown affine strain,
out-of-plane coupling, plasticity or changes of coordinate frame. No extra
optimized rigid/gain parameters are authorized. Source/convention or a reviewed
gauge-invariance test is needed before claiming an admitted observation map.

For fixed BC, the scalar q response derivative obeys
`Kff*u'_f = -(K'ff*u_f + K'fb*u_b)`.
Uniform E cancels; a pure rigid imposed field also makes q invisible. Localization
of b and visibly non-rigid training deformation make sensitivity POSSIBLE, not
proved. Actual sensitivity/profile/rank relative to nuisance modes and noise
has NOT been numerically evaluated: no admitted basis/BC or producer solve yet.
Report this as pending, not identifiable. A nonzero algebraic derivative alone
would still not prove practical recovery from this DIC signal.

## Independent review and producer preflight

Four original v1 files at commit9629f31 were uploaded to the existing independent
ChatGPT review conversation at
https://chatgpt.com/c/6ac7974d-c838-8325-9322-fbc639d581cb . Review asks separately
for structural-inspector Code Ready and physical design readiness. Corrected
index semantics require a fresh code review after the v1 response.

Round1 final verdict is now available: structural `REVISE_CODE`, physics
`NOT_READY`. See `review_round1.md`. Identity/member ambiguity and timestamp
truncation were independently reproduced. Fixed rigid-quotient scoring was
accepted only as a prospective narrowed observable. Corrected inspector now
has13 synthetic cases; no actual inspector rerun or FEM/q solve before review.

Read-only producer preflight: `ssh -o BatchMode=yes -o ConnectTimeout=12
gpu-taobo 'hostname; df -h / /mnt/data2 /mnt/data3; nvidia-smi ...'` exited255,
connection to172.16.100.2:22 timed out. `route -n get172.16.100.2` used en0/default
gateway, not a Taobo tunnel. SSH config explicitly requires existing Tunnelblick
Taobo VPN. No remote directory, job or process was created; no machine switch,
VPN configuration change, credential handling or Mac real-data solve occurred.
Connectivity must be restored before the conditional Taobo launch. This is an
execution blocker separate from the scientific admission work.
