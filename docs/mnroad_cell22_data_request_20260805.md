# MnROAD Cell 22 synchronized trajectory request

Prepared: 2026-08-05. This is a request specification only; it has not been submitted.

## Research purpose

We need one same-asset, timestamped pavement trajectory to evaluate whether a frozen continuous damage-field representation plus stability-validated weak selection can identify traffic, temperature, and moisture corrections without phase-field hidden labels.

Preferred overlap window: `2009-01-01` to `2013-12-31`, or the longest interval in which Cell 22 has synchronized distress, loading, environmental, and mechanical measurements.

## Minimum requested fields

| Domain | Requested records | Mandatory join fields |
|---|---|---|
| Distress geometry | Crack survey, distress map, image, vector location, crack length/width/type, or repeated station-referenced distress observations | cell, station/offset or image footprint, survey timestamp, units, survey method |
| Traffic/load | WIM or axle spectrum, vehicle class, lane, daily ESAL or source records needed to compute it | timestamp, lane, direction, quality flag |
| Mechanical response | `LE`, `TE`, `PG` numeric time series and FWD drops where available | sensor ID, cell, station, offset, depth, timestamp, units, sampling rate |
| Temperature | `TC` and other pavement-depth temperature measurements | sensor ID, depth, timestamp, units, quality flag |
| Moisture | `WM`, `EC`, or other calibrated pavement moisture observations | sensor ID, depth, timestamp, units, calibration/quality flag |
| Structure/material | Layer boundaries, material type, construction date, laboratory properties, sensor installation/removal | cell, layer/depth, validity interval, units |
| Maintenance/censoring | Repairs, overlays, sealing, sensor failures, survey gaps, cell closure or terminal observation | event timestamp, affected station/lane, event type, reset semantics |

## File-level requirements

- Raw or least-aggregated numeric files are preferred over plots or PDFs.
- Every table must include a data dictionary, units, timestamp timezone, missing-value code, and quality flags.
- Sensor IDs must map to the official Cell 22 sensor-location table.
- Distress observations must retain station/offset or another repeatable physical coordinate.
- Traffic values must state whether they are mainline-wide, lane-specific, measured, or estimated.
- Maintenance and survey absence must not be silently encoded as zero distress.

## Acceptance gate

The packet is accepted for real-road FTS only if it supports all of the following:

1. At least three repeated distress observations for the same physical Cell 22 region.
2. A strict chronological train/future-test split.
3. Overlapping traffic, pavement temperature, and moisture observations.
4. At least one mechanical stream, preferably FWD or strain.
5. Explicit maintenance/reset and terminal-censoring semantics.
6. Frozen raw files, hashes, provenance, units, and join keys.
7. No phase-field or FEM hidden labels used as observations.

## Draft request text

Subject: Request for synchronized MnROAD Cell 22 distress, load, environmental, and sensor data

We are conducting a non-commercial academic study of pavement-crack evolution from sparse observations. We would like to request the longest available synchronized trajectory for MnROAD Cell 22, preferably covering 2009-2013. The required data are repeated station-referenced crack/distress observations; lane-specific traffic or WIM/ESAL records; numeric LE/TE strain, PG pressure, TC pavement temperature, WM/EC moisture, and FWD records; layer/material metadata; and maintenance, sensor-quality, missingness, and terminal-observation information. For every file, timestamps, units, sensor IDs, station/offset/depth, quality flags, and a data dictionary are important. We will not treat plots, sensor-layout files, or mainline traffic totals as synchronized cell-level measurements. Could you please advise which files are directly available and which require a formal data request?
