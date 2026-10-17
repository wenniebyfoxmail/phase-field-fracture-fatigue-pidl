# E039 — conservative pore-like terminal-spur audit

2026-10-17. S03 controlled image-geometry diagnostic, not a new forecast.
User observes pores among candidate crack pixels and authorises the next
source/geometry-only repair. Reuse only E038's five existing stages18/19/21/22/23.
No new source acquisition, training, material correspondence or four-anchor repair.

## Frozen comparison and single intervention

Comparator is saved E038 v1, never replaced. Apply the same one-pass rule to
all45 saved setting-frame masks, no re-extraction or setting selection. Only
original RGBs of these5frames may be decoded for inspection/plots. New candidate
name `protected-terminal-spur-v1`; not v1.1 or a pore ground-truth classifier.

Use v1 graph adjacency (orthogonal/diagonal suppression). Trace degree1 endpoints
through degree2 nodes to a junction of degree>=3. Exclude junction from branch.
Eligible iff branch geodesic length<=60 nativepx AND length/median original
2xEDT thickness<=3 AND no original full/common representative-path point on it.
60 is the existing guide-corridor scale; ratio3 is an explicit conservative
short/broad shape hypothesis, not calibrated pore accuracy. Freeze once, no search.
Only terminal branches, one pass; retain loops, isolated components, long/slender
branches and all branches touching protected paths. Protect the union of original
full/common path-point inscribed disks (integer ceil radius), intersected with
input mask. Delete pixels assigned by nearest original-skeleton ownership to an
eligible branch, only outside protected disks. No added pixels or gap bridging.

All original protected points and 2xEDT readings must remain exactly unchanged;
assert this. Newly skeletonised paths are separately recomputed and may change.
Original-path preservation is by construction, not evidence of true crack width.
Common band remains fixed [3900,1700,4600,1950]; ROI [3800,900,4800,3500].
Image mask thickness is not old half-depth width, physical aperture or mm.

## Outputs and decision

Primary descriptive comparison: per-frame default-mask removed pixel count and
fraction; retained/removed source overlays reveal whether removal looks pore-like,
linear or ambiguous. No accuracy/precision labels without independent human truth.
Report every frame, complete branch ledger and all45 settings, no best-case crop.
For each default frame, one zoom is chosen mechanically: largest connected
removed-pixel component (ties label order); equal padding80px, no error selection.
Show raw/before/after/deleted comparison at same support. All removed regions are
reviewable candidates, not definitively pores; short broad real branches may be
removed. Pores on protected trunks, loops and isolated compact components remain.

Secondary: per-frame full/common max absolute relative area changes over existing
8OAT settings before/after this same rule. No pooled statistics or significance;
5frames one trajectory,45 correlated cases. No forecast files parsed or rescored.
Record residual sensitivity even if it is not reduced. A useful local clean-up
does not imply the entire pore problem solved; retain v1 regardless of outcome.

## Execution and review

R000 hashes all135 E038 input artifacts plus inherited protections, code/protocol.
Independent read-only admission plus synthetic short/broad versus long/slender,
protected-path, loop and empty-mask checks before R001. R001 single45case pass,
internal180s cap/external200s, clean commit receipt, fail on identity/thickness
change; no tune/rerun for gain. Preview/final renderer reads saved arrays only.
Independent numeric/deletion-overlay review after run; AI review is not human GT.
Preserve original code, old half-depth and all prior scoring files by hashes.
Update canonical track then frontier and existing Obsidian note/one Roadmap entry.
