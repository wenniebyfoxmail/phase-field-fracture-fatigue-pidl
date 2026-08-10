# LTPP spatial-registration v2 full-source availability receipt — result

## Decision

`SOURCE_AUGMENTATION_AVAILABLE__NO_REGISTRATION`

All eight frozen 06-1253 survey dates have an official full-page manual
distress-survey PDF available through InfoPave.  This is a useful source-data
finding, but it does **not** change the frozen v1 decision
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL` and does not qualify a v2
registration route.  No controls were extracted, no transform was fit, no
model was selected, and no registration residual was calculated.

## Frozen receipt

The canonical completed package is:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_full_source_availability_receipt_20260810_after_render_name_repair/`

It contains the eight verbatim PDFs, raw official API responses, a
display-only uncropped page-4 render for each date, `source_receipt.json`, and
`manifest.sha256`.  A direct recomputation verified all 18 manifest entries.
The completed package manifest is:

`73ad3b65865837ce22d142605341ac61e9b5d5973da269f0a6d5e2ba68ce11f0`

The first named output directory
`ltpp_06_1253_full_source_availability_receipt_20260810/` is retained as an
implementation-abort record: only the 1991 PDF and a display render were
created.  The run stopped before a receipt or manifest because `pdftoppm`
zero-pads a single-page suffix (`-04.png`) rather than using `-4.png`.  The
repair changed only that display-file discovery, added a regression test, and
used the new `..._after_render_name_repair` output directory.  It did not
change sources, dates, page number, or any registration method.

## Official source check

InfoPave's Manual Distress Survey Viewer states that legacy display images may
be cropped and directs users to the survey PDF for the complete map.  The
official `GetDistressPDF` response returned exactly one HTTPS PDF for each
frozen survey:

| Date | InfoPave PDF ID | PDF bytes | SHA-256 prefix |
|---|---:|---:|---|
| 1991-06-10 | 860849 | 355,532 | `96df733b8b30` |
| 1995-10-24 | 860850 | 265,126 | `d803e064136f` |
| 1997-02-28 | 860851 | 299,247 | `3224d92ee956` |
| 1998-04-07 | 860852 | 296,510 | `740a7d1348a1` |
| 2001-09-13 | 860853 | 362,627 | `33d73d172ef4` |
| 2003-05-14 | 860854 | 376,431 | `e315f3fe296b` |
| 2007-11-06 | 860855 | 383,890 | `03d4fba81e5d` |
| 2012-04-17 | 860856 | 350,702 | `49a27b5580f1` |

The completed receipt holds the full URLs and full SHA-256 values.  The
1995 PDF is nine scanned, 300-dpi monochrome pages.  Its uncropped fourth page
visibly contains the two original 50-ft map panels, their outer frames,
printed dotted grid, and metre/feet ticks.  The 0–50-ft panel's printed grid
is also visible in the existing viewer PNG.  Therefore the earlier
`0/10` dense-grid result is an outcome of the frozen automated
layout-observability rule, not evidence that official 1995 source material
contains no visually identifiable grid at all.

## What this does and does not repair

The PDF establishes a reproducible fuller source context.  It can support a
future, separately frozen engineering MVP for deterministic page orientation
and map-panel windowing based on printed outer frames and coordinate ticks.
It does not itself provide a separate physical measurement, a point-level GPS
tie, or a new external fiducial.  The PDFs are scanned manual survey maps;
their printed grid is a potential **Tier B** reference, not Tier A.

The LTPP IMS documentation describes `SECTION_COORDINATES` as latitude and
longitude for a test section or project site.  Even where present, such a
section-level position cannot locate the 66 individual map-grid intersections
and is not an eligible per-map final control.

Thus there are still **no confirmed independent final controls**.  A Tier B
attempt remains plausible because all eight dates now have a retained full
source map, but it cannot be called available until two blinded independent
annotators apply the frozen consensus protocol and every required final and
development candidate survives.  The user and implementer remain ineligible
to annotate final controls because they have already seen v1 outcomes.

## Recommended next action

Do not retune the old A/B frame candidates and do not run a v2 final gate.
The smallest useful next engineering action is a separately preregistered
`full-source map-panel MVP`: use the newly frozen PDFs only to render and
visually review deterministic orientation plus the two printed panel frames
per source page.  It must exclude crack/WIM/repair/handwriting information and
produce no qualification claim.  If that visual MVP is satisfactory, a source
amendment and external re-review are required before new blind Tier B packets
can use PDF-derived source windows.

## Verification

```bash
/Users/wenxiaofang/miniconda3/bin/python3 -m pytest -q \
  tests/test_ltpp_acquire_full_distress_pdfs_v2.py
```

Result: `4 passed`.
