# MnROAD same-cell data request: first mechanical road packet

Date: 2026-07-31

## Requested scope

Please provide one internally consistent MnROAD Mainline Cell 22 packet covering
2009-01-01 through 2013-09-21, or the longest common interval available within
that window. The purpose is a research-only, observation-aware pavement damage
forecast pilot.

## Required channels

- Dynamic response for Cell 22 `LE101-102`, `TE101-102` and `PG101-102`, with
  timestamp, units, load/test identifier, station, offset and depth.
- Cell 22 thermocouples `TC101-116`, with timestamp, units, station, offset and
  depth.
- FWD drop records for Cell 22: session date/time, lane, station/test position,
  applied load or stress, all geophone deflections, sensor offsets, pavement and
  air temperature, GPS/status and quality flags.
- Every dated Cell 22 distress survey/map and maintenance or reconstruction
  event in the same interval.
- Mainline traffic/WIM records sufficient to recover daily FHWA vehicle-class
  counts, heavy-commercial volume and BESAL/CESAL; raw axle groups and speed are
  preferred when releasable.
- Cell geometry, layer thickness/material description, construction and
  maintenance dates, lane and station coordinate definitions.

## Delivery contract

Keep raw values and quality flags. Do not interpolate missing periods. Include
the timezone, timestamp convention, units, sensor calibration/version changes,
removed/replaced sensor dates and a data dictionary. A row must retain Cell 22,
station and sensor identity so channels can be joined only when they refer to
the same physical asset and time interval.

FEM damage, fatigue history, degradation, raw energy and active driver are not
requested as measurements. They will remain model-side latent states inferred
from the real observable packet.
