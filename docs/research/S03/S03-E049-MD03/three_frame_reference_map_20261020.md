# MD03 three-frame identity/time/load and extensometer audit — 2026-10-20

## Purpose and authority

Continue original goal observation → state → evolution: distinguish real
opening/state changes from texture changes. Active D3 is reference semantics,
not model fitting. Follow-up received from research HQ; latest human request
in HQ thread01a14bb9-6cd1-7ee2-9647-5190d786f7ba was read and confirmed as
continuing research-window coordination. Work is limited to the already
approved/obtained MD03 files and existing arrays. No new attachment, TIFF
decode, CV, registration, threshold, fit, training, forecast or rescore.
No messaging back is assumed solely from an incoming agent request.

Reuse the completed ZIP/CRC/hash and Fig.7 check; do not repeat downloads or
full archive validation. Read author MAT and the two original machine TXT
files, the already read author MATLAB script and existing image catalogue.
New outputs are an auditable table and structural/unit checks, not a new
scientific prediction run. Old masks, identification, half-depth and scoring
remain unchanged. Base commit0690e7d8; script
`scripts/md03_three_frame_reference_map.py` SHA recorded in `mapping.json`.

## Main conclusion

**Within author files, three exact time-key/row/unit connections are now
verified. The link from literal published IMG filenames to author photo
numbers remains conditional; local opening coordinates remain absent.**

The earlier candidate mapping can therefore be made substantially more
explicit, without falsely upgrading it to independently certified crack truth.

## Three-frame table

Conditional assumption only: the published TIFF numeric suffix equals the
author's `testData.present` photo number for PLA3 (19.2% DIC beam). Author
folderPath is PLABeam3, firstPhoto4; no literal IMG basename/reference-image
field or photo-index generator is supplied. Public catalogue begins IMG_0003;
0003 being a reference frame is compatible with the metadata, not documented.

All rows below are 1-based author-array indices; load/displacement units follow
author script usage plus exact machine-column conversions, not a new scale fit.

| Fixed image | present/time row | Time key | Raw machine time column | Machine row | DIC row | Author load (kN) | LVDT2 (mm) | Author DIC midspan (mm) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|IMG_0089.tif|79|430|430.45023|427|86|9.644498276|0.475234|0.339493570|
|IMG_0132.tif|120|645|645.29919|640|129|12.930561544|1.115060|0.821576558|
|IMG_0175.tif|157|860|859.99921|852|172|14.159510240|1.893570|1.484485612|

See: all three time keys have exactly one machine record, match their saved
`n` row and have exactly one DIC row; conditional loading increases across
the three fixed observations. Therefore: these are useful conditional loading
context and reference observables, not just arbitrary file-order ranks.
Does not show: literal photo identity confirmation, a calibrated local opening,
independent future prediction, or knowledge of the next realised load at origin.
Front-face DIC midspan and opposite LVDT are different observables, not duplicate
ground-truth measurements of crack width; their difference is not scored here.

### Exact file-internal checks

- MAT machine datatime equals rounding the raw machine TXT column1 for all
  1107 PLA3 /1255 PLA5 rows. The MAT DIC time array itself has no explicit unit
  label; seconds is consistent with machine-time context but not independently
  documented on the photo/time field. Keep table column labelled time key.
- MAT load equals TXT column2 ×4.4482 exactly for both beams. This is consistent
  with kip→kN conversion rounded by the author dataset. The analysis script
  separately uses4.4482216 for non-DIC beams; do not reconvert the already
  metric MAT load or silently alter saved values to that slightly different factor.
- MAT machine disp equals TXT column4 ×25.4 exactly: it is LVDT2 in mm, not
  the average of TXT columns4 and5 in these DIC cases.
- For each of seven gauges in each beam, data's consecutive Total/X/Y triplets
  exactly equal the named Ext1…7 arrays. These are elongation/projection values,
  not pixel coordinates. Stored midspan arrays equal the author's formulas.

## Synchronisation metadata limitations are real, not whole-route failure

`testData.time = 5*(present-firstPhoto+1)` holds for all203/243 entries, but
saved `n` matches that time in machine datatime for only198/203 PLA3 and
232/243 PLA5 entries. Every mismatch points to an earlier machine time; the
expected time is absent in the machine array. Selected89/132/175 are NOT
among these mismatches. Example PLA3 photo45: expected210, saved row203
contains205. All16 exceptions are retained in mapping.json, not repaired.

Only1/18 PLA3 missing indices and0/4 PLA5 missing indices yield an absent
machine time under the same formula. Therefore `missing` is neither a reliable
list of unpublished image files nor a complete exact-time failure list. Its
generation semantics are unresolved. Author analysis script uses unique-time
intersection, not `n`, and checks resulting lengths only; that code is source
evidence, not proof that every possible join is safe. No author code is executed.

