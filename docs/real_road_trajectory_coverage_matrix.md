# Real-road trajectory coverage audit

Evidence state: 2026-08-05.

## Verdict

**Zero currently possessed or directly downloadable routes pass the complete real-road trajectory gate.** The active Freeze-Then-Select goal remains active, but it cannot yet claim real-road closure. The completed Ferrite carrier experiments establish a controlled support-selection result only; they do not establish real-road crack geometry, tip, initiation-time, or cross-section forecasting reliability.

The missing object is not simply more data. It is one joinable trajectory keyed by the same physical asset and observation time, containing registered crack geometry, future repeats, traffic/load, temperature/weather, moisture, structure/material context, mechanical observation, and maintenance/censoring semantics. Different datasets must not be concatenated and described as one physical trajectory.

## Minimum pass rule

A route passes only if all mandatory conditions are demonstrated from possessed files:

1. Stable physical `asset_key` and auditable `time_key`.
2. Registered image, 3D surface, vector distress map, or equivalent geometry at repeated times.
3. A future crack geometry target supporting strict chronological train/test separation.
4. Traffic or axle-load history, temperature/weather history, and in-pavement moisture or a defensible moisture observation.
5. Fixed structure/material metadata and at least one mechanical observation such as FWD or strain.
6. Explicit maintenance events, observation resets, and terminal censoring.
7. A site holdout requiring no phase-field hidden labels.

The machine-readable decision table is `real_road_trajectory_coverage_matrix.csv`.

## Route findings

| Route | Geometry trajectory | Forcing/mechanics | Current decision |
|---|---|---|---|
| PaveTrack_PD | Repeated fixed-location images, boxes and masks | No linked load, weather, moisture, structure, or mechanics reported | Geometry-only audit route; not a complete FTS mechanism route |
| Local LTPP 06B410 | Six distress JPGs all dated `2000-06-28`; no future image date | Profile records span dates, but no joined forcing/mechanics trajectory | Fail |
| LTPP InfoPave section | Repeated section distress surveys/maps; exact coordinate registration unproved | Traffic, climate, FWD, structure, M&R are plausible joins; moisture absent | Conditional route; no pass yet |
| Local MnROAD Cell 22 | No possessed repeated crack masks/maps | Daily lane traffic and sensor layout exist; numeric cell sensor series absent | Fail |
| Requested MnROAD Cell 22 | Unknown until request is fulfilled | Potentially strongest traffic-temperature-moisture-strain route | Conditional; no pass before file audit |
| Prospective road pilot | Can be designed to pass | Can be designed to pass | Required fallback if acquisition audits fail |

## Evidence boundaries

### PaveTrack_PD

The V3 ZIP manifest has now been audited without downloading the 5.69 GB archive. It contains 165 anonymized location directories, 8,936 JPGs, four plate-desensitization XML files, and `Dataset_PDdescription.xlsx`. Of the JPGs, 8,918 encode millisecond timestamps spanning `2022-04-18` to `2023-12-31`; the median location has 50 observations. The workbook provides `reid`, date, category, image name, polygon segmentation, and bounding box. A bounded five-date registration audit for location `10` then failed: only the June-July edge met the graph gate, while August and September produced degenerate homographies with transformed crack-center errors above 1,070 px. This route is now restricted to scene-level segmentation/tracking; it cannot support physical tip/initiation claims. Traffic/load, weather, moisture, structure/mechanics, maintenance/reset, and censoring remain absent. See `pavetrack_pd_manifest_audit_20260805.md/json` and `pavetrack_pd_registration_gate_20260805.md/json`. Sources: [Scientific Data article](https://www.nature.com/articles/s41597-025-05748-5), [ScienceDB record](https://doi.org/10.57760/sciencedb.20383).

### LTPP / InfoPave

InfoPave exposes section timelines, repeated 50-ft distress maps, traffic, climate, FWD, structure, and maintenance/rehabilitation records. The local `06B410` packet is insufficient and the current official status endpoint rejects `06B410` as an invalid section ID. California asphalt section `06-1253` (`LDW_SECTION_ID=2056`) has now been downloaded at map level: 90 maps covering nine dates and ten fixed segments. A frozen `0-50 ft` audit confirms a common physical `0-50 ft × 0-5 m` drawing grid across all nine dates. Raster dimensions and cropping vary, so grid rectification and crack-line vectorization remain mandatory; drawn line thickness is not crack width, and initiation is interval-censored. Traffic/climate/FWD/structure tables are not yet extracted and moisture remains unavailable. See `ltpp_section_candidate_audit_20260805.md/json` and `ltpp_06_1253_geometry_gate_20260805.md/json`. Sources: [InfoPave](https://infopave.fhwa.dot.gov/), [Manual Distress Survey Viewer](https://infopave.fhwa.dot.gov/Media/ManualDistressSurveyViewer), [Standard Data Release](https://infopave.fhwa.dot.gov/Data/StandardDataRelease/).

### MnROAD

MnROAD officially provides design/layer information, traffic, weather, laboratory and performance monitoring; field monitoring includes FWD, moisture and crack surveys. Some raw dynamic-load and sensor records require a request. The local traffic workbook supplies daily lane vehicle classes through 2013, and `sensor_locations.xlsx` proves the Cell 22 sensor layout, but neither supplies the missing synchronized numeric sensor trajectory or repeated crack geometry. Sources: [MnROAD data](https://www.dot.state.mn.us/mnroad/data/index.html), [field monitoring](https://www.dot.state.mn.us/mnroad/data/field-monitoring.html).

## Next acquisition gate: no training

1. Download and audit the PaveTrack_PD manifest for exact timestamps, fixed-location identity, maintenance transitions, missing frames, masks, and terminal observation semantics.
2. Extract one LTPP section with at least three distress dates and prove coordinate consistency while joining traffic, climate, FWD, structure, and M&R by section and date.
3. Prepare a MnROAD Cell 22 request for synchronized numeric `LE/TE`, `PG`, `TC`, moisture, FWD, crack survey/distress map, WIM/ESAL, timestamps, units, missingness, and quality flags.

If none yields registered future geometry plus traffic, temperature, and moisture for the same asset, trigger a prospective pilot rather than relaxing the evidence standard.

## Prospective pilot contract

The smallest defensible pilot should contain at least three independent sections and four inspection times per section; fixed georeferenced patches; calibrated images or 3D surfaces; crack masks; traffic/axle load; temperature and rainfall; in-pavement moisture; FWD or sparse strain; layer/material metadata; maintenance/reset events; and terminal observation status.

Use earlier observations for training and final observations for forecasting, with a separate site holdout. Report registered mask IoU/Dice, crack endpoint or tip error, initiation-interval error, crack area/length error, and uncertainty coverage. Run stability selection only when a forcing-variation and identifiability gate shows that traffic, temperature, and moisture are distinguishable.

## Active-goal recovery rule

The blocked real-road part can resume immediately when **one** route satisfies all seven minimum-pass conditions and its raw files, provenance, time split, and join keys are frozen. Until then, support-set results remain a semi-synthetic diagnostic; the correct action is acquisition/audit, not architecture optimization.
