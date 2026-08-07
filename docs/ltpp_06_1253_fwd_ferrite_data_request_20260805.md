# LTPP 06-1253 FWD-to-Ferrite data request contract

Prepared: 2026-08-05. This is an acquisition and qualification contract. It does
not authorize a Ferrite solve, modulus inversion, field-adapter fit, or PIDL
training.

## Mechanism question

Can measured, same-section FWD basins constrain a section-specific layered
elastic mechanical prior for the `0-50 ft` distress-map panel without treating
synthetic Ferrite fields as observed road mechanics?

If the answer is yes, the accepted evidence remains hybrid and must be labelled
`ltpp_observation_plus_ferrite_prior`. If the answer is no, LTPP 06-1253 remains
a registered geometry-climate route only; no missing mechanics may be replaced
with constants, zeros, the existing SENT producer, or a generic road model.

## Exact spatial and temporal scope

- Section key: `STATE_CODE=06`, `SHRP_ID=1253`.
- Distress-map panel: longitudinal station `0-50 ft`, equivalent to
  `0-15.24 m`; transverse map extent `0-5 m`.
- Accept only FWD points whose official location record places the load centre
  inside `0-50 ft`. Preserve the original station and lane/location code.
- Request all drops at the accepted points on these seven dates:

| Test date | Role | Leakage rule |
|---|---|---|
| 1989-11-14 | pre-initialization context | not a distress-map target |
| 1991-06-10 | first-map boundary | eligible at/after this boundary |
| 1993-07-14 | within 1991-1995 interval | eligible only for later targets |
| 1995-10-24 | map boundary | eligible at/after this boundary |
| 1997-02-28 | map boundary | eligible at/after this boundary |
| 1998-04-07 | map boundary | eligible at/after this boundary |
| 2003-05-15 | one day after 2003 map | prohibited for prediction of 2003-05-14 |

The existing preview rows suggest panel-overlapping stations near `0`, `7.6`,
and `15.2 m`, but this is not an acceptance fact. The full
`MON_DEFL_LOC_INFO` records decide inclusion.

## Required official tables and fields

Field spelling may differ by release. The export must retain the official data
dictionary and map every delivered column to the semantic fields below rather
than silently renaming or dropping keys.

### 1. `MON_DEFL_MASTER`

Required semantics:

- `STATE_CODE`, `SHRP_ID`, `TEST_DATE`, `DEFL_UNIT_ID`;
- FWD/device identifier or serial number;
- pass count, operator/software metadata, and available test-level quality
  fields.

This is the parent/day record and supplies the deflection unit/device context.

### 2. `MON_DEFL_LOC_INFO`

Required semantics:

- `STATE_CODE`, `SHRP_ID`, `TEST_DATE`, `TEST_TIME`, `DEFL_UNIT_ID`;
- `POINT_NO` and/or `POINT_LOC`, with its unit;
- `LANE_NO` plus the corresponding `LANE_SPEC` code description;
- `CONFIGURATION_NO`;
- air temperature, pavement-surface temperature, and their units;
- available location/configuration quality flags.

This table determines panel overlap, lane/wheel-path semantics, test time, and
the configuration used for each point.

### 3. `MON_DEFL_DROP_DATA`

Required semantics for every drop, not just a selected load level:

- `STATE_CODE`, `SHRP_ID`, `TEST_DATE`, `TEST_TIME`;
- `POINT_NO`/`POINT_LOC`, `LANE_NO`, `DROP_NO`;
- drop height or load-level identifier where available;
- `DROP_LOAD` and load unit. In the current InfoPave dictionary this is peak
  load-plate pressure in `kPa`, not total force;
- `PEAK_DEFL_1` through the highest sensor present, preserving nulls;
- deflection unit;
- `NON_DECREASING_DEFL` and every delivered drop/basin quality flag.

A row containing only `PEAK_DEFL_1` is not a deflection basin and fails this
contract.

### 4. `MON_DEFL_DEV_CONFIG`

Required semantics:

- `CONFIGURATION_NO`, device/unit identifier and validity information;
- load-plate radius and unit;
- number of deflection sensors;
- load-cell and temperature-sensor calibration factors;
- available calibration dates/status and configuration quality flags.

### 5. `MON_DEFL_DEV_SENSORS`

Required semantics:

- `CONFIGURATION_NO`, `SENSOR_NO`, `CENTER_OFFSET` and offset unit;
- sensor calibration factor and serial number where available;
- `CENTER_OFFSET_FLAG` and other sensor-quality fields.