The previous157/173 and97/100 public-index overlaps remain catalogue facts,
not a validated full sequence mapping. Do not join all frames by ordinal rank,
reuse nearest earlier times implicitly, or infer capture cadence solely from
the exact5-key pattern. This preserves the successful three-row file-internal
connections without suppressing general bookkeeping discrepancies.

## Seven extensometers: both PLA3 and PLA5

Both beams contain Ext1…7 with Total, X, Y; PLA3 has222 samples and PLA5 has248.
Headers say Extensometer1…7 and Elongation/X-Proj/Y-Proj. Author script provides:
`left = Ext2.Y - Ext1.Y/2`, `right = -Ext3.Y - Ext1.Y/2`,
`mid = (left+right)/2`. The resulting signal is averaged with machine LVDT2.

| Gauge | Supported role from author code | What cannot be assigned |
|---|---|---|
|Ext1|Shared differential beam-end correction term for both midspan estimates|Exact two endpoint pixels, reference length, orientation and locations unknown |
|Ext2|Y projection used for author midDispYL estimate|Which exact physical/pixel endpoints make it a left-side estimate unknown |
|Ext3|Negative Y projection used for author midDispYR estimate|Endpoint order/sign convention not spatially documented |
|Ext4|Stored DIC extensometer signal; unused in supplied flexural analysis|No purpose, local crack identity or endpoint coordinates |
|Ext5|Stored DIC extensometer signal; unused in supplied flexural analysis|Same missing definitions; not assigned by signal shape |
|Ext6|Stored DIC extensometer signal; unused in supplied flexural analysis|Same missing definitions; not assumed a crack gauge |
|Ext7|Stored DIC extensometer signal; unused in supplied flexural analysis|Same missing definitions; not assumed a crack gauge |

Roles for Ext1–3 come from formulas/names and the paper's deflection description;
they do not uniquely specify gauge geometry. No attempt to infer endpoints by
fitting our texture jump or looking for a convenient correlation. Ext4–7 may
contain useful local information, so calling the entire export only global
deflection would discard an unresolved opportunity.

## Exact remaining gaps / usable boundary

| Required definition | Missing location in supplied material | Impact |
|---|---|---|
|Literal image name ↔ photo integer and reference-frame convention|MAT testData has firstPhoto/present/time/n/folderPath, but no filenames or creation script; author .m starts after MAT creation|Three-row load mapping remains conditional, not impossible |
|Gauge endpoint pairs and order|Each MAT Ext has only Total/X/Y; no start/end/u/v/point-ID/reference-image fields; supplied .m gives formulas but no point selection|Cannot identify the material interval or assign a crack to Ext4–7 |
|Reference length, units, axis/sign and calibration|No per-gauge definition/calibration table; script treats values as metric; Fig.7 has no gauge annotations|Cannot convert/localise these signals as physical opening measurements |
|DIC full grid/ROI → native TIFF transform|No pixel/grid positions or full field in MAT; Fig.7 shows rendered strain only|Cannot compare x2782,y1900 quantitatively to the author field |
|Fig.7 state a–i ↔ exact original image|Figure letters identify load–deflection points, not IMG names/time keys|Qualitative crack-band reference only; no target-state reassignment |

**Usable now:** author source-code semantics;7-gauge signal identity; file-internal
time/unit conversions; three conditional retrospective loads and global
deflections; qualitative author strain localisation. **Not established:** exact
physical image pairing, per-gauge local crack width, pixelwise independent
reference, or prediction validity. The next realised load is not automatically
known to a predictor just because it exists in retrospective machine data.

## Next decision, not another same-image micro-repair

This bounded read-only mapping audit is complete. Further algebra on the same
seven arrays cannot uniquely create missing gauge endpoints. The decision-changing
missing evidence is the photo-index preparation convention plus Ext1–7 endpoint/
reference-image definitions (or an author DIC project/full-field export).
Use one consolidated request draft if that source evidence is to be sought;
do not send it without the user's final approval. In the meantime preserve
conditional load context and existing observer-space development results, with
no rescore or claim upgrade. D01's separate geometry route remains unaffected.

## Evidence / provenance

Author files, unchanged:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/reference_attachment_check_20261020/R001/unpacked/Four point bending test data/`:
beamDispData.mat; analyzeFlexuralBeamData.m (lines5–10,16–27,36–81,88–93);
paghdasi-PLA beam #3--07121731 copy.txt and #5--07121804 copy.txt.
No workbook/figure/source-pixel reopening was needed in this step.

Exact rows, all metadata exceptions, input hashes and execution script identity:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E049-MD03/reference_mapping_20261020/R001/mapping.json`.
This new file is an audit output, not a modified copy of the author MAT or
old forecast evidence. Earlier attachment-review conclusions remain dated
history; the present table advances the file-internal load connection only.
