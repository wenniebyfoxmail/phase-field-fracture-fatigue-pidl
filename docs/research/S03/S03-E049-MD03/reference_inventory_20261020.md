# MD03 existing reference inventory — 2026-10-20

## Purpose / boundary

Continue active D3: determine whether an already-held, located local DIC or
real-opening reference can distinguish the saved texture-jump candidate from
nonlinear deformation/texture effects. C1 evidence availability, controlled
experiment; not a new measurement, training run or prediction evaluation.

User approved file lists and existing explanatory text only. This check made
zero network calls/downloads, opened no new result attachments and decoded no
images. No ZIP listing/extraction, PDF/figure fetch, DIC computation, annotation
or new-reference production. Old observer, half-depth definition, masks and
scores remain unchanged. No new sub-agent or external contact.

Reuse previous E049 inventory and local-check result. Read only the existing
MD03 metadata JSON, dataset-description text, cached paper-method/availability
text and local file names/sizes. This is a 2026-10-20 local audit of the
2026-10-18 cached publication snapshot, NOT a live check of the platform.

## What exists, and what it establishes

| Asset | Existing cache / local state | Reference value and remaining uncertainty |
|---|---|---|
| 19.2% beam image catalogue | 173 TIFF entries, IMG_0003…0175; locally held originals are only IMG_0089/0132/0175 in the known E049 source folder | Original DIC-input photographs, not author-exported displacement/opening truth; no pixels reopened |
| 33.7% beam image catalogue | 100 TIFF entries, IMG_0225…0324; no originals in E049 source folder | Different beam; remains unopened, not a substitute reference for 19.2% |
| Four point bending test data.zip | Root catalogue ID 9e2dca53-991d-467c-8d16-4ff814798fcf, 1,919,356 bytes; no named local payload found in checked roots | Description promises load/displacement data; ZIP members, specimen joins, DIC exports or synchronisation remain UNKNOWN, not absent |
| Compression test data.zip | Root catalogue ID 4cd39c31-cea3-46f6-803c-10f069a151b0, 165,831 bytes; no named local payload found | Compression data, not an established reference for the selected bending-image location; unopened |
| Existing publisher text, §2.3 | Canon EOS 6D / 100mm macro, front-face speckles, one DIC beam per ratio; DIC and opposite LVDT averaged for midspan deflection | Confirms DIC acquisition/use, but global deflection is not local crack opening |
| Existing publisher text, §3.3 and Fig.7 description | Explicitly names OpteCAL, front-face strain fields and their relation to the load–deflection curve for a 19.2% beam | Author DIC results EXIST according to the text. Fig.7 itself was not opened/downloaded; no numeric field or pixel correspondence acquired |
| Existing publisher text, data availability | Points to the same Mendeley DOI | Does not independently specify which ZIP contains DIC exports or image-to-state mapping |
| Our E049 outputs | Cached masks, global transforms, synthetic controls, J/Q and match diagnostics | Algorithm-derived evidence from the same images, NOT a newly obtained independent reference; no arrays or figures reopened this turn |

Cached root has two image folders and two ZIP entries. All 273 image-folder
entries are TIFFs; there is no separately catalogued DIC numerical export,
opening table, manual annotation or calibration/readme among those entries.
This does not inspect the ZIP interiors, prove absence elsewhere, or certify
current platform completeness. The empty image-folder tail pages support the
cached image counts; filenames/upload dates do not supply capture chronology.

## Coordinate / synchronisation chain

| Required connection | Available in existing material | Status |
|---|---|---|
| 19.2% folder → beam group | Folder label and paper DIC description | Group-level link exists; exact mechanical-test replicate/file key unresolved |
| IMG_0089/0132/0175 → native pixel position | Previous E049 source metadata and saved crop conventions; x2782,y1900 is our native-image candidate | Our coordinate bookkeeping exists; it is not an author DIC coordinate mapping |
| IMG filename → OpteCAL reference/deformed frame or Fig.7 state | No such lookup in the examined text/catalogue fields | Not established |
| DIC grid/ROI → native image pixels | No origin, axis/sign, grid spacing, crop/rescale transform or control-point mapping found in examined text | Not established |
| DIC displacement → local opening across a particular gap | No displacement export, opening gauge definition, units/error or crossing-line identity available | Not established; a strain hotspot is not itself an opening-width label |
| Image/DIC state → machine load/time | Paper states that fields and load–deflection curve were correlated, but supplies no filename join in this text | Association exists at description level; per-file synchronisation unresolved |

The TIFF catalogue JSON fields contain file identity, byte count, hash,
content type and publication timestamps/URLs, not per-frame DIC coordinates,
camera calibration or load/time keys. No physical px-to-mm mapping is inferred
from specimen dimensions or lens focal length. No need to require absolute
load for relative-stage development, but matching the reference to the actual
image/location is necessary to test a real local opening claim.

## Bounded conclusion / next decision

**Author DIC work is documented; a usable local reference is not yet in hand.**
The missing item is access plus an auditable image/state/coordinate join, not
evidence that the authors never performed DIC. This inventory is complete;
do not repeat same-image threshold/matching checks as a replacement reference.
Preserve the structure-sensitive component and old candidate-area 5.81% result
within its original observer-space scope. D01 geometry work is independent.

Proposed next package, NOT executed: obtain permission to inspect Fig.7 and
the four-point-bending ZIP's file list/README/header/schema information together,
without new TIFFs, parameter fitting, target choice or prediction rescore.
Question: can the original filenames, mechanical-test identity and DIC states/
coordinates be linked? If linked exports exist, define a bounded reference
comparison; if only global load/deflection is supplied, use it only as loading
context and request located DIC/opening evidence separately. Figure-level
agreement alone would be qualitative localisation, not numeric crack truth.
Any download/new attachment opening or author contact requires separately
scoped approval; no such action was performed today.

## Evidence pointers and check limits

Raw catalogue and description cache:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/open_data/s03_independent_sequence_metadata_20261018/`:
`wv7hvgg8c7_folders_v1.json`, `wv7hvgg8c7_root_files.json`,
`md03_192_files.json`, `md03_337_files.json`, their cached empty tails,
`md03_page.txt`, `md03_paper_text.txt` and `audit_receipt.json`.

The short md03_paper_text.txt is only an abstract; method claims above come
from the different, already-held 43,730-byte publisher_text.txt at
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/metadata/publisher_text.txt`:
§2.3 line94; §3.3 line167; Fig.7 caption line173; data availability line203.
Only existing textual description was inspected; figure URLs were not followed.

Known original-image presence checked by directory listing, not image decoding
or rehashing payloads. Filename-only searches for MD03 / wv7hvgg8c7 / article
ID109184 / repository ID3781m1pg / lattice-reinforcement / exact bending-ZIP
name covered local_archive, the project tree, Downloads, Documents, Obsidian
attachments and Paper Reading. No extra clearly named source reference was
found. This is not a full-device content search; generic/renamed files or
unmounted/remote archives are not ruled out. Other-dataset DIC exports are not
silently treated as MD03 references.

275-row catalogue (273 TIFF + 2 ZIP), local-original presence and ten text/
metadata input hashes saved at:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/reference_inventory_20261020/`:
`file_inventory.tsv`, `text_sources_manifest.json`. Original payload hashes
are publication metadata only, NOT reverified against unopened payloads today.
No experiment run receipt is implied by this documentation-only inventory.
