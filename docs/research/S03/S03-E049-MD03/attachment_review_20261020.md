# MD03 two ZIPs + author Fig.7 inspected — 2026-10-20

## Decision and scope

User annotations explicitly approve downloading/opening both ZIPs and advancing
the Fig.7 + bending-package directory/document/header check. Continue D3 C1
reference qualification, not a new forecast or measurement experiment.

**Substantive progress: author DIC extensometer records and synchronisation
metadata are now obtained. A located local crack-opening reference is not.**
Do not keep describing all DIC/synchronisation information as absent. Conversely,
do not interpret projected elongations as native pixel coordinates or the
published strain figure as an opening-width ground truth.

No new TIFF, new beam pixels, segmentation, matching, model training, load-curve
analysis, forecast re-evaluation or author contact. Existing identification,
half-depth width and scores remain unchanged. Fig.7 and the two packages are
newly exposed development evidence, not a future blind reference.

## Downloads and file contents

Official source: https://data.mendeley.com/datasets/wv7hvgg8c7/1, version1.
Both archive sizes and SHA256 match the saved official catalogue; ZIP CRC checks
pass. Resource forks and .DS_Store retained in original ZIP but excluded from
substantive member counts. Effective members extracted without executing code.

| Download | Verified bytes | Effective contents |
|---|---:|---|
| Compression test data.zip |165,831|1 MATLAB analysis script + 10 machine TXT files; no DIC export, frame map or local crack annotation among these members |
| Four point bending test data.zip |1,919,356|1 MATLAB analysis script, beamDispData.mat, Lattice Reinforced UHPC.xlsx, 7 TXT machine files, Plain UHPC.csv (11 files) |
| Author Fig.7 JPEG |1,412,530|2963×3674 original published load–deflection / DIC-strain composite; source SHA256 3c5045c3ab9e9559005d9e6f1c89673fb064f7dc8ebf80294e469c8f3ad5b7e0 |

Bending ZIP SHA256: 8921d591cba63e54bea08464d18c12c4f4f197950b035d971eadffec0fbfea29.
Compression ZIP SHA256: 98f86b4208d04c163e68774dd52d1e7982449e558832da6367bd50a14685f48e.
Fig.7 source: https://ars.els-cdn.com/content/image/1-s2.0-S026412752030719X-gr7_lrg.jpg.
Web-reader image access failed, direct authorised source download succeeded;
not treated as missing reference. Paper DOI:10.1016/j.matdes.2020.109184.

## What beamDispData.mat actually contains

Top-level `beamData` has PLA3 and PLA5 structures. The author script labels
beams1–3 as19.2%,4–7 as33.7%, and explicitly uses PLA3/PLA5 for the two DIC
cases. Group-to-test identity is supported by that script, rather than guessed
from a similar filename. Minor unused/commented ordering inconsistencies in
other control-beam descriptions are not silently repaired or used as identity.

| Field | PLA3 | PLA5 | Meaning / limit |
|---|---|---|---|
| `data` |222×21|248×21|7 extensometers × Total/elongation, X-Proj, Y-Proj; not a spatial DIC grid |
| `Ext1`…`Ext7` |222 values per component|248 per component|Each has Total/X/Y; these are projected elongation signals, NOT native endpoint coordinates |
| `time` |222 keys|248 keys|DIC time axis; no unit label in this MAT header inspection |
| `testData` |disp/load/datatime each1107 entries|each1255 entries|Machine records with synchronisation bookkeeping |
| `present`, `missing`, `firstPhoto`, `folderPath`, `time`, `n` |203 present,18 missing,firstPhoto4,PLABeam3|243 present,4 missing,firstPhoto226,PLABeam5|Photo-index / sampling-time evidence; no explicit IMG basenames or generator script |

The author `.m` file loads this MAT (lines16–19), uses Ext1/2/3 to compensate
beam-end differential motion and construct midspan deflection (21–27), then
uses unique machine times and intersected DIC times (39–80). It comments that
machine sampling is faster than image sampling and that some times were not
sampled. We read this code but did not run it. Ext4–7 could contain additional
local gauge information, but their endpoints/purpose are not specified; do not
declare all seven signals global deflection, or assign any one to x2782,y1900.
DIC values are described by the script as already metric; exact units of every
extensometer/time field are not separately documented in the MAT headers.

## Recovered time-key connection, still provisional filename join

