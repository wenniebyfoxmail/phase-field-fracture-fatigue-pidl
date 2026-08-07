# LTPP section candidate audit

Audit date: 2026-08-05. Source: [LTPP InfoPave Manual Distress Survey Viewer](https://infopave.fhwa.dot.gov/Media/ManualDistressSurveyViewer), SDR 39.

## Decision

`06-1253` is the primary LTPP extraction candidate. It preserves the asphalt-on-unbound-base physical setting and provides nine repeated manual distress-map surveys under one construction number. It is not yet a passing real-road FTS route because same-segment coordinate consistency and the traffic/climate/FWD/structure join have not been extracted, and moisture is not established.

## Why local 06B410 was rejected

The current InfoPave `GetStateSectionStatus` endpoint returns `Invalid section ID provided.` for `06B410`. The local packet also contains only one distress-image date. It is therefore removed from consideration as the primary repeated-geometry route rather than being silently reformatted or treated as a valid current section.

## Primary asphalt candidate: 06-1253

- Internal `LDW_SECTION_ID`: `2056`.
- Pavement: Asphalt Concrete on Unbound Granular Base.
- Viewer construction numbers: one.
- Viewer maintenance/construction resets: none shown.
- Surveys: nine.
- Every survey supplies ten maps representing the same nominal 50-ft segment sequence from 0–50 ft through 450–500 ft.

Survey dates:

`1991-06-10`, `1995-10-24`, `1997-02-28`, `1998-04-07`, `2001-09-13`, `2003-05-14`, `2007-11-06`, `2012-04-17`, `2015-03-02`.

The first seven viewer descriptions say transverse-profile data was collected, while the final two say distress data was collected. Because every event still exposes ten `DistressItems`, map availability is proven; consistent distress semantics across all nine dates is not yet proven.

## Maintenance-semantics control: 06-0202

`06-0202` is a rigid-pavement control rather than the primary route. It has:

- Four surveys under construction 1.
- Nine surveys after a 2004 lane-shoulder joint-sealing reset.
- One survey after a 2015 crack/joint-sealing reset.

This section demonstrates that InfoPave construction numbers can provide explicit reset boundaries. It must not be mixed across those boundaries as one uninterrupted damage trajectory.

## Next gate

1. Download only one fixed 50-ft segment from all nine `06-1253` surveys.
2. Confirm image dimensions, orientation, station direction, lane boundaries, and drawing scale.
3. Determine whether crack lines are vectorizable in a common station-lateral coordinate frame.
4. Reject dates whose map semantics are profile-only or incompatible with manual distress geometry.
5. Join the accepted survey dates to traffic, climate, FWD, structure, and M&R records by section and time.
6. Treat moisture correction identification as unavailable unless an independent same-section moisture observation is found.

No PIDL, field adapter, weak selection, or prediction training is authorized before this gate passes.

## Preserved evidence

Raw California section listings, complete viewer JSON for `06-1253` and `06-0202`, and SHA-256 hashes are stored under:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_candidate_audit_20260805/`

The compact receipt is `ltpp_section_candidate_audit_20260805.json`.
