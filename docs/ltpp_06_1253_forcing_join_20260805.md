# LTPP 06-1253 forcing join gate (2026-08-05)

## Decision

`06-1253` now passes the minimum input gate for a **real repeated-geometry, climate-conditioned, no-hidden-label validation route**. It does not pass the stronger gate for traffic-temperature-moisture mechanism discovery.

This distinction is mandatory:

- The nine accepted distress-map dates share an explicit physical road grid.
- Monthly temperature and precipitation are available for every year from 1991 through 2012.
- Seven FWD events are available from 1989 through 2003.
- The official cross-section response exposes one four-layer AC-on-unbound-base construction.
- Traffic consists of only five monthly snapshots in 1991-1992.
- Humidity and moisture are absent.

The raw official responses are frozen under:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_forcing_20260805`

The directory contains 62 raw files and `raw_files.sha256`. The file-level manifest is the provenance boundary; derived interval features must point back to it.

## Official interfaces used

- [InfoPave Section Timeline](https://infopave.fhwa.dot.gov/Data/SectionTimeLine/?Section=06-1253)
- `/Data/GetTimelineData`
- `/Data/GetTrafficData`
- `/Data/GetPreviewData`
- `/Data/GetSectionTimeLineConstructionData`
- `/DynamicView/GetCrossSectionData`

The frontend request contract was recovered from the official `SectionTimeline.js`, `previewSectionTimeLine.js`, and `CrossSectionViewer.js` scripts. Preview responses were accepted only when they parsed as JSON and returned `Message == "success"`.

## Joined forcing inventory

### Climate

Temperature and precipitation each contain 12 monthly records per year for 1991-2012, giving 264 values per field. Annual mean temperature across the retrieved years ranges from 15.37 to 17.59 in the API's displayed units. Annual precipitation sums range from 801.1 to 1901.8 in the API's displayed units.

These are monthly bins, not observation-time weather. Any interval feature must predeclare whether the source and target months are included, excluded, or prorated.

The API reports no humidity and no wind records for this section. It supplies no pavement moisture state.

### Traffic

Only the following months have preview records:

| Month | Average daily volume | Days of data | Average daily percent trucks |
|---|---:|---:|---:|
| 1991-02 | 1034 | 1 | 1.9 |
| 1991-10 | 1535 | 4 | 7.7 |
| 1992-02 | 1208 | 5 | 3.4 |
| 1992-05 | 1663 | 4 | 4.0 |
| 1992-10 | 1500 | 7 | 3.5 |

These five snapshots cannot be interpolated into a continuous 1991-2015 traffic history without introducing an external model. If such a model is later used, its values must be labelled imputed forcing rather than LTPP observations.

### FWD

The frozen response contains seven events:

| Date | Station rows | Prediction use |
|---|---:|---|
| 1989-11-14 | 21 | pre-initialization context |
| 1991-06-10 | 21 | first-map boundary |
| 1993-07-14 | 6 | inside 1991-1995 interval |
| 1995-10-24 | 21 | target boundary |
| 1997-02-28 | 21 | target boundary |
| 1998-04-07 | 21 | target boundary |
| 2003-05-15 | 21 | after the 2003-05-14 map |

Each row exposes `TEST_DATE`, `STATION`, and `PEAK_DEFL_1`. The 2003-05-15 event is future information for the 2003-05-14 target and is prohibited in that prediction fold. It becomes eligible only for later targets.

### Structure and reset status

The cross-section response describes one construction with four layers:

| Layer | Material | Thickness (in) |
|---|---|---:|
| AC | Chip seal | 0.2 |
| AC | Dense-graded hot-mix surface | 3.6 |
| GB | Crushed gravel base | 15.3 |
| SS | Clayey gravel with sand subgrade | 14.8 |

The section is marked `Out of Study`; the timeline places that event on 2011-06-01. No maintenance or rehabilitation event is exposed in the retrieved timeline. That absence is a viewer fact, not proof that no unrecorded work occurred.

## Leakage-safe interval decision

The machine-readable interval table is [ltpp_06_1253_interval_coverage_20260805.csv](/Users/wenxiaofang/phase-field-fracture-with-pidl/upload%20code/docs/ltpp_06_1253_interval_coverage_20260805.csv).

Seven transitions ending on or before 2012-04-17 have complete monthly temperature and precipitation coverage. The final 2012-04-17 to 2015-03-02 transition has only May-December 2012 climate values and no 2013-2015 values. It is a valid geometry target but not a complete climate-conditioned target.

The ten 50-ft panels can supply spatial-section perturbations for stability analysis, but all panels share the same section-level forcing. They do not create ten independent traffic or climate histories.

## Consequence for Freeze-Then-Select

The next authorized experiment is deliberately narrower than the full goal:

1. Rectify each distress map to the explicit 0-50 ft by 0-5 m grid.
2. Separate crack strokes from grid, lane boundaries, labels, and severity codes.
3. Freeze the vectorized crack/damage field without equation-selection feedback.
4. Use predeclared temporal folds ending no later than 2012-04-17.
5. Compare FTS, single-shot selection, and joint training on geometry prediction and support stability for geometry/climate terms only.
6. Treat FWD as intermittent with explicit missingness; omit traffic and moisture from confirmatory support claims.

The stronger traffic-temperature-moisture objective still needs a second source, with MnROAD remaining the preferred mechanism route. LTPP should not be stretched beyond what its observed forcing supports.

## Goal status

The goal should remain active, not `blocked`: the LTPP geometry-climate route has a concrete next operation and can produce real no-hidden-label evidence. A future `blocked` judgment would be appropriate only if all of the following recur for at least three goal turns:

- canonical grid rectification cannot be qualified;
- no crack/vector labels can be separated from drawing artefacts without hidden target use;
- the MnROAD request and any alternate forcing source remain unavailable;
- no narrower real-road metric can still be evaluated honestly.

The goal is also not complete. Traffic-moisture support recovery and cross-section generalization across independent road sections remain open.