For every saved `testData.present` entry, the corresponding time equals
`5*(present-firstPhoto+1)` exactly:203/203 and243/243. This is an observed
metadata relationship, not a prescribed camera timing rule or a new fit.

If `present` uses the published TIFF numeric suffix, the three fixed files have:

| Source | Candidate PLA3 time key | Occurrences in machine datatime |
|---|---:|---:|
|IMG_0089|430|1|
|IMG_0132|645|1|
|IMG_0175|860|1|

This is a promising actionable join, NOT yet a certified filename/time/load
mapping. The MAT does not store literal IMG names; the photo-index generator
and definitions of `n`/`missing` are not supplied. Time-unit seconds is plausible
from the experimental context but not established by this field-name check.
No load values have been joined to these files and no future load is assumed
known at a prediction origin.

Mismatch matters: only157/173 published19.2% suffixes are in PLA3.present;
3 is before firstPhoto4 and15 others occur in its missing list. PLA5 overlaps
97/100 public suffixes;225 is before firstPhoto226,285/315 are marked missing.
Those TIFFs DO exist in the public catalogue: `missing` cannot simply be
interpreted as absent downloadable photographs. The MAT spans more indices
than the public folders. Do not force a row-order zip or fabricate a bijection.

## Workbook / text schemas

Read-only XML structure/header inspection of the10-sheet XLSX, plus its shared
strings, found TIME[sec], LOAD[kips], LVDT2/3[in], average, kN and mm headers;
no coordinate/frame-name header or embedded media. The author script uses only
`fully infiltrated (horiz)` for one mechanical-test curve. No workbook edits,
formula recalculation or new export. The seven bending TXT files are numeric
from their first line (not labelled headers); units/column interpretation
come from author code and related tabular headers, not invented TXT labels.
Plain UHPC.csv and compression TXT files do have machine-measurement headers.

Parser used bundled Python standard XML for workbook metadata, and existing
Conda SciPy for MATLAB structure because bundled Python lacks SciPy. No
MATLAB execution, spreadsheet macros, formula execution, code installation
or external data transmission from the files.

## Fig.7 interpretation and remaining local reference gap

Actually opened the unchanged original JPEG. Top is load(kN) versus midpoint
deflection(mm), marked a–i. Bottom shows authors' epsilon_xx strain overlays:
early panels mostly low strain, later multiple near-vertical localisation
bands and a dominant late band. This supports the authors' multi-crack
evolution interpretation at figure scale. It is not a new result from us.

No IMG filenames, native pixel axes, Ext1–7 endpoints, DIC ROI/grid transform,
full-field numeric strain/displacement export, or local crack-opening gauge
definition were found in these two archives or Fig.7. The figure can supply a
qualitative spatial reference; without a matched state/coordinate system it
cannot numerically validate our1.576px jump or physical width. Do not digitise
rainbow colours into opening millimetres or fit an overlay by prediction error.

## Next action

Prioritise one coherent provenance/synchronisation audit on the already fixed
89/132/175: test index conventions and reference-frame offsets against author
time bookkeeping, establish units and source-beam identity, and compare the
saved machine/DIC sampling logic without changing forecasts. At the same time
prepare a concise list of missing extensometer endpoints / full-field export
and Fig.7-state filenames for a single possible author enquiry, not repeated
same-image threshold checks. Sending any enquiry needs human approval.

This is a next proposal, not an executed time/load join, forecast rescore or
request sent. Even a recovered realised load is retrospective reference unless
the loading schedule was known at the origin. D01 remains a separate route.

## Reproducible evidence

Parent archive:
`local_archive/experiments/S03-E049-MD03/reference_attachment_check_20261020/R001/`.
`download_and_members.json` holds requests, sizes, hashes and all archive
members; `schema_and_text.json` holds source-script text, MAT field shapes,
metadata and workbook headers; `time_metadata_audit.json` holds catalogue
overlaps and the three candidate time keys. `unpacked/` contains the verified
member bytes. `author_Fig7.jpg` + same-stem `.md` preserve source and reading
limits. Inspectors: `scripts/md03_reference_attachment_inventory.py` and
`scripts/md03_reference_attachment_inspect.py`. New scripts were uncommitted
during reading; base commit8f4d58fe plus actual script SHA retained in QA.
Old code/assets untouched; no claim of an old-payload hash audit this turn.
