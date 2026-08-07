# LTPP 06-1253 real-route preflight contract

## Purpose

Prevent a qualified coordinate carrier from being silently promoted to a qualified phase-field snapshot. The real-road Freeze-Then-Select producer may start only after both semantic geometry and mechanical-field provenance pass.

## Mandatory inputs

1. `grid_gate_results.json` with all nine maps passed.
2. The official forcing audit for section `06-1253`, internal ID `2056`.
3. A post-lock primary/secondary pairing report with passed review metrics.
4. An adjudicated GeoJSON manifest declaring qualified geometry, excluded uncertain lines, no future-map label leakage, and a reviewed-package SHA-256.
5. A qualified Ferrite mechanical-prior manifest tied to the same section and declared as `ltpp_observation_plus_ferrite_prior`.

Before that manifest can exist, the FWD acquisition package must pass
`ltpp_06_1253_fwd_ferrite_data_request_20260805.md`. Preview rows containing
only `PEAK_DEFL_1` do not pass this requirement.

The mechanical package must supply, rather than fabricate:

- `known_residual`;
- `u`, `v`;
- `psi_plus`, `psi_active`;
- `alpha_bar`, `f_alpha`, `g_stiffness`;
- `ell`, `Gc_base`;
- a snapshot hash and Ferrite runtime hash;
- the exact LTPP FWD dates used for calibration.
- raw `MON_DEFL_*` file hashes and release/data-dictionary provenance;
- panel-overlapping station/lane records from `MON_DEFL_LOC_INFO`;
- measured drop loads and complete multi-sensor basins;
- load-plate radius, sensor count, configuration-specific offsets and units;
- FWD quality exclusions, join audit, calibration/holdout split, and basin-fit
  uncertainty/non-identifiability report.

The package is hybrid evidence. It must never be described as entirely observed road mechanics.
No Ferrite execution is authorized while the FWD qualification decision is
`STOP_BEFORE_FERRITE`.

The current qualified state, if recorded as
`QUALIFIED_FOR_LAYERED_ELASTIC_DIAGNOSTIC_ONLY`, authorizes only the separately
preregistered axisymmetric basin diagnostic. It does not satisfy this real-route
mechanical-manifest gate until that diagnostic passes its frozen 2003 holdout
and a new manifest explicitly preserves the hybrid evidence boundary.

## Candidate authorization

For the currently frozen LTPP data:

| Candidate family | Status | Reason |
|---|---|---|
| Low temperature | eligible after preflight | Monthly temperature exists for 1991-2012 |
| Absolute temperature change | eligible after preflight | Monthly temperature exists |
| Monthly precipitation | eligible after library implementation | Monthly precipitation exists |
| Cumulative/rate traffic | disabled | Only five monthly snapshots in 1991-1992 |
| Moisture/humidity | disabled | No humidity or pavement-moisture observations |
| Seven-day rain | disabled | Monthly precipitation cannot be relabelled as seven-day rain |
| Traffic-temperature interaction | disabled | Continuous observed traffic is absent |
| Traffic-moisture interaction | disabled | Both required forcing histories are absent |

This means LTPP can support a climate-conditioned geometry route, not the full traffic-temperature-moisture claim. The latter still requires MnROAD or another same-asset forcing source.

## Fail-closed command

```bash
/Users/wenxiaofang/miniconda3/bin/python3 \
  "/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/SENS_tensile/run_ltpp_06_1253_real_route_preflight.py" \
  --grid-gate "/path/to/grid_gate_results.json" \
  --forcing-audit "/path/to/ltpp_06_1253_forcing_join_20260805.json" \
  --pairing-report "/path/to/pairing_report.json" \
  --adjudicated-manifest "/path/to/adjudicated_manifest.json" \
  --mechanical-manifest "/path/to/ferrite_mechanical_manifest.json" \
  --output "/path/to/real_route_preflight.json"
```

`STOP_BEFORE_FIELD_ADAPTER` is the expected decision until every mandatory input passes. No missing mechanical field may be replaced with zeros or constants merely to satisfy the existing snapshot schema.
