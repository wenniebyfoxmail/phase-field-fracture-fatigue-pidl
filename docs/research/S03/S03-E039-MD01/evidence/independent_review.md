# E039 independent review

2026-10-17. Review restricted to45 saved E038 masks from existing frames
18/19/21/22/23 and the declared one-pass postprocessor. No new image acquisition,
forecasts, tuning, producer edits or extra positions. This report/script/results
are confined to the authorised new E039-R004 review directory.

## Result and process status are separate

The45 numerical cases, all_metrics.json and summary.json are complete and
independently reproducible. No numerical deletion/aggregation blocker found.
The original R001 run_receipt.json remains `execution=running`; it is NOT a
successful final process receipt. Producer reported an exclusive-create
FileExistsError on writing the final receipt over the initial same-name file.
That is consistent with the code and preserved initial receipt, but should be
recorded by a separate reconciliation, not by overwriting the original or
rerunning numerical work. Numerical completeness does not prove process exit0,
final metadata persistence or a successful end-to-end producer run.

Reviewed execution commit `2fb6ba7538000a2ebb24d9b771289bf759a16542`, clean initial
receipt. Effective manifest is R005/input_manifest.json SHA256
`29c3340ba7db7e3d3ec687deeb8bbd0e9b5c8bf2231b51e11b60170bede9b6b9`.
All213 protected source/code/input hashes match before and after independent
review; all R001 numerical payload hashes remain unchanged during review.
Superseded R000 hash-only preparation is not used as the execution input.

## Independent numerical work

`independent_check.py` does not import producer functions. It independently
constructs8-neighbour dictionary graphs with the declared diagonal suppression,
traces endpoint-to-junction branches, recalculates branch geodesic lengths,
median original2xEDT, length/thickness ratio, path intersection, and all eligibility
decisions. Every branch ledger entry in45 cases matches exactly, including
endpoint/junction coordinates and ordered skeleton points.

The original full/common path union is reconstructed from frozen E038 path
JSON. Protected tubes are independently rasterised by integer squared-distance
disks (not producer cv2.circle); all tube pixels agree. Eligible skeleton,
nearest-owner deletions, retained/removed masks and protected points all agree
pixel-for-pixel. No added mask pixels, no lost protected points; original full
AND common path2xEDT preserved exactly in every case.

Nearest-owner reconstruction shares the declared SciPy EDT minimizer/tie
convention with the producer. An additional KDTree calculation independently
checks nearest distances, owner distance optimality and all unambiguous owner
coordinates. Equal-distance assignment remains an implementation convention,
not a true pore boundary or probabilistic pixel ownership.

New full/common skeletons, every saved path adjacency/diagonal constraint,
arc lengths, boundary endpoint flags, local EDT samples and saved-path metric
aggregations all match exactly. Removed counts/fractions, eligible/terminal
counts, protected-point counts and all5 primary/secondary summaries match
exactly. Independent heap-Dijkstra path selection yields some equal-length
coordinate ties; maximum own-path mean-thickness difference is
0.0013777662105027844px, with all lengths/counts/P10/P50/P90 unchanged. All metrics
computed on actual saved paths match exactly. Details/tie records are retained
in independent_results.json. Independent verification runtime20.12s.

Shared SciPy EDT and skimage skeletonize are explicit reproducibility limits.
This is independent code/arithmetic reconstruction, not separate human labels,
physical aperture validation or fully library-independent skeleton/EDT truth.
The archived E037 reviewer helper is reused, with its SHA recorded. No original
RGB decoding was necessary for numeric reconstruction; visual source evidence
is reviewed separately below. No old forecast/score contents were parsed.

## Exact bounded outcomes

All counts below concern default-v1 masks, not numbers of confirmed pores.

|Stage|Removed px / original area|Eligible terminal branches|Full max relative area change before→after|Common max relative area change before→after|
|---|---:|---:|---:|---:|
|18|3625 / 29754 (12.183%)|173|29.764%→28.199%|70.203%→57.383%|
|19|2336 / 21803 (10.714%)|97|46.851%→44.866%|156.454%→153.372%|
|21|2670 / 34528 (7.733%)|123|16.343%→14.505%|19.635%→18.141%|
|22|2887 / 39285 (7.349%)|125|20.868%→18.795%|11.172%→9.746%|
|23|2440 / 40497 (6.025%)|103|12.448%→11.880%|8.602%→6.858%|

All45 cases retained. The descriptive sensitivity maxima decrease in these
five cases, but substantial residual sensitivity remains (notably stage19
common153.37%). This does not establish improved segmentation accuracy. Before
and after maxima use their respective default-mask area denominators, not a
common fixed denominator or physical uncertainty bound. Protected original-path
EDT invariance is by construction, not an independently validated width result.
Newly skeletonised paths may differ even when original path pixels/EDT persist.

## Preview source/deletion visual review

Actually viewed all5 R002 F01_step{18,19,21,22,23}_pore_candidate_cleanup_preview
PNGs and F02_removal_and_residual_sensitivity_preview.png. These display original,
before/retained/deleted overlays and the mechanically chosen largest removed
component with fixed80px padding, not a hand-picked most favourable example.

Qualitative AI review of the displayed largest-component crops (not pixel truth):

|Stage|Visual description|Interpretation limit|
|---|---|---|
|18|Broad side patch beside an irregular thin crack; pore-/texture-like candidate, with other edge-adjacent deletions|Ambiguous attachment to actual crack; many trunk-associated broad patches and pores remain protected|
|19|Short lateral bulb left of the visible crack; pore-like/side-wing candidate|Could include genuine local crack-edge opening; not confirmed pore|
|21|Compact side lobe beside the crack|Pore-like or rough-edge candidate, still ambiguous|
|22|Largest deletion sits on the dark visible opening/edge and short flank wings|Edge-adjacent ambiguous; cannot call all removed pixels pores or false positives|
|23|Thin flank strips and lateral wing tightly adjacent to open crack|Edge-adjacent ambiguous; possible real crack-edge loss|

These are visual descriptions of one automatic crop per frame, not exhaustive
labels for thousands of pixels. AI review saw the algorithm overlays; it is
not blinded annotation, precision/recall or an independent reference standard.
No pore-versus-crack accuracy percentage is justified. Loops, isolated compact
components and pores embedded on protected representative trunks intentionally
remain, so the method does not solve the whole pore problem. Protecting the
original path also preserves original false positives along it. Original fine
crack omissions are not repaired by a deletion-only rule.

The preview F02 stage23 after=6.86 annotation lies too close to0-axis/bottom of
the common panel; requested a display-only upward offset or extra y margin.
No numeric correction requested. Final rendering/reconciliation review pending.