Do not assume nominal offsets when official configuration-specific offsets are
available. For reference only, FHWA's nine-sensor layout is `0, 203, 305, 457,
610, 914, 1219, 1524, -305 mm`; the delivered table remains authoritative.

When `DROP_LOAD` is supplied as plate pressure, derive total force only as
`pressure * pi * radius^2` after unit conversion. Preserve both the raw pressure
and derived force, including the exact plate radius and conversion expression.

### 6. FWD temperature tables

Request `MON_DEFL_TEMP_DEPTHS` and `MON_DEFL_TEMP_VALUES`, including:

- `STATE_CODE`, `SHRP_ID`, `TEST_DATE` and all finer time/location keys present;
- measurement depth and unit;
- temperature value, unit, time, and quality flag.

Temperature values must be joined/interpolated to drop time only through a
predeclared, leakage-safe procedure. Monthly climate is not a substitute for
FWD-time pavement temperature.

### 7. Structure, material, and backcalculation tables

Request the applicable `EXPERIMENT_SECTION`, `INV_*`, and `TST_*` records needed
to establish construction validity intervals, layer boundaries/thicknesses,
material identity, and available laboratory properties. Also request, if
present for 06-1253:

- `BAKCAL_BASIN`, `BAKCAL_PASS`, `BAKCAL_STRUCTURE_LAYERS`, and
  `BAKCAL_LAYER_LINK`;
- the available `BAKCAL_MODULUS_*` basin/section/layer tables;
- the available `BAKCAL_BEST_FIT_*` basin/section/layer tables.

Existing LTPP backcalculated moduli are an independent comparison/initialization
source, not automatic truth. Their release, method, quality flags, layer model,
and construction validity interval must be retained.

## Join contract

Use release-specific primary keys from the official data dictionary. At minimum,
the following relationships must be reproducible and uniqueness-audited:

1. `MASTER -> LOC_INFO` on `STATE_CODE, SHRP_ID, TEST_DATE, DEFL_UNIT_ID`.
2. `LOC_INFO -> DROP_DATA` on the release-defined point key, including
   `STATE_CODE, SHRP_ID, TEST_DATE, TEST_TIME, LANE_NO` and `POINT_NO` or its
   documented equivalent.
3. `LOC_INFO -> DEV_CONFIG` on `CONFIGURATION_NO`, additionally constrained by
   device/unit and validity fields if the release requires them.
4. `LOC_INFO -> DEV_SENSORS` through `CONFIGURATION_NO`, with one accepted row
   per sensor after quality filtering.
5. Temperature depth/value tables on `STATE_CODE, SHRP_ID, TEST_DATE` plus every
   finer official key required to prevent many-to-many joins.
6. Structure/material/backcalculation records on section, construction number,
   layer/point keys, and validity dates as defined by the release.

Every join must report unmatched rows, duplicate-key counts, and many-to-many
expansion. A join that silently multiplies drops or sensors fails.

## Raw delivery and provenance requirements

- Export raw or least-aggregated records, not screenshots or plotted basins.
- Include the release/version, extraction timestamp, query/filter definition,
  data dictionaries, code tables, units, null codes, and quality flags.
- Freeze every delivered file and a `SHA-256` manifest before derivation.
- Preserve unfiltered records; write exclusions to a separate auditable table.
- Record whether values are measured, estimated, corrected, or backcalculated.
- Record station units explicitly. The current table dictionary reports
  `POINT_LOC` in `m`, `DROP_LOAD` plate pressure in `kPa`, deflection in
  `micrometres`, and sensor offsets in `mm`; never infer total force or any unit
  from magnitude.

## Qualification gate before Ferrite

All conditions must pass:

1. At least one full multi-sensor basin with measured load exists at an
   officially located point within `0-50 ft`.
2. Load-plate radius, sensor count, configuration-specific offsets, units, and
   calibration/quality metadata are present.
3. Each retained basin passes declared missing-sensor and non-decreasing-basin
   rules; exclusions remain traceable.
4. Layer thickness/material records are valid on the FWD date, or the ambiguity
   is represented as an uncertainty range rather than a fixed truth.
5. Raw files, dictionaries, query, hashes, join audit, and leakage ledger are
   frozen.
6. The Ferrite design predeclares boundary conditions, load footprint, layer
   constitutive assumptions, parameter bounds, basin misfit, holdout strategy,
   and non-identifiability reporting.
7. At least one FWD date/point or load level is held out from calibration for a
   genuine basin-prediction check.

Passing this gate authorizes only a smallest layered-elastic Ferrite diagnostic.
It does not qualify a phase-field teacher or support a claim that `u`, energy,
history, degradation, or damage are road-observed labels.

## Fail-closed outcomes

- Full basin/load/configuration absent: `STOP_BEFORE_FERRITE`.
- Basin available but layer inversion non-identifiable: retain an uncertainty
  ensemble or stop; do not choose one convenient modulus set.
- No panel-overlapping FWD point: use FWD only as section-level context, not as
  a local mechanical calibration target.
- Only preview `PEAK_DEFL_1` available: retain the current geometry-climate
  route and continue the MnROAD/prospective-data branch.

## Minimal output asset and registry

The first accepted asset is a `fwd_qualification_report.json` containing raw
hashes, joined basin counts, panel-overlap stations, units/configurations,
quality exclusions, leakage decisions, and a fail-closed decision. No FEM field
package should exist before that report passes. Register the verdict in
`docs/research_frontier.md`; register a later executed diagnostic through the
PIDL attempt ledger and experiment inventory.

## Official references

- [FHWA LTPP database appendix: MON_DEFL relationships](https://www.fhwa.dot.gov/publications/research/infrastructure/pavements/ltpp/reports/03088/app.cfm)
- [FHWA LTPP monitoring chapter: FWD table contents](https://www.fhwa.dot.gov/publications/research/infrastructure/pavements/ltpp/reports/03088/09.cfm)
- [FHWA FWD sensor offsets and units](https://www.fhwa.dot.gov/publications/research/infrastructure/pavements/ltpp/06132/chapt4.cfm)
- [FHWA LTPP flexible-pavement backcalculation data requirements](https://www.fhwa.dot.gov/publications/research/infrastructure/pavements/ltpp/15036/004.cfm)
