# LTPP spatial-registration v2 full-source availability receipt — preregistration

## Status

`SOURCE_AVAILABILITY_ONLY__NO_REGISTRATION`

This is a source-acquisition receipt for an engineering diagnostic.  It does
not amend the frozen v1 result
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`, disclose v2 final controls,
extract controls, fit a transform, select a model, compute registration errors,
or authorize a 2-D crack model.

## Question

Does the official InfoPave Manual Distress Survey Viewer expose a full-page
source artefact for every one of the eight frozen 06-1253 survey dates, in
addition to the pre-existing per-50-ft viewer PNGs?  This matters because the
official viewer warns that its legacy display images can be cropped.

## Frozen method

For section `LDW_SECTION_ID=2056`, query the official endpoint
`POST https://infopave.fhwa.dot.gov/Media/GetDistressPDF` once per frozen
survey date using `SURVEY_TYPE=MDS`.  Require exactly one HTTPS `.pdf` response
per date.  Download that returned source PDF verbatim, record its byte count
and SHA-256, retain the raw API response, and rasterise page 4 as an *uncropped
display-only* source visual at 160 dpi.

No page is cropped to a 0–50-ft map; no grid line, road boundary, tick,
handwriting, repair, WIM, distress mark, or crack is parsed.  Rendering is for
human source comparison only.

## Interpretation rules

- A full PDF can demonstrate that the viewer PNG may omit page context.  It is
  not automatically an independent Tier-A reference.
- Printed map geometry in the PDF can only become Tier B through the already
  approved blinded two-annotator protocol.  Neither the user nor implementer
  can annotate final controls because both have seen v1 outcomes.
- Section-level GPS/latitude-longitude metadata, if available through an LTPP
  data release, locates the test section but does not locate the 66 map-grid
  intersections and therefore is not a per-map Tier-A audit control.
- Any later attempt to use full-page PDFs as registration inputs needs a dated
  source amendment, an externally reviewed deterministic map-window rule, new
  frozen input hashes, and a separate experiment name.  This receipt alone
  cannot change qualification status.

## Success and stop rules

Success is exactly eight retrieved PDFs plus a verified manifest.  Failure for
any missing/replaced/non-PDF response is recorded as source unavailability; it
does not permit a fallback to a different date or asset.  The run stops after
the receipt and does not progress to control collection or registration.
